"""Idempotent native sidecar installer. Existing scope/configuration is authoritative."""
from pathlib import Path
import argparse,json,os,plistlib,secrets,shutil,subprocess,sys
FILES=('catalog.py','query.py','retrieval.py','server.py','extract_document.py','ocr.swift','requirements.txt','config.example.json','install.py')

def merged_config(existing,home):
    result=dict(existing)
    defaults={'root':str(home/'Documents'),'exclude':[],'embedding_model':'embeddinggemma:300m-qat-q8_0','scan_interval':600,'max_content_bytes':256*1024*1024,'document_timeout_seconds':240}
    for key,value in defaults.items():result.setdefault(key,value)
    return result

def install(root,source):
    root.mkdir(parents=True,exist_ok=True,mode=0o700)
    config=root/'config.json'
    value=merged_config(json.loads(config.read_text()) if config.exists() else {},Path.home())
    for name in FILES:
        if (source/name).resolve()!=(root/name).resolve():shutil.copy2(source/name,root/name)
    config.write_text(json.dumps(value,indent=2)+'\n');config.chmod(0o600)
    key=root/'.key'
    if not key.exists():key.write_text(secrets.token_urlsafe(40));key.chmod(0o600)
    python=root/'venv/bin/python'
    if not python.exists():subprocess.run([sys.executable,'-m','venv',str(root/'venv')],check=True)
    subprocess.run([str(python),'-m','pip','install','-r',str(root/'requirements.txt')],check=True)
    if sys.platform=='darwin':subprocess.run(['/usr/bin/swiftc',str(root/'ocr.swift'),'-o',str(root/'ocr')],check=True)
    plist=Path.home()/'Library/LaunchAgents/local.open-notebook.files.plist';plist.parent.mkdir(exist_ok=True)
    plist.write_bytes(plistlib.dumps({'Label':'local.open-notebook.files','ProgramArguments':[str(python),'-m','uvicorn','server:app','--host','0.0.0.0','--port','8322'],'WorkingDirectory':str(root),'EnvironmentVariables':{'LOCAL_FILES_HOME':str(root)},'RunAtLoad':True,'KeepAlive':True,'StandardOutPath':str(root/'stdout.log'),'StandardErrorPath':str(root/'stderr.log'),'Nice':10,'ThrottleInterval':10}));plist.chmod(0o600)
    # Loading/restarting is an explicit deployment step, never kill ongoing indexing here.
    print('Files installed; existing scope and credentials preserved. LaunchAgent prepared.')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,default=Path.home()/'Library/Application Support/OpenNotebookFiles');args=parser.parse_args();install(args.root,Path(__file__).parent)
