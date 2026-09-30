import json
import os
import httpx

def generate_tests(context):
    model=os.environ.get('ASENT_OLLAMA_MODEL')
    if not model:return {'available':False,'reason':'Optional Ollama disabled; set ASENT_OLLAMA_MODEL','candidates':[]}
    # Fixed localhost endpoint; never source code to a hosted model.
    try:
        r=httpx.post('http://127.0.0.1:11434/api/generate',json={'model':model,'stream':False,'format':'json','prompt':'Return JSON {"tests":[{"rule_id":"AUTHZ.IDOR.001","source":"pytest source using case fixture"}]}. Only local read-only requests through case fixture. Context: '+json.dumps(context)[:12000],'options':{'temperature':0,'num_predict':1200}},timeout=30,trust_env=False)
        r.raise_for_status();d=r.json();v=json.loads(d['response'])
        return {'available':True,'model':model,'candidates':v.get('tests',[])[:2],'tokens':d.get('eval_count')}
    except Exception as e:return {'available':False,'reason':str(e),'candidates':[]}
