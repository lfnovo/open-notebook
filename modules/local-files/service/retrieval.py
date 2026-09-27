"""Bounded, format-scoped hybrid retrieval. Source documents remain unchanged."""
import time,hashlib
from pathlib import Path
from query import OFFICE_EXT, query_terms, wants_document, normalized
import re

def search(catalog, query, limit):
    start=time.monotonic();terms,formats=query_terms(query);warnings=[];rankings=[];bodies={};timings={};mark=start
    document_intent=wants_document(query)
    expression=' OR '.join('"'+w+'"*' for w in terms)
    clause=' AND f.extension IN ('+','.join('?' for _ in formats)+')' if formats else ''
    with catalog.db() as db:
        if expression:
            names=db.execute('SELECT f.id FROM names JOIN files f ON f.id=names.rowid WHERE names MATCH ?'+clause+' ORDER BY names.rank LIMIT 150',[expression,*formats]).fetchall()
            rankings.append([(r[0],None) for r in names])
            chunks=db.execute('SELECT c.id,c.digest,c.body FROM contents JOIN chunks c ON c.id=contents.rowid WHERE contents MATCH ? AND EXISTS (SELECT 1 FROM files f WHERE f.digest=c.digest'+clause+') ORDER BY contents.rank LIMIT 150',[expression,*formats]).fetchall()
        else:chunks=[];rankings.append([])
        def files_for(digest):
            return db.execute('SELECT f.id FROM files f WHERE f.digest=?'+clause+' LIMIT 60',[digest,*formats])
        rankings.append([(f[0],chunk['body']) for chunk in chunks for f in files_for(chunk['digest'])])
        if expression and document_intent and not formats:
            # Reserve candidates for authored office documents; code with matching
            # identifiers must not crowd them out before reranking. Keep all other
            # formats in the ordinary channels (this is a boost, not an exclusion).
            docs=db.execute("SELECT f.id FROM names JOIN files f ON f.id=names.rowid WHERE names MATCH ? AND f.extension IN ('pdf','docx','xlsx','pptx') ORDER BY names.rank LIMIT 80",(expression,)).fetchall()
            rankings.append([(r[0],None) for r in docs])
        timings['lexical_ms']=round((time.monotonic()-mark)*1000);mark=time.monotonic()
        if not terms:rankings.append([(r[0],None) for r in db.execute('SELECT f.id FROM files f WHERE 1'+clause+' ORDER BY mtime DESC LIMIT 150',formats)])
        try:
            if catalog.vector is not None and len(catalog.vector) and terms:
                import httpx,numpy as np
                with catalog.cache_lock:q=catalog.embedding_cache.get(query)
                if q is None:
                    response=httpx.post(catalog.config.get('ollama_url','http://127.0.0.1:11434')+'/api/embed',json={'model':catalog.config['embedding_model'],'input':query,'truncate':False,'keep_alive':'10m'},timeout=12)
                    response.raise_for_status();q=np.asarray(response.json()['embeddings'][0],dtype=np.float32)
                    if q.shape!=(768,) or not np.isfinite(q).all():raise ValueError('invalid_query_embedding')
                    with catalog.cache_lock:
                        catalog.embedding_cache[query]=q
                        while len(catalog.embedding_cache)>128:catalog.embedding_cache.popitem(last=False)
                timings['query_embedding_ms']=round((time.monotonic()-mark)*1000);mark=time.monotonic()
                indexes=[catalog.scoped_vector(ext) for ext in formats] if formats else [catalog.vector]
                matches={}
                with catalog.vector_lock:
                    for idx in indexes:
                        for match in idx.search(q,count=100):matches[int(match.key)]=min(matches.get(int(match.key),float('inf')),float(match.distance))
                semantic=[]
                for key in sorted(matches,key=matches.get):
                    chunk=db.execute('SELECT digest,body FROM chunks WHERE id=?',(key,)).fetchone()
                    if chunk:semantic.extend((f[0],chunk['body']) for f in files_for(chunk['digest']))
                rankings.append(semantic)
        except Exception:warnings.append('semantic_unavailable')
        timings['semantic_ms']=round((time.monotonic()-mark)*1000);mark=time.monotonic()
        scores={}
        for channel,ranking in enumerate(rankings):
            seen=set()
            for position,(fid,body) in enumerate(ranking):
                if fid in seen:continue
                seen.add(fid);scores[fid]=scores.get(fid,0)+(3 if channel==2 and document_intent and not formats else 1.5 if channel==0 else 1)/(40+position+1)
                if body:bodies.setdefault(fid,body)
        results=[];groups={}
        for fid in sorted(scores,key=scores.get,reverse=True):
            row=db.execute('SELECT * FROM files WHERE id=?',(fid,)).fetchone()
            if not row or not catalog.allowed(row['path']):continue
            try:
                st=Path(row['path']).stat()
                if st.st_mtime_ns!=row['mtime'] or st.st_size!=row['size']:continue
            except OSError:continue
            key=row['digest'] or row['path']
            if key in groups:groups[key]['copies'].append(row['path']);continue
            item={k:row[k] for k in ('id','path','name','extension','size','mtime','status','error')}
            boost=1.35 if document_intent and row['extension'] in OFFICE_EXT|{'md','txt','markdown'} else 1
            item.update(score=round(scores[fid]*boost,6),snippet=bodies.get(fid,'')[:1400],copies=[],sha256=row['digest'])
            groups[key]=item;results.append(item)
        results.sort(key=lambda item:item['score'],reverse=True)
        timings['candidate_ms']=round((time.monotonic()-mark)*1000);mark=time.monotonic()
        if results and catalog.config.get('reranker_url'):
            try:
                import httpx,math
                shortlist=results[:32];key=Path(catalog.config['reranker_key_file']).read_text().strip()
                documents=[r['name']+'\n'+r['snippet'] for r in shortlist]
                cache_key=hashlib.sha256((query+'\0'+'\0'.join(documents)).encode()).hexdigest()
                with catalog.cache_lock:cached=catalog.rerank_cache.get(cache_key)
                if cached and time.monotonic()-cached[0]<60:values=cached[1]
                else:
                    response=httpx.post(catalog.config['reranker_url']+'/rerank',json={'query':query,'documents':documents},headers={'Authorization':'Bearer '+key},timeout=20)
                    response.raise_for_status();values=response.json()['scores']
                    if len(values)==len(shortlist) and all(math.isfinite(float(v)) for v in values):
                        with catalog.cache_lock:
                            catalog.rerank_cache[cache_key]=(time.monotonic(),values)
                            while len(catalog.rerank_cache)>128:catalog.rerank_cache.popitem(last=False)
                if len(values)!=len(shortlist) or any(not math.isfinite(float(v)) for v in values):raise ValueError('invalid_reranker_response')
                if max(values)<.001:warnings.append('weak_relevance')
                else:
                    ordered=sorted(zip(shortlist,values),key=lambda pair:float(pair[1])*(1.2 if document_intent and pair[0]['extension'] in OFFICE_EXT|{'md','txt','markdown'} else 1),reverse=True)
                    results=[dict(item,relevance=score) for item,score in ordered]+results[len(shortlist):]
            except Exception:warnings.append('reranker_unavailable')
        if document_intent and not formats:
            # An explicitly requested document with a matching office filename
            # outranks code identifiers, even if a neural reranker prefers them.
            def document_filename_match(item):
                words=re.findall(r'[a-z0-9]+',normalized(item['name']))
                return item['extension'] in OFFICE_EXT and any(w.startswith(t) for w in words for t in terms)
            results.sort(key=document_filename_match,reverse=True)
        timings['rerank_ms']=round((time.monotonic()-mark)*1000);mark=time.monotonic()
        status=catalog.status()
        timings['status_ms']=round((time.monotonic()-mark)*1000)
        partial=status['phase'] in ('starting','scanning') or status['counts'].get('pending',0)>0 or status['vector_pending']>0
        return {'results':results[:limit],'query_terms':terms,'extensions':formats,'warnings':warnings,'timings':timings,'timing_ms':round((time.monotonic()-start)*1000),'partial_index':partial,'retrieval':'filename BM25 + passage BM25 + format-scoped multilingual HNSW + reciprocal rank fusion'}
