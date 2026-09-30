def verify_runtime(contract,events,receiver):
    violations=[]
    for e in events:
        if e['type'] in contract['denied']:
            # Interpreter startup is a harness action, not attributed to package behavior.
            if e['type']=='EXECUTE_BINARY' and ('python' in str(e['resource']) or 'strace' in str(e['resource'])):continue
            if e['type']=='PROCESS_CREATE' and 'CLONE_THREAD' in e['raw']:continue # local receiver thread, not arbitrary subprocess
            violations.append({'capability':e['type'],'resource':e['resource'],'evidence':e['raw'],'rule':'PDF_MINIMUM_CAPABILITY'})
    if receiver and 'NETWORK_CONNECT' in contract['denied']:
        violations.append({'capability':'CANARY_FLOW' if 'CAVR_FAKE_SECRET_NOT_A_CREDENTIAL' in receiver else 'UNJUSTIFIED_NETWORK_PAYLOAD','resource':'loopback mock receiver','evidence':receiver,'rule':'NO_SECRET_TO_NETWORK'})
    return violations
