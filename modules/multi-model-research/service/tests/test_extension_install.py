import json
from pathlib import Path
import pytest

from install_extension_host import install


def test_native_host_uses_the_operator_selected_extension_id(tmp_path,monkeypatch):
    home=tmp_path/'home';runtime=tmp_path/'research'
    (runtime/'venv/bin').mkdir(parents=True)
    (runtime/'venv/bin/python').touch()
    (runtime/'config.json').write_text(json.dumps({'bridge_key_path':'unchanged-private-path'}))
    monkeypatch.setenv('RESEARCH_ROOT',str(runtime))
    monkeypatch.setattr(Path,'home',classmethod(lambda cls:home))
    extension_id='a'*32
    install(extension_id)
    manifest=json.loads((home/'Library/Application Support/Google/Chrome/NativeMessagingHosts/com.open_notebook.research.json').read_text())
    assert manifest['allowed_origins']==['chrome-extension://'+extension_id+'/']
    assert 'export RESEARCH_EXTENSION_ID='+extension_id in (runtime/'extension-host/native-host').read_text()
    config=json.loads((runtime/'config.json').read_text())
    assert config['bridge_key_path']=='unchanged-private-path'
    assert config['extension_id']==extension_id


def test_invalid_extension_id_is_rejected_before_files_are_written(tmp_path,monkeypatch):
    root=tmp_path/'untouched'
    monkeypatch.setenv('RESEARCH_ROOT',str(root))
    with pytest.raises(ValueError):install('bad-id;command')
    assert not root.exists()
