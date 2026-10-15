"""Deterministic single-thread atomic samples using only public Metal APIs.

The input buffer contains one initialized scalar at binding 0. Binding 1 is
an ordinary scalar output array. Every fetch records both its previous value
and a subsequent atomic load; weak CAS deliberately mismatches and records
false, the overwritten expected argument, and the unchanged final state.

This module does not compile or execute GPU work.
"""
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1]

# Reviewed literal traces, independent of the source renderer and GPU output.
# uint: 12 -> store20 -> exchange30 -> +7 -> -5 -> min9 -> max24
#       -> &15 (8) -> |3 (11) -> ^6 (13); CAS(expected99) fails.
# int:  12 -> store20 -> exchange(-30) -> +7 (-23) -> -5 (-28)
#       -> min(-40) -> max24; remaining bitwise/CAS trace matches uint.
_UINT_EXPECTED = (12, 20, 20, 30, 30, 37, 37, 32, 32, 9, 9,
                  24, 24, 8, 8, 11, 11, 13, 0, 13, 13)
_INT_EXPECTED = (12, 20, 20, -30, -30, -23, -23, -28, -28, -40, -40,
                 24, 24, 8, 8, 11, 11, 13, 0, 13, 13)
_SPECS = {
    f'atomic_{scalar}_{space}': (scalar, space, fmt, 12, expected)
    for scalar, fmt, expected in [('uint', 'I', _UINT_EXPECTED),
                                  ('int', 'i', _INT_EXPECTED)]
    for space in ('global', 'local')
}
# Header 32023.883: float supports device load/store/exchange/add/sub/CAS
# only. There are no public threadgroup float or float min/max/bitwise overloads.
# All arithmetic below is exact in binary32: 4 + 0.5 - 1 = 3.5.
_SPECS['atomic_float_global'] = ('float', 'global', 'f', 1.5,
    (1.5, 2.5, 2.5, 4.0, 4.0, 4.5, 4.5, 3.5, 0.0, 3.5, 3.5))


def all_cases():
    """Return fresh descriptors; source paths are relative to the lab root."""
    return [dict(name=name, source=f'runtime/atomic-sources/{name}.metal',
                 format=fmt, threads=1, input=struct.pack('<' + fmt, initial),
                 expected=list(expected), tolerance=0, flags=[])
            for name, (_, _, fmt, initial, expected) in _SPECS.items()]


def render_source(name):
    """Render original, finite public-API source with no atomic pointer casts."""
    scalar, space, _, _, _ = _SPECS[name]
    signed = scalar == 'int'
    suffix = '' if signed else 'u'
    store, mismatch, desired, final = '20' + suffix, '99' + suffix, '77' + suffix, '13'
    operations = [('exchange', -30 if signed else 30), ('fetch_add', 7),
                  ('fetch_sub', 5), ('fetch_min', -40 if signed else 9),
                  ('fetch_max', 24), ('fetch_and', 15),
                  ('fetch_or', 3), ('fetch_xor', 6)]
    if scalar == 'float':
        suffix = 'f'
        store, mismatch, desired, final = '2.5f', '99.0f', '77.0f', '3.5'
        operations = [('exchange', 4.0), ('fetch_add', 0.5), ('fetch_sub', 1.0)]
    binding = (f'device atomic_{scalar} *state' if space == 'global'
               else f'device const {scalar} *input')
    lines = ['#include <metal_stdlib>', 'using namespace metal;', '',
             '// Dispatch exactly one GPU thread.',
             f'kernel void probe({binding} [[buffer(0)]],',
             f'                  device {scalar} *out [[buffer(1)]]) {{']
    if space == 'local':
        lines += [f'    threadgroup atomic_{scalar} storage;',
                  f'    threadgroup atomic_{scalar} *state = &storage;',
                  '    atomic_store_explicit(state, input[0], memory_order_relaxed);']
    lines += ['    out[0] = atomic_load_explicit(state, memory_order_relaxed);',
              f'    atomic_store_explicit(state, {store}, memory_order_relaxed);',
              '    out[1] = atomic_load_explicit(state, memory_order_relaxed);']
    index = 2
    for operation, operand in operations:
        lines.append(f'    out[{index}] = atomic_{operation}_explicit(state, {operand}{suffix}, memory_order_relaxed);')
        lines.append(f'    out[{index + 1}] = atomic_load_explicit(state, memory_order_relaxed);')
        index += 2
    lines += [f'    // State is {final}, so expected=99 cannot match, even for weak CAS.',
              f'    {scalar} expected = {mismatch};',
              f'    out[{index}] = {scalar}(atomic_compare_exchange_weak_explicit(state, &expected, {desired}, memory_order_relaxed, memory_order_relaxed));',
              f'    out[{index + 1}] = expected;',
              f'    out[{index + 2}] = atomic_load_explicit(state, memory_order_relaxed);',
              '}', '']
    return '\n'.join(lines)


def write_sources(root=ROOT):
    """Materialize sources explicitly, refusing to overwrite differing files."""
    paths = []
    for case in all_cases():
        path = Path(root) / case['source']
        text = render_source(case['name'])
        if path.exists():
            if path.read_text() != text:
                raise FileExistsError(f'Refusing to replace differing source: {path}')
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('x') as output:
                output.write(text)
        paths.append(path)
    return paths


if __name__ == '__main__':
    for path in write_sources():
        print(path)
