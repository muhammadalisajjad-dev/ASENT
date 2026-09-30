import re
from packaging.version import Version,InvalidVersion
from backend.threat_repo.repository import active

def canonical(name):return re.sub(r'[-_.]+','-',name).lower()

def packages(knowledge,node):
    matches=[]
    for r in active(knowledge,'package_threats'):
        d=r['data']
        if canonical(d.get('package',''))!=canonical(node['name']) or d.get('ecosystem')!=node.get('ecosystem','PyPI'):continue
        exact=d.get('version')==node['version'] and d.get('artifact_hash')==node.get('sha256') and bool(d.get('artifact_hash'))
        matches.append({**r,'match_strength':'exact artifact + version' if exact else 'name metadata only','automatic_verdict':False})
    return matches

def affected(version,data):
    if version in data.get('versions',[]):return True
    ranges=data.get('ranges',[])
    if not ranges:return False if data.get('versions') else None
    try:v=Version(version)
    except InvalidVersion:return None
    uncertain=False
    for item in ranges:
        if item.get('type') not in ('ECOSYSTEM','SEMVER'):uncertain=True;continue
        if item.get('type')=='SEMVER' and data.get('ecosystem') not in ('PyPI',):uncertain=True;continue
        within=False
        try:
            for event in item.get('events',[]):
                if 'introduced' in event:within=event['introduced']=='0' or v>=Version(event['introduced'])
                elif 'fixed' in event:
                    if within and v<Version(event['fixed']):return True
                    within=False
                elif 'last_affected' in event:
                    if within and v<=Version(event['last_affected']):return True
                    within=False
                elif 'limit' in event:
                    if within and v<Version(event['limit']):return True
                    within=False
                else:uncertain=True
            if within:return True
        except InvalidVersion:uncertain=True
    return None if uncertain else False

def vulnerabilities(knowledge,node):
    hits=[];unknown=[]
    for r in active(knowledge,'vulnerabilities'):
        d=r['data']
        if canonical(d.get('package',''))!=canonical(node['name']) or d.get('ecosystem')!=node.get('ecosystem','PyPI'):continue
        result=affected(node['version'],d)
        if result is True:hits.append(r)
        if result is None:unknown.append(r['id'])
    return hits,unknown
