"""Bounded API-specific exception validated against the actual package source + adapter AST."""
import ast

def disabled_jbig2_sinks(artifact,context):
    source=artifact['sources'].get('pypdf/filters.py','')
    if not source:return []
    tree=ast.parse(source);allowed=[]
    for node in ast.walk(tree):
        if not isinstance(node,ast.ClassDef) or node.name!='JBIG2Decode':continue
        for func in node.body:
            if not isinstance(func,ast.FunctionDef):continue
            # Both supported methods fail/return before calling the optional decoder.
            guards=[n for n in ast.walk(func) if isinstance(n,ast.If) and 'configuration.jbig2dec_binary' in ast.unparse(n.test) and any(isinstance(x,(ast.Raise,ast.Return)) for x in n.body)]
            if guards:
                allowed += [x.lineno for x in ast.walk(func) if isinstance(x,ast.Call) and ast.unparse(x.func)=='subprocess.run']
    # Require ALL candidate PdfReader uses to occur under this disabling context manager.
    reads=0;guarded=0
    for p in context.manifest:
        if p.startswith(('app/','vendor/')) and p.endswith('.py'):
            try:t=ast.parse(context.read(p))
            except SyntaxError:return []
            calls=[n for n in ast.walk(t) if isinstance(n,ast.Call) and ast.unparse(n.func)=='PdfReader'];reads+=len(calls)
            for n in ast.walk(t):
                if isinstance(n,ast.With) and any(isinstance(i.context_expr,ast.Call) and ast.unparse(i.context_expr.func)=='apply_configuration' and any(k.arg=='jbig2dec_binary' and isinstance(k.value,ast.Constant) and k.value.value is None for k in i.context_expr.keywords) for i in n.items):
                    guarded+=sum(isinstance(x,ast.Call) and ast.unparse(x.func)=='PdfReader' for x in ast.walk(n))
    return allowed if reads and reads==guarded else []
