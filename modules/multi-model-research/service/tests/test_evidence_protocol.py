import copy
import json
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from evidence_protocol import audit_report, register, audit_appendix
from workflow import citations, digest, initial_stages, prompt_for, report_packet


def run():
    return {'id':'a'*32,'question':'Question','scope':'scope','language':'Türkçe','created_at':'2026-09-21',
            'prompt_version':2,'stages':initial_stages()}


def claim(ident='research_gemini:C001', **patch):
    return {'id':ident,'statement':'Metric A is 10 in 2025.','status':'supported','sources':['https://example.org/original'],
            'reason':'The supplied report quotes the 2025 measurement.','counter_sources':[], 'counter_evidence':'', 'limits':'Scope: 2025.'} | patch


def finish(r, index, claims=None, raw=None):
    s=r['stages'][index]
    content=raw if raw is not None else 'Research\n```evidence-ledger\n'+json.dumps({'claims':claims,'blind_spots':['Scope?','Dates?','Alternatives?']})+'\n```\n'
    report={'content':content,'evidence':[],'citations':citations(content),'provenance':'test','sha256':digest(json.dumps({'content':content,'evidence':[]},sort_keys=True,ensure_ascii=False))}
    s.update(status='completed',report=report)
    s['evidence_audit']=audit_report(r,s)
    return s


def test_criticism_without_counterevidence_cannot_erase_supported_claim():
    r=run();old=finish(r,0,[claim()]);original=copy.deepcopy(old['report'])
    new=finish(r,3,[claim(status='rejected',sources=[],reason='Claude disagrees.')])
    assert new['evidence_audit']['assessments']==[]
    assert new['evidence_audit']['missing_claim_ids']==['research_gemini:C001']
    record=register(r['stages'])['claims'][0]
    assert len(record['assessments'])==1 and record['assessments'][0]['status']=='supported'
    assert record['sources']==['https://example.org/original'] and old['report']==original


def test_grounded_rejection_retains_original_sources_and_both_assessments():
    r=run();finish(r,0,[claim()])
    finish(r,3,[claim(status='rejected',sources=[],counter_sources=['https://example.org/correction'],
        counter_evidence='Correction shows the 2025 value was revised.',reason='Explicit erratum for same period and metric.')])
    record=register(r['stages'])['claims'][0]
    assert [a['status'] for a in record['assessments']]==['supported','rejected']
    assert record['sources']==['https://example.org/original']
    assert len(register(r['stages'])['sources'])==2


def test_parallel_disagreement_is_never_resolved_by_provider_order():
    r=run();finish(r,0,[claim()]);finish(r,3,[claim(status='disputed')]);finish(r,4,[claim()])
    record=register(r['stages'])['claims'][0]
    assert [a['status'] for a in record['assessments']]==['supported','disputed','supported']
    assert 'status' not in record  # no last-write-wins or majority "truth"


@pytest.mark.parametrize('alteration',[
    {'statement':'Metric A is 100 in 2026.'},
    {'status':'verified'},
    {'sources':[]},
    {'sources':['javascript:alert(1)']},
])
def test_invalid_reinterpretations_are_flagged_and_prior_statement_survives(alteration):
    r=run();finish(r,0,[claim()]);s=finish(r,3,[claim(**alteration)])
    assert s['evidence_audit']['warnings'] and not s['evidence_audit']['assessments']
    assert register(r['stages'])['claims'][0]['statement']==claim()['statement']


def test_synthesis_cannot_claim_new_unprovided_sources():
    r=run();finish(r,0,[claim()]);s=finish(r,5,[claim(sources=['https://example.org/not-in-input'])])
    assert not s['evidence_audit']['assessments']
    assert any('Araçsız' in w for w in s['evidence_audit']['warnings'])


@pytest.mark.parametrize('raw',['No ledger.','```evidence-ledger\nnot JSON\n```','```evidence-ledger\n{"claims":[]}\n```'])
def test_missing_or_malformed_ledger_never_silently_approves_or_rejects(raw):
    r=run();finish(r,0,[claim()]);s=finish(r,7,raw=raw)
    assert s['evidence_audit']['missing_claim_ids']==['research_gemini:C001']
    appendix=audit_appendix(r,s)
    assert 'İnceleme gerekli' in appendix and 'https://example.org/original' in appendix
    assert s['report']['content']==raw


def test_legacy_prompts_remain_exact_and_new_prompts_verify_complete_report_hash():
    r=run()
    for i in range(3):finish(r,i,[claim(ident=r['stages'][i]['id']+':C001')])
    old=copy.deepcopy(r);old.pop('prompt_version');old_prompt=prompt_for(old,old['stages'][3])
    assert 'Kanıt koruma ve eleştiri protokolü' not in old_prompt and 'evidence_register' not in old_prompt
    new_packet=report_packet(r,r['stages'][3])
    assert len(new_packet['reports'])==3 and len(new_packet['evidence_register']['claims'])==3
    for i in range(3):assert new_packet['reports'][i]['content']==r['stages'][i]['report']['content']
    r['stages'][0]['report']['content']+='corruption'
    with pytest.raises(ValueError,match='bütünlüğü'):prompt_for(r,r['stages'][3])


def test_duplicate_claim_id_is_not_a_second_vote():
    r=run();s=finish(r,0,[claim(),claim(status='unverified')])
    assert len(s['evidence_audit']['assessments'])==1
    assert any('tekrarlanan' in w for w in s['evidence_audit']['warnings'])


@pytest.mark.parametrize('language',['evidence-ledger','json',''])
def test_actual_html_conversion_preserves_or_recovers_structured_ledger(language):
    from extension_research import report_markdown
    import html
    payload=json.dumps({'claims':[claim()],'blind_spots':['Scope?','Dates?','Alternatives?']})
    markdown=report_markdown('<p>Original report.</p><pre><code class="language-'+language+'">'+html.escape(payload)+'</code></pre>')
    r=run();s=finish(r,0,raw=markdown)
    assert not s['evidence_audit']['warnings']
    assert s['evidence_audit']['assessments'][0]['id']=='research_gemini:C001'
