"""Refresh real release metadata and advisories; record origin, retrieval date and digest."""
import argparse
import json
import sys
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import httpx
from backend.config import ROOT
from backend.orchestrator.hashing import digest
from backend.integrations.osv_adapter import OSV
p=argparse.ArgumentParser();p.add_argument('--package',default='pypdf');p.add_argument('--version',default='6.19.0');args=p.parse_args()
query={'package':{'name':args.package,'ecosystem':'PyPI'},'version':args.version}
url=f'https://pypi.org/pypi/{args.package}/{args.version}/json'
response=httpx.get(url,timeout=15);response.raise_for_status();body=response.json()
record={'query':query,'retrieved_at':datetime.now(timezone.utc).isoformat(),'source':url,'response':body,'response_sha256':digest(body)}
folder=ROOT/'advisories';folder.mkdir(exist_ok=True);(folder/('registry-'+digest(query)+'.json')).write_text(json.dumps(record,indent=2))
print('Retrieved genuine PyPI metadata:',len(body.get('vulnerabilities',[])),'advisory entries')
result=OSV().query(args.package,args.version,live=True)
print('OSV:',result['mode'],'available:',result['available'])
if not result['available']:print(result.get('error'))
