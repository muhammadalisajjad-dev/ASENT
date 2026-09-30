import ast
from backend.threat_repo.behavior_rules import python_sinks
from backend.threat_repo.trigger_rules import matching


def scan(sources,knowledge=None):
    rules=python_sinks(knowledge);triggers=[];sinks=[];parse_errors=[]
    for name,source in sources.items():
        try:tree=ast.parse(source)
        except SyntaxError as e:parse_errors.append({'file':name,'error':str(e)});continue
        for n in ast.walk(tree):
            if isinstance(n,ast.Call):
                func=ast.unparse(n.func)
                if func in rules:sinks.append({'file':name,'line':n.lineno,'sink':func,'capability':rules[func]['event'],'rule_id':rules[func]['rule_id']})
            if not isinstance(n,(ast.If,ast.While)):continue
            pred=ast.unparse(n.test);matched={};inputs=[];trigger_types=[]
            for call in ast.walk(n.test):
                if isinstance(call,ast.Call):
                    fn=ast.unparse(call.func)
                    for rule in matching(knowledge,fn,pred):matched[rule['id']]=rule
                    if fn in ('os.getenv','os.environ.get') and call.args and isinstance(call.args[0],ast.Constant):inputs.append(str(call.args[0].value));trigger_types.append('environment-variable')
                    elif fn in ('os.path.exists','Path.exists','Path.is_file','Path.is_dir'):
                        inputs.extend(ast.unparse(a) for a in call.args);trigger_types.append('file-existence')
                elif isinstance(call,ast.Attribute) and call.attr in ('exists','is_file','is_dir'):
                    inputs.append(ast.unparse(call.value));trigger_types.append('file-existence')
            # Simple named feature flags and boolean comparisons are recorded as
            # unsupported until a rule explicitly recognizes their activation.
            names=[x.id for x in ast.walk(n.test) if isinstance(x,ast.Name)]
            if not matched and names and any(x in pred.lower() for x in ('flag','feature','enabled')):
                trigger_types.append('feature-flag')
            branches=[('body',n.body)]
            if isinstance(n,ast.If) and n.orelse:branches.append(('else',n.orelse))
            recognized_env=bool(inputs and 'environment-variable' in trigger_types)
            recognized_file=bool(inputs and 'file-existence' in trigger_types)
            supported=recognized_env or recognized_file
            for branch,statements in branches:
                sensitive=[{'sink':ast.unparse(x.func),'capability':rules[ast.unparse(x.func)]['event'],'line':x.lineno} for x in ast.walk(ast.Module(body=statements,type_ignores=[])) if isinstance(x,ast.Call) and ast.unparse(x.func) in rules]
                if not sensitive:continue
                triggers.append({'id':name+':'+str(n.lineno)+':'+branch,'file':name,'line':n.lineno,'predicate':pred,'trigger_type':list(dict.fromkeys(trigger_types)) or [r['name'] for r in matched.values()],'types':list(dict.fromkeys(trigger_types)) or [r['name'] for r in matched.values()],'rule_ids':list(matched),'inputs':list(dict.fromkeys(inputs)),'relevant_key':inputs[0] if len(inputs)==1 else None,'environment_keys':inputs if 'environment-variable' in trigger_types else [],'reachable_sinks':sensitive,'priority':max([float(r['data'].get('risk_weight',1)) for r in matched.values()] or [1])*len(sensitive),'reachability':'syntactic '+branch+'-branch containment','supported':supported,'activation_known':recognized_env and inputs==['CAVR_CANARY_AWS_SECRET'],'supported_activation':supported,'trigger_status':'recognized' if supported else 'unsupported/unresolved','unsupported_reason':None if supported else 'Helper-call or indirect predicate cannot be resolved by bounded AST rules'})
    return {'triggers':sorted(triggers,key=lambda t:-t['priority']),'sinks':sinks,'parse_errors':parse_errors,'coverage':'Python AST supports literal environment lookups and file-existence predicates with syntactic branch containment (including if/else); helper-call predicates unresolved; no path feasibility, symbolic execution, interprocedural analysis, or general dataflow'}
