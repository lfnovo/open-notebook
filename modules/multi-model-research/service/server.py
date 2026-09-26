"""Native research sidecar; the Open Notebook backend proxies this authenticated service."""
from __future__ import annotations
import asyncio
from contextlib import asynccontextmanager
from datetime import date
import hmac
import io
import json
import os
from pathlib import Path
import re
import uuid
import zipfile
from urllib.parse import urlparse
from fastapi import FastAPI, File, Form, Header, Request, UploadFile
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field
from typing import Literal
from browser_research import BrowserResearch
from browser_runtime import PROVIDERS, BrowserAttention, BrowserRuntime
from extension_research import ExtensionResearch, ExtensionRuntime
from engine import AccountProvider, Engine, NotebookSink, ServiceError
from importers import MAX_BYTES, MAX_TEXT, extract
from store import Store
from workflow import digest, prompt_for, ready
from evidence_protocol import VERSION, register, audit_appendix
from token_budget import TokenBudget
from packet_markdown import evidence_body

ROOT=Path(os.environ.get('RESEARCH_ROOT', Path(__file__).resolve().parent))
os.environ.setdefault('TIKTOKEN_CACHE_DIR',str(ROOT/'tiktoken-cache'))
STATE_ROOT=Path(os.environ.get('RESEARCH_DATA_DIR',str(ROOT/'data')))
KEY=(ROOT/'.research-key').read_text().strip()
ENGINE=None
BROWSER=None
CONFIG=json.loads((ROOT/'config.json').read_text())

@asynccontextmanager
async def lifespan(app):
    global ENGINE,BROWSER
    import tiktoken
    encoding=await asyncio.to_thread(tiktoken.get_encoding,'o200k_base')
    counter=lambda text:len(encoding.encode(text,disallowed_special=()))
    budget=TokenBudget(counter,CONFIG.get('token_margin'),CONFIG.get('forecast_output_tokens_by_round'))
    store=Store(STATE_ROOT);await store.open()
    # The browser is constructed now but only launched on first use, so starting the
    # service never opens a window by itself.
    if CONFIG.get('browser_transport','extension')=='extension':
        runtime=ExtensionRuntime()
        BROWSER=ExtensionResearch(runtime,STATE_ROOT,timeout=CONFIG.get('browser_timeout_seconds',7200))
    else:
        runtime=BrowserRuntime(STATE_ROOT.parent)
        BROWSER=BrowserResearch(runtime,STATE_ROOT,timeout=CONFIG.get('browser_timeout_seconds',7200))
    ENGINE=Engine(store,AccountProvider(Path(CONFIG['bridge_key_path']),CONFIG.get('account_timeout_seconds',3900)),NotebookSink(CONFIG.get('notebook_password','')),counter,CONFIG.get('max_input_tokens',90000),browser=BROWSER,budget=budget,input_limits=CONFIG.get('provider_input_limits'),compaction=CONFIG.get('context_compaction',True),compaction_headroom=CONFIG.get('compaction_headroom',.05),segmented=CONFIG.get('segmented_synthesis',True))
    await ENGINE.recover()
    yield
    await ENGINE.close();await store.close()

app=FastAPI(lifespan=lifespan,docs_url=None,redoc_url=None)

@app.middleware('http')
async def authenticate(request:Request,call_next):
    if request.url.path!='/health' and not hmac.compare_digest(request.headers.get('authorization',''),'Bearer '+KEY):
        return JSONResponse({'detail':'Yerel araştırma servisi kimlik doğrulaması gerekli.'},status_code=401)
    length=request.headers.get('content-length')
    if length and (not length.isdigit() or int(length)>32*1024*1024):return Response(status_code=413)
    response=await call_next(request);response.headers['Cache-Control']='no-store';return response

@app.exception_handler(ServiceError)
async def service_error(request,exc):return JSONResponse({'detail':str(exc)},status_code=exc.status)

