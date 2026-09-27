"""Read-only account discovery; ranked, maximum-effort preliminary research.
Calibrated synthesis remains pinned to its measured model/runtime. No API keys.
"""
import json,math,os,re,selectors,signal,subprocess,threading,time
from datetime import datetime, timezone
from pathlib import Path
EFFORTS=['none','minimal','low','medium','high','xhigh','max','ultra']
class SelectionError(Exception):
    def __init__(self,message,status=503,retry_at=None):super().__init__(message);self.status=status;self.retry_at=retry_at

def quota_reset_at(message):
    """Parse only a terminal provider error, never echoed user/report content."""
    match=re.search(r'Resets in\s+((?:\d+(?:\.\d+)?[hms])+)',message,re.I)
    if not match:return None
    seconds=sum(float(n)*{'h':3600,'m':60,'s':1}[unit.lower()] for n,unit in re.findall(r'(\d+(?:\.\d+)?)([hms])',match[1],re.I))
    return time.time()+seconds if 0<seconds<=366*86400 else None

def rpc(executable,args,first,after=None,timeout=15):
    p=subprocess.Popen([executable,*args],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
                       text=True,cwd='/tmp',start_new_session=True)
    selector=selectors.DefaultSelector();selector.register(p.stdout,selectors.EVENT_READ);results={}
    def send(value):p.stdin.write(json.dumps(value)+'\n');p.stdin.flush()
    try:
        send(first);deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            if not selector.select(.2):continue
            line=p.stdout.readline()
            if not line:break
            try:value=json.loads(line)
            except ValueError:continue
            if value.get('type')=='control_response':return value.get('response',{}).get('response',{})
            if value.get('id')==1:
                for request in after or []:send(request)
            elif value.get('id') in (2,3):
                results[value['id']]=value.get('result',{})
                if len(results)==2:return results
        raise SelectionError('Account model discovery timed out; no research prompt was sent.')
    finally:
        selector.close()
        try:os.killpg(p.pid,signal.SIGTERM);p.wait(timeout=2)
        except (ProcessLookupError,subprocess.TimeoutExpired):
            if p.poll() is None:os.killpg(p.pid,signal.SIGKILL);p.wait()

def discover(provider,executable):
    if provider=='codex':
        data=rpc(executable,['-c','mcp_servers={}','app-server','--stdio'],{'id':1,'method':'initialize','params':{'clientInfo':{'name':'open-notebook-model-policy','version':'1'}}},[
            {'method':'initialized'},{'id':2,'method':'model/list','params':{'includeHidden':False}},{'id':3,'method':'account/rateLimits/read'}])
        models=[{'model':m['model'],'efforts':[e['reasoningEffort'] for e in m.get('supportedReasoningEfforts',[])],
                 'description':m.get('description','')} for m in data.get(2,{}).get('data',[]) if not m.get('hidden')]
        limits=data.get(3,{})
        # Only the account-wide Codex pool is applicable to every candidate.
        pool=limits.get('rateLimitsByLimitId',{}).get('codex') or limits.get('rateLimits') or {}
        blocked=bool(pool.get('spendControlReached')) or any(isinstance(pool.get(k),dict) and pool[k].get('usedPercent',0)>=100 and pool[k].get('resetsAt',time.time()+1)>time.time() for k in ('primary','secondary'))
        return {'models':models,'quota':'exhausted' if blocked else 'available' if pool else 'unknown'}
    if provider=='claude':
        data=rpc(executable,['--print','--input-format','stream-json','--output-format','stream-json','--verbose','--strict-mcp-config','--mcp-config','{"mcpServers":{}}','--setting-sources','','--no-chrome','--no-session-persistence','--tools',''],{'type':'control_request','request_id':'models','request':{'subtype':'initialize'}})
        models=[{'model':m.get('resolvedModel') or m['value'],'efforts':m.get('supportedEffortLevels',['high']),
                 'description':m.get('description','')} for m in data.get('models',[])]
        return {'models':models,'quota':'unknown'}
    value=subprocess.run([executable,'models'],capture_output=True,text=True,timeout=20,cwd='/tmp')
    if value.returncode:raise SelectionError('Gemini account models could not be read; no research prompt was sent.')
    models=[{'model':line.split()[0],'efforts':['low','medium','high'],'description':line} for line in value.stdout.splitlines() if re.match(r'^gemini-[\w.-]+\s',line)]
    return {'models':models,'quota':'unknown'}

def ranking(model):
    name=model['model'];versions=tuple(map(int,re.findall(r'\d+',name.split('[')[0])))
    family=next((weight for label,weight in [('astra',100),('fable',100),('opus',80),('pro',80),('sol',70),('sonnet',60),('terra',60),('flash',40),('luna',30),('haiku',20)] if label in name),0)
    return (family,versions,'high' in name)

class ModelPolicy:
    def __init__(self,executables,state=None):
        self.executables=executables;self.state=Path(state) if state else None;self.lock=threading.RLock();self.cache={};self.cooldowns={};self.discovery_locks={provider:threading.RLock() for provider in ('codex','claude','gemini')}
        if self.state and self.state.exists():
            try:self.cooldowns=json.loads(self.state.read_text())
            except (ValueError,OSError):pass
    def limited(self,provider,retry_at=None):
        with self.lock:
            until=retry_at if isinstance(retry_at,(int,float)) and math.isfinite(retry_at) and time.time()<retry_at<=time.time()+366*86400 else 0
            self.cooldowns[provider]=max(self.cooldowns.get(provider,0),time.time()+60,until)
            if self.state:
                self.state.parent.mkdir(exist_ok=True);temp=self.state.with_suffix('.tmp');temp.write_text(json.dumps(self.cooldowns));os.chmod(temp,0o600);temp.replace(self.state)
    def check_quota(self,provider):
        with self.lock:
            until=self.cooldowns.get(provider,0)
            if until>time.time():
                stamp=datetime.fromtimestamp(until,timezone.utc).isoformat()
                raise SelectionError('Account quota is exhausted. Retry after '+stamp+'; no replacement request was sent.',429,until)
    def choose(self,spec,excluded=()):
        provider=spec['provider']
        with self.discovery_locks[provider]:
            self.check_quota(provider)
            stamp,data=self.cache.get(provider,(0,None))
            if time.time()-stamp>60 or data is None:
                try:data=discover(provider,self.executables[provider])
                except SelectionError:raise
                except Exception:raise SelectionError('Account model availability could not be verified. No research prompt was sent.') from None
                stamp=time.time();self.cache[provider]=(stamp,data)
            if data['quota']=='exhausted':raise SelectionError('Account quota is exhausted; wait for the provider reset.',429)
            unique={m['model']:m for m in data['models'] if m['model'] not in excluded}
            choices=sorted(unique.values(),key=ranking,reverse=True)
            if not choices:raise SelectionError('No available research model was found for this account.')
            selected=choices[0];efforts=[e for e in selected['efforts'] if e in EFFORTS]
            if not efforts:raise SelectionError('Maximum supported reasoning effort could not be verified.')
            return {'model':selected['model'],'effort':max(efforts,key=EFFORTS.index),'policy':'ranked-live-account-catalog-v1',
                    'quota':data['quota'],'checked_at':stamp if stamp else time.time(),'candidates':[c['model'] for c in choices]}
