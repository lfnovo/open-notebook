"""Install the private native host for this installation's Chrome extension."""
import json
import os
import argparse
import re
from pathlib import Path
import shlex
import shutil
from extension_bridge import ORIGIN


def install(extension_id=None):
    extension_id=extension_id or ORIGIN.split('://')[1].rstrip('/')
    if not re.fullmatch(r'[a-p]{32}',extension_id):raise ValueError('Invalid extension ID')
    origin='chrome-extension://'+extension_id+'/'
    source=Path(__file__).resolve().parent
    runtime=Path(os.environ.get('RESEARCH_ROOT', Path.home()/'Library/Application Support/OpenNotebookResearch'))
    python=runtime/'venv/bin/python'
    if not python.is_file():raise RuntimeError('Araştırma Python ortamı bulunamadı.')
    target=runtime/'extension-host';target.mkdir(parents=True,exist_ok=True,mode=0o700)
    target.chmod(0o700)
    shutil.copy2(source/'extension_bridge.py',target/'extension_bridge.py')
    (target/'extension_bridge.py').chmod(0o600)
    launcher=target/'native-host'
    launcher.write_text('#!/bin/sh\nexport RESEARCH_EXTENSION_ROOT='+shlex.quote(str(runtime/'extension-bridge'))+'\nexport RESEARCH_EXTENSION_ID='+shlex.quote(extension_id)+'\nexec '+shlex.quote(str(python))+' '+shlex.quote(str(target/'extension_bridge.py'))+' "$@"\n')
    launcher.chmod(0o700)
    hosts=Path.home()/'Library/Application Support/Google/Chrome/NativeMessagingHosts'
    hosts.mkdir(parents=True,exist_ok=True)
    manifest={'name':'com.open_notebook.research','description':'Open Notebook local research connection',
              'path':str(launcher),'type':'stdio','allowed_origins':[origin]}
    path=hosts/'com.open_notebook.research.json'
    path.write_text(json.dumps(manifest,indent=2)+'\n');path.chmod(0o600)
    config=runtime/'config.json'
    if config.exists():
        settings=json.loads(config.read_text());settings['extension_id']=extension_id
        config.write_text(json.dumps(settings,indent=2)+'\n');config.chmod(0o600)
    print('Chrome native host installed for '+origin+'; restart an idle research service to use this ID.')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--extension-id')
    install(parser.parse_args().extension_id)
