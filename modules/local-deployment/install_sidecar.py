#!/usr/bin/env python3
"""Initialize private sidecar state. Does not install packages, start services or overwrite configuration."""
import argparse
import json
from pathlib import Path
import secrets
import shutil

SERVICES = {
    'multi-model-research': ('.research-key', 'RESEARCH_ROOT', 8320),
    'account-models': ('.bridge-key', 'ACCOUNT_BRIDGE_ROOT', 8317),
    'local-audio': ('.audio-key', 'LOCAL_AUDIO_ROOT', 8318),
    'natural-voice': ('.voice-key', 'NATURAL_VOICE_ROOT', 8319),
}

def initialize(module, destination):
    source=Path(__file__).resolve().parents[1]/module/'service'
    destination=destination.expanduser().resolve()
    destination.mkdir(parents=True,exist_ok=True,mode=0o700)
    key,env,port=SERVICES[module]
    path=destination/key
    if not path.exists():
        with path.open('x',opener=lambda name,flags: __import__('os').open(name,flags,0o600)) as stream:
            stream.write(secrets.token_urlsafe(48)+'\n')
    for name in ('config.example.json','voices.json'):
        target=destination/('config.json' if name=='config.example.json' else name)
        if (source/name).exists() and not target.exists():
            shutil.copy2(source/name,target);target.chmod(0o600)
    for name in ('tmp','models','voices','data'):
        (destination/name).mkdir(exist_ok=True,mode=0o700)
    print(json.dumps({'module':module,'private_root':str(destination),'root_environment_variable':env,'port':port,'source':str(source),'next':'Review config.json, install the pinned requirements in a separate venv, then use run_sidecar.py. Keys are never printed.'},indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('module',choices=SERVICES)
    parser.add_argument('--state',type=Path,required=True)
    args=parser.parse_args();initialize(args.module,args.state)
