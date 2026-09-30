import ast
import json
import subprocess
import sys
from pathlib import Path

def scan(root):
    try:
        p=subprocess.run([sys.executable,'-m','bandit','-r',str(Path(root)/'app'),'-f','json','-q'],capture_output=True,text=True,timeout=20)
        data=json.loads(p.stdout)
        return {'available':True,'tool':'Bandit','exit_code':p.returncode,'findings':[{'rule':x['test_id'],'severity':x['issue_severity'],'confidence':x['issue_confidence'],'file':x['filename'],'line':x['line_number'],'message':x['issue_text']} for x in data.get('results',[])]}
    except Exception as e:return {'available':False,'tool':'Bandit','reason':str(e),'findings':[]}
