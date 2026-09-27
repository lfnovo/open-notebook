"""Module boundaries: opt-in, auth, persistence, busy guard and source isolation."""
import asyncio
import importlib.util
import json
from pathlib import Path

from fastapi import FastAPI
import httpx
import pytest

from api.routers import modules as routes
from open_notebook.modules.registry import ModuleError, Registry

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def registry(tmp_path, monkeypatch):
    root = tmp_path/'modules'
    for mid in ('account-models','multi-model-research','local-workspace'):
        dest = root/mid
        dest.mkdir(parents=True)
        (dest/'module.json').write_bytes((ROOT/'modules'/mid/'module.json').read_bytes())
    (root/'installed.json').write_text(json.dumps(['account-models','multi-model-research','local-workspace']))
    monkeypatch.setenv('OPEN_NOTEBOOK_MODULES', '')
    monkeypatch.setenv('OPEN_NOTEBOOK_MODULE_DIR',str(root))
    monkeypatch.setenv('OPEN_NOTEBOOK_MODULE_STATE',str(tmp_path/'state/modules.json'))
    return Registry()


def test_default_is_opt_in_and_catalog_never_exposes_service_secrets(registry,monkeypatch):
    monkeypatch.setenv('LOCAL_RESEARCH_KEY','private-sentinel')
    research=next(x for x in registry.catalog() if x['id']=='multi-model-research')
    assert research['installed'] and not research['enabled']
    assert 'private-sentinel' not in json.dumps(registry.catalog())
    assert 'key_env' not in json.dumps(registry.catalog())
    with pytest.raises(ModuleError):registry.require_enabled('multi-model-research')


def test_enable_persists_across_registry_instances_and_disable_preserves_data(registry):
    sentinel=registry.state.parent.parent/'report.md';sentinel.write_text('immutable evidence')
    registry.set_enabled('multi-model-research',True)
    assert 'multi-model-research' in Registry().enabled()
    registry.set_enabled('multi-model-research',False)
    assert 'multi-model-research' not in Registry().enabled()
    assert sentinel.read_text()=='immutable evidence'
    assert registry.state.stat().st_mode & 0o777 == 0o600


def test_build_module_records_pending_change_without_lying_about_active_code(registry):
    registry.set_enabled('local-workspace',False)
    item=next(m for m in registry.catalog() if m['id']=='local-workspace')
    assert not item['enabled'] and item['active'] and item['pending_build']


def test_unknown_or_uninstalled_module_rejected(registry):
    with pytest.raises(ModuleError):registry.set_enabled('missing',True)
    (registry.root/'installed.json').write_text('[]')
    with pytest.raises(ModuleError):Registry().set_enabled('multi-model-research',True)


def test_bad_configuration_fails_closed(registry):
    registry.state.parent.mkdir(parents=True)
    registry.state.write_text('{broken')
    with pytest.raises(ModuleError):registry.enabled()


@pytest.mark.parametrize('mutation',['cycle','alias','directory','dependency'])
def test_invalid_manifest_graph_is_rejected(registry,mutation):
    path=registry.root/'account-models/module.json';data=json.loads(path.read_text())
    if mutation=='cycle':data['dependencies']=['multi-model-research']
    if mutation=='alias':data['service']={'url_env':'TEST_URL','key_env':'TEST_KEY','proxy_alias':'notebooks'}
    if mutation=='directory':data['id']='different'
    if mutation=='dependency':data['dependencies']=['missing']
    path.write_text(json.dumps(data))
    with pytest.raises(ModuleError):Registry()


@pytest.mark.asyncio
async def test_exclusive_update_waits_for_proxy_lease(registry):
    entered=asyncio.Event()
    async def writer():
        async with registry.lock(exclusive=True):entered.set()
    async with registry.lock():
        task=asyncio.create_task(writer())
        await asyncio.sleep(.1)
        assert not entered.is_set()
    await asyncio.wait_for(task,1)
    assert entered.is_set()


