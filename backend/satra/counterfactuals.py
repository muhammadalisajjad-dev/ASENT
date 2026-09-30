import ast
from pathlib import Path

def mutate_ownership(root):
    path=Path(root)/'app/security.py'
    tree=ast.parse(path.read_text());found=False
    for node in tree.body:
        if isinstance(node,ast.FunctionDef) and node.name=='can_access_invoice':node.body=[ast.Return(ast.Constant(True))];found=True
    if not found:return False
    ast.fix_missing_locations(tree);path.write_text(ast.unparse(tree)+'\n');return True