@app.get('/health')
async def health():
    browser=BROWSER.runtime if BROWSER else None
    return {'status':'healthy' if ENGINE else 'loading','account_review':'v1','research_controls':'v1','stage_controls':'v1','active_synthesis':len(ENGINE.tasks)+len(ENGINE.control_tasks) if ENGINE else 0,
            'pending_exports':len(ENGINE.background) if ENGINE else 0,
            'mode':'browser_research' if BROWSER else 'web_research_imports',
            'browser_transport':getattr(browser,'transport','playwright') if browser else None,
            'browser_open':bool(browser and browser.context),'providers':list(PROVIDERS)}

@app.get('/browser/status')
async def browser_status(deep:bool=False):
    if not BROWSER:raise ServiceError('Tarayıcı araştırma bağlantısı yapılandırılmadı.',503)
    results=[]
    for provider in PROVIDERS:
        results.append(await BROWSER.runtime.status(provider,deep=deep))
    return {'checked_at':date.today().isoformat(),'deep':deep,'connections':results}

@app.get('/accounts/status')
async def accounts_status():
    import httpx
    async with httpx.AsyncClient(timeout=10) as client:
        response=await client.get('http://127.0.0.1:8317/health')
        response.raise_for_status()
        return {'profiles':response.json().get('preliminary',{}),'queues':response.json().get('queues',{})}

@app.post('/browser/login')
async def browser_login():
    """Launch an automation-free Chrome on the research profile for the user to sign in.

    Providers reject sign-in from an automation-controlled browser, so this deliberately
    does NOT reuse the Playwright context. No credentials are handled by this service.
    """
    if not BROWSER:raise ServiceError('Tarayıcı araştırma bağlantısı yapılandırılmadı.',503)
    if ENGINE and ENGINE.tasks:raise ServiceError('Çalışan araştırma varken giriş penceresi açılmaz.',409)
    try:result=await BROWSER.runtime.open_login_browser()
    except BrowserAttention as exc:raise ServiceError(str(exc),409)
    if result.get('transport')=='extension':
        return dict(result,message='Chrome eklentisi bağlı. Günlük Chrome hesapların görev pencerelerinde kullanılır; parola bu servise girilmez. Chrome açık kalmalıdır.')
    return dict(result,message='Otomasyon bağlantısı olmayan normal Chrome açıldı. Üç hesaba giriş '
                'yapın, güvenlik doğrulamalarını tamamlayın, sonra o pencereyi tamamen kapatın '
                '(Cmd+Q). Parola bu servise girilmez ve saklanmaz.')

@app.get('/browser/login')
async def browser_login_state():
    if not BROWSER:raise ServiceError('Tarayıcı araştırma bağlantısı yapılandırılmadı.',503)
    return {'login_browser_pid':BROWSER.runtime.login_browser_pid()}

@app.post('/browser/close')
async def browser_close():
    if not BROWSER:raise ServiceError('Tarayıcı araştırma bağlantısı yapılandırılmadı.',503)
    if ENGINE and any(k for k in ENGINE.tasks):raise ServiceError('Çalışan araştırma varken tarayıcı kapatılmaz.',409)
    await BROWSER.runtime.close()
    return {'closed':getattr(BROWSER.runtime,'transport',None)!='extension',
            'message':'Chrome bağlantısını eklenti panelinden durdurabilirsiniz.' if getattr(BROWSER.runtime,'transport',None)=='extension' else ''}

class RunCreate(BaseModel):
    question:str=Field(min_length=5,max_length=12000)
    scope:str=Field(default='',max_length=30000)
    language:str=Field(default='Türkçe',min_length=2,max_length=60)
    auto_synthesize:bool=True
    preliminary:bool=True
    account_review:bool=True
    execution_mode:Literal['imports','browser']='imports'
    as_of:date=Field(default_factory=date.today)
    notebook_id:str|None=None

@app.get('/runs')
async def list_runs():
    result=[]
    for run in await ENGINE.store.all():
        result.append({k:run[k] for k in ('id','question','scope','created_at','updated_at','status','notebook_id')}
                      | {'completed':sum(s['status']=='completed' for s in run['stages']),'total':len(run['stages']),'preliminary':run.get('preliminary',False)})
    return result