@pytest.mark.asyncio
async def test_catalog_and_routes_inherit_auth_and_disable_gate(registry,monkeypatch):
    # Real auth middleware, isolated app: no DB, no provider traffic.
    from api.auth import PasswordAuthMiddleware
    monkeypatch.setenv('OPEN_NOTEBOOK_PASSWORD','test-password')
    app=FastAPI();app.add_middleware(PasswordAuthMiddleware)
    routes.register_module_routes(app)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
        assert (await client.get('/api/modules')).status_code==401
        assert (await client.get('/api/research/runs')).status_code==401
        client.headers['Authorization']='Bearer test-password'
        assert (await client.get('/api/modules')).status_code==200
        assert (await client.get('/api/research/runs')).status_code==404
        assert (await client.get('/api/modules/multi-model-research/service/runs')).status_code==404
        assert (await client.put('/api/modules/unknown',json={'enabled':True})).status_code==404


@pytest.mark.asyncio
@pytest.mark.parametrize('mode',['active','pending','offline','idle'])
async def test_disable_guard_fails_closed_and_keeps_enabled(registry,monkeypatch,mode):
    registry.set_enabled('multi-model-research',True)
    monkeypatch.setenv('LOCAL_RESEARCH_URL','http://sidecar')
    monkeypatch.setenv('LOCAL_RESEARCH_KEY','secret')
    real_client=httpx.AsyncClient
    def handler(request):
        if mode=='offline':raise httpx.ConnectError('unreachable',request=request)
        if request.url.path=='/health':return httpx.Response(200,json={'status':'healthy','active_synthesis':int(mode=='active')})
        return httpx.Response(200,json=[{'status':'needs_attention' if mode=='pending' else 'paused'}])
    monkeypatch.setattr(routes.httpx,'AsyncClient',lambda **kwargs:real_client(transport=httpx.MockTransport(handler),**kwargs))
    if mode=='idle':
        await routes.configure_module('multi-model-research',routes.ModuleUpdate(enabled=False))
        assert 'multi-model-research' not in registry.enabled()
    else:
        with pytest.raises(Exception) as error:await routes.configure_module('multi-model-research',routes.ModuleUpdate(enabled=False))
        assert error.value.status_code in (409,503)
        assert 'multi-model-research' in registry.enabled()


