from backend.threat_repo.repository import active

def python_sinks(knowledge):
    return {call:{'event':r['data'].get('runtime_event',r['name']),'rule_id':r['id']} for r in active(knowledge,'behaviors') for call in r['data'].get('python_sinks',[]) if isinstance(call,str)}

def normalize_name(event):
    return {'SECRET_ACCESS':'SECRET_READ','PROCESS_CREATE':'PROCESS_EXEC','EXECUTE_BINARY':'NATIVE_EXEC'}.get(event,event)
