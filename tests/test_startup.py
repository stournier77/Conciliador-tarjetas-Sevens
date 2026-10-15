import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('startup', ROOT/'launchers/arranque.py')
a = importlib.util.module_from_spec(spec); spec.loader.exec_module(a)

class StartupTests(unittest.TestCase):
    def test_timeout(self):
        with self.assertRaises(subprocess.TimeoutExpired):
            a.run([sys.executable, '-c', 'import time; time.sleep(10)'], timeout=.1)
    def test_zip_traversal(self):
        with tempfile.TemporaryDirectory() as t:
            t=Path(t)
            for name in ('../historico.xlsx', '/tmp/escape', 'runtime_mac/file', 'app\\..\\escape'):
                with zipfile.ZipFile(t/'bad.zip','w') as z: z.writestr(name,'bad')
                with self.assertRaises(ValueError): a.validate_zip(t/'bad.zip',t/'new')
    def test_preserve(self):
        with tempfile.TemporaryDirectory() as t:
            t=Path(t); source=t/'source'; target=t/'Archivos APP'
            (source/'app').mkdir(parents=True); (target/'app').mkdir(parents=True)
            (source/'app/main.py').write_text('new'); (target/'app/main.py').write_text('old')
            (target/'runtime_mac').mkdir(); (target/'runtime_mac/keep').write_text('runtime')
            (target/'custom.txt').write_text('custom')
            historical=t/'Conciliaciones Tarjetas Maveric'; historical.mkdir(); (historical/'keep.xlsx').write_bytes(b'history')
            a.deploy(source,target)
            self.assertEqual((target/'app/main.py').read_text(),'new')
            self.assertEqual((target/'runtime_mac/keep').read_text(),'runtime')
            self.assertEqual((target/'custom.txt').read_text(),'custom')
            self.assertEqual((historical/'keep.xlsx').read_bytes(),b'history')
            self.assertEqual(next((target/'backups').rglob('main.py')).read_text(),'old')
    def test_rollback(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as t:
            t=Path(t); source=t/'s'; target=t/'d'; source.mkdir(); target.mkdir()
            (source/'version.txt').write_text('new'); (target/'version.txt').write_text('old')
            real=a.shutil.copy2
            def fail(src,dst,*args,**kwargs):
                if Path(src)==source/'version.txt': raise OSError('simulated copy failure')
                return real(src,dst,*args,**kwargs)
            with patch.object(a.shutil,'copy2',side_effect=fail):
                with self.assertRaises(OSError): a.deploy(source,target)
            self.assertEqual((target/'version.txt').read_text(),'old')
    def test_bad_environment(self):
        from unittest.mock import patch
        with patch.object(a,'run',side_effect=subprocess.TimeoutExpired('probe',25)):
            self.assertFalse(a.healthy())

if __name__=='__main__': unittest.main()
