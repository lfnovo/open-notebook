"""The gate decides on the packet that is actually sent, not on what is kept on disk."""
import sys
import uuid
from pathlib import Path
import pytest
import pytest_asyncio

sys.path.insert(0, str(Path(__file__).parents[1]))
from context_compaction import PROTECTED
from engine import Engine
from packet_markdown import ledger_blocks
from store import Store
from token_budget import TokenBudget
from test_workflow import Provider, Sink, create, settle

FILLER = ('Bu bölümde konuyu ele alacağız ve ayrıntılarıyla inceleyeceğiz. '
          'Kavramsal çerçeve büyük ölçüde tartışmalı kalmaktadır ve uzlaşma bulunmamaktadır. '
          'İlgili yazın bu noktada birbirinden ayrışmakta ve farklı sonuçlara varmaktadır. ') * 74
EVIDENCE = 'Ölçüm 2026-03-14 tarihinde https://example.org/kaynak üzerinde yapıldı.'
ROUND_ONE = ['research_gemini', 'research_chatgpt', 'research_claude']
ROUND_TWO = ['review_chatgpt', 'review_claude']


def text_for(stage_id):
    return (f'# {stage_id}\n\n{EVIDENCE}\n\n{FILLER}\n\n'
            '```evidence-ledger\n'
            '{"claims":[{"id":"' + stage_id + ':C001","statement":"Tek iddia.","status":"supported",'
            '"sources":["https://example.org/kaynak"],"reason":"Gerekçe.","counter_sources":[],'
            '"counter_evidence":"","limits":"Kapsam."}],"blind_spots":["Soru?"]}\n```\n')


async def engine_with(tmp_path, limit, compaction=True):
    store = Store(tmp_path); await store.open()
    counter = lambda text: len(text) // 4
    engine = Engine(store, Provider(), Sink(), counter, limit,
                    budget=TokenBudget(counter), compaction=compaction)
    return store, engine


async def fill(engine, run_id, stage_ids):
    for stage_id in stage_ids:
        packet = await engine.packet(run_id, stage_id)
        await engine.import_report(run_id, stage_id, text_for(stage_id), [], '', packet['sha256'], [])


async def upto_synthesis(engine, auto=False):
    run = await create(engine, auto=auto)
    await fill(engine, run['id'], ROUND_ONE + ROUND_TWO)
    # The last import kicks a background pass; let it finish before touching the run.
    await settle(engine)
    return run['id']


@pytest_asyncio.fixture
async def tight(tmp_path):
    store, engine = await engine_with(tmp_path, 30000)
    yield engine
    await engine.close(); await store.close()


@pytest_asyncio.fixture
async def roomy(tmp_path):
    store, engine = await engine_with(tmp_path, 10 ** 7)
    yield engine
    await engine.close(); await store.close()


@pytest.mark.asyncio
async def test_fitting_packet_unchanged(roomy):
    rid=await upto_synthesis(roomy)
    packet=await roomy.packet(rid,'synthesis_chatgpt')
    assert packet['compaction'] is None and packet['fits']


@pytest.mark.asyncio
@pytest.mark.parametrize('packet_format',[None,'markdown-v1'])
async def test_unsent_legacy_packet_keeps_its_declared_representation(roomy,packet_format):
    from workflow import prompt_for
    run=await create(roomy,False)
    run['packet_format']=packet_format
    stage=run['stages'][0]
    stage.update(packet_format=packet_format,mode='account')
    assert roomy.prepared(run,stage)[0]==prompt_for(run,stage)


@pytest.mark.asyncio
async def test_new_web_research_is_not_replaced_by_a_source_only_synthesis_plan(roomy):
    from workflow import prompt_for
    run=await create(roomy,False)
    stage=dict(run['stages'][0],mode='account',account_profile='preliminary_research')
    policy={'block_status':'context_limit','blocked':True,'findings':[]}
    assert roomy.preparation_plan(run,stage,prompt_for(run,stage),policy) is None
    assert policy['blocked']


@pytest.mark.asyncio
async def test_shared_reference_encoding_is_exact_and_peer_independent(tight):
    from context_compaction import expand_prompt
    from workflow import prompt_for
    rid=await upto_synthesis(tight)
    run=await tight.get(rid)
    a=await tight.packet(rid,'synthesis_chatgpt'); b=await tight.packet(rid,'synthesis_claude')
    assert a['evidence_packet']==b['evidence_packet']
    assert expand_prompt(a['prompt'])==prompt_for(run,tight.stage(run,'synthesis_chatgpt'))
    assert a['compaction']['removed_sentences']==0


@pytest.mark.asyncio
async def test_never_submitted_identity_does_not_bind_a_round(tight):
    rid=await upto_synthesis(tight); run=await tight.get(rid)
    tight.stage(run,'synthesis_chatgpt')['evidence_packet']={'sha256':'old','bytes':1,'format':'markdown'}
    await tight.store.save(run)
    packet=await tight.packet(rid,'synthesis_claude')
    assert 'ECA-018' not in {f['id'] for f in packet['policy']['findings']}


@pytest.mark.asyncio
async def test_lowest_peer_budget_is_shared_and_profile_margin_matches_counting(tmp_path):
    store,engine=await engine_with(tmp_path,30000)
    try:
        engine.budget=TokenBudget(engine.budget.counter,{'Claude':{'multiplier':1.95,'overhead_tokens':4096}})
        rid=await upto_synthesis(engine);run=await engine.get(rid)
        a=engine.stage(run,'synthesis_chatgpt'); b=engine.stage(run,'synthesis_claude')
        assert engine.round_raw_limit(run,a)==engine.stage_raw_limit(b)
        preliminary=dict(a,account_profile='preliminary_merge')
        assert engine.stage_raw_limit(preliminary)==int((30000-4096)/1.25)
    finally:await engine.close();await store.close()


@pytest.mark.asyncio
async def test_exhaustive_segmentation_is_planned_when_unique_material_is_too_large(tmp_path):
    from workflow import digest
    import json
    store,engine=await engine_with(tmp_path,30000)
    try:
        rid=await upto_synthesis(engine);run=await engine.get(rid)
        for stage in run['stages'][:5]:
            report=stage['report'];report['content']='\n'.join(f'Unique condition {stage["id"]} {i}: retain the exception.' for i in range(2400))
            report['sha256']=digest(json.dumps({'content':report['content'],'evidence':[], 'researched_at':report['researched_at']},ensure_ascii=False,sort_keys=True))
        await store.save(run)
        a=await engine.packet(rid,'synthesis_chatgpt');b=await engine.packet(rid,'synthesis_claude')
        assert not a['fits'] and not a['policy']['blocked']
        assert a['preparation']['parts']>1
        assert a['preparation']==b['preparation']
        assert a['preparation']['coverage_verified']
        assert not a['preparation']['semantic_lossless']
    finally:await engine.close();await store.close()
