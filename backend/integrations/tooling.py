import shutil
import sys
import importlib.util
import subprocess
from functools import lru_cache

@lru_cache(maxsize=1)
def strace_status(path):
    if not path:return False,'strace not installed'
    try:
        p=subprocess.run([path,'-o','/dev/null','true'],capture_output=True,text=True,timeout=3)
        return p.returncode==0,p.stderr[-700:] if p.returncode else None
    except Exception as e:return False,str(e)

def availability():
    out={}
    for name in ('git','strace','docker','podman','terraform','checkov','bandit','semgrep','ollama','bpftrace'):
        path=shutil.which(name);out[name]={'available':bool(path),'path':path}
    for name in ('docker','podman'):
        if out[name]['available']:
            try:
                p=subprocess.run([name,'info'],capture_output=True,text=True,timeout=4)
                out[name]['available']=p.returncode==0
                out[name]['reason']=None if p.returncode==0 else p.stderr[-300:]
            except Exception as e:out[name]['available']=False;out[name]['reason']=str(e)
    if importlib.util.find_spec('bandit') is not None:out['bandit']={'available':True,'path':sys.executable+' -m bandit','backend':'Python module in active interpreter'}
    out['strace']['installed']=bool(out['strace']['path'])
    out['strace']['available'],out['strace']['reason']=strace_status(out['strace']['path'])
    return out

def optional_scan(tool,path):
    if not shutil.which(tool):return {'available':False,'tool':tool,'reason':'Optional backend unavailable'}
    commands={'checkov':['checkov','-d',str(path),'--framework','terraform','--output','json','--quiet','--skip-download'], 'terraform':['terraform','fmt','-check','-recursive',str(path)]}
    try:
        p=subprocess.run(commands[tool],capture_output=True,text=True,timeout=40)
        return {'available':True,'tool':tool,'exit_code':p.returncode,'stdout':p.stdout[:30000],'stderr':p.stderr[:2000],'claim':'format check only' if tool=='terraform' else 'candidate scanner evidence'}
    except Exception as e:return {'available':False,'tool':tool,'reason':str(e)}
