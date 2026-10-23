"""Machine-readable interface to the same standalone conversion engine."""
import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from engine import Engine, Store, inspect_source, METHODS

def parser():
    p=argparse.ArgumentParser(description='Sparkitecture Software Converter — local engine, optional AI client')
    p.add_argument('--workspace',default=str(Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'Sparkitecture'/'SoftwareConverter'))
    p.add_argument('--json-file',help='Also save the complete machine-readable response to this path')
    sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('capabilities',help='Discover actual adapters, statuses, and permissions')
    q=sub.add_parser('inspect',help='Read input without executing it'); q.add_argument('source')
    q=sub.add_parser('convert',help='Run a real local job'); q.add_argument('source'); q.add_argument('--target',action='append',required=True,help='OS:Format, repeatable, e.g. Windows:EXE')
    q.add_argument('--method',choices=METHODS,default='Smart Auto'); q.add_argument('--python',default='',help='Build Python executable')
    q.add_argument('--entry',default=''); q.add_argument('--test-args',help='JSON array of arguments for source/output test')
    q.add_argument('--allow-execution',action='store_true',help='Authorize running source and output for the selected test')
    sub.add_parser('jobs'); sub.add_parser('recipes')
    q=sub.add_parser('job'); q.add_argument('id')
    q=sub.add_parser('handoff'); q.add_argument('id'); q.add_argument('--copy-to',help='Copy existing diagnostic ZIP to this file')
    return p

def main(argv=None):
    args=parser().parse_args(argv); code=0
    try:
        store=Store(args.workspace)
        if args.command=='capabilities':
            result={'schema':'sparkitecture.converter.v1','ai_required':False,'network_calls':False,
                    'implemented':['inspect','Python source to native EXE/executable via PyInstaller','selected behavioral baseline comparison','local recipes','diagnostic handoff'],
                    'unimplemented':['arbitrary binary reconstruction','hybrid rewriting','compatibility adapters','remote workers','native installers','Android packaging','automatic AI calls'],
                    'permissions':{'build':'explicit convert command','run_source_and_output':'--allow-execution plus --test-args','external_upload':'not implemented'},
                    'statuses':['VERIFIED_SELECTED_TEST','BUILT_UNTESTED','PARTIAL','UNRESOLVED','FAILED','CANCELLED'],
                    'exit_codes':{'0':'requested read or completed build/selected-test verification','1':'error','2':'partial','3':'unresolved','130':'cancelled'}}
        elif args.command=='inspect': result=inspect_source(args.source)
        elif args.command=='jobs': result=store.jobs()
        elif args.command=='recipes': result=store.recipes()
        elif args.command in ('job','handoff'):
            result=next((j for j in store.jobs() if j['id']==args.id),None)
            if result is None: raise ValueError('Unknown job ID')
            if args.command=='handoff':
                path=result.get('handoff')
                if not path: raise ValueError('This job has no diagnostic handoff')
                if args.copy_to:
                    dest=Path(args.copy_to)
                    if dest.exists(): raise ValueError('Copy destination already exists; choose a new path')
                    dest.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(path,dest); path=str(dest.resolve())
                result={'id':args.id,'handoff':path,'uploaded':False,'source_included':False}
        else:
            targets=[]
            for target in args.target:
                if ':' not in target: raise ValueError('Target must be OS:Format')
                osname,fmt=target.split(':',1)
                if not osname or not fmt: raise ValueError('Target must contain OS and format')
                targets.append((osname,fmt))
            tests=json.loads(args.test_args) if args.test_args is not None else None
            if tests is not None and (not isinstance(tests,list) or not all(isinstance(x,str) for x in tests)):
                raise ValueError('Test arguments must be a JSON array of strings')
            python=args.python
            if not python:
                settings=store.root/'settings.json'
                if settings.exists(): python=json.loads(settings.read_text()).get('python','')
            engine=Engine(store,lambda text:print(text,file=sys.stderr,flush=True))
            import signal
            signal.signal(signal.SIGINT,lambda *_:engine.stop.set())
            result=engine.convert(args.source,targets,args.method,python,args.entry,tests,args.allow_execution)
            code={'PARTIAL':2,'UNRESOLVED':3,'FAILED':1,'CANCELLED':130}.get(result['status'],0)
        response={'schema':'sparkitecture.converter.v1','ok':code==0,'result':result}
    except Exception as e:
        code=1; response={'schema':'sparkitecture.converter.v1','ok':False,'error':str(e)}
    text=json.dumps(response,indent=2,ensure_ascii=True)
    print(text)
    if args.json_file:
        path=Path(args.json_file); path.parent.mkdir(parents=True,exist_ok=True); path.write_text(text,encoding='utf-8')
    return code

if __name__=='__main__': sys.exit(main())
