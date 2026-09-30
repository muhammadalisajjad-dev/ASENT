from backend.orchestrator.event_router import route

def invalidated_modules(paths):return set(route(paths))

def invalidate_changed(store,run,context,emit):
    invalid=[]
    for e in store.evidence(run.run_id):
        if e['stale']:continue
        if e['input_hash']!=context.input_hash(e['analyzer']):
            store.invalidate(e['evidence_id']);invalid.append(e['analyzer'])
            emit('evidence.invalidated',{'reason':'Relevant code, policy, artifact or knowledge inputs changed','files':run.changed_surfaces.get(e['analyzer'],[]),'threat_repo_version':context.knowledge['version'],'rerun_required':True,'module':e['analyzer'],'evidence_id':e['evidence_id'],'old_input_hash':e['input_hash'],'new_input_hash':context.input_hash(e['analyzer'])})
    return sorted(set(invalid))
