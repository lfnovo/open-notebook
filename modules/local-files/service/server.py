"""Authenticated host service. Indexing is local and incremental, never an upload."""
from contextlib import asynccontextmanager
import asyncio, hmac, json, os, threading, time
from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.responses import Response
from pydantic import BaseModel, Field
from catalog import Catalog

ROOT=Path(os.environ.get('LOCAL_FILES_HOME',str(Path.home()/'Library/Application Support/OpenNotebookFiles')))
CONFIG=json.loads((ROOT/'config.json').read_text());KEY=(ROOT/'.key').read_text().strip()
catalog=Catalog(ROOT,CONFIG);stop=threading.Event();enabled=threading.Event();dirty=set();dirty_lock=threading.Lock();rescan=threading.Event()
if not (ROOT/'enabled.json').exists() or json.loads((ROOT/'enabled.json').read_text()):enabled.set()
events_seen=0;WORKERS=[]
catalog.active=lambda:enabled.is_set() and not stop.is_set()

def authorize(authorization:str=Header(default='')):
    if not hmac.compare_digest(authorization,'Bearer '+KEY):raise HTTPException(401,'Authentication required')

def scanner():
    while not stop.is_set():
        if enabled.is_set():catalog.scan()
        rescan.wait(CONFIG.get('scan_interval',600));rescan.clear()

def extract_worker():
    while not stop.is_set():
        if not enabled.is_set():stop.wait(1);continue
        with dirty_lock:paths=list(dirty);dirty.clear()
        for path in paths:
            try:
                if catalog.allowed(path):catalog.change(path)
            except Exception as exc:
                catalog.progress['error']='File update: '+type(exc).__name__;rescan.set()
        try:worked=catalog.process_one()
        except Exception as exc:catalog.progress['error']=type(exc).__name__;worked=False
        stop.wait(.01 if worked else 1)

def vector_worker():
    try:catalog.load_vectors()
    except Exception as exc:catalog.vector_error=type(exc).__name__;return
    while not stop.is_set():
        try:worked=enabled.is_set() and catalog.embed_batch()
        except Exception as exc:catalog.vector_error=type(exc).__name__;worked=False
        stop.wait(.1 if worked else 10)

def cleanup_worker():
    while not stop.is_set():
        if enabled.is_set():
            try:catalog.collect_garbage(20000)
            except Exception as exc:catalog.progress['error']='Cleanup: '+type(exc).__name__
        stop.wait(2)

@asynccontextmanager
async def lifespan(app):
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    class Changes(FileSystemEventHandler):
        def on_any_event(self,event):
            global events_seen
            events_seen+=1
            if not enabled.is_set() or event.event_type not in ('created','modified','deleted','moved'):return
            with dirty_lock:
                for p in (event.src_path,getattr(event,'dest_path',None)):
                    if p and catalog.allowed(p):dirty.add(p)
                if len(dirty)>10000:dirty.clear();rescan.set()
            if event.is_directory and event.event_type in ('created','deleted','moved') and any(p and catalog.allowed(p) for p in (event.src_path,getattr(event,'dest_path',None))):rescan.set()
    watcher=Observer();watcher.schedule(Changes(),str(catalog.root),recursive=True);watcher.start()
    threads=[threading.Thread(target=fn,daemon=True) for fn in (scanner,extract_worker,vector_worker,cleanup_worker)]
    WORKERS.extend(threads)
    for thread in threads:thread.start()
    yield
    stop.set();rescan.set();watcher.stop();watcher.join(timeout=5)

app=FastAPI(lifespan=lifespan,dependencies=[Depends(authorize)])
class Search(BaseModel):
    query:str=Field(min_length=1,max_length=2000)
    limit:int=Field(default=20,ge=1,le=60)
class Control(BaseModel):enabled:bool
@app.get('/health')
def health():return {'status':'healthy','enabled':enabled.is_set()}
@app.get('/status')
def status():return dict(catalog.status(),phase=catalog.progress['phase'] if enabled.is_set() else 'paused',enabled=enabled.is_set(),events_seen=events_seen,pending_events=len(dirty),workers_alive=[t.is_alive() for t in WORKERS])
@app.post('/control')
def control(body:Control):
    saved=ROOT/'enabled.tmp';saved.write_text(json.dumps(body.enabled));saved.chmod(0o600);saved.replace(ROOT/'enabled.json')
    if body.enabled:enabled.set();rescan.set()
    else:enabled.clear()
    return health()
@app.post('/refresh')
def refresh():rescan.set();return status()
@app.post('/search')
async def search(body:Search):
    if not enabled.is_set():raise HTTPException(409,'File index is paused')
    return await asyncio.to_thread(catalog.search,body.query,body.limit)
@app.get('/files/{file_id}')
def file_info(file_id:int):
    with catalog.db() as db:row=db.execute('SELECT * FROM files WHERE id=?',(file_id,)).fetchone()
    if not row or not catalog.allowed(row['path']):raise HTTPException(404,'File not available')
    try:file=catalog.open_file(row['path'])
    except (OSError,ValueError):raise HTTPException(404,'File no longer readable')
    from fastapi.responses import StreamingResponse
    from starlette.background import BackgroundTask
    def chunks():
        try:
            while data:=file.read(1024*1024):yield data
        finally:file.close()
    return StreamingResponse(chunks(),background=BackgroundTask(file.close),media_type='application/octet-stream',headers={'Content-Disposition':"attachment; filename*=UTF-8''"+__import__('urllib.parse',fromlist=['quote']).quote(row['name']), 'X-Content-Type-Options':'nosniff'})
