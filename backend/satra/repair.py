import ast
from pathlib import Path
from backend.config import ROOT

def propose(root,evidence):
    root=Path(root);changed=[];details=evidence['details'] if 'details' in evidence else evidence
    contract=details.get('contract')
    if not contract or contract['rule_id']!='AUTHZ.IDOR.001':return []
    p=root/'app/security.py';tree=ast.parse(p.read_text())
    # Exact supported API slice. No arbitrary code generation or whole-file reset.
    for n in tree.body:
        if isinstance(n,ast.FunctionDef) and n.name=='can_access_invoice' and [a.arg for a in n.args.args]==['user','invoice']:
            n.body=ast.parse('return user["role"] == "admin" or invoice["owner_id"] == user["id"]').body
    ast.fix_missing_locations(tree);text=ast.unparse(tree)+'\n'
    if p.read_text()!=text:p.write_text(text);changed.append('app/security.py')
    if not details.get('oracle',{}).get('accepted',False):
        target=root/'tests/test_security.py';target.write_text((ROOT/'backend/satra/trusted_security.py').read_text());changed.append('tests/test_security.py')
    return changed
