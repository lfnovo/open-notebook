from test_catalog import cat,drain
from catalog import Catalog,query_terms
from pathlib import Path
import os,io,zipfile

def test_extension_filter_before_candidate_limit(cat):
    for i in range(170):(cat.root/f'strategy-{i}.md').write_text('noise')
    path=cat.root/'The detailed business strategy documentation and roadmap.pdf';path.write_bytes(b'fixture')
    cat.scan()
    assert [r['name'] for r in cat.search('strategy pdf')['results']]==[path.name]

def test_natural_words_are_not_implicit_code_extensions():
    assert query_terms('go to market strategy')[1]==[]
    assert query_terms('C programlama stratejisi')[1]==[]
    assert query_terms('strategy ext:go filetype:py .rs')[1]==['go','py','rs']

def test_gc_preserves_shared_digest_then_removes_all_indexes(cat):
    a=cat.root/'a.md';b=cat.root/'b.md';a.write_text('strategy shared evidence');b.write_bytes(a.read_bytes())
    cat.scan();drain(cat)
    import numpy as np
    with cat.db() as db:db.execute('UPDATE chunks SET vector=?',(np.ones(768,dtype=np.float32).tobytes(),))
    cat.load_vectors();idx=cat.scoped_vector('md');assert len(idx)==1
    a.unlink();cat.change(a);cat.collect_garbage();assert cat.search('strategy')['results'][0]['name']=='b.md'
    b.unlink();cat.change(b)
    for _ in range(3):cat.collect_garbage()
    with cat.db() as db:
        for table in ('files','documents','chunks','contents'):assert db.execute('SELECT count(*) FROM '+table).fetchone()[0]==0
    assert len(cat.vector)==0

def test_office_priority_persists_for_future_arrivals(cat):
    old=cat.root/'plan.pdf';old.write_bytes(b'fixture');cat.change(old)
    recent=cat.root/'recent.ts';recent.write_text('newer');cat.change(recent)
    cat.extract=lambda data,ext: 'recognized '+ext
    cat.process_one()
    with cat.db() as db:assert db.execute('SELECT status FROM files WHERE path=?',(str(old),)).fetchone()[0]=='indexed'

def test_xlsx_and_pptx_text(cat):
    from openpyxl import Workbook
    book=Workbook();book.active.title='Budget';book.active['A1']='strategic customer growth';book.save(cat.root/'roadmap.xlsx')
    with zipfile.ZipFile(cat.root/'roadmap.pptx','w') as z:
        z.writestr('ppt/slides/slide1.xml','<p:sld xmlns:p="p" xmlns:a="a"><a:t>Security strategy</a:t></p:sld>')
        z.writestr('ppt/notesSlides/notesSlide1.xml','<p:sld xmlns:p="p" xmlns:a="a"><a:t>Contract evidence</a:t></p:sld>')
    cat.scan();drain(cat)
    assert cat.search('customer xlsx')['results']
    assert cat.search('contract pptx')['results']

def test_large_text_is_not_limited_to_20_mb(cat):
    path=cat.root/'large.txt';payload=b'A'*(21*1024**2);path.write_bytes(payload)
    assert cat.read_bytes(path)==payload

def test_parser_upgrade_requeues_previously_metadata_only(cat):
    path=cat.root/'plan.xlsx';path.write_bytes(b'fixture');cat.scan()
    with cat.db() as db:
        db.execute("UPDATE files SET status='metadata_only'");db.execute("DELETE FROM metadata WHERE key='extraction_version'")
    updated=Catalog(cat.state,cat.config)
    assert updated.status()['counts']['pending']==1

def test_installer_never_resets_existing_scope():
    from install import merged_config
    original={'root':'/Users/example','exclude':['/Users/example/Documents/Codex'],'exclude_names':['node_modules'],'max_content_bytes':123456789,'exclude_hidden_directories':True}
    assert all(merged_config(original,Path('/Users/example'))[k]==v for k,v in original.items())

def test_filtered_semantic_search_does_not_lose_pdf_behind_other_formats(cat,monkeypatch):
    import numpy as np,httpx
    # The PDF is deliberately orthogonal to the query; 160 closer MDs must not crowd it out.
    for i in range(160):(cat.root/f'noise-{i}.md').write_text('unrelated content '+str(i))
    (cat.root/'needle.pdf').write_bytes(b'fixture')
    cat.extract=lambda data,ext: data.decode() if ext=='md' else 'foreign language document'
    cat.scan()
    for _ in range(162):cat.process_one()
    one=np.zeros(768,dtype=np.float32);one[0]=1
    two=np.zeros(768,dtype=np.float32);two[1]=1
    with cat.db() as db:
        for row in db.execute('SELECT id,digest FROM chunks').fetchall():
            ext=db.execute('SELECT extension FROM files WHERE digest=?',(row['digest'],)).fetchone()[0]
            db.execute('UPDATE chunks SET vector=? WHERE id=?',((two if ext=='pdf' else one).tobytes(),row['id']))
    cat.load_vectors()
    class Response:
        def raise_for_status(self):pass
        def json(self):return {'embeddings':[one.tolist()]}
    monkeypatch.setattr(httpx,'post',lambda *a,**k:Response())
    hits=cat.search('soyut kavram pdf')['results']
    assert len(hits)==1 and hits[0]['name']=='needle.pdf'

def test_document_intent_reserves_office_filename_candidates(cat):
    for i in range(170):(cat.root/f'strategy-{i}.py').write_text('code')
    (cat.root/'strategy memorandum.pdf').write_bytes(b'fixture');cat.scan()
    assert cat.search('strateji dokumanim nerede')['results'][0]['extension']=='pdf'
    # Generic topic queries still allow code; explicit docx never returns a PDF.
    assert cat.search('strateji')['results']
    assert not cat.search('strategy docx')['results']


def test_unrelated_edits_keep_pdf_graph_but_pdf_edits_invalidate_it(cat):
    import numpy as np
    pdf=cat.root/'evidence.pdf';note=cat.root/'note.md'
    pdf.write_bytes(b'fixture');note.write_text('working note')
    cat.extract=lambda data,ext: 'document '+ext
    cat.scan();drain(cat)
    with cat.db() as db:db.execute('UPDATE chunks SET vector=?',(np.ones(768,dtype=np.float32).tobytes(),))
    cat.load_vectors();graph=cat.scoped_vector('pdf');assert len(graph)==1
    note.write_text('changed note');cat.change(note)
    assert cat.scoped_vector('pdf') is graph
    note.unlink();cat.change(note)
    assert cat.scoped_vector('pdf') is graph
    pdf.write_bytes(b'changed document');cat.change(pdf)
    assert len(cat.scoped_vector('pdf'))==0
