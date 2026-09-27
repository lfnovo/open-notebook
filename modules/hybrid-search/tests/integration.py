"""Run in an isolated SurrealDB database with the real local embedding/reranker.
Requires the application environment. Never run against the user's data.
"""
import os
assert os.environ.get('SURREAL_DATABASE', '').startswith('hybrid_validation_')
import asyncio
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import time
import httpx
from open_notebook.database.repository import ensure_record_id
try:
    from open_notebook.modules.hybrid_search import service
except ImportError:
    import sys
    sys.path.insert(0, '/tmp')
    from hybrid_search import service

FIXTURES = [
 ('code', 'Ürün kılavuzu', 'AB-123 cihazı 24 volt doğru akımla çalışır. Bakım aralığı altı aydır.'),
 ('othercode', 'Benzer ürün', 'AB-1234 cihazı 12 volt doğru akımla çalışır. Bakım aralığı üç aydır.'),
 ('land', 'İmar belgesi', 'Arsaların imar durumları belediyeden öğrenilir. Parsellerin yapılaşma koşulları imar planına bağlıdır.'),
 ('legal', 'Kira artışı', 'Türk Borçlar Kanunu TBK 344 kira artışını düzenler. Konut kirası yenileme döneminde on iki aylık TÜFE ortalaması esas alınır.'),
 ('circuit', 'Execution safety', 'The emergency circuit breaker cancels pending orders when the daily loss limit is breached. New trades are blocked until a human reviews the incident.'),
 ('bias', 'Validation', 'Look-ahead bias occurs when future observations leak into training data. Time series cross-validation must preserve chronological order.'),
 ('profit', 'İşlem maliyeti', 'Net getiri hesaplanırken komisyon, slippage ve funding maliyetleri brüt kârdan düşülür.'),
 ('unit', 'Risk hesabı', 'İzin verilen risk sermayenin yüzde ikisidir. Pozisyon büyüklüğü risk tutarının stop mesafesine bölünmesiyle hesaplanır.'),
 ('vacuum', 'Temizlik cihazı', 'Robot süpürgenin toz haznesi her kullanım sonunda temizlenir. HEPA filtre ayda bir kontrol edilir.'),
 ('backup', 'Database recovery', 'Point-in-time recovery replays transaction logs to restore a database to a selected timestamp. Backups must be tested through actual restores.'),
 ('coffee', 'Kahve demleme', 'Filtre kahvede su sıcaklığı 92 ile 96 derece arasında tutulur. Öğütüm kalınlığı ekstraksiyon süresini etkiler.'),
 ('auth', 'Güvenlik', 'Çok faktörlü kimlik doğrulama yalnız parolanın çalınmasına karşı ek koruma sağlar. Kurtarma kodları çevrimdışı saklanır.'),
 ('whisper', 'Speech processing', 'Automatic speech recognition converts audio recordings into text. Word error rate measures substitutions, deletions and insertions in the transcript.'),
 ('rerank', 'Arama sistemi', 'Çapraz kodlayıcı soru ve belgeyi birlikte değerlendirerek adayların ilgisini yeniden sıralar. BM25 ve vektör adayları RRF ile birleştirilir.'),
 ('cash', 'Nakit akışı', 'Tahsilat gecikmesi işletmenin nakit döngüsünü uzatır. Kârlılık ile likidite aynı kavram değildir.'),
 ('temperature', 'Sıcaklık sensörü', 'ZX-904 sensörünün çalışma aralığı eksi kırk ile seksen beş santigrat derecedir.'),
 ('tail', 'Uzun teknik ek', ('Bu bölüm genel bakım ve kayıt kurallarını açıklar. Düzenli inceleme yapılmalıdır.\n'*100)+'\nNEX-770 hata kodu, optik okuyucunun kalibrasyonunun bozulduğunu gösterir. Çözüm referans kartıyla yeniden kalibre etmektir.'),
 ('scope_a', 'Özel A', 'Gizli test sözcüğü ScopeSecretA yalnız birinci deftere aittir.'),
 ('scope_b', 'Özel B', 'Gizli test sözcüğü ScopeSecretB yalnız ikinci deftere aittir.'),
 ('identical_a', 'Ortak metin', 'Aynı metin farklı defterde olsa da kapsam dışına taşınamaz.'),
 ('identical_b', 'Ortak metin', 'Aynı metin farklı defterde olsa da kapsam dışına taşınamaz.'),
]
QUERIES = [
 ('AB-123 bakım süresi nedir?', 'code'),('AB-1234 kaç volt?', 'othercode'),
 ('arsanın imar durumunu nereden öğrenirim?', 'land'),('parsellerde yapılaşma şartları', 'land'),
 ('TBK 344 kira artışı', 'legal'),('kira yenilemede TÜFE ortalaması', 'legal'),
 ('Günlük kayıp sınırı aşılırsa bekleyen emirler ne olur?', 'circuit'),('What blocks trading after a daily loss?', 'circuit'),
 ('Gelecek bilgisi eğitim verisine sızarsa hangi hata oluşur?', 'bias'),('"look-ahead bias"', 'bias'),
 ('işlemde gerçek kâr nasıl hesaplanır?', 'profit'),('funding ve slippage', 'profit'),
 ('stop uzaklığına göre pozisyon boyutu', 'unit'),('sermayenin yüzde ikisi risk', 'unit'),
 ('robot süpürgenin filtresi', 'vacuum'),('Belirli bir zamana veritabanını geri döndürmek', 'backup'),
 ('Yedekler nasıl doğrulanır?', 'backup'),('kahve su sıcaklığı', 'coffee'),
 ('öğütüm ekstraksiyon süresi', 'coffee'),('parola çalınmasına ek koruma', 'auth'),
 ('Kurtarma kodları nerede saklanır?', 'auth'),('ses kaydını yazıya dönüştürme hata oranı', 'whisper'),
 ('word error rate', 'whisper'),('BM25 ile vektör nasıl birleştirilir?', 'rerank'),
 ('çapraz kodlayıcı ne yapar?', 'rerank'),('kâr varken nakit neden yok?', 'cash'),
 ('tahsilat gecikmesi likidite', 'cash'),('ZX-904 sıcaklık aralığı', 'temperature'),
 ('NEX-770 hatasının çözümü', 'tail'),('optik okuyucunun kalibrasyonu', 'tail'),
]