@pytest.mark.asyncio
async def test_proxy_preserves_idempotency_but_not_client_authorization(registry,monkeypatch):
    registry.set_enabled('multi-model-research',True)
    monkeypatch.setenv('LOCAL_RESEARCH_URL','http://sidecar')
    monkeypatch.setenv('LOCAL_RESEARCH_KEY','sidecar-key')
    real_client=httpx.AsyncClient;captured=[]
    def handler(request):
        captured.append(request)
        return httpx.Response(201,json={'ok':True},headers={'Cache-Control':'no-store'})
    monkeypatch.setattr(routes.httpx,'AsyncClient',lambda **kwargs:real_client(transport=httpx.MockTransport(handler),**kwargs))
    app=FastAPI();routes.register_module_routes(app)
    async with real_client(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
        result=await client.post('/api/research/runs',json={'question':'test'},headers={'Authorization':'Bearer browser-token','Idempotency-Key':'one-operation'})
        assert result.status_code==201
        assert captured[0].headers['authorization']=='Bearer sidecar-key'
        assert captured[0].headers['idempotency-key']=='one-operation'
        assert json.loads(captured[0].content)=={'question':'test','language':'Türkçe','auto_synthesize':True,'execution_mode':'browser','preliminary':True}


def test_overlay_preflight_does_not_modify_checkout_or_destination(tmp_path):
    spec=importlib.util.spec_from_file_location('prepare',ROOT/'scripts/prepare_modules.py')
    script=importlib.util.module_from_spec(spec);spec.loader.exec_module(script)
    root=tmp_path/'source';mod=root/'modules/theme';mod.mkdir(parents=True)
    (mod/'module.json').write_text(json.dumps({'id':'theme','dependencies':[]}))
    (mod/'overlay.json').write_text(json.dumps([{'target':'file.txt','sha256_before':'wrong'}]))
    (root/'file.txt').write_text('upstream improvement')
    output=tmp_path/'build'
    with pytest.raises(ValueError,match='Upstream file changed'):script.prepare(root,output,['theme'])
    assert not output.exists()
    assert (root/'file.txt').read_text()=='upstream improvement'


def test_new_bundles_enable_all_installed_modules(registry, monkeypatch):
    monkeypatch.delenv('OPEN_NOTEBOOK_MODULES')
    assert registry.enabled() == registry.installed


def test_v1_migration_is_lossless_and_does_not_reenable_later(registry):
    registry.state.parent.mkdir(parents=True)
    registry.state.write_text(json.dumps({'version':1,'enabled':[]}))
    registry.set_enabled('account-models',False)
    snapshot=json.loads(registry.state.read_text())
    assert snapshot['version']==2
    assert 'account-models' not in Registry().enabled()
    assert 'local-workspace' in Registry().enabled()


def test_runtime_dependency_cannot_be_disabled_while_research_uses_it(registry):
    registry.set_enabled('multi-model-research',True)
    with pytest.raises(ModuleError,match='depends'):
        registry.set_enabled('account-models',False)
    registry.set_enabled('multi-model-research',False)
    registry.set_enabled('account-models',False)
    with pytest.raises(ModuleError,match='dependencies'):
        registry.set_enabled('multi-model-research',True)


@pytest.mark.parametrize('values',[{'timeout_seconds':False},{'timeout_seconds':0},{'timeout_seconds':7201},{'timeout_seconds':'600'},{'api_key':'secret'}, {'timeout_seconds':None}])
def test_settings_reject_invalid_types_ranges_and_secrets_without_writing(registry,values):
    with pytest.raises(ModuleError):registry.update('account-models',settings=values)
    assert not registry.state.exists()


def test_settings_persist_independently_and_disabled_settings_are_retained(registry):
    registry.update('account-models',settings={'timeout_seconds':1800})
    registry.update('multi-model-research',settings={'language':'English','auto_synthesize':False})
    registry.set_enabled('account-models',False)
    assert Registry().settings('account-models')['timeout_seconds']==1800
    assert Registry().settings('multi-model-research')['language']=='English'


def test_revision_conflict_never_loses_other_window_changes(registry):
    revision=registry.snapshot()['revision']
    registry.update('account-models',settings={'timeout_seconds':1800},expected_revision=revision)
    with pytest.raises(ModuleError,match='another window'):
        registry.update('account-models',settings={'timeout_seconds':900},expected_revision=revision)
    assert registry.settings('account-models')['timeout_seconds']==1800


def test_build_settings_are_desired_until_new_build_applies_them(registry):
    registry.update('local-workspace',settings={'density':'compact'})
    item=next(m for m in registry.catalog() if m['id']=='local-workspace')
    assert item['pending_build']
    assert registry.settings('local-workspace',effective=True)['density']=='comfortable'
    (registry.root/'build.json').write_text(json.dumps({'settings':{'local-workspace':{'density':'compact'}}}))
    assert not next(m for m in Registry().catalog() if m['id']=='local-workspace')['pending_build']


def test_typed_bus_shares_detached_values_and_enforces_model_gate(registry):
    from open_notebook.modules.runtime import ModuleBus, model_policy
    from open_notebook.modules.contracts import SettingsQuery
    bus=ModuleBus(registry)
    settings=bus.query(SettingsQuery('account-models'));settings['timeout_seconds']=1
    assert registry.settings('account-models')['timeout_seconds']==3900
    assert model_policy('openai_compatible','chatgpt-account','language')['timeout']==3900
    registry.set_enabled('account-models',False)
    with pytest.raises(ModuleError,match='disabled'):
        model_policy('openai_compatible','chatgpt-account','language')
    # Other providers and ordinary API models are independent of this module.
    assert model_policy('openai','gpt-test','language')=={}
    assert model_policy('openai_compatible','other','language')=={}


@pytest.mark.asyncio
async def test_request_defaults_only_fill_missing_values_and_leave_reports_untouched(registry,monkeypatch):
    from open_notebook.modules.service import ModuleManager
    registry.set_enabled('multi-model-research',True)
    registry.update('multi-model-research',settings={'language':'English','auto_synthesize':False})
    monkeypatch.setenv('LOCAL_RESEARCH_URL','http://sidecar');monkeypatch.setenv('LOCAL_RESEARCH_KEY','secret')
    real=httpx.AsyncClient;captured=[]
    def handler(request):
        captured.append(json.loads(request.content));return httpx.Response(200,json={'ok':True})
    monkeypatch.setattr(routes.httpx,'AsyncClient',lambda **kwargs:real(transport=httpx.MockTransport(handler),**kwargs))
    manager=ModuleManager(registry)
    for path,body in [('runs',{'question':'test'}),('runs',{'question':'test','language':'Türkçe'}),('runs/x/stages/y/import',{'text':'immutable report'})]:
        await manager.request('multi-model-research',path,'POST',{},json.dumps(body).encode(),{'content-type':'application/json'})
    assert captured[0]['language']=='English' and captured[0]['auto_synthesize'] is False
    assert captured[1]['language']=='Türkçe'
    assert captured[2]=={'text':'immutable report'}


def test_local_audio_content_adapter_closes_both_primary_and_fallback(tmp_path,monkeypatch):
    from open_notebook.modules.content_adapter import ContentAudioAdapter, DENIED_PROVIDER
    root=tmp_path/'modules';(root/'local-audio').mkdir(parents=True)
    (root/'local-audio/module.json').write_bytes((ROOT/'modules/local-audio/module.json').read_bytes())
    (root/'installed.json').write_text('["local-audio"]')
    monkeypatch.setenv('OPEN_NOTEBOOK_MODULE_DIR',str(root));monkeypatch.setenv('OPEN_NOTEBOOK_MODULE_STATE',str(tmp_path/'state.json'))
    monkeypatch.delenv('OPEN_NOTEBOOK_MODULES',raising=False)
    adapter=ContentAudioAdapter()
    assert adapter.configure('openai_compatible','whisper-small-local')['stt_timeout']==600
    Registry().set_enabled('local-audio',False)
    config=adapter.configure('openai_compatible','whisper-small-local')
    assert config['audio_provider']==config['stt_provider']==DENIED_PROVIDER
    # Real provider factory must reject before any network or automatic fallback.
    from esperanto import AIFactory
    with pytest.raises(Exception):AIFactory.create_speech_to_text(DENIED_PROVIDER,'whisper-small-local',{})


def test_settings_payload_is_strict_and_rejects_empty_updates():
    from pydantic import ValidationError
    for value in [{},{'enabled':'false'},{'unexpected':True},{'expected_revision':1}]:
        with pytest.raises(ValidationError):routes.ModuleUpdate(**value)


@pytest.mark.asyncio
async def test_real_model_and_podcast_entrypoints_enforce_module_policy(registry,monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, Mock
    from open_notebook.ai.models import Model, ModelManager, AIFactory
    from open_notebook.ai import key_provider
    from open_notebook.podcasts.models import _resolve_model_config
    row=SimpleNamespace(name='chatgpt-account',provider='openai_compatible',type='language',credential=None)
    monkeypatch.setattr(Model,'get',AsyncMock(return_value=row))
    monkeypatch.setattr(key_provider,'provision_provider_keys',AsyncMock())
    factory=Mock(return_value=object());monkeypatch.setattr(AIFactory,'create_language',factory)
    registry.update('account-models',settings={'timeout_seconds':2400})
    await ModelManager().get_model('model:managed')
    assert factory.call_args.kwargs['config']['timeout']==2400
    _,_,config=await _resolve_model_config('model:managed')
    assert config['timeout']==2400
    factory.reset_mock();registry.set_enabled('account-models',False)
    with pytest.raises(ModuleError,match='disabled'):await ModelManager().get_model('model:managed')
    with pytest.raises(ModuleError,match='disabled'):await _resolve_model_config('model:managed')
    factory.assert_not_called()


@pytest.mark.asyncio
async def test_real_plain_text_extraction_still_works_with_local_audio_disabled(registry,monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    from open_notebook.graphs import source
    path=registry.root/'local-audio';path.mkdir()
    (path/'module.json').write_bytes((ROOT/'modules/local-audio/module.json').read_bytes())
    (registry.root/'installed.json').write_text(json.dumps([*registry.installed,'local-audio']))
    Registry().set_enabled('local-audio',False)
    settings=SimpleNamespace(youtube_preferred_languages=None,default_content_processing_engine_url=None,
        default_content_processing_engine_doc=None,docling_ocr=None,docling_formulas=None,docling_vision=None,
        _load_from_db=AsyncMock())
    monkeypatch.setattr(source.ContentSettings,'get_instance',AsyncMock(return_value=settings))
    monkeypatch.setattr(source.ModelManager,'get_defaults',AsyncMock(return_value=SimpleNamespace(default_speech_to_text_model='model:local')))
    monkeypatch.setattr(source.Model,'get',AsyncMock(return_value=SimpleNamespace(provider='openai_compatible',name='whisper-small-local')))
    result=await source.content_process({'content_state':{'content':'Module boundaries preserve ordinary text extraction.'}})
    assert result['extraction'].content=='Module boundaries preserve ordinary text extraction.'


def test_unrelated_module_edits_do_not_conflict(registry):
    research=next(item for item in registry.catalog() if item['id']=='multi-model-research')
    registry.update('account-models',settings={'timeout_seconds':1800})
    registry.update('multi-model-research',settings={'language':'English'},expected_revision=research['revision'])
    assert registry.settings('multi-model-research')['language']=='English'
    assert registry.settings('account-models')['timeout_seconds']==1800


def test_private_service_config_is_not_an_http_setting(tmp_path,monkeypatch):
    from open_notebook.modules.service import service_config
    from open_notebook.modules.registry import Manifest
    key=tmp_path/'key';key.write_text('sidecar-only-secret')
    config=tmp_path/'services.json';config.write_text(json.dumps({'demo':{'url':'http://127.0.0.1:8322','key_file':str(key)}}))
    monkeypatch.setenv('OPEN_NOTEBOOK_SERVICE_CONFIG',str(config))
    item=Manifest(schema_version=1,id='demo',name='Demo',description='',version='1',author='test',activation='runtime',service={'url_env':'DEMO_TEST_URL','key_env':'DEMO_TEST_KEY'})
    base,headers=service_config(item);assert base=='http://127.0.0.1:8322' and headers['Authorization']=='Bearer sidecar-only-secret'
    monkeypatch.setenv('DEMO_TEST_URL','http://override');monkeypatch.setenv('DEMO_TEST_KEY','override-key')
    assert service_config(item)==('http://override',{'Authorization':'Bearer override-key'})


@pytest.mark.asyncio
async def test_service_control_failure_restores_previous_module_state(registry,monkeypatch):
    from open_notebook.modules.service import ModuleManager
    item=registry.get('multi-model-research');item.service.control_path='control'
    monkeypatch.setenv('LOCAL_RESEARCH_URL','http://sidecar');monkeypatch.setenv('LOCAL_RESEARCH_KEY','test')
    real=httpx.AsyncClient
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kw:real(transport=httpx.MockTransport(lambda req:httpx.Response(503)),**kw))
    registry.update('account-models',enabled=True)
    with pytest.raises(ModuleError,match='restored'):await ModuleManager(registry).configure('multi-model-research',enabled=True)
    assert 'multi-model-research' not in registry.enabled()
