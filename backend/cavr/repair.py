from packaging.version import Version
from packaging.specifiers import SpecifierSet
try:
    import z3
except ImportError:z3=None

def rank_repairs(current,candidates,constraint='',verified_candidate_ids=()):
    choices=[]
    for c in candidates:
        # Eligibility is supplied by the service only after real verification;
        # proposal fields and caller booleans are never evidence.
        if c.get('rejected') or c.get('candidate_id') not in verified_candidate_ids:continue
        if c['name']==current['name'] and constraint and Version(c['version']) not in SpecifierSet(constraint):continue
        # Small compatible version, transitive path, upgrade, explicit API replacement.
        level=c.get('level',0 if c['name']==current['name'] else 3)
        if level==3 and not c.get('api_slice'):continue
        v1,v2=Version(current['version']),Version(c['version'])
        delta=sum(abs(a-b)*w for a,b,w in zip((v1.release+(0,0,0))[:3],(v2.release+(0,0,0))[:3],(100,10,1)))
        compatibility=bool(c.get('api_slice')) if level==3 else True
        if not compatibility:continue
        security=functional=0
        disruption=10*c.get('files_changed',0)
        cost=1000*level+delta+disruption-security-functional
        choices.append({**c,'compatibility':'API slice verified' if level==3 else 'same package line','score':{'level_cost':1000*level,'version_delta':delta,'change_disruption':disruption,'security_credit':security,'functional_credit':functional},'cost':cost})
    if not choices:return []
    if z3:
        solver=z3.Optimize();choice=z3.Int('repair_choice');solver.add(choice>=0,choice<len(choices));solver.minimize(z3.Sum([z3.If(choice==i,c['cost'],0) for i,c in enumerate(choices)]))
        if solver.check()==z3.sat:
            selected=solver.model()[choice].as_long();choices=[choices[selected]]+sorted([c for i,c in enumerate(choices) if i!=selected],key=lambda c:c['cost'])
    else:choices.sort(key=lambda c:c['cost'])
    return choices
