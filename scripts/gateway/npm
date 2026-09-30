#!/usr/bin/env python3
"""Deliberate dependency action hold; requests never execute pip/npm on the host."""
import os
import shlex
import sys
import urllib.request
import json
rid=os.environ.get('ASENT_RUN_ID')
if not rid:sys.exit('Set ASENT_RUN_ID to the dashboard run ID. No installation performed.')
command=shlex.join([os.path.basename(sys.argv[0]),*sys.argv[1:]])
url=os.environ.get('ASENT_URL','http://127.0.0.1:8000')+'/api/runs/'+rid+'/dependency'
request=urllib.request.Request(url,data=json.dumps({'command':command}).encode(),headers={'Content-Type':'application/json'})
with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(request,timeout=180) as response:result=json.load(response)
print(json.dumps(result,indent=2));print('Gateway only: no host installation. Inspect the accepted reconstruction.')
sys.exit(0 if result['allowed'] else 3)
