"""Explicit OSV response import. An unavailable query cannot become an empty successful scan."""
from backend.orchestrator.run_context import now
from backend.orchestrator.hashing import digest
from backend.integrations.osv_adapter import OSV

def records(response,retrieved_at=None):
    advisories=response.get('vulns') if isinstance(response,dict) else None
    if advisories is None and isinstance(response,dict) and response.get('id'):advisories=[response]
    if not isinstance(advisories,list):raise ValueError('Expected an OSV vulnerability or query response with vulns array')
    stamp=retrieved_at or now();out=[]
    for v in advisories:
        if not isinstance(v,dict) or not v.get('id'):raise ValueError('OSV record requires an identifier')
        for index,item in enumerate(v.get('affected',[])):
            pkg=item.get('package',{})
            if not pkg.get('name') or not pkg.get('ecosystem'):raise ValueError('OSV affected record requires ecosystem and package')
            sev=str(v.get('database_specific',{}).get('severity','INFO')).upper();sev='MEDIUM' if sev=='MODERATE' else sev
            if sev not in ('INFO','LOW','MEDIUM','HIGH','CRITICAL'):sev='INFO'
            out.append({'id':str(v['id'])+'.'+str(index),'category':'vulnerabilities','name':str(v['id'])+' / '+pkg['name'],'description':v.get('summary',v.get('details',''))[:20000],'severity':sev,'source_id':'SRC-OSV','updated_at':stamp,'data':{'ecosystem':pkg['ecosystem'],'package':pkg['name'],'versions':item.get('versions',[]),'ranges':item.get('ranges',[]),'advisory_id':v['id'],'aliases':v.get('aliases',[]),'references':v.get('references',[]),'severity_scores':v.get('severity',[]),'retrieved_at':stamp,'last_updated':v.get('modified'),'source':'https://osv.dev/vulnerability/'+v['id'],'response_digest':digest(v)}})
    return {'schema_version':'asent.threat-repository.v1','records':out}

def query(name,version,ecosystem='PyPI'):
    result=OSV().query(name,version,ecosystem=ecosystem,live=True)
    if not result['available'] or not result.get('source','').startswith('https://api.osv.dev'):raise ValueError('OSV query unavailable; import a genuine saved OSV JSON response instead')
    return records(result['response'],result['retrieved_at']),result
