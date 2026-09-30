import ast
from backend.orchestrator.hashing import digest

def build(context):
    p=context.policy.get('ownership',{});required=['subject','action','resource','expected_status','state_effect','authority']
    source=context.read('app/main.py')
    try:tree=ast.parse(source)
    except SyntaxError:return None
    routes=[ast.unparse(d) for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) for d in n.decorator_list]
    if not all(k in p for k in required) or 'FR-03' not in context.srs or not any('/invoices/{invoice_id}' in d for d in routes):return None
    if p['expected_status']!=403 or '403' not in context.srs:return None
    contract={'rule_id':'AUTHZ.IDOR.001','version':1,**p,'route':'GET /invoices/{invoice_id}','authority_sources':['SRS.md#FR-03','policy.json#ownership','trusted baseline app/main.py'],'srs_digest':digest(context.srs),'policy_digest':digest(context.policy),'preconditions':['authenticated normal user','existing invoice owned by another user'],'counterfactual':'bypass can_access_invoice ownership guard','scope':['app/main.py','app/security.py']}
    contract['digest']=digest(contract);return contract
