ACCEPTABLE={'CAVR':{'VERIFIED'},'SATRA':{'ACCEPT'},'SABLE':{'PRESERVED','NOT_APPLICABLE'}}
BLOCKING={'CAVR':{'REJECTED'},'SATRA':{'REJECT'},'SABLE':{'REGRESSED'}}

def decide(applicable,evidence,snapshot,input_hashes):
    reasons=[];blocking=[];statuses={}
    for module in applicable:
        rows=[e for e in evidence if e['analyzer']==module and not e.get('stale')]
        e=rows[-1] if rows else None
        if not e: reasons.append(f'{module}: current evidence missing');statuses[module]='PENDING';continue
        statuses[module]=e['status']
        if not e.get('integrity_valid',True):reasons.append(f'{module}: evidence integrity failed');continue
        if e['candidate_snapshot']!=snapshot or e['input_hash']!=input_hashes[module]:reasons.append(f'{module}: stale input or candidate snapshot');continue
        if e['status'] in BLOCKING[module] or e.get('blocking'):blocking.append(f"{module}: {e['status']}")
        elif e['status']=='RESTRICTED' and module=='CAVR' and e.get('details',{}).get('restriction_enforced'):continue
        elif e['status'] not in ACCEPTABLE[module]:reasons.append(f"{module}: {e['status']}")
    if blocking:return 'BLOCK',blocking+reasons,statuses
    if reasons:return 'REVIEW',reasons,statuses
    if not applicable:return 'REVIEW',['No supported security surfaces were established'],statuses
    return 'ACCEPT',['Every applicable module has current acceptable evidence for this exact candidate'],statuses
