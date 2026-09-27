import os
from pathlib import Path
import shutil
import tempfile

_state=tempfile.TemporaryDirectory(prefix='notebook-account-tests-')
root=Path(_state.name)
shutil.copy2(Path(__file__).parent/'config.example.json',root/'config.json')
(root/'.bridge-key').write_text('isolated-test-key')
os.environ['ACCOUNT_BRIDGE_ROOT']=str(root)

def pytest_sessionfinish(session,exitstatus):
    _state.cleanup()
