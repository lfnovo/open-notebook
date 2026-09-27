import io
import json
from pathlib import Path
import sys
import uuid
import zipfile
import httpx
import pytest
sys.path.insert(0,str(Path(__file__).parents[1]))
import server
from test_workflow import engine

@pytest.mark.asyncio
async def test_authenticated_multipart_dates_and_lossless_export(engine,monkeypatch):
    monkeypatch.setattr(server,'ENGINE',engine)
    monkeypatch.setattr(server,'STATE_ROOT',engine.store.root)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app),base_url='http://test') as client:
        assert (await client.get('/health')).status_code==200
        assert (await client.get('/runs')).status_code==401
        client.headers['Authorization']='Bearer '+server.KEY
        data={'preliminary':False,'question':'Test research workspace with primary evidence','auto_synthesize':False,'as_of':'2026-09-21'}
        headers={'Idempotency-Key':uuid.uuid4().hex}
        response=await client.post('/runs',json=data,headers=headers);assert response.status_code==201,response.text
        run=response.json();rid=run['id']
        assert (await client.post('/runs',json=data,headers=headers)).json()['id']==rid
        assert (await client.get(f'/runs/{rid}/stages/review_claude/packet')).status_code==409
        packet=(await client.get(f'/runs/{rid}/stages/research_gemini/packet')).json()
        report='Exact report text with Turkish characters: çğıöşü and evidence https://example.org/source'
        form={'packet_sha':packet['sha256'],'researched_at':'2026-09-20'}
        response=await client.post(f'/runs/{rid}/stages/research_gemini/import',data=form,files={'file':('original.md',report.encode(),'text/markdown'),'evidence_files':('evidence.txt',b'Exact primary evidence','text/plain')})
        assert response.status_code==200,response.text
        stage=response.json()['stages'][0];assert stage['report']['researched_at']=='2026-09-20'
        response=await client.get(f'/runs/{rid}/export');assert response.status_code==200
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            assert archive.read('research_gemini/original-0.md')==report.encode()
            assert archive.read('research_gemini/report.md').decode()==report
            assert archive.read('research_gemini/evidence-0.txt')==b'Exact primary evidence'
            assert json.loads(archive.read('research.json'))['as_of']=='2026-09-21'
            assert json.loads(archive.read('research.json'))['prompt_version']==2
            register=json.loads(archive.read('evidence-register.json'))
            assert register['sources'][0]['url']=='https://example.org/source'
            assert 'İnceleme gerekli' in archive.read('research_gemini/local-audit.md').decode()
        invalid=await client.post(f'/runs/{rid}/stages/research_chatgpt/import',data={'text':report,'packet_sha':'wrong','researched_at':'yesterday'})
        assert invalid.status_code==422
        duplicate=await client.post(f'/runs/{rid}/stages/research_chatgpt/import',data={'text':report,'packet_sha':packet['sha256']},files={'file':('r.txt',report.encode())})
        assert duplicate.status_code==400


class StubRuntime:
    """Reports connection state without opening anything."""

    def __init__(self, results):
        self.results = results
        self.deep_calls = []
        self.opened = 0
        self.playwright_started = False
        self.context = None

    async def status(self, provider, deep=False):
        self.deep_calls.append(deep)
        return self.results[provider]

    async def start(self):
        # Reaching this from the sign-in path would be the bug: providers reject
        # sign-in from an automation-controlled browser.
        self.playwright_started = True

    def login_browser_pid(self):
        return 4242 if self.opened else None

    async def open_login_browser(self):
        self.opened += 1
        return {'pid': 4242, 'already_open': False}

    async def close(self):
        self.context = None


class StubBrowserService:
    def __init__(self, runtime):
        self.runtime = runtime


@pytest.mark.asyncio
async def test_browser_endpoints_report_state_and_never_leak_credentials(engine, monkeypatch):
    runtime = StubRuntime({
        'ChatGPT': {'provider': 'ChatGPT', 'status': 'login_required', 'message': 'Giriş gerekli.'},
        'Gemini': {'provider': 'Gemini', 'status': 'connected', 'message': 'Oturum açık.'},
        'Claude': {'provider': 'Claude', 'status': 'verification_required', 'message': 'Doğrulama gerekli.'},
    })
    monkeypatch.setattr(server, 'ENGINE', engine)
    monkeypatch.setattr(server, 'BROWSER', StubBrowserService(runtime))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app), base_url='http://test') as client:
        assert (await client.get('/browser/status')).status_code == 401
        client.headers['Authorization'] = 'Bearer ' + server.KEY
        body = (await client.get('/browser/status')).json()
        assert [c['status'] for c in body['connections']] == ['login_required', 'connected', 'verification_required']
        assert runtime.deep_calls == [False, False, False]
        deep = (await client.get('/browser/status', params={'deep': True})).json()
        assert deep['deep'] is True and runtime.deep_calls[-1] is True
        opened = (await client.post('/browser/login')).json()
        assert runtime.opened == 1 and 'parola' in opened['message'].lower()
        # The sign-in window must be a plain Chrome, never the Playwright context.
        assert runtime.playwright_started is False
        assert opened['pid'] == 4242
        assert (await client.get('/browser/login')).json()['login_browser_pid'] == 4242
        # A browser run needs the browser wired up; without it the request is refused.
        run = (await client.post('/runs', json={'question': 'Tarayıcı kipinde tek soru', 'execution_mode': 'browser'},
                                 headers={'Idempotency-Key': uuid.uuid4().hex}))
        assert run.status_code == 201 and run.json()['execution_mode'] == 'browser'
        monkeypatch.setattr(server, 'BROWSER', None)
        refused = await client.post('/runs', json={'question': 'Tarayıcı kapalıyken', 'execution_mode': 'browser'},
                                    headers={'Idempotency-Key': uuid.uuid4().hex})
        assert refused.status_code == 503
