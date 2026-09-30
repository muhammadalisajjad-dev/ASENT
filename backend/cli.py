"""Local CLI for the same HTTP gateway used by the dashboard."""
import argparse
import json
import os
import shlex
import sys
import time
from pathlib import Path
import httpx
from backend.integrations.research_loader import load as load_research

def main():
    parser=argparse.ArgumentParser(prog='asent',description='ASENT local assurance gateway (start scripts/start.sh first)')
    parser.add_argument('--url',default=os.environ.get('ASENT_URL','http://127.0.0.1:8000'))
    sub=parser.add_subparsers(dest='action',required=True)
    for action in ('run','watch'):
        p=sub.add_parser(action);p.add_argument('--scenario',default='safe');p.add_argument('--repository');p.add_argument('--repair',action='store_true');p.add_argument('--wait',action='store_true');p.add_argument('--srs');p.add_argument('--plan')
    p=sub.add_parser('dependency');p.add_argument('--run',required=True);p.add_argument('command',nargs=argparse.REMAINDER)
    p=sub.add_parser('replay');p.add_argument('bundle');p.add_argument('--wait',action='store_true');p.add_argument('--repair',action='store_true')
    p=sub.add_parser('research');p.add_argument('manifest');p.add_argument('--opt-in',action='store_true');p.add_argument('--wait',action='store_true')
    p=sub.add_parser('report');p.add_argument('run');p.add_argument('--output')
    sub.add_parser('capabilities')
    args=parser.parse_args()
    with httpx.Client(base_url=args.url,timeout=180,trust_env=False) as client:
        def call(method,path,body=None):
            r=client.request(method,'/api'+path,json=body);r.raise_for_status();return r.json()
        if args.action in ('run','watch'):
            body={'scenario':args.scenario,'repository':str(Path(args.repository).resolve()) if args.repository else None,'mode':'watch' if args.action=='watch' else 'manual','auto_repair':args.repair}
            for key in ('srs','plan'):
                if getattr(args,key):body[key]=Path(getattr(args,key)).read_text()
            result=call('POST','/runs',body)
        elif args.action=='dependency':
            command=args.command[1:] if args.command[:1]==['--'] else args.command
            result=call('POST','/runs/'+args.run+'/dependency',{'command':shlex.join(command)})
            print(json.dumps(result,indent=2));return 0 if result['allowed'] else 3
        elif args.action=='replay':result=call('POST','/replay',{'bundle':str(Path(args.bundle).resolve()),'auto_repair':args.repair})
        elif args.action=='research':result=call('POST','/runs',load_research(args.manifest,args.opt_in))
        elif args.action=='report':
            result=call('GET','/runs/'+args.run+'/report')
            if args.output:Path(args.output).write_text(json.dumps(result,indent=2));print(args.output);return 0
        else:result=call('GET','/capabilities')
        if getattr(args,'wait',False):
            rid=result['run_id'];deadline=time.monotonic()+300
            while result['lifecycle'] not in ('COMPLETE','ERROR','INTERRUPTED') and time.monotonic()<deadline:
                time.sleep(.5);result=call('GET','/runs/'+rid)
            if result['lifecycle'] not in ('COMPLETE','ERROR','INTERRUPTED'):raise TimeoutError('Run remains active; inspect dashboard')
        print(json.dumps(result,indent=2))
    return 0

if __name__=='__main__':
    try:raise SystemExit(main())
    except (httpx.HTTPError,ValueError,FileNotFoundError,TimeoutError) as e:print(str(e),file=sys.stderr);raise SystemExit(2)
