from backend.threat_repo.repository import refs
from backend.threat_repo.versioning import MODULE_CATEGORIES

def explanation(knowledge,module):
    records=[r for category in sorted(MODULE_CATEGORIES[module]) for r in refs(knowledge,category)]
    source_ids={r['source_id'] for r in records}
    return {'threat_repo_version':knowledge['version'],'digest':knowledge['digest'],'module_digest':knowledge['module_digests'][module],'rules':records,'sources':[r for r in knowledge['records'] if r['category']=='sources' and r['id'] in source_ids],'role':'Supporting reusable knowledge, combined with observed evidence and independent project obligations'}
