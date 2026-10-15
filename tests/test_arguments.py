import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]

class ArgumentTests(unittest.TestCase):
    def module(self):
        path=ROOT/'tools/arguments.py'
        self.assertTrue(path.exists(),'Argument table generator missing')
        spec=importlib.util.spec_from_file_location('arguments',path)
        mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
        return mod

    def test_signature_preserves_nested_types(self):
        mod=self.module()
        result=mod.parse_signature('declare { i32, float } @air.example(<2 x float>, i8 addrspace(1)* nocapture, i32 immarg) #1')
        self.assertEqual(result['return_type'],'{ i32, float }')
        self.assertEqual(result['parameters'],['<2 x float>','i8 addrspace(1)* nocapture','i32 immarg'])

    def test_conversion_candidate_is_not_claimed_verified(self):
        mod=self.module()
        result=mod.conversion_candidate('air.convert.s.i32.f.f32.rtz.sat')
        self.assertEqual(result['input_type'],'float')
        self.assertEqual(result['output_type'],'i32')
        self.assertEqual(result['status'],'name_inferred_candidate')
        self.assertIsNone(mod.conversion_candidate('air.async_wg_copy'))

    def test_every_catalog_entry_has_a_row(self):
        self.module()
        subprocess.run([sys.executable,str(ROOT/'tools/arguments.py')],cwd=ROOT,check=True,timeout=30)
        data=json.loads((ROOT/'AIR-ARGUMENTS.json').read_text())
        catalog=json.loads((ROOT/'AIR-INTRINSICS.json').read_text())
        self.assertEqual({r['name'] for r in data['intrinsics']},{r['name'] for r in catalog['intrinsics']})
        self.assertEqual(len(data['intrinsics']),18117)
        unknown=next(r for r in data['intrinsics'] if r['name']=='air.async_wg_copy')
        self.assertEqual(unknown['status'],'unresolved')
        self.assertFalse(unknown['signatures'])
        markdown=(ROOT/'AIR-ARGUMENTS.md').read_text()
        self.assertEqual(sum(l.startswith('| air.') for l in markdown.splitlines()),18117)

if __name__=='__main__': unittest.main()
