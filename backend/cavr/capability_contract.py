from backend.orchestrator.hashing import digest
from backend.threat_repo.capability_rules import rule
from backend.threat_repo.repository import active

def infer(context,node):
    usage=context.dependency_context();is_pdf='pdf' in context.srs.lower() and any(x['package'].lower() in ('pypdf','pypdf2') and x['purpose']=='PDF text extraction' for x in usage.get('dependency_attributions',[]))
    pdf=rule(context.knowledge,'CAP-PDF-001')
    minimum_denied={'SECRET_ACCESS','NETWORK_CONNECT','PROCESS_CREATE','PERSISTENCE_WRITE','EXECUTE_BINARY'}
    supported=bool(is_pdf and pdf and minimum_denied.issubset(pdf['data'].get('denied',[])))
    contract={'purpose':'local invoice PDF text extraction' if is_pdf else 'unresolved','vocabulary':[r['name'] for r in active(context.knowledge,'behaviors')],'required':pdf['data'].get('required',[]) if supported else [],'denied':sorted(minimum_denied | set(pdf['data'].get('denied',[]) if pdf else [])),'evidence':usage,'knowledge_rule':pdf['id'] if pdf else None,'confidence':'rule-grounded' if supported else 'insufficient','package':node['name'],'authority':'SRS + actual call sites + reusable knowledge + minimum local-PDF boundary'}
    contract['digest']=digest(contract);return contract
