"""Exercise the legacy research startup copy without launching real services."""
import os
from pathlib import Path
import subprocess

import pytest


@pytest.mark.parametrize('existing',[False,True])
def test_startup_copies_new_service_modules_and_preserves_private_settings(tmp_path,existing):
    root=Path(__file__).resolve().parents[1]
    source=tmp_path/'bundle/research';source.mkdir(parents=True)
    for path in (root/'modules/multi-model-research/service').glob('*.py'):
        (source/path.name).write_text('# bundled service module\n')
    (source/'future_layer.py').write_text('# future module\n')
    for name in ('config.json','.research-key','service.plist','requirements.lock'):
        (source/name).write_text('bundled '+name)
    target=tmp_path/'runtime';(target/'venv/bin').mkdir(parents=True)
    python=target/'venv/bin/python';python.write_text('#!/bin/bash\nexit 0\n');python.chmod(0o700)
    if existing:
        (target/'config.json').write_text('operator configuration')
        (target/'.research-key').write_text('operator key')
    template=(root/'modules/local-deployment/legacy-templates/control.sh.template').read_text()
    function=template.split('research_start() {',1)[1].split('\nvoice_start()',1)[0]
    script='''set -euo pipefail
curl() { printf '{"active_synthesis":0,"pending_exports":0}'; }
launchctl() { return 0; }
research_start() {'''+function+'\nresearch_start\n'
    subprocess.run(['/bin/bash','-c',script],env={**os.environ,'DIR':str(source.parent),
        'RESEARCH_DIR':str(target),'RESEARCH_SERVICE':'test-no-service'},check=True,capture_output=True)
    assert (target/'future_layer.py').read_bytes()==(source/'future_layer.py').read_bytes()
    for name in ('context_compaction.py','context_preparation.py','segmented_execution.py','stage_controls.py'):
        assert (target/name).read_bytes()==(source/name).read_bytes()
    assert (target/'config.json').read_text()==('operator configuration' if existing else 'bundled config.json')
    assert (target/'.research-key').read_text()==('operator key' if existing else 'bundled .research-key')