@app.post('/runs',status_code=201)
async def create_run(body:RunCreate,idempotency_key:str=Header(alias='Idempotency-Key')):
    if not re.fullmatch(r'[a-zA-Z0-9_-]{8,100}',idempotency_key):raise ServiceError('Geçerli bir istek kimliği gerekli.')
    if not body.question.strip():raise ServiceError('Araştırma sorusu boş olamaz.')
    if body.notebook_id and not re.fullmatch(r'notebook:[a-zA-Z0-9]+',body.notebook_id):raise ServiceError('Geçersiz not defteri kimliği.')
    if body.execution_mode=='browser' and not BROWSER:raise ServiceError('Tarayıcı araştırma bağlantısı yapılandırılmadı.',503)
    return await ENGINE.create(body.model_dump(mode='json'),idempotency_key)

@app.get('/runs/{run_id}')
async def get_run(run_id:str):return await ENGINE.get(run_id)

@app.get('/runs/{run_id}/context-plan')
async def context_plan(run_id:str):return await ENGINE.context_plan(run_id)

@app.get('/runs/{run_id}/stages/{stage_id}/packet')
async def packet(run_id:str,stage_id:str):return await ENGINE.packet(run_id,stage_id)

@app.get('/runs/{run_id}/stages/{stage_id}/evidence')
async def common_evidence(run_id:str,stage_id:str):
    value=await ENGINE.packet(run_id,stage_id)
    body,fmt=evidence_body(value['prompt'])
    name='evidence-'+value['evidence_packet']['sha256'][:12]+('.md' if fmt=='markdown' else '.json')
    return Response(body,media_type='text/markdown' if fmt=='markdown' else 'application/json',
                    headers={'Content-Disposition':'attachment; filename="'+name+'"'})

@app.post('/runs/{run_id}/stages/{stage_id}/import')
async def import_report(run_id:str,stage_id:str,text:str=Form(''),origin_url:str=Form(''),
                        packet_sha:str=Form(...),file:UploadFile|None=File(None),
                        evidence_files:list[UploadFile]|None=File(None),researched_at:date|None=Form(None)):
    if origin_url and urlparse(origin_url).scheme not in ('http','https'):raise ServiceError('Rapor adresi http veya https olmalı.')
    if len(origin_url)>2000:raise ServiceError('Rapor adresi çok uzun.')
    originals=[];evidence=[];total=0
    async def read(upload):
        nonlocal total
        raw=await upload.read(MAX_BYTES+1);total+=len(raw)
        if len(raw)>MAX_BYTES or total>24*1024*1024:raise ServiceError('Dosya boyutu sınırı aşıldı.',413)
        name=Path(upload.filename or 'report.txt').name
        try:content=await asyncio.to_thread(extract,name,raw)
        except ValueError as exc:raise ServiceError(str(exc))
        except Exception:raise ServiceError('Belge okunamadı. Markdown veya metin biçimini deneyin.')
        originals.append((name,raw));return name,content
    if file:
        _,file_text=await read(file)
        if text.strip():raise ServiceError('Rapor için ya dosya yükleyin ya metin yapıştırın; ikisini birlikte göndermeyin.')
        text=file_text
    if len(text.strip())<40:raise ServiceError('Rapor en az 40 karakter içermeli.')
    if len(text.encode())>MAX_TEXT:raise ServiceError('Rapor metni en fazla 4 MB olabilir.',413)
    if len(evidence_files or [])>6:raise ServiceError('En fazla altı ek kanıt dosyası yükleyebilirsiniz.')
    for upload in evidence_files or []:
        name,content=await read(upload);evidence.append({'name':name,'content':content,'sha256':digest(content)})
    return await ENGINE.import_report(run_id,stage_id,text,evidence,origin_url,packet_sha,originals,researched_at.isoformat() if researched_at else None)

class ControlRequest(BaseModel):
    expected_state: dict | None = None
    # Maintenance can release a global pause without retrying unrelated failures.
    retry_attention: bool = True

