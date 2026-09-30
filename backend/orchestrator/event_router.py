from pathlib import PurePosixPath
AUTHORITY={'SRS.md','policy.json','plan.md'}
MANIFESTS={'requirements.txt','pyproject.toml','poetry.lock','package.json','package-lock.json','dependencies.lock.json','uv.lock'}

def route(paths,event_kind='file.changed'):
    result={'CAVR':[],'SATRA':[],'SABLE':[]}
    for p in paths:
        name=PurePosixPath(p).name
        if name in AUTHORITY:
            for m in result:result[m].append(p)
        elif name in MANIFESTS or p.startswith('vendor/'):
            result['CAVR'].append(p);result['SATRA'].append(p)
        elif p.endswith(('.tf','.tf.json','.tfvars')) or p.startswith('infra/'):
            result['SABLE'].append(p)
        elif p.endswith('.py'):
            result['SATRA'].append(p)
            if not p.startswith('tests/'):result['CAVR'].append(p)
        elif 'config' in p:
            for m in result:result[m].append(p)
    if event_kind=='dependency.intercepted':result['CAVR'].append('<dependency-action>')
    return {k:sorted(set(v)) for k,v in result.items() if v}
