import hashlib
import io
import json
from pathlib import Path
import runpy
import tarfile

import pytest


def verifier():
    return runpy.run_path(str(Path(__file__).parents[1]/'legacy-templates/backup.py.template'))['verify_archive']


def archive(path, fault=None):
    files={'z.txt':'Türkçe koşullar'.encode(),'folder/a.txt':b'full original evidence'}
    manifest={n:{'size':len(b),'sha256':hashlib.sha256(b).hexdigest()} for n,b in files.items()}
    if fault=='content':files['z.txt']=b'corrupt'
    if fault=='missing':files.pop('z.txt')
    if fault=='extra':files['other']=b'extra'
    if fault=='size':manifest['z.txt']['size']+=1
    if fault=='hash':manifest['z.txt']['sha256']='0'*64
    with tarfile.open(path,'w:gz') as tar:
        for n,b in files.items():
            item=tarfile.TarInfo(n);item.size=len(b);tar.addfile(item,io.BytesIO(b))
        if fault=='duplicate':
            item=tarfile.TarInfo('z.txt');item.size=len(files['z.txt']);tar.addfile(item,io.BytesIO(files['z.txt']))
        if fault=='link':
            item=tarfile.TarInfo('link');item.type=tarfile.SYMTYPE;item.linkname='/etc/passwd';tar.addfile(item)
        if fault=='traversal':
            item=tarfile.TarInfo('../escape');tar.addfile(item,io.BytesIO(b''))
        if fault!='manifest':
            data=json.dumps({'created':'test','files':manifest}).encode()
            item=tarfile.TarInfo('manifest.json');item.size=len(data);tar.addfile(item,io.BytesIO(data))


def test_verifies_every_file_in_one_forward_archive_pass(tmp_path,monkeypatch):
    path=tmp_path/'backup.tar.gz';archive(path)
    original_open=tarfile.open;original_extract=tarfile.TarFile.extractfile;modes=[]
    def opened(*a,**kw):
        modes.append(kw.get('mode',a[1] if len(a)>1 else 'r'));return original_open(*a,**kw)
    def extracted(self,member,*a,**kw):
        assert isinstance(member,tarfile.TarInfo),'Named lookup can seek backward through gzip'
        return original_extract(self,member,*a,**kw)
    monkeypatch.setattr(tarfile,'open',opened);monkeypatch.setattr(tarfile.TarFile,'extractfile',extracted)
    assert verifier()(path)==2
    assert modes==['r|gz']


@pytest.mark.parametrize('fault',['content','missing','extra','size','hash','duplicate','link','traversal','manifest'])
def test_corrupt_incomplete_or_unsafe_archives_are_not_verified(tmp_path,fault):
    path=tmp_path/'backup.tar.gz';archive(path,fault)
    with pytest.raises(RuntimeError):verifier()(path)
