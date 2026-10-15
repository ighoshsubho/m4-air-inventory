"""Source-generated same-width Metal conversion samples; no GPU execution.

Ten numeric scalar types, all ordered source/destination pairs (including
identity), and widths 1/2/4. No bool, three-lane padding, cross-width
constructors, boundary semantics, or claims that every cast is an AIR call.
"""
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIRECTORY = Path('runtime/conversion-sources')
FORMATS = {'char': 'b', 'uchar': 'B', 'short': 'h', 'ushort': 'H',
           'int': 'i', 'uint': 'I', 'long': 'q', 'ulong': 'Q',
           'half': 'e', 'float': 'f'}


def all_cases():
    """Return runner-compatible dictionaries without filesystem side effects."""
    cases = []
    for src, src_format in FORMATS.items():
        for dst, dst_format in FORMATS.items():
            for width in (1, 2, 4):
                suffix = '' if width == 1 else str(width)
                name = f'convert_{src}{suffix}_to_{dst}{suffix}'
                values = list(range(1, width + 1))
                cases.append({'name': name, 'source': str(SOURCE_DIRECTORY / (name + '.metal')),
                              'format': dst_format, 'threads': 1,
                              'input': struct.pack('<' + src_format * width, *values),
                              'expected': [float(v) for v in values] if dst in ('half', 'float') else values,
                              'tolerance': 0, 'flags': []})
    return cases


def write_sources(root=ROOT):
    """Write exactly 300 small MSL kernels under the corpus directory."""
    paths = []
    for case in all_cases():
        src, dst = case['name'][len('convert_'):].split('_to_')
        source = ('#include <metal_stdlib>\nusing namespace metal;\n'
                  f'kernel void probe(device const {src} *a [[buffer(0)]],\n'
                  f'                  device {dst} *b [[buffer(1)]]) {{\n'
                  f'    b[0] = {dst}(a[0]);\n}}\n')
        path = Path(root) / case['source']
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source)
        paths.append(path)
    return paths


def analyze_ir(text):
    """Report observed AIR calls and LLVM casts, including absence of both."""
    import re
    from probe_runner import parse_ir
    result = parse_ir(text)
    result['conversion_opcodes'] = sorted(set(re.findall(
        r'=\s*(trunc|zext|sext|fptrunc|fpext|fptoui|fptosi|uitofp|sitofp|bitcast)\b', text)))
    result['lowering'] = ('air_call' if result['calls'] else
                          'llvm_cast_only' if result['conversion_opcodes'] else
                          'no_conversion_call_or_opcode')
    return result


def validate_compile_only(root=ROOT, evidence=None, cases=None, budget=300):
    """Sequential source compilation and IR decoding; never link or run a GPU.

    Each case gets at most 10 seconds across compile+decode; the whole run
    (including compiler-version capture) also has a monotonic wall-time budget.
    Existing evidence is never overwritten. Failed commands retain their logs.
    """
    import hashlib
    import json
    import time
    from probe_runner import run_command

    root = Path(root).resolve()
    evidence = Path(evidence).resolve() if evidence is not None else root / SOURCE_DIRECTORY / 'compile-evidence'
    evidence.mkdir(parents=True, exist_ok=False)
    selected = all_cases() if cases is None else list(cases)
    start = time.monotonic()
    deadline = start + budget
    report = {'schema_version': 1, 'compile_only': True, 'gpu_executed': False,
              'sequential': True, 'per_case_timeout_seconds': 10,
              'per_command_timeout_seconds': 10, 'budget_seconds': budget,
              'compiler_version': None, 'compiler_command': None,
              'cases': [], 'successful': 0, 'failed': 0,
              'unattempted': len(selected), 'elapsed_seconds': 0.0}

    def save():
        report['elapsed_seconds'] = time.monotonic() - start
        report['successful'] = sum(row['status'] == 'success' for row in report['cases'])
        report['failed'] = len(report['cases']) - report['successful']
        report['unattempted'] = len(selected) - len(report['cases'])
        (evidence / 'report.json').write_text(json.dumps(report, indent=2) + '\n')

    def recorded_command(argv, cwd, prefix, timeout):
        command_start = time.monotonic()
        try:
            return run_command(argv, cwd, prefix, timeout)
        except OSError as exc:
            stdout, stderr = str(prefix) + '.stdout.txt', str(prefix) + '.stderr.txt'
            Path(stdout).touch(exist_ok=True)
            with Path(stderr).open('a') as stream:
                stream.write(str(exc) + '\n')
            return {'argv': list(argv), 'cwd': str(cwd), 'exit_code': None,
                    'elapsed_seconds': time.monotonic() - command_start,
                    'timeout_seconds': timeout, 'timed_out': False,
                    'stdout_path': stdout, 'stderr_path': stderr, 'launch_error': str(exc)}

    save()
    if time.monotonic() < deadline:
        version = recorded_command(['xcrun', 'metal', '--version'], root, evidence / 'compiler-version',
                              min(10, deadline - time.monotonic()))
        report['compiler_command'] = version
        report['compiler_version'] = Path(version['stdout_path']).read_text() + Path(version['stderr_path']).read_text()
        save()
    for case in selected:
        if time.monotonic() >= deadline:
            break
        case_deadline = min(deadline, time.monotonic() + 10)
        directory = evidence / case['name']
        directory.mkdir()
        source = root / case['source']
        snapshot = directory / source.name
        snapshot.write_bytes(source.read_bytes())
        air, ll = directory / 'kernel.air', directory / 'kernel.ll'
        row = {key: value for key, value in case.items() if key != 'input'}
        row.update(input_hex=case['input'].hex(), commands=[], status='compile_failed',
                   source_sha256=hashlib.sha256(snapshot.read_bytes()).hexdigest(),
                   source_snapshot=str(snapshot))
        report['cases'].append(row)
        commands = [(['xcrun', 'metal', '-std=metal3.2', *case['flags'], '-c', str(snapshot), '-o', str(air)], 'compile'),
                    (['xcrun', 'metal-opt', '-S', str(air), '-o', str(ll)], 'decode')]
        for argv, stage in commands:
            remaining = case_deadline - time.monotonic()
            if remaining <= 0:
                row['status'] = 'budget_exhausted'
                break
            record = recorded_command(argv, root, directory / stage, min(10, remaining))
            row['commands'].append(record)
            if record['exit_code'] != 0:
                row['status'] = stage + '_failed'
                break
        else:
            row.update(analyze_ir(ll.read_text()))
            row['status'] = 'success'
            row['air_path'], row['ll_path'] = str(air), str(ll)
            row['artifact_sha256'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (air, ll)}
        (directory / 'result.json').write_text(json.dumps(row, indent=2) + '\n')
        save()
    save()
    return report
