import ast

def preflight(source):
    try:tree=ast.parse(source)
    except SyntaxError as e:return False,'Syntax error: '+str(e)
    for n in ast.walk(tree):
        if isinstance(n,(ast.Import,ast.ImportFrom)):
            modules=[a.name for a in n.names] if isinstance(n,ast.Import) else [n.module]
            if any(m not in ('pytest',) for m in modules):return False,'Imports outside permitted test vocabulary'
        if isinstance(n,ast.Attribute) and (n.attr.startswith('__') or n.attr in ('skip','xfail','system','execute','Popen')):return False,'Unsafe or non-discriminative test construct'
        if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id in ('eval','exec','open','compile','getattr','setattr','__import__'):return False,'Unsafe side effect / dynamic execution'
    if not any(isinstance(n,ast.Assert) for n in ast.walk(tree)):return False,'No assertion'
    if '/invoices/' not in source:return False,'No locality evidence for invoice security contract'
    return True,'Passed syntax and locality preflight; execution still required'

def is_pass(result):return result.get('available') and result.get('exit_code')==0 and result.get('passed',0)>0 and result.get('skipped',0)==0 and result.get('errors',0)==0

def killed(result):
    return result.get('available') and result.get('exit_code')==1 and result.get('failed',0)>0 and result.get('errors',0)==0 and any('AssertionError' in t.get('message','') or 'assert ' in t.get('message','') for t in result.get('tests',[]) if t['status']=='FAIL')

def judge(baseline,mutant,repeat,feasible):
    if not feasible:return {'accepted':False,'diagnosis':'INCONCLUSIVE','reason':'Counterfactual not independently shown to violate the contract'}
    if not is_pass(baseline):return {'accepted':False,'diagnosis':'PRE_EXISTING_TEST_GAP','reason':'Candidate test does not pass secure baseline'}
    if not is_pass(repeat):return {'accepted':False,'diagnosis':'INCONCLUSIVE','reason':'Baseline repeatability failed'}
    if killed(mutant):return {'accepted':True,'diagnosis':'PRESERVED_WITHIN_MODEL','reason':'Passes secure baseline twice and kills valid ownership bypass'}
    if is_pass(mutant):return {'accepted':False,'diagnosis':'ORACLE_WEAKENED','reason':'Test passes even when independently demonstrated ownership bypass is active'}
    return {'accepted':False,'diagnosis':'INCONCLUSIVE','reason':'Execution failure is not a mutant kill'}
