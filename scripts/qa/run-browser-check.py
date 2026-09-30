"""Run a real local server and browser check in one process/network namespace."""
import os
import subprocess
import sys
import time
from pathlib import Path
import httpx
root=Path(__file__).resolve().parents[2];os.chdir(root)
env={**os.environ,'ASENT_DATA':str(root/'runtime-browser')}
with (root/'reports/browser-server.log').open('w') as log:
    server=subprocess.Popen([sys.executable,'-m','uvicorn','backend.main:app','--host','127.0.0.1','--port','8000'],env=env,stdout=log,stderr=log)
    try:
        with httpx.Client(trust_env=False,timeout=2) as client:
            for i in range(40):
                try:
                    r=client.get('http://127.0.0.1:8000/api/health')
                    if r.status_code==200:break
                except httpx.HTTPError:pass
                time.sleep(.2)
            else:raise RuntimeError('Local server did not start')
        code=subprocess.run(['node','scripts/qa/browser-check.cjs'],env=env,timeout=180).returncode
    finally:server.terminate();server.wait(timeout=8)
raise SystemExit(code)
