import json
import tempfile
import unittest
import zipfile
import sys
import threading
from pathlib import Path
from engine import Store, Engine, inspect_source, unpack, inventory

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name); self.store=Store(self.root/'state')
    def tearDown(self): self.tmp.cleanup()
    def test_source_detection_without_execution(self):
        p=self.root/'app'; p.mkdir(); (p/'main.py').write_text('import os\nraise RuntimeError("must not run")')
        x=inspect_source(p); self.assertEqual(x['format'],'Python source'); self.assertEqual(x['imports'],['os'])
    def test_zip_traversal_rejected_before_extract(self):
        p=self.root/'bad.zip'
        with zipfile.ZipFile(p,'w') as z: z.writestr('ok.py',''); z.writestr('../escape.py','')
        with self.assertRaises(ValueError): unpack(p,self.root/'extracted')
        self.assertFalse((self.root/'extracted/ok.py').exists())
    def test_zip_case_collision_rejected(self):
        p=self.root/'bad.zip'
        with zipfile.ZipFile(p,'w') as z: z.writestr('main.py',''); z.writestr('MAIN.py','')
        with self.assertRaises(ValueError): unpack(p,self.root/'extracted')
    def test_unknown_target_handoff_preserves_source(self):
        p=self.root/'test.py'; p.write_text('print("ok")')
        result=Engine(self.store).convert(p,[('Android','APK')])
        self.assertEqual(result['status'],'UNRESOLVED'); self.assertEqual(p.read_text(),'print("ok")')
        with zipfile.ZipFile(result['handoff']) as z:
            self.assertIn('receipt.json',z.namelist()); self.assertFalse(any(n.endswith('.py') for n in z.namelist()))
        self.assertEqual(self.store.jobs()[0]['status'],'UNRESOLVED')
    def test_no_toolchain_is_honest_unresolved(self):
        p=self.root/'main.py'; p.write_text('print("ok")')
        r=Engine(self.store).convert(p,[('Windows','EXE')]); self.assertEqual(r['status'],'UNRESOLVED')
    def test_cancelled_before_build(self):
        p=self.root/'main.py'; p.write_text('print("ok")'); e=Engine(self.store); e.stop.set()
        self.assertEqual(e.convert(p,[('Windows','EXE')])['status'],'CANCELLED')
    def test_recipe_success_and_failure_are_separate(self):
        self.store.record_recipe('a',True,{'method':'direct'}); self.store.record_recipe('a',False,{'method':'direct'})
        r=self.store.recipes()[0]; self.assertEqual((r['successes'],r['failures']),(1,1))
    def test_recursive_workspace_rejected(self):
        (self.root/'main.py').write_text('print("ok")')
        r=Engine(self.store).convert(self.root,[('Windows','EXE')]); self.assertEqual(r['status'],'FAILED')
        self.assertIn('outside',r['error'])
    def test_active_command_cancel(self):
        from engine import Cancelled
        e=Engine(self.store); timer=threading.Timer(.4,e.stop.set); timer.start()
        try:
            with self.assertRaises(Cancelled):
                e.run_command([sys.executable,'-c','import time; time.sleep(60)'],self.root,self.root/'cancel.log',10)
        finally: timer.cancel()
    def test_cli_json_and_unresolved_exit(self):
        import subprocess
        p=self.root/'main.py'; p.write_text('print("ok")')
        r=subprocess.run([sys.executable,str(Path(__file__).parent/'cli.py'),'--workspace',str(self.root/'cli'), 'convert',str(p),'--target','Android:APK'],capture_output=True,text=True)
        self.assertEqual(r.returncode,3)
        self.assertEqual(json.loads(r.stdout)['result']['status'],'UNRESOLVED')

if __name__=='__main__': unittest.main()
