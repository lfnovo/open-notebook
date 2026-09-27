"""Portable configuration must actually change isolated builds and maintenance."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tarfile

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


@pytest.fixture
def source(tmp_path):
    root=tmp_path/'source';root.mkdir()
    for mid,activation in [('theme','build'),('feature','runtime')]:
        module=root/'modules'/mid;module.mkdir(parents=True)
        (module/'module.json').write_text(json.dumps({'id':mid,'activation':activation,'dependencies':[]}))
    generated=root/'frontend/src/lib/modules';generated.mkdir(parents=True)
    (generated/'generated.ts').write_text('// core module host')
    subprocess.run(['git','init','-q',str(root)],check=True)
    return root


def test_exported_disabled_runtime_stays_available_while_build_overlay_is_removed(source,tmp_path):
    script=load('prepare',ROOT/'scripts/prepare_modules.py')
    config={'version':2,'revision':5,'enabled':[], 'settings':{},'installed':['theme','feature']}
    output=tmp_path/'out'
    assert script.prepare(source,output,[],config)==['feature']
    assert json.loads((output/'modules/defaults.json').read_text())['enabled']==[]
    assert json.loads((output/'modules/installed.json').read_text())==['feature']
    assert not (source/'modules/installed.json').exists()


def test_invalid_export_does_not_touch_source_or_create_output(source,tmp_path):
    script=load('prepare',ROOT/'scripts/prepare_modules.py')
    output=tmp_path/'out'
    with pytest.raises(ValueError):script.prepare(source,output,[],{'version':2,'revision':1,'enabled':['missing'],'settings':{}})
    assert not output.exists()


@pytest.mark.parametrize('compression',['gzip','xz'])
def test_backup_policy_is_consumed_and_original_files_are_preserved(tmp_path,compression):
    module=load('backup',ROOT/'modules/local-deployment/backup.py')
    source=tmp_path/'reports';source.mkdir();(source/'evidence.md').write_text('immutable evidence')
    policy=module.BackupPolicy({'version':2,'enabled':['local-deployment'],'settings':{'local-deployment':{'compression':compression}}})
    archive=module.BackupJob(policy).create(tmp_path/'backup.tar',[source])
    with tarfile.open(archive) as stream:
        assert stream.extractfile('reports/evidence.md').read()==b'immutable evidence'
    assert (source/'evidence.md').read_text()=='immutable evidence'
    assert archive.stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError):module.BackupJob(policy).create(archive,[source])


def test_disabled_maintenance_does_not_create_an_archive(tmp_path):
    module=load('backup',ROOT/'modules/local-deployment/backup.py')
    with pytest.raises(ValueError,match='disabled'):module.BackupPolicy({'version':2,'enabled':[]})
