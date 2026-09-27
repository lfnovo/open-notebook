"""Local catalog: explicit scope, content-addressed passages and independent retrieval.

No source file is modified. SQLite is authoritative; the vector cache is disposable.
"""
from __future__ import annotations
import hashlib, json, os, re, sqlite3, stat, threading, time, unicodedata
from pathlib import Path

from query import TEXT_EXT, DOC_EXT, OFFICE_EXT, IMAGE_EXT, normalized, query_terms
from collections import OrderedDict
EXTRACTION_VERSION = 'documents-ocr-v2'

class Catalog:
    def __init__(self, state:Path, config:dict):
        self.state=state;state.mkdir(parents=True,exist_ok=True,mode=0o700);state.chmod(0o700)
        self.root=Path(config['root']).resolve();self.excludes=[Path(p).absolute() for p in config['exclude']]+[state.resolve()]
        # Build output, dependency trees and caches repeat at every depth, so they
        # cannot be expressed as absolute prefixes. They are matched by name.
        self.exclude_names=set(config.get('exclude_names',[]))
        # Hidden directories hold tool state, not documents, and their names are
        # open-ended, so they are matched by their leading dot rather than listed.
        self.skip_hidden=bool(config.get('exclude_hidden_directories',False))
        # Glob patterns for directory names that are generated rather than written,
        # and for files that are lockfiles or build output rather than documents.
        self.exclude_patterns=list(config.get('exclude_name_patterns',[]))
        self.exclude_files=list(config.get('exclude_file_patterns',[]))
        self.resolved_excludes=[p.resolve() for p in self.excludes];self.exclusions_checked=time.monotonic()
        self.active=lambda:True
        self.max_bytes=config.get('max_content_bytes',256*1024*1024)
        self.config=config;self.lock=threading.RLock();self.scan_lock=threading.Lock();self.progress={'phase':'starting','visited':0,'unreadable_directories':0,'last_scan':None,'error':None}
        with self.db() as db:
            db.executescript('''
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS files(id INTEGER PRIMARY KEY,path TEXT UNIQUE,name TEXT,extension TEXT,size INTEGER,mtime INTEGER,seen INTEGER,digest TEXT,status TEXT,error TEXT);
            CREATE INDEX IF NOT EXISTS file_digest ON files(digest);
            CREATE INDEX IF NOT EXISTS file_pending ON files(status);
            CREATE INDEX IF NOT EXISTS file_priority ON files((CASE WHEN extension IN ('pdf','docx','md','markdown') THEN 0 ELSE 1 END),id) WHERE status='pending';
            CREATE VIRTUAL TABLE IF NOT EXISTS names USING fts5(name,path,tokenize='unicode61 remove_diacritics 2',prefix='2 3 4');
            CREATE TABLE IF NOT EXISTS documents(digest TEXT PRIMARY KEY,characters INTEGER,passages INTEGER);
            CREATE TABLE IF NOT EXISTS chunks(id INTEGER PRIMARY KEY AUTOINCREMENT,digest TEXT,position INTEGER,body TEXT,vector BLOB,UNIQUE(digest,position));
            CREATE INDEX IF NOT EXISTS chunk_digest ON chunks(digest);
            CREATE VIRTUAL TABLE IF NOT EXISTS contents USING fts5(body,tokenize='unicode61 remove_diacritics 2',prefix='2 3 4');
            ''')
        with self.db() as db:
            if 'priority' not in [r[1] for r in db.execute('PRAGMA table_info(files)')]:db.execute('ALTER TABLE files ADD COLUMN priority INTEGER NOT NULL DEFAULT 1')
            db.execute("CREATE INDEX IF NOT EXISTS file_priority_v2 ON files(priority,(CASE WHEN extension IN ('pdf','docx','md','markdown') THEN 0 ELSE 1 END),id) WHERE status='pending'")
        with self.db() as db:
            db.execute("CREATE INDEX IF NOT EXISTS file_priority_v3 ON files(priority,mtime DESC,id) WHERE status='pending'")
            db.execute('CREATE INDEX IF NOT EXISTS chunk_vector_pending ON chunks(id) WHERE vector IS NULL')
        os.chmod(state/'catalog.sqlite3',0o600)
        self.extract_turn=0
        self.vector=None;self.vector_lock=threading.RLock();self.vector_error=None
        self.vector_scopes=OrderedDict();self.embedding_cache=OrderedDict();self.rerank_cache=OrderedDict();self.cache_lock=threading.Lock()
        self.gc_cursor=0;self.gc_removed=0
        self._upgrade_extraction()

    def db(self):
        db=sqlite3.connect(self.state/'catalog.sqlite3',timeout=30);db.row_factory=sqlite3.Row;return db

    def allowed(self,path):
        try:
            lexical=Path(os.path.abspath(path));real=lexical.resolve(strict=False)
            if time.monotonic()-self.exclusions_checked>1:
                self.resolved_excludes=[p.resolve() for p in self.excludes];self.exclusions_checked=time.monotonic()
            if self.exclude_names and (self.exclude_names.intersection(lexical.parts) or self.exclude_names.intersection(real.parts)):
                return False
            if self.exclude_patterns:
                import fnmatch
                for part in lexical.parts[len(self.root.parts):]:
                    if any(fnmatch.fnmatch(part,pat) for pat in self.exclude_patterns):
                        return False
            if self.exclude_files and lexical.is_file():
                import fnmatch
                if any(fnmatch.fnmatch(lexical.name,pat) for pat in self.exclude_files):
                    return False
            if self.skip_hidden:
                root_parts=len(self.root.parts)
                if any(part.startswith('.') for part in lexical.parts[root_parts:-1] if part not in ('.','..')):
                    return False
                if lexical.is_dir() and lexical.name.startswith('.') and len(lexical.parts)>root_parts:
                    return False
            return lexical.is_relative_to(self.root) and real.is_relative_to(self.root) and not any(lexical.is_relative_to(p) for p in self.excludes) and not any(real.is_relative_to(p) for p in self.resolved_excludes)
        except (OSError,ValueError,RuntimeError):return False

    def content_status(self,path,size):
        ext=path.suffix.lower().lstrip('.')
        if size>self.max_bytes:return 'too_large'
        if ext not in DOC_EXT:return 'metadata_only'
        # Authentication stores are catalogued by name, never sent to extraction/models.
        if path.name.startswith('.env') or path.name.lower() in {'credentials.json','auth.json','id_rsa','id_ed25519','cookies','login data'}:return 'metadata_only'
        return 'pending'

    def upsert(self,path,db,seen):
        if not self.allowed(path):return
        try:
            st=path.stat()
            if not stat.S_ISREG(st.st_mode):return
            old=db.execute('SELECT * FROM files WHERE path=?',(str(path),)).fetchone()
            if old and old['size']==st.st_size and old['mtime']==st.st_mtime_ns:
                db.execute('UPDATE files SET seen=? WHERE id=?',(seen,old['id']));return
            state=self.content_status(path,st.st_size)
            if old:
                with self.vector_lock:self.vector_scopes.pop(old['extension'],None)
                fid=old['id'];db.execute('DELETE FROM names WHERE rowid=?',(fid,))
                db.execute('UPDATE files SET size=?,mtime=?,seen=?,digest=NULL,status=?,error=NULL WHERE id=?',(st.st_size,st.st_mtime_ns,seen,state,fid))
            else:
                fid=db.execute('INSERT INTO files(path,name,extension,size,mtime,seen,status) VALUES(?,?,?,?,?,?,?)',(str(path),path.name,path.suffix.lower().lstrip('.'),st.st_size,st.st_mtime_ns,seen,state)).lastrowid
            db.execute('INSERT INTO names(rowid,name,path) VALUES(?,?,?)',(fid,normalized(path.name),normalized(str(path.relative_to(self.root)))))
        except (OSError,ValueError):pass

    def scan(self):
        if not self.scan_lock.acquire(blocking=False):return
        self.progress.update(phase='scanning',visited=0,unreadable_directories=0,error=None);seen=time.time_ns();blocked=[]
        try:
            def error(exc):
                self.progress['unreadable_directories']+=1
                if exc.filename:blocked.append(str(exc.filename))
            # Walk does not follow directory symlinks; their canonical in-scope targets
            # are visited under the root. No red-excluded target can be reached via alias.
            batch=[]
            def flush():
                with self.lock,self.db() as db:
                    for path in batch:self.upsert(path,db,seen)
                batch.clear()
                time.sleep(.005)
            for folder,dirs,files in os.walk(self.root,followlinks=False,onerror=error):
                if not self.active():
                    if batch:flush()
                    self.progress['phase']='paused';return
                dirs[:]=[d for d in dirs if self.allowed(Path(folder)/d) and not (Path(folder)/d).is_symlink()]
                dirs.sort(key=lambda d:(d not in ('Documents','obsidian','Developer','conductor'),d))
                for name in files:
                    batch.append(Path(folder)/name);self.progress['visited']+=1
                    if len(batch)>=500:flush()
            if batch:flush()
            with self.lock,self.db() as db:
                # Inaccessible directories are reported, not misclassified as deletion.
                for row in db.execute('SELECT id,path,extension FROM files WHERE seen<?',(seen,)).fetchall():
                    if any(row['path']==p or row['path'].startswith(p+os.sep) for p in blocked):continue
                    with self.vector_lock:self.vector_scopes.pop(row['extension'],None)
                    db.execute('DELETE FROM names WHERE rowid=?',(row['id'],));db.execute('DELETE FROM files WHERE id=?',(row['id'],))
                self.progress.update(phase='watching',last_scan=time.time())
        except Exception as exc:self.progress.update(phase='error',error=type(exc).__name__)
        finally:self.scan_lock.release()

    def change(self,path):
        path=Path(path)
        with self.lock,self.db() as db:
            if path.is_file():
                self.upsert(path,db,time.time_ns())
                db.execute("UPDATE files SET priority=0 WHERE path=? AND status='pending'",(str(path),))
            elif not path.exists():
                # Escaped LIKE patterns would be unsafe for literal filenames; use range.
                prefix=str(path)+os.sep
                rows=db.execute('SELECT id,extension FROM files WHERE path=? OR (path>=? AND path<?)',(str(path),prefix,prefix+'\U0010ffff')).fetchall()
                for row in rows:
                    with self.vector_lock:self.vector_scopes.pop(row['extension'],None)
                    db.execute('DELETE FROM names WHERE rowid=?',(row['id'],));db.execute('DELETE FROM files WHERE id=?',(row['id'],))

    def open_file(self,path):
        if not self.allowed(path):raise ValueError('out_of_scope')
        real=Path(path).resolve(strict=True)
        # O_NOFOLLOW protects the final component; re-check canonical scope before read.
        fd=os.open(real,os.O_RDONLY|os.O_NOFOLLOW)
        try:
            st=os.fstat(fd)
            if not stat.S_ISREG(st.st_mode):raise ValueError('not_regular_file')
            return os.fdopen(fd,'rb')
        except BaseException:os.close(fd);raise

    def read_bytes(self,path):
        with self.open_file(path) as f:
            if os.fstat(f.fileno()).st_size>self.max_bytes:raise ValueError('too_large')
            data=f.read(self.max_bytes+1)
            if len(data)>self.max_bytes:raise ValueError('too_large')
            return data

    def extract(self,data,ext):
        if ext in OFFICE_EXT | IMAGE_EXT:
            import subprocess,sys,signal
            proc=subprocess.Popen([sys.executable,str(Path(__file__).with_name('extract_document.py')),ext,str(self.max_bytes)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
            try:
                output,error=proc.communicate(data,timeout=self.config.get('document_timeout_seconds',240))
                if proc.returncode:
                    reason=error.decode('utf-8',errors='replace').strip()
                    raise ValueError(reason if reason in ('ocr_unavailable','empty_document','document_limit','document_parse_failed') else 'document_parse_failed')
                return output.decode('utf-8')
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid,signal.SIGKILL);proc.communicate()
                raise ValueError('document_parse_timeout')
        if data.startswith((b'\xff\xfe',b'\xfe\xff')):return data.decode('utf-16')
        if b'\0' in data[:4096]:raise ValueError('binary_content')
        for enc in ('utf-8-sig','cp1254'):
            try:return data.decode(enc)
            except UnicodeError:pass
        raise ValueError('unsupported_encoding')

    def _upgrade_extraction(self):
        # Only reopen previously unsupported/failed content after a parser release.
        # Successful reports and source bytes are not rewritten.
        with self.db() as db:
            db.execute('CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY,value TEXT)')
            old=db.execute("SELECT value FROM metadata WHERE key='extraction_version'").fetchone()
            if old and old[0]==EXTRACTION_VERSION:return
            rows=db.execute("SELECT id,path,size FROM files WHERE status IN ('metadata_only','too_large','unreadable')").fetchall()
            for row in rows:
                if self.content_status(Path(row['path']),row['size'])=='pending':
                    db.execute("UPDATE files SET status='pending',error=NULL WHERE id=?",(row['id'],))
            db.execute("INSERT OR REPLACE INTO metadata VALUES('extraction_version',?)",(EXTRACTION_VERSION,))
            db.execute("CREATE INDEX IF NOT EXISTS file_priority_v4 ON files((CASE WHEN extension IN ('pdf','docx','xlsx','pptx') THEN 0 ELSE 1 END),priority,mtime DESC,id) WHERE status='pending'")

    def collect_garbage(self,limit=500):
        # Cursor-bounded scan: avoid re-scanning all healthy chunks every second.
        # Shared digests survive while any current file references them.
        with self.lock,self.db() as db,self.vector_lock:
            db.execute('BEGIN IMMEDIATE')
            batch=db.execute('SELECT id FROM chunks WHERE id>? ORDER BY id LIMIT ?',(self.gc_cursor,limit)).fetchall()
            if not batch:self.gc_cursor=0;return 0
            end=batch[-1][0]
            rows=db.execute('SELECT id,digest FROM chunks c WHERE id>? AND id<=? AND NOT EXISTS (SELECT 1 FROM files f WHERE f.digest=c.digest)',(self.gc_cursor,end)).fetchall()
            for row in rows:
                db.execute('DELETE FROM contents WHERE rowid=?',(row['id'],))
                db.execute('DELETE FROM chunks WHERE id=?',(row['id'],))
                for idx in [self.vector,*self.vector_scopes.values()]:
                    if idx is not None and row['id'] in idx:idx.remove(row['id'])
                db.execute('DELETE FROM documents WHERE digest=? AND NOT EXISTS (SELECT 1 FROM chunks WHERE digest=?) AND NOT EXISTS (SELECT 1 FROM files WHERE digest=?)',(row['digest'],row['digest'],row['digest']))
            self.gc_cursor=end;self.gc_removed+=len(rows)
            return len(rows)

    def process_one(self):
        self.extract_turn+=1
        # New/edited documents get a fast lane; one in eight slots still drains
        # initial coverage, so a busy workspace cannot starve the original backlog.
        order="id" if self.extract_turn%8==0 else "(CASE WHEN extension IN ('pdf','docx','xlsx','pptx') THEN 0 ELSE 1 END),priority,mtime DESC,id"
        with self.db() as db:
            row=db.execute("SELECT * FROM files WHERE status='pending' ORDER BY "+order+" LIMIT 1").fetchone()
        if not row:return False
        try:
            data=self.read_bytes(row['path']);digest=hashlib.sha256(data).hexdigest()
            with self.db() as db:known=db.execute('SELECT 1 FROM documents WHERE digest=?',(digest,)).fetchone()
            if not known:
                text=self.extract(data,row['extension'])
                if not text.strip():raise ValueError('empty_document')
                # Paragraph-like bounded windows with overlap, without truncating document.
                parts=[text[i:i+1800] for i in range(0,len(text),1600)]
            with self.lock,self.db() as db:
                current=Path(row['path']).stat()
                if current.st_mtime_ns!=row['mtime'] or current.st_size!=row['size']:
                    self.upsert(Path(row['path']),db,time.time_ns());return True
                if not self.allowed(row['path']):raise ValueError('out_of_scope')
                if known and not db.execute('SELECT 1 FROM documents WHERE digest=?',(digest,)).fetchone():
                    return True
                if not known:
                    db.execute('INSERT OR IGNORE INTO documents VALUES(?,?,?)',(digest,len(text),len(parts)))
                    for i,body in enumerate(parts):
                        cursor=db.execute('INSERT OR IGNORE INTO chunks(digest,position,body) VALUES(?,?,?)',(digest,i,body))
                        if cursor.rowcount:db.execute('INSERT INTO contents(rowid,body) VALUES(?,?)',(cursor.lastrowid,normalized(body)))
                db.execute("UPDATE files SET digest=?,status='indexed',error=NULL WHERE id=? AND mtime=?",(digest,row['id'],row['mtime']))
            if known:self.index_digest(digest)
        except Exception as exc:
            with self.db() as db:db.execute("UPDATE files SET status='unreadable',error=? WHERE id=? AND mtime=?",(str(exc)[:160] if isinstance(exc,ValueError) else type(exc).__name__,row['id'],row['mtime']))
        return True

    def load_vectors(self):
        from usearch.index import Index
        import numpy as np
        idx=Index(ndim=768,metric='cos',dtype='f16')
        with self.db() as db:
            cursor=db.execute('SELECT id,vector FROM chunks c WHERE vector IS NOT NULL AND EXISTS (SELECT 1 FROM files f WHERE f.digest=c.digest)')
            while batch:=cursor.fetchmany(1000):idx.add(np.array([r['id'] for r in batch],dtype=np.uint64),np.stack([np.frombuffer(r['vector'],dtype=np.float32) for r in batch]))
        with self.vector_lock:self.vector=idx;self.vector_scopes.clear()

    def embed_batch(self):
        import httpx,numpy as np
        with self.db() as db:rows=db.execute('SELECT id,body FROM chunks WHERE vector IS NULL AND digest IN (SELECT digest FROM files WHERE digest IS NOT NULL) LIMIT 8').fetchall()
        if not rows:return False
        with httpx.Client(timeout=60) as client:
            response=client.post(self.config.get('ollama_url','http://127.0.0.1:11434')+'/api/embed',json={'model':self.config['embedding_model'],'input':[r['body'] for r in rows],'truncate':False,'keep_alive':'10m'})
            response.raise_for_status();vectors=np.asarray(response.json()['embeddings'],dtype=np.float32)
        if vectors.shape!=(len(rows),768) or not np.isfinite(vectors).all():raise ValueError('invalid_embeddings')
        with self.lock,self.db() as db,self.vector_lock:
            for row,vec in zip(rows,vectors):
                current=db.execute('SELECT digest FROM chunks WHERE id=?',(row['id'],)).fetchone()
                if not current or not db.execute('SELECT 1 FROM files WHERE digest=?',(current['digest'],)).fetchone():continue
                db.execute('UPDATE chunks SET vector=? WHERE id=?',(vec.tobytes(),row['id']))
                self.add_vector(db,row['id'],current['digest'],vec)
        self.vector_error=None;return True

    def add_vector(self,db,key,digest,vec):
        if self.vector is not None and key not in self.vector:self.vector.add(key,vec)
        exts={r[0] for r in db.execute('SELECT DISTINCT extension FROM files WHERE digest=?',(digest,))}
        for ext,idx in self.vector_scopes.items():
            if ext in exts and key not in idx:idx.add(key,vec)

    def index_digest(self,digest):
        import numpy as np
        with self.lock,self.db() as db,self.vector_lock:
            for row in db.execute('SELECT id,vector FROM chunks WHERE digest=? AND vector IS NOT NULL',(digest,)):
                self.add_vector(db,row['id'],digest,np.frombuffer(row['vector'],dtype=np.float32))

    def scoped_vector(self,extension):
        # A lazily built per-format graph filters BEFORE top-k. Subsequent vector
        # writes update loaded graphs; bounded LRU keeps unused graphs out of RAM.
        from usearch.index import Index
        import numpy as np
        with self.lock,self.vector_lock:
            if extension in self.vector_scopes:
                self.vector_scopes.move_to_end(extension);return self.vector_scopes[extension]
            idx=Index(ndim=768,metric='cos',dtype='f16')
            with self.db() as db:
                cursor=db.execute('SELECT id,vector FROM chunks c WHERE vector IS NOT NULL AND EXISTS (SELECT 1 FROM files f WHERE f.digest=c.digest AND f.extension=?)',(extension,))
                while batch:=cursor.fetchmany(1000):idx.add(np.array([r['id'] for r in batch],dtype=np.uint64),np.stack([np.frombuffer(r['vector'],dtype=np.float32) for r in batch]))
            self.vector_scopes[extension]=idx
            while len(self.vector_scopes)>4:self.vector_scopes.popitem(last=False)
            return idx

    def status(self):
        with self.db() as db:
            counts={r[0]:r[1] for r in db.execute('SELECT status,count(*) FROM files GROUP BY status')}
            passages=db.execute('SELECT count(*) FROM chunks').fetchone()[0]
            vectors=passages-db.execute('SELECT count(*) FROM chunks WHERE vector IS NULL').fetchone()[0]
        return dict(self.progress,root=str(self.root),excluded=[str(p) for p in self.excludes],excluded_names=sorted(self.exclude_names),hidden_directories='excluded' if self.skip_hidden else 'included',excluded_patterns=self.exclude_patterns,excluded_files=self.exclude_files,files=sum(counts.values()),counts=counts,passages=passages,vectors=vectors,semantic_error=self.vector_error,embedding_model=self.config['embedding_model'],directory_symlinks='canonical_targets_only',max_content_bytes=self.max_bytes,vector_pending=passages-vectors,gc_removed=self.gc_removed,content_formats=sorted(DOC_EXT),ocr_available=Path(__file__).with_name('ocr').is_file())

    def search(self,query,limit=20):
        from retrieval import search
        return search(self,query,limit)
