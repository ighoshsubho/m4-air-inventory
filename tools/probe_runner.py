"""Sequential compile-only Metal probes; no GPU execution."""
import re
import argparse
import hashlib
import json
import os
import pathlib
import signal
import subprocess
import time


def run_command(argv, cwd, prefix, timeout=20):
    prefix = pathlib.Path(prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    stdout_path, stderr_path = str(prefix) + '.stdout.txt', str(prefix) + '.stderr.txt'
    start = time.monotonic()
    timed_out = False
    with open(stdout_path, 'w') as out, open(stderr_path, 'w') as err:
        process = subprocess.Popen(argv, cwd=cwd, stdout=out, stderr=err, start_new_session=True)
        try:
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGKILL)
            code = process.wait()
    return {'argv': list(argv), 'cwd': str(cwd), 'exit_code': code,
            'elapsed_seconds': time.monotonic() - start, 'timeout_seconds': timeout,
            'timed_out': timed_out, 'stdout_path': stdout_path, 'stderr_path': stderr_path}


def parse_ir(text):
    triple = re.search(r'^target triple = "([^"]+)"', text, re.M)
    return {
        'declarations': [line for line in text.splitlines() if line.startswith('declare ') and '@air.' in line],
        'calls': sorted(set(re.findall(r'\bcall\b[^\n]*?@([\w.$-]+)', text)) & set(re.findall(r'@(air\.[\w.$-]+)', text))),
        'metadata_labels': sorted(set(re.findall(r'^!(air\.[\w.]+)\s*=', text, re.M)) | set(re.findall(r'!"(air\.[^"\n]+)"', text))),
        'target_triple': triple.group(1) if triple else None,
    }


def run_corpus(root, specs, evidence, max_seconds=180):
    root, evidence = pathlib.Path(root).resolve(), pathlib.Path(evidence).resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    manifest = {'schema_version': 1, 'compile_only': True, 'gpu_executed': False,
                'sequential': True, 'per_command_timeout_seconds': 20,
                'budget_seconds': max_seconds, 'probes': [], 'successful': 0, 'failed': 0,
                'unattempted': len(specs), 'elapsed_seconds': 0.0}
    (evidence / 'probe-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    for spec in specs:
        if time.monotonic() - start >= max_seconds:
            break
        source = root / spec['source']
        name = spec.get('name', source.stem)
        directory = evidence / 'probes' / name
        directory.mkdir(parents=True, exist_ok=True)
        air, ll = directory / (name + '.air'), directory / (name + '.ll')
        row = dict(spec, name=name, source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                   commands=[], air_path=str(air), ll_path=str(ll))
        # Snapshot source with every recorded attempt, including failed compilation.
        snapshot = directory / source.name
        snapshot.write_bytes(source.read_bytes())
        row['source_snapshot'] = str(snapshot)
        command = ['xcrun', 'metal', '-std=' + spec.get('standard', 'metal3.2'), *spec.get('flags', []), '-c', str(source), '-o', str(air)]
        row['commands'].append(run_command(command, root, directory / 'compile', timeout=min(20, max_seconds - (time.monotonic() - start))))
        if row['commands'][-1]['exit_code'] == 0 and time.monotonic() - start < max_seconds:
            row['commands'].append(run_command(['xcrun', 'metal-opt', '-S', str(air), '-o', str(ll)], root, directory / 'decode', timeout=min(20, max_seconds - (time.monotonic() - start))))
        row['status'] = 'success' if len(row['commands']) == 2 and all(c['exit_code'] == 0 for c in row['commands']) else 'failed'
        if row['status'] == 'success':
            row.update(parse_ir(ll.read_text()))
        manifest['probes'].append(row)
        manifest['successful' if row['status'] == 'success' else 'failed'] += 1
        manifest['elapsed_seconds'] = time.monotonic() - start
        manifest['unattempted'] = len(specs) - len(manifest['probes'])
        (directory / 'result.json').write_text(json.dumps(row, indent=2) + '\n')
        (evidence / 'probe-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
        print(f"{name}: {row['status']}", flush=True)
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=pathlib.Path, default=pathlib.Path(__file__).resolve().parents[1])
    parser.add_argument('--spec', default='probes/corpus.json')
    parser.add_argument('--evidence', default='evidence')
    parser.add_argument('--budget', type=float, default=180)
    args = parser.parse_args()
    result = run_corpus(args.root, json.loads((args.root / args.spec).read_text()), args.root / args.evidence, args.budget)
    print(json.dumps({key: result[key] for key in ('successful', 'failed', 'unattempted', 'elapsed_seconds')}))
