import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

class RuntimeCasesTests(unittest.TestCase):
    def test_integer_reference_and_half_layout(self):
        self.assertTrue((ROOT/'tools/runtime_cases.py').exists(), 'Runtime cases not implemented')
        import runtime_cases as cases
        row = cases.integer_case('integer_uint', 32, False, 1)
        self.assertEqual(row['expected'], [27, 3, 2, 402653184, 0, 27, 21, 192, 3, 24])
        self.assertEqual(len(cases.math_case('math_half4', 'e', 4)['input']), 24)
        self.assertEqual(len(cases.math_case('math_half4', 'e', 4)['expected']), 88)

    def test_collectives_have_unique_outputs_and_bounded_dispatch(self):
        import runtime_cases as cases
        rows=cases.all_cases()
        simd=next((r for r in rows if r['name']=='simd_float'),None)
        self.assertIsNotNone(simd,'Collective GPU cases missing')
        self.assertEqual(simd['threads'],32)
        self.assertEqual(simd['expected'][:8],[32,1,1,1,1,0,1,1])
        barrier=next(r for r in rows if r['name']=='barriers_threadgroup_atomic')
        self.assertEqual(barrier['expected'],list(range(32)))
        self.assertTrue(barrier['unordered'])

    def test_matrix_and_vote_have_finite_reference_outputs(self):
        import runtime_cases as cases
        rows={r['name']:r for r in cases.all_cases()}
        self.assertIn('simd_matrix_float',rows,'Matrix GPU cases missing')
        self.assertEqual(rows['simd_matrix_float']['expected'],[float(i%9==0) for i in range(64)])
        self.assertEqual(rows['simd_vote']['expected'][:3],[1,1,4294967295])

if __name__ == '__main__': unittest.main()
