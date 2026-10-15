"""CPU-only checks: these tests never submit GPU work."""
import importlib
import operator
from pathlib import Path
import re
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))


class AtomicCasesTests(unittest.TestCase):
    def module(self):
        self.assertTrue((ROOT / 'tools/atomic_cases.py').exists(),
                        'Atomic cases have not been implemented')
        return importlib.import_module('atomic_cases')

    def test_uint_device_trace_and_buffer_contract(self):
        module = self.module()
        case = next(c for c in module.all_cases() if c['name'] == 'atomic_uint_global')
        self.assertEqual(set(case), {'name', 'source', 'format', 'threads', 'input',
                                    'expected', 'tolerance', 'flags'})
        self.assertEqual(case['format'], 'I')
        self.assertEqual(case['threads'], 1)
        self.assertEqual(case['input'], struct.pack('<I', 12))
        self.assertEqual(case['expected'],
                         [12, 20, 20, 30, 30, 37, 37, 32, 32, 9, 9,
                          24, 24, 8, 8, 11, 11, 13, 0, 13, 13])
        self.assertEqual(case['tolerance'], 0)
        self.assertEqual(case['flags'], [])
        source = module.render_source(case['name'])
        self.assertIn('device atomic_uint *state [[buffer(0)]]', source)
        self.assertIn('device uint *out [[buffer(1)]]', source)
        operations = re.findall(r'\batomic_(\w+)_explicit\(', source)
        self.assertTrue({'load', 'store', 'exchange', 'fetch_add', 'fetch_sub',
                         'fetch_min', 'fetch_max', 'fetch_and', 'fetch_or',
                         'fetch_xor', 'compare_exchange_weak'} <= set(operations))
        self.assertIn('uint expected = 99u;', source)
        self.assertIn('out[19] = expected;', source)
        self.assertIn('out[20] = atomic_load_explicit(state, memory_order_relaxed);', source)
        self.assertNotRegex(re.sub(r'//[^\n]*', '', source),
                            r'\b(for|while|if|reinterpret_cast|as_type)\b')

    def test_integer_address_spaces_and_signed_trace(self):
        module = self.module()
        rows = {case['name']: case for case in module.all_cases()}
        names = {f'atomic_{scalar}_{space}' for scalar in ('int', 'uint')
                 for space in ('global', 'local')}
        self.assertTrue(names <= rows.keys(), 'Missing integer/address-space coverage')
        for name in names:
            case = rows[name]
            source = module.render_source(name)
            signed = name.startswith('atomic_int_')
            scalar = 'int' if signed else 'uint'
            self.assertEqual(case['format'], 'i' if signed else 'I')
            self.assertEqual(case['expected'],
                [12, 20, 20, -30, -30, -23, -23, -28, -28, -40, -40,
                 24, 24, 8, 8, 11, 11, 13, 0, 13, 13] if signed else
                rows['atomic_uint_global']['expected'])
            if name.endswith('local'):
                self.assertIn(f'device const {scalar} *input [[buffer(0)]]', source)
                self.assertIn(f'threadgroup atomic_{scalar} storage;', source)
                self.assertLess(source.index('atomic_store_explicit(state, input[0]'),
                                source.index('atomic_load_explicit(state'))
            else:
                self.assertIn(f'device atomic_{scalar} *state [[buffer(0)]]', source)
            code = re.sub(r'//[^\n]*', '', source)
            self.assertNotRegex(code, r'\b(for|while|if|reinterpret_cast|as_type|barrier)\b')
            indices = [int(i) for i in re.findall(r'out\[(\d+)\] =', source)]
            self.assertEqual(indices, list(range(len(case['expected']))))

    def test_float_exact_trace_and_only_header_supported_operations(self):
        module = self.module()
        rows = {case['name']: case for case in module.all_cases()}
        self.assertIn('atomic_float_global', rows, 'Missing device float atomics')
        self.assertEqual(set(rows), {f'atomic_{scalar}_{space}'
                         for scalar in ('int', 'uint') for space in ('global', 'local')}
                         | {'atomic_float_global'})
        case = rows['atomic_float_global']
        self.assertEqual(case['format'], 'f')
        self.assertEqual(case['input'], struct.pack('<f', 1.5))
        self.assertEqual(case['expected'],
                         [1.5, 2.5, 2.5, 4.0, 4.0, 4.5, 4.5, 3.5, 0.0, 3.5, 3.5])
        self.assertEqual(case['tolerance'], 0)
        source = module.render_source(case['name'])
        self.assertIn('device atomic_float *state [[buffer(0)]]', source)
        self.assertEqual(set(re.findall(r'\batomic_(\w+)_explicit\(', source)),
                         {'load', 'store', 'exchange', 'fetch_add', 'fetch_sub',
                          'compare_exchange_weak'})
        self.assertIn('float expected = 99.0f;', source)
        self.assertIn('out[9] = expected;', source)
        self.assertIn('out[10] = atomic_load_explicit(state, memory_order_relaxed);', source)
        # Every expected value is exactly representable as float32.
        self.assertEqual(list(struct.unpack('<11f', struct.pack('<11f', *case['expected']))),
                         case['expected'])


    def test_independent_cpu_model_checks_every_output_and_defined_range(self):
        for case in self.module().all_cases():
            floating, signed = case['format'] == 'f', case['format'] == 'i'
            state = struct.unpack('<' + case['format'], case['input'])[0]
            trace = [state]
            state = 2.5 if floating else 20
            trace.append(state)
            replace = lambda old, new: new
            operations = ([(replace, 4.0), (operator.add, 0.5), (operator.sub, 1.0)]
                if floating else [(replace, -30 if signed else 30), (operator.add, 7),
                    (operator.sub, 5), (min, -40 if signed else 9), (max, 24),
                    (operator.and_, 15), (operator.or_, 3), (operator.xor, 6)])
            for operation, operand in operations:
                trace.append(state)
                state = operation(state, operand)
                trace.append(state)
                if floating:
                    self.assertEqual(struct.unpack('<f', struct.pack('<f', state))[0], state)
                else:
                    self.assertGreaterEqual(state, -2147483648 if signed else 0)
                    self.assertLessEqual(state, 2147483647 if signed else 4294967295)
            self.assertNotEqual(state, 99, 'Weak CAS must never take its success path')
            trace.extend([0, state, state])
            self.assertEqual(trace, case['expected'], case['name'])

    def test_generation_is_explicit_repeatable_and_does_not_clobber(self):
        module = self.module()
        self.assertTrue(hasattr(module, 'write_sources'), 'Missing explicit source generator')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = module.write_sources(root)
            self.assertEqual(len(paths), 5)
            for case, path in zip(module.all_cases(), paths):
                self.assertEqual(path, root / case['source'])
                self.assertEqual(path.read_text(), module.render_source(case['name']))
            self.assertEqual(module.write_sources(root), paths)
            paths[0].write_text('unrelated pre-existing source')
            with self.assertRaises(FileExistsError):
                module.write_sources(root)
            self.assertEqual(paths[0].read_text(), 'unrelated pre-existing source')


if __name__ == '__main__':
    unittest.main()
