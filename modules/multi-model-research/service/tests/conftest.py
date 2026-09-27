"""Private, throwaway sidecar configuration; never read the operator's tokens."""
import json
import os
from pathlib import Path
import tempfile

_state = tempfile.TemporaryDirectory(prefix='notebook-research-tests-')
root=Path(_state.name)
(root/'.research-key').write_text('isolated-test-key')
(root/'config.json').write_text(json.dumps({'bridge_key_path':str(root/'missing-key'),'browser_transport':'extension'}))
os.environ['RESEARCH_ROOT']=str(root)
os.environ['RESEARCH_DATA_DIR']=str(root/'data')
os.environ['RESEARCH_EXTENSION_ROOT']=str(root/'spool')

def pytest_sessionfinish(session,exitstatus):
    _state.cleanup()
