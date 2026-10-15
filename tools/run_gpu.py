"""Opt-in GPU sample checks. Stops the suite on any failure; not a sandbox."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import time
from probe_runner import run_command, parse_ir
from runtime_cases import all_cases

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--limit',type=int,default=13)
    parser.add_argument('--start',type=int,default=0)
    parser.add_argument('--output',default='runtime/results')
    parser.add_argument('--suite',choices=['original','conversions','atomics','extended-math'],default='original')
    parser.add_argument('--budget',type=float,default=180)
    args=parser.parse_args()
    started=time.monotonic()
    if args.budget<=0: raise SystemExit('Budget must be positive')
    if args.suite=='conversions':
        from conversion_cases import all_cases as selected_cases
    elif args.suite=='atomics':
        from atomic_cases import all_cases as selected_cases
    elif args.suite=='extended-math':
        from extended_math_cases import all_cases as selected_cases
    else: selected_cases=all_cases
    out=(ROOT/args.output).resolve()
    out.mkdir(parents=True,exist_ok=True)
    if (out/'results.json').exists():
        raise SystemExit('Refusing to overwrite runtime evidence; choose a new --output')
    host=out/'gpu-host'
    build=run_command(['xcrun','swiftc',str(ROOT/'runtime/GPUHost.swift'),'-o',str(host)],ROOT,out/'host-build',60)
    result={'scope':'Small defined-input GPU samples, not complete semantics or all intrinsics','suite':args.suite,'cases':[],'host_build':build,'budget_seconds':args.budget}
    def save(): (out/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    if build['exit_code']!=0: raise SystemExit('Host compilation failed; see logs')
    manifest=json.loads((ROOT/'probes/corpus.json').read_text())
    definitions={p['name']:p for p in manifest}
    selected=selected_cases()[max(0,args.start):max(0,args.start)+max(0,args.limit)]
    result['selected_cases']=len(selected)
    for case in selected:
        if time.monotonic()-started>=args.budget:
            result['stopped_reason']='total_budget'; save(); break
        name=case['name']; directory=out/name; directory.mkdir()
        source=ROOT/(case['source'] if 'source' in case else definitions[name]['source'])
        copied=directory/source.name; copied.write_bytes(source.read_bytes())
        air,ll,lib=[directory/(name+suffix) for suffix in ('.air','.ll','.metallib')]
        row={'name':name,'source':str(copied),'source_sha256':hashlib.sha256(copied.read_bytes()).hexdigest(),'commands':[],'status':'not_submitted','expected':case['expected'],'tolerance':case['tolerance'],'threads':case['threads'],'format':case['format'],'unordered':case.get('unordered',False)}
        result['cases'].append(row)
        commands=[['xcrun','metal','-std=metal3.2',*case['flags'],'-c',str(copied),'-o',str(air)],['xcrun','metal-opt','-S',str(air),'-o',str(ll)],['xcrun','metallib',str(air),'-o',str(lib)]]
        for i,command in enumerate(commands):
            if time.monotonic()-started>=args.budget:
                row['status']='not_submitted'; result['stopped_reason']='total_budget'; save(); return
            record=run_command(command,ROOT,directory/('prepare-'+str(i)),20); row['commands'].append(record)
            if record['exit_code']!=0:
                row['status']='preparation_failed'; save(); raise SystemExit('Preparation failed: '+name)
        row.update(parse_ir(ll.read_text()))
        row['artifact_sha256']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (air,ll,lib)}
        input_path=directory/'input.bin'; input_path.write_bytes(case['input'])
        output_path=directory/'output.bin'
        expected_bytes=len(case['expected'])*struct.calcsize(case['format'])
        spec={'library':str(lib),'function':'probe','threads':case['threads'],'buffers':[{'index':0,'input':str(input_path)},{'index':1,'size':expected_bytes,'output':str(output_path)}]}
        if 'required_width' in case: spec['requiredWidth']=case['required_width']
        if case.get('output_binding')==0:
            spec['buffers']=[{'index':0,'size':expected_bytes,'output':str(output_path)}]
        (directory/'dispatch.json').write_text(json.dumps(spec,indent=2)+'\n')
        row['input_hex']=case['input'].hex(); row['status']='submission_pending'; save()
        if time.monotonic()-started>=args.budget:
            row['status']='not_submitted'; result['stopped_reason']='total_budget'; save(); return
        execution=run_command([str(host),str(directory/'dispatch.json')],ROOT,directory/'execute',20)
        row['commands'].append(execution)
        if execution['exit_code']!=0:
            row['status']='execution_failed_or_unavailable'; save(); raise SystemExit('Execution stopped: '+name+'; inspect logs, do not auto-retry')
        row['execution']=json.loads(Path(execution['stdout_path']).read_text())
        actual=list(struct.unpack('<'+case['format']*len(case['expected']),output_path.read_bytes()))
        row['actual']=actual
        checked=sorted(actual) if case.get('unordered') else actual
        matches=[(a==e if case['tolerance']==0 else math.isfinite(a) and abs(a-e)<=case['tolerance']*max(1,abs(e))) for a,e in zip(checked,case['expected'])]
        row['status']='passed_sample' if all(matches) else 'output_mismatch'
        row['failed_indices']=[i for i,v in enumerate(matches) if not v]
        save(); print(name,row['status'],flush=True)
        if not all(matches): raise SystemExit('Output mismatch; no more submissions')
        if row['execution']['thermal_state_after']!=0: raise SystemExit('Thermal pressure increased; no more submissions')
        time.sleep(0.1)
    print(json.dumps({'cases':len(result['cases']),'passed':sum(r['status']=='passed_sample' for r in result['cases'])}))


if __name__=='__main__': main()
