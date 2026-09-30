import json
import sqlite3
import threading
from pathlib import Path
from backend.config import ROOT
from backend.orchestrator.hashing import digest
from backend.orchestrator.run_context import now
from backend.threat_repo.models import ThreatRecord,ThreatImport
from backend.threat_repo.versioning import MODULE_CATEGORIES,module_digest


def seeds():
    records=[]
    for p in sorted((ROOT/'backend/threat_repo/seed').glob('*.json')):records.extend(json.loads(p.read_text())['records'])
    return records

def active(knowledge,category):
    records=(knowledge or {'records':seeds()})['records']
    return [r for r in records if r['category']==category and r['enabled']]

def refs(knowledge,category):
    return [{'id':r['id'],'version':r['version'],'source_id':r['source_id'],'description':r['description'],'severity':r['severity']} for r in active(knowledge,category)]

class ThreatRepository:
    def __init__(self,path):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True);self.lock=threading.RLock()
        with self.connect() as c:
            c.executescript('''
            CREATE TABLE IF NOT EXISTS threat_records(id TEXT PRIMARY KEY,category TEXT,body TEXT);
            CREATE TABLE IF NOT EXISTS threat_versions(revision INTEGER PRIMARY KEY,version TEXT,digest TEXT,created_at TEXT,body TEXT);
            CREATE TABLE IF NOT EXISTS threat_changes(id INTEGER PRIMARY KEY,version TEXT,changed_ids TEXT,reason TEXT,timestamp TEXT);
            ''')
            count=c.execute('SELECT COUNT(*) FROM threat_versions').fetchone()[0]
        if not count:self.import_records({'records':seeds()},'Initial curated knowledge seed')
    def connect(self):return sqlite3.connect(self.path,timeout=30)
    def snapshot(self):
        with self.connect() as c:r=c.execute('SELECT body FROM threat_versions ORDER BY revision DESC LIMIT 1').fetchone()
        return json.loads(r[0]) if r else None
    def import_records(self,bundle,reason='JSON import'):
        validated=ThreatImport.model_validate(bundle)
        if validated.schema_version!='asent.threat-repository.v1':raise ValueError('Unsupported threat export schema')
        if len({r.id for r in validated.records})!=len(validated.records):raise ValueError('Duplicate record IDs in import')
        with self.lock,self.connect() as c:
            old=self.snapshot()
            current={r['id']:r for r in (old or {}).get('records',[])};changes=[]
            known_sources={r['id'] for r in current.values() if r['category']=='sources'}|{r.id for r in validated.records if r.category=='sources'}
            for record in validated.records:
                row=record.model_dump(mode='json')
                if row['source_id'] not in known_sources:raise ValueError('Unknown provenance source: '+row['source_id'])
                prior=current.get(row['id'])
                if prior:
                    if prior['category']!=row['category']:raise ValueError('Record category is immutable')
                    equivalent={k:v for k,v in prior.items() if k not in ('version','updated_at')}=={k:v for k,v in row.items() if k not in ('version','updated_at')}
                    if equivalent:continue
                    row['version']=prior['version']+1;row['updated_at']=now()
                current[row['id']]=row;changes.append(row['id'])
                c.execute('INSERT OR REPLACE INTO threat_records VALUES(?,?,?)',(row['id'],row['category'],json.dumps(row)))
            if old and not changes:return {'snapshot':old,'changed_ids':[],'affected_modules':[]}
            records=sorted(current.values(),key=lambda r:r['id']);revision=(old or {}).get('revision',0)+1
            version='TR-'+now()[:10].replace('-','.')+'.'+str(revision).zfill(3)
            state={'schema_version':'asent.threat-repository.v1','revision':revision,'version':version,'digest':digest(records),'rule_set_digest':digest([r for r in records if r['category']!='sources']),'updated_at':now(),'records':records,'module_digests':{m:module_digest(records,m) for m in MODULE_CATEGORIES}}
            c.execute('INSERT INTO threat_versions VALUES(?,?,?,?,?)',(revision,version,state['digest'],state['updated_at'],json.dumps(state)))
            c.execute('INSERT INTO threat_changes(version,changed_ids,reason,timestamp) VALUES(?,?,?,?)',(version,json.dumps(changes),reason,now()))
            affected=[m for m in MODULE_CATEGORIES if not old or old['module_digests'][m]!=state['module_digests'][m]]
            return {'snapshot':state,'changed_ids':changes,'affected_modules':affected}
    def enable(self,record_id,enabled):
        row=next((r for r in self.snapshot()['records'] if r['id']==record_id),None)
        if not row:raise KeyError(record_id)
        return self.import_records({'records':[{**row,'enabled':enabled}]},'Enable/disable '+record_id)
    def export(self):return {'schema_version':'asent.threat-repository.v1','records':self.snapshot()['records']}
    def history(self):
        with self.connect() as c:rows=c.execute('SELECT version,changed_ids,reason,timestamp FROM threat_changes ORDER BY id DESC').fetchall()
        return [{'version':v,'changed_ids':json.loads(ids),'reason':r,'timestamp':t} for v,ids,r,t in rows]
