import json
import pytest
from context_preparation import digest, PreparationError


def frozen(text, cuts):
    parts=[];offset=0;start=0
    for i,end in enumerate(cuts+[len(text)],1):
        value=text[start:end];size=len(value.encode())
        parts.append({'id':f'P{i}','text':value,'start_byte':offset,'end_byte':offset+size,'sha256':digest(value)})
        start=end;offset+=size
    return {'version':'segmented-evidence-v1','source_sha256':digest(text),'source_bytes':offset,'parts':parts}


def test_only_exact_frozen_boundary_prefix_is_a_fragment():
    from synthesis_boundaries import boundary_references, render_references
    url='https://example.org/long/path'
    text='Türkçe source: '+url+'\nNext.'
    cut=text.index('/long')+2
    plan=frozen(text,[cut]);fragments=boundary_references(plan,text,{url})
    prefix=text[text.index('https://'):cut]
    assert set(fragments)=={prefix}
    proof=fragments[prefix][0]
    assert proof['complete_url']==url and proof['part_id']=='P1'
    assert proof['boundary_byte']==len(text[:cut].encode())
    raw=f'The partial address `{prefix}` is not evidence. Complete address {url}.'
    rendered,audit=render_references(raw,fragments,{url})
    assert raw!=rendered and url in rendered and 'not a source' in rendered
    assert audit['original_report_sha256']==digest(raw)
    assert audit['rendered_report_sha256']==digest(rendered)
    assert audit['reconstruction_verified'] is True
    assert audit['references'][0]['fragment']==prefix
    assert plan['parts'][0]['text']==text[:cut]


def test_unknown_prefix_and_unrelated_invented_sources_still_fail():
    from synthesis_boundaries import boundary_references, render_references
    url='https://example.org/long/path';text=url+' tail'
    plan=frozen(text,[len(url)-2]);fragments=boundary_references(plan,text,{url})
    for report in ['https://example.org/long','https://evil.invalid/source',url[:-2]+' https://evil.invalid/source']:
        with pytest.raises(PreparationError):render_references(report,fragments,{url})


def test_no_fragment_if_complete_url_ends_at_boundary_or_occurs_elsewhere_only():
    from synthesis_boundaries import boundary_references
    url='https://example.org/long/path'
    for text,cut in [(url+' next',len(url)),('https://example.org/l WRONG '+url,len('https://example.org/l'))]:
        assert boundary_references(frozen(text,[cut]),text,{url})=={}


def test_frozen_bytes_and_boundary_offsets_are_verified():
    from synthesis_boundaries import boundary_references
    url='https://example.org/long/path';plan=frozen(url,[len(url)-2]);plan['parts'][0]['end_byte']-=1
    with pytest.raises(PreparationError):boundary_references(plan,url,{url})


def test_escaped_json_url_at_boundary_and_repeated_occurrences_preserve_provenance():
    from synthesis_boundaries import boundary_references, render_references
    url='https://acorn.firefox.com/latest/foundations/styles/motion-YsUZhS6a'
    text=json.dumps({'report':'Üç saniye [Acorn]('+url+').\nConditions remain.'},ensure_ascii=False)
    cut=text.index(url)+len('https://acorn.firefox.com/latest/f')
    prefix='https://acorn.firefox.com/latest/f'
    proof=boundary_references(frozen(text,[cut]),text,{url})
    raw=f'`{prefix}` is cut. It is not used as evidence: `{prefix}`.'
    rendered,audit=render_references(raw,proof,{url})
    assert audit['references'][0]['occurrences']==2
    assert 'Conditions' not in rendered
    assert len(proof[prefix])==1


def test_no_changes_for_existing_full_sources_and_plain_prose():
    from synthesis_boundaries import render_references
    raw='Uncertainty and https://example.org/valid'
    assert render_references(raw,{}, {'https://example.org/valid'})==(raw,None)
