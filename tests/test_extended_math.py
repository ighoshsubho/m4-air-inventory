import unittest
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
class ExtendedMathTests(unittest.TestCase):
    def test_cases_have_exact_output_sizes_and_valid_domain(self):
        self.assertTrue((ROOT/'tools/extended_math_cases.py').exists(),'Extended math suite missing')
        import extended_math_cases
        rows=extended_math_cases.all_cases()
        self.assertEqual(len(rows),12)
        self.assertTrue(all(r['threads']==1 and len(r['expected'])>10 for r in rows))
        self.assertTrue(all((ROOT/r['source']).exists() for r in rows))
if __name__=='__main__': unittest.main()
