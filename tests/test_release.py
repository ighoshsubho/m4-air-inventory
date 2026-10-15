import hashlib
import json
import math
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ReleaseTests(unittest.TestCase):
    def test_release_is_text_only_and_has_no_personal_paths(self):
        forbidden = [b'/' + b'Users/', b'/' + b'home/', b'/' + b'var/folders/', b'/' + b'private/var/']
        manifest = ROOT / 'RELEASE-MANIFEST.json'
        self.assertTrue(manifest.exists(), 'Sanitized export has not been built')
        for relative, digest in json.loads(manifest.read_text())['files'].items():
            data = (ROOT / relative).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), digest, relative)
            data.decode('utf-8')
            for token in forbidden:
                self.assertNotIn(token, data, relative)
            self.assertNotIn(b'\x00', data, relative)
            self.assertNotIn(Path(relative).suffix, ['.air', '.metallib', '.bin', '.pyc'])

    def test_catalog_and_runtime_summary_agree(self):
        path = ROOT / 'GPU-RESULTS.json'
        self.assertTrue(path.exists(), 'Sanitized execution record missing')
        results = json.loads(path.read_text())
        self.assertEqual(len(results['cases']), 338)
        symbols = set()
        for case in results['cases']:
            self.assertEqual(case['status'], 'passed_sample')
            self.assertEqual(len(case['actual']), len(case['expected']))
            actual = sorted(case['actual']) if case['unordered'] else case['actual']
            for a, e in zip(actual, case['expected']):
                self.assertTrue(a == e if case['tolerance'] == 0 else math.isfinite(a) and abs(a-e) <= case['tolerance'] * max(1, abs(e)))
            source = ROOT / case['source']
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), case['source_sha256'])
            symbols.update(case['calls'])
        self.assertEqual(len(symbols), 573)
        coverage = json.loads((ROOT / 'GPU-COVERAGE.json').read_text())
        self.assertEqual(len(coverage['intrinsics']), 18116)
        self.assertEqual(sum(r['status'] == 'passed_sample' for r in coverage['intrinsics']), 353)
        self.assertFalse(coverage['summary']['complete'])
        names = (ROOT / 'AIR-2.8-INTRINSICS.txt').read_text().splitlines()
        self.assertEqual(len(names), 18116)
        self.assertEqual(len(set(names)), len(names))


if __name__ == '__main__':
    unittest.main()
