import networkx as nx

def build(name,triggers,events,receiver):
    g=nx.DiGraph();g.add_node('package',label=name,kind='package')
    for i,t in enumerate(triggers):
        nid='trigger-'+str(i);g.add_node(nid,label=t['predicate'],kind='predicate',file=t.get('file'),line=t.get('line'),inputs=t.get('inputs',[]));g.add_edge(nid,'package',relation='conditions',provenance='static AST')
    for kind in ['SECRET_ACCESS','NETWORK_CONNECT']:
        for e in events:
            if e['type']!=kind:continue
            target=str(e['resource']);eid=f"event-{len([n for n in g if str(n).startswith('event-')])}";g.add_node(eid,label=target,kind=kind,source=e.get('source','unknown'),raw=e.get('raw'));g.add_edge('package',eid,relation='observed '+kind.lower(),provenance=e.get('source','unknown'))
    secret_nodes=[n for n,d in g.nodes(data=True) if d.get('kind')=='SECRET_ACCESS']
    network_nodes=[n for n,d in g.nodes(data=True) if d.get('kind')=='NETWORK_CONNECT']
    marker='CAVR_FAKE_SECRET_NOT_A_CREDENTIAL'
    targets=[n for n,d in g.nodes(data=True) if d.get('kind')=='NETWORK_CONNECT' and d.get('label') in ('127.0.0.1:18765',"('127.0.0.1', 18765)")]
    if marker in receiver and secret_nodes and targets:
        sources=secret_nodes
        # Receiver payload equality links the controlled fake source to a network
        # event; it is fixture-linked evidence, not general taint propagation.
        g.add_edge(sources[0],targets[0],relation='fixture-linked source-to-sink',provenance='receiver exact fake-marker equality',fixture_condition='controlled endpoint 127.0.0.1:18765',evidence='bounded controlled canary; not general taint analysis')
    return {'nodes':[{'id':n,**d} for n,d in g.nodes(data=True)],'edges':[{'source':a,'target':b,**d} for a,b,d in g.edges(data=True)]}
