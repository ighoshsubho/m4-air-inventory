import importlib
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
FORMATS = {'char': 'b', 'uchar': 'B', 'short': 'h', 'ushort': 'H',
           'int': 'i', 'uint': 'I', 'long': 'q', 'ulong': 'Q',
           'half': 'e', 'float': 'f'}


class ConversionCasesTests(unittest.TestCase):
    def module(self):
        self.assertTrue((ROOT / 'tools/conversion_cases.py').exists(),
                        'Conversion corpus has not been implemented')
        return importlib.import_module('conversion_cases')

    def test_exhaustive_same_width_cases_have_correct_buffer_layouts(self):
        cases = self.module().all_cases()
        self.assertEqual(len(cases), 300)
        by_name = {case['name']: case for case in cases}
        self.assertEqual(len(by_name), 300)
        for src, src_fmt in FORMATS.items():
            for dst, dst_fmt in FORMATS.items():
                for width in (1, 2, 4):
                    suffix = '' if width == 1 else str(width)
                    name = f'convert_{src}{suffix}_to_{dst}{suffix}'
                    case = by_name[name]
                    values = list(range(1, width + 1))
                    self.assertEqual(set(case), {'name', 'source', 'format', 'threads',
                                                 'input', 'expected', 'tolerance', 'flags'})
                    self.assertEqual(case['source'], f'runtime/conversion-sources/{name}.metal')
                    self.assertEqual(case['format'], dst_fmt)
                    self.assertEqual(case['threads'], 1)
                    self.assertEqual(case['input'], struct.pack('<' + src_fmt * width, *values))
                    self.assertEqual(case['expected'], values)
                    output = struct.pack('<' + dst_fmt * width, *case['expected'])
                    self.assertEqual(len(output), struct.calcsize('<' + dst_fmt) * width)
                    self.assertEqual(case['tolerance'], 0)
                    self.assertEqual(case['flags'], [])

    def test_generate_sources_is_bounded_and_matches_every_case(self):
        module = self.module()
        self.assertTrue(hasattr(module, 'write_sources'), 'Source generation missing')
        import tempfile
        with tempfile.TemporaryDirectory(dir=ROOT / 'runtime/conversion-sources') as temp:
            root = Path(temp)
            paths = module.write_sources(root)
            self.assertEqual(len(paths), 300)
            self.assertLess(sum(path.stat().st_size for path in paths), 100000)
            for case in module.all_cases():
                src, dst = case['name'][len('convert_'):].split('_to_')
                text = (root / case['source']).read_text()
                self.assertEqual(text, '#include <metal_stdlib>\nusing namespace metal;\n'
                                 'kernel void probe(device const ' + src + ' *a [[buffer(0)]],\n'
                                 '                  device ' + dst + ' *b [[buffer(1)]]) {\n'
                                 '    b[0] = ' + dst + '(a[0]);\n}\n')
            self.assertEqual(module.write_sources(root), paths)

    def test_ir_analysis_distinguishes_calls_from_plain_casts_and_identity(self):
        module = self.module()
        self.assertTrue(hasattr(module, 'analyze_ir'), 'IR conversion analysis missing')
        text = ('target triple = "air64-apple-macosx26.0.0"\n'
                'declare float @air.convert.f.f32.s.i32(i32)\n'
                '%1 = call float @air.convert.f.f32.s.i32(i32 %x)\n'
                '%2 = sext i8 %x to i32\n'
                '%3 = trunc i64 %x to i32\n'
                '%4 = fpext half %x to float\n'
                '%5 = bitcast i32 %x to float\n')
        result = module.analyze_ir(text)
        self.assertEqual(result['calls'], ['air.convert.f.f32.s.i32'])
        self.assertEqual(result['conversion_opcodes'], ['bitcast', 'fpext', 'sext', 'trunc'])
        self.assertEqual(result['lowering'], 'air_call')
        plain = module.analyze_ir('%2 = zext i8 %x to i32\n')
        self.assertEqual(plain['calls'], [])
        self.assertEqual(plain['lowering'], 'llvm_cast_only')
        identity = module.analyze_ir('declare i32 @air.unused(i32)\n%1 = load i32, ptr %a\n')
        self.assertEqual(identity['calls'], [])
        self.assertEqual(identity['lowering'], 'no_conversion_call_or_opcode')

    def test_compile_only_preserves_failures_and_parses_successes(self):
        module = self.module()
        self.assertTrue(hasattr(module, 'validate_compile_only'), 'Compile validation missing')
        import json
        import tempfile
        from unittest.mock import patch
        calls = []

        def command(argv, cwd, prefix, timeout):
            # Deliberate unit-test fixtures, never used as compiler evidence.
            calls.append(argv)
            self.assertGreater(timeout, 0)
            self.assertLessEqual(timeout, 10)
            prefix = Path(prefix)
            prefix.parent.mkdir(parents=True, exist_ok=True)
            failed = '-c' in argv and 'uchar' in argv[argv.index('-c') + 1]
            timed_out = '-c' in argv and 'short' in argv[argv.index('-c') + 1]
            out, err = str(prefix) + '.stdout.txt', str(prefix) + '.stderr.txt'
            Path(out).write_text('UNIT TEST compiler version' if '--version' in argv else '')
            Path(err).write_text('fixture compile failure' if failed else '')
            if '-o' in argv:
                Path(argv[argv.index('-o') + 1]).write_text('%1 = sext i8 %x to i32\n')
            return {'argv': argv, 'exit_code': -9 if timed_out else 1 if failed else 0,
                    'timed_out': timed_out, 'stdout_path': out, 'stderr_path': err,
                    'timeout_seconds': timeout}

        with tempfile.TemporaryDirectory(dir=ROOT / 'runtime/conversion-sources') as temp:
            root = Path(temp)
            module.write_sources(root)
            selected = [row for row in module.all_cases() if row['name'] in
                        ('convert_char_to_char', 'convert_char_to_uchar', 'convert_char_to_short')]
            evidence = root / 'runtime/conversion-sources/evidence'
            with patch('probe_runner.run_command', side_effect=command):
                report = module.validate_compile_only(root, evidence, cases=selected, budget=30)
            self.assertEqual([row['status'] for row in report['cases']],
                             ['success', 'compile_failed', 'compile_failed'])
            self.assertEqual(report['successful'], 1)
            self.assertEqual(report['failed'], 2)
            self.assertEqual(report['unattempted'], 0)
            self.assertFalse(report['gpu_executed'])
            self.assertTrue(report['sequential'])
            self.assertIn('UNIT TEST', report['compiler_version'])
            self.assertEqual(report['cases'][0]['conversion_opcodes'], ['sext'])
            self.assertEqual(Path(report['cases'][1]['commands'][0]['stderr_path']).read_text(),
                             'fixture compile failure')
            self.assertTrue(report['cases'][2]['commands'][0]['timed_out'])
            self.assertEqual(json.loads((evidence / 'report.json').read_text()), report)
            self.assertEqual(len(calls), 5)
            self.assertTrue(all(argv[:2] in (['xcrun', 'metal'], ['xcrun', 'metal-opt']) for argv in calls))
            with self.assertRaises(FileExistsError):
                module.validate_compile_only(root, evidence, cases=selected)

    def test_unavailable_command_is_preserved_as_failure(self):
        module = self.module()
        import json
        import tempfile
        from unittest.mock import patch
        with tempfile.TemporaryDirectory(dir=ROOT / 'runtime/conversion-sources') as temp:
            root = Path(temp)
            module.write_sources(root)
            evidence = root / 'runtime/conversion-sources/evidence'
            with patch('probe_runner.run_command', side_effect=FileNotFoundError('UNIT TEST missing tool')):
                report = module.validate_compile_only(root, evidence, cases=module.all_cases()[:1])
            self.assertEqual(report['failed'], 1)
            self.assertEqual(report['compiler_command']['exit_code'], None)
            self.assertEqual(report['cases'][0]['status'], 'compile_failed')
            command = report['cases'][0]['commands'][0]
            self.assertIn('UNIT TEST missing tool', command['launch_error'])
            self.assertIn('UNIT TEST missing tool', Path(command['stderr_path']).read_text())
            self.assertEqual(json.loads((evidence / 'report.json').read_text()), report)


if __name__ == '__main__':
    unittest.main()
