from backend.threat_repo.repository import active

def matching(knowledge,call,predicate):
    result=[]
    for r in active(knowledge,'triggers'):
        d=r['data'];matched=any(call.endswith(x) if x.startswith('.') else call.startswith(x) if x.endswith('.') else call==x for x in d.get('match_calls',[]) if isinstance(x,str))
        # These broad patterns require additional lexical support; never activate arbitrary predicates.
        if r['id']=='TRIG-CLOUD':matched=matched and any(x in predicate.lower() for x in ('ci','aws','cloud','azure'))
        if r['id']=='TRIG-SANDBOX':matched=matched and any(x in predicate.lower() for x in ('docker','container','sandbox'))
        if r['id']=='TRIG-METADATA':matched=matched and '169.254.169.254' in predicate
        if matched:result.append(r)
    return result