class LocalEmbedding:
    async def aembed(self, texts):
        async with httpx.AsyncClient(timeout=180,trust_env=False) as c:
            r=await c.post('http://host.lima.internal:11434/api/embed',json={'model':'embeddinggemma:300m-qat-q8_0','input':texts,'truncate':False});r.raise_for_status();return r.json()['embeddings']
class Models:
    async def get_embedding_model(self):return LocalEmbedding()

async def main():
    service.settings=lambda:service.DEFAULTS.copy()
    service.model_manager=Models()
    e=service.HybridSearch()
    spec=SimpleNamespace(name='embeddinggemma:300m-qat-q8_0')
    async def model():return '1234feedbabe5678'*4,spec
    e.model=model
    q=service.checked_query
    for table in ('note','source','source_insight','notebook','artifact','reference','hs_document','hs_state','hs_p_1234feedbabe5678'):
        await q(f'REMOVE TABLE IF EXISTS {table}')
    await q('CREATE notebook:a; CREATE notebook:b;')
    for name,title,content in FIXTURES:
        await q('CREATE $id CONTENT $body',{'id':ensure_record_id('note:'+name),'body':{'title':title,'content':content}})
        if name.endswith('_a') or name.endswith('_b'):
            nb='notebook:'+name[-1]
            await q('RELATE $id->artifact->$nb',{'id':ensure_record_id('note:'+name),'nb':ensure_record_id(nb)})
    await e.sync()
    status=await e.status();print('INDEX',json.dumps(status),flush=True)
    assert status['status']=='ready',status
    assert status['index']['documents']==len(FIXTURES)
    assert status['passages']>len(FIXTURES)
    for language in ('tr','en'):
        plan=await q(f"SELECT id,search::score(0) AS score FROM hs_p_1234feedbabe5678 WITH INDEX hs_{language}_text WHERE search_{language} @0@ 'imar' EXPLAIN FULL")
        assert any(r['operation']=='Iterate Index' for r in plan),plan
    plan=await q('SELECT id FROM hs_p_1234feedbabe5678 WHERE embedding <|20,100|> $v EXPLAIN',{'v':(await LocalEmbedding().aembed(['arama']))[0]})
    assert any(r['operation']=='Iterate Index' for r in plan),plan
    checks=[]
    rows,diag=await e.search('ScopeSecretB',30,True,True,['notebook:a'],rerank=False)
    assert all(r['id'].endswith('_a') for r in rows),rows
    rows,diag=await e.search('Aynı metin',30,True,True,['notebook:a'],rerank=False)
    assert all(r['id'].endswith('_a') for r in rows),rows
    checks+=['scope_before_limit','identical_content_scope_isolation','bm25_indexes','hnsw_index']
    # Changed/deleted content must not leak through stale index or query cache.
    await q('UPDATE note:scope_a SET content="Updated ScopeNewest"')
    async def no_start():pass
    e.start=no_start
    rows,diag=await e.search('ScopeSecretA',30,True,True,['notebook:a'],rerank=False)
    assert 'note:scope_a' not in [r['id'] for r in rows] and diag['pending_documents']==1
    await q('DELETE note:scope_b')
    rows,diag=await e.search('ScopeSecretB',30,True,True,['notebook:b'],rerank=False)
    assert 'note:scope_b' not in [r['id'] for r in rows]
    await e.sync();assert e.state['status']=='ready'
    checks+=['stale_version_excluded','deleted_document_excluded','incremental_reindex']
    results=[]
    for query, expected in QUERIES:
        fused,_=await e.search(query,10,rerank=False)
        fused_ids=[r["id"] for r in fused]
        fused_rank=fused_ids.index("note:"+expected)+1 if "note:"+expected in fused_ids else None
        rows,diag=await e.search(query,10,rerank=True)
        ids=[r['id'] for r in rows];rank=ids.index('note:'+expected)+1 if 'note:'+expected in ids else None
        results.append({'query':query,'expected':'note:'+expected,'rank':rank,'fusion_rank':fused_rank,'diagnostics':diag})
        print('QUERY',query,rank,diag['timings'],diag['warnings'],flush=True)
    summary={'queries':len(results),'recall_at_10':sum(r['rank'] is not None for r in results)/len(results),'mrr_at_10':sum(1/r['rank'] if r['rank'] else 0 for r in results)/len(results),'top1':sum(r['rank']==1 for r in results)/len(results),'checks':checks,'results':results}
    Path('/tmp/hybrid-benchmark.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
    print('SUMMARY',{k:v for k,v in summary.items() if k!='results'},flush=True)
    assert summary['recall_at_10']>=.9
    assert all(r['diagnostics']['reranked'] or 'weak_relevance' in r['diagnostics']['warnings'] for r in results), 'Reranker did not run'
    await e.close()
if __name__=='__main__':asyncio.run(main())