@app.post('/runs/{run_id}/stages/{stage_id}/retry')
async def retry_stage(run_id:str,stage_id:str,body:ControlRequest | None=None):
    """User-triggered retry of one stalled stage; also resets its backoff schedule."""
    return await ENGINE.retry_stage(run_id,stage_id,body.expected_state if body else None)

@app.post('/runs/{run_id}/stages/{stage_id}/actions/{action}')
async def stage_action(run_id:str,stage_id:str,action:str,body:ControlRequest):
    if body.expected_state is None:raise ServiceError('Aşama etkileri güncel durumla onaylanmalıdır.',409)
    return await ENGINE.stage_action(run_id,stage_id,action,body.expected_state)

@app.post('/runs/{run_id}/{action}')
async def action(run_id:str,action:str,body:ControlRequest | None=None):
    if action=='sync':return await ENGINE.sync(run_id)
    if action=='automate' and not BROWSER:raise ServiceError('Chrome araştırma bağlantısı yapılandırılmadı.',503)
    return await ENGINE.action(run_id,action,body.expected_state if body else None,
                              retry_attention=body.retry_attention if body else True)

@app.get('/runs/{run_id}/export')
async def export(run_id:str):
    run=await ENGINE.get(run_id);stream=io.BytesIO()
    shared_files=set()
    with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('research.json',json.dumps(run,ensure_ascii=False,indent=2))
        archive.writestr('question.md','# '+run['question']+'\n\n'+run['scope'])
        if run.get('prompt_version',1)>=VERSION:
            archive.writestr('evidence-register.json',json.dumps(register(run['stages']),ensure_ascii=False,indent=2))
        for stage in run['stages']:
            journal=ENGINE.input_path(run,stage).parent/'segmented-journal.json'
            if journal.is_file():archive.write(journal,stage['id']+'/segmented-journal.json')
            snapshots=ENGINE.input_path(run,stage).parent/'source-snapshots'
            if snapshots.is_dir():
                for snapshot in sorted(snapshots.iterdir()):
                    if snapshot.is_file() and not snapshot.is_symlink() and re.fullmatch(r'[a-f0-9]{64}\.(json|body)',snapshot.name):
                        archive.write(snapshot,stage['id']+'/source-snapshots/'+snapshot.name)
            if ready(run,stage):
                prompt=ENGINE.input_prompt(run,stage)
                archive.writestr(stage['id']+'/input-packet.md',prompt)
                body,fmt=evidence_body(prompt)
                name=f'round-{stage["round"]}/evidence-{digest(body)[:12]}.'+('md' if fmt=='markdown' else 'json')
                if name not in shared_files:
                    archive.writestr(name,body);shared_files.add(name)
            if stage['report']:
                archive.writestr(stage['id']+'/report.md',stage['report']['content'])
                if stage.get('evidence_audit'):
                    archive.writestr(stage['id']+'/evidence-audit.json',json.dumps(stage['evidence_audit'],ensure_ascii=False,indent=2))
                    archive.writestr(stage['id']+'/local-audit.md',audit_appendix(run,stage))
                for i,item in enumerate(stage['report'].get('evidence',[])):
                    archive.writestr(stage['id']+'/evidence-'+str(i)+'.txt',item['content'])
                for item in stage['report'].get('original_files',[]):
                    path=STATE_ROOT/'artifacts'/run_id/stage['id']/item['file']
                    if path.is_file():archive.write(path,stage['id']+'/original-'+item['file'])
                # Browser jobs keep their own report, raw HTML and submission journal.
                for item in stage['report'].get('browser_files',[]):
                    path=STATE_ROOT/item['path']
                    if path.is_file() and STATE_ROOT in path.resolve().parents:
                        archive.write(path,stage['id']+'/browser-'+item['name'])
    return Response(stream.getvalue(),media_type='application/zip',
                    headers={'Content-Disposition':'attachment; filename="research-'+run_id[:8]+'.zip"'})

if __name__=='__main__':
    import uvicorn
    uvicorn.run(app,host='127.0.0.1',port=8320,access_log=False,log_level='warning')
