from backend.threat_repo.repository import active
from backend.threat_repo.behavior_rules import normalize_name

def correlate(knowledge,events,receiver,contract):
    """Sequence evidence only; exact inert-marker receipt is the bounded causal witness."""
    hits=[]
    for r in active(knowledge,'source_sink'):
        d=r['data'];sources=[(i,e) for i,e in enumerate(events) if normalize_name(e['type'])==d.get('source_event')]
        sinks=[(i,e) for i,e in enumerate(events) if normalize_name(e['type'])==d.get('sink_event')]
        pairs=[(a,b) for ai,a in sources for bi,b in sinks if ai<bi]
        if pairs:
            a,b=pairs[0];observed='CAVR_FAKE_SECRET_NOT_A_CREDENTIAL' in receiver and d.get('source_event')=='SECRET_READ' and d.get('sink_event')=='NETWORK_CONNECT'
            hits.append({'rule_id':r['id'],'rule_version':r['version'],'source_id':r['source_id'],'severity':r['severity'],'source_event':a,'sink_event':b,'causal_witness':'exact fake marker received by local harness' if observed else 'ordered co-occurrence only; data-flow not proven','causal_confirmed':observed,'unjustified':a['type'] in contract['denied'] or b['type'] in contract['denied'],'rationale':r['description']})
    return hits
