import ast
import difflib
from pathlib import Path
TOKENS={'owner','auth','user','role','invoice','password','execute','subprocess','path','pickle','request'}

def localize(baseline,candidate):
    regions=[];diffs=[]
    for p in sorted(Path(candidate).rglob('*.py')):
        if '__pycache__' in p.parts or '.git' in p.parts:continue
        rel=p.relative_to(candidate);old=Path(baseline)/rel;before=old.read_text() if old.exists() else '';after=p.read_text()
        changed=before!=after
        if changed:diffs+=list(difflib.unified_diff(before.splitlines(),after.splitlines(),fromfile=str(rel),tofile=str(rel),lineterm=''))
        try:tree=ast.parse(after)
        except SyntaxError as e:regions.append({'file':str(rel),'reason':'parse error','error':str(e),'changed':changed});continue
        for n in ast.walk(tree):
            if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and any(t in ast.unparse(n).lower() for t in TOKENS):
                if changed or str(rel).startswith('app/'):
                    regions.append({'file':str(rel),'function':n.name,'start':n.lineno,'end':n.end_lineno,'changed':changed,'reason':'Changed security region' if changed else 'Mandatory security authority/route region','families':['authorization','authentication'] if any(t in n.name for t in ('invoice','admin','user','login')) else ['input handling']})
    return {'regions':regions,'diff':'\n'.join(diffs)}
