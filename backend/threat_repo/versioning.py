from backend.orchestrator.hashing import digest
MODULE_CATEGORIES={
 'CAVR':{'vulnerabilities','package_threats','behaviors','triggers','source_sink','capability_rules'},
 'SATRA':{'satra_rules'},
 'SABLE':{'sable_rules'},
}

def module_digest(records,module):
    rows=[r for r in records if r['category'] in MODULE_CATEGORIES[module]]
    sources={r['source_id'] for r in rows}
    rows += [r for r in records if r['category']=='sources' and r['id'] in sources]
    return digest(sorted(rows,key=lambda r:r['id']))

def compatible(old,new,module):return old['module_digests'][module]==new['module_digests'][module]
