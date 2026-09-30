import json
import sqlite3
import threading
from pathlib import Path
from backend.orchestrator.hashing import digest
from backend.orchestrator.run_context import Evidence,RunContext,now

class Store:
    def __init__(self,root):
        self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True)
        self.path=self.root/'asent.sqlite3';self.lock=threading.RLock()
        with self.connect() as c:
            c.executescript('''
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY,body TEXT);
            CREATE TABLE IF NOT EXISTS evidence(id TEXT PRIMARY KEY,run_id TEXT,module TEXT,body TEXT,content_hash TEXT,stale INTEGER DEFAULT 0);
            CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT,run_id TEXT,kind TEXT,body TEXT,previous_hash TEXT,hash TEXT);
            CREATE TABLE IF NOT EXISTS cache(key TEXT PRIMARY KEY,body TEXT);
            CREATE TABLE IF NOT EXISTS experiments(id TEXT PRIMARY KEY,body TEXT);
            ''')
    def connect(self): return sqlite3.connect(self.path,timeout=30)
    def save_run(self,run):
        with self.lock,self.connect() as c:c.execute('INSERT OR REPLACE INTO runs VALUES(?,?)',(run.run_id,run.model_dump_json()))
    def run(self,rid):
        with self.connect() as c:row=c.execute('SELECT body FROM runs WHERE id=?',(rid,)).fetchone()
        if not row:raise KeyError(rid)
        return RunContext.model_validate_json(row[0])
    def runs(self,limit=100):
        with self.connect() as c: rows=c.execute('SELECT body FROM runs ORDER BY rowid DESC'+(' LIMIT ?' if limit else ''),(limit,) if limit else ()).fetchall()
        return [json.loads(r[0]) for r in rows]
    def put_evidence(self,e):
        body=e.model_dump(mode='json');h=digest(body)
        with self.lock,self.connect() as c:c.execute('INSERT INTO evidence(id,run_id,module,body,content_hash) VALUES(?,?,?,?,?)',(e.evidence_id,e.run_id,e.analyzer,json.dumps(body),h))
        out=self.root/'evidence'/e.run_id;out.mkdir(parents=True,exist_ok=True)
        (out/(e.evidence_id+'.json')).write_text(json.dumps({'sha256':h,'evidence':body},indent=2))
    def evidence(self,rid):
        with self.connect() as c:rows=c.execute('SELECT body,content_hash,stale FROM evidence WHERE run_id=? ORDER BY rowid',(rid,)).fetchall()
        return [{**json.loads(b),'content_hash':h,'integrity_valid':digest(json.loads(b))==h,'stale':bool(s)} for b,h,s in rows]
    def invalidate(self,eid):
        with self.lock,self.connect() as c:c.execute('UPDATE evidence SET stale=1 WHERE id=?',(eid,))
    def event(self,rid,kind,data):
        body={'timestamp':now(),'data':data}
        with self.lock,self.connect() as c:
            row=c.execute('SELECT hash FROM events WHERE run_id=? ORDER BY id DESC LIMIT 1',(rid,)).fetchone()
            previous=row[0] if row else '0'*64
            h=digest({'run_id':rid,'kind':kind,'body':body,'previous_hash':previous})
            cur=c.execute('INSERT INTO events(run_id,kind,body,previous_hash,hash) VALUES(?,?,?,?,?)',(rid,kind,json.dumps(body),previous,h))
            return {'id':cur.lastrowid,'run_id':rid,'kind':kind,**body,'previous_hash':previous,'hash':h}
    def events(self,rid,after=0):
        with self.connect() as c: rows=c.execute('SELECT id,kind,body,previous_hash,hash FROM events WHERE run_id=? AND id>? ORDER BY id',(rid,after)).fetchall()
        return [{'id':i,'run_id':rid,'kind':k,**json.loads(b),'previous_hash':p,'hash':h} for i,k,b,p,h in rows]
    def verify_chain(self,rid):
        previous='0'*64
        for e in self.events(rid):
            if e['previous_hash']!=previous or e['hash']!=digest({'run_id':rid,'kind':e['kind'],'body':{'timestamp':e['timestamp'],'data':e['data']},'previous_hash':previous}):return False
            previous=e['hash']
        return True
    def cache_get(self,key):
        with self.connect() as c:row=c.execute('SELECT body FROM cache WHERE key=?',(key,)).fetchone()
        if not row:return None
        data=json.loads(row[0])
        if '_cache_digest' not in data:return None
        expected=data.pop('_cache_digest')
        return data if digest(data)==expected else None
    def cache_put(self,key,value):
        with self.lock,self.connect() as c:c.execute('INSERT OR REPLACE INTO cache VALUES(?,?)',(key,json.dumps({**value,'_cache_digest':digest(value)})))
    def cache_clear(self):
        with self.lock,self.connect() as c:
            count=c.execute('SELECT COUNT(*) FROM cache').fetchone()[0]
            c.execute('DELETE FROM cache')
            return count
    def experiment(self,value):
        with self.lock,self.connect() as c:c.execute('INSERT OR REPLACE INTO experiments VALUES(?,?)',(value['experiment_id'],json.dumps(value)))
    def experiments(self):
        with self.connect() as c:rows=c.execute('SELECT body FROM experiments ORDER BY rowid DESC').fetchall()
        return [json.loads(x[0]) for x in rows]
