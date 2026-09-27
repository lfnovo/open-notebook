#!/usr/bin/env python3
"""Run an installed local service with an explicit interpreter and private state."""
import argparse
import os
import json
from pathlib import Path
from install_sidecar import SERVICES

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('module',choices=SERVICES)
    parser.add_argument('--state',type=Path,required=True)
    parser.add_argument('--python',type=Path,required=True)
    args=parser.parse_args()
    state=args.state.expanduser().resolve();python=args.python.expanduser().resolve()
    key,env,port=SERVICES[args.module]
    if not (state/key).is_file() or not python.is_file():
        parser.error('Initialize private state and provide its venv Python first.')
    os.environ[env]=str(state)
    if args.module=='multi-model-research':
        os.environ['RESEARCH_EXTENSION_ROOT']=str(state/'extension-bridge')
        settings=json.loads((state/'config.json').read_text())
        if settings.get('extension_id'):os.environ['RESEARCH_EXTENSION_ID']=settings['extension_id']
    source=Path(__file__).resolve().parents[1]/args.module/'service'
    os.chdir(source)
    command=[str(python),str(source/'server.py')] if args.module=='account-models' else [str(python),'-m','uvicorn','server:app','--host','127.0.0.1','--port',str(port)]
    os.execv(str(python),command)
