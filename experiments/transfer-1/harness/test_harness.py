"""Host-only checks; does not call a receiver or need authentication."""
import json
import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from common import verify_inputs, write_json
from controls import sources
from decision import decide
from offline import decision_checks
from regressions import crash_checks
from run_slot import audited_rows

class HarnessTests(unittest.TestCase):
    def test_frozen_inputs_and_control_distinctness(self):
        self.assertEqual(len(verify_inputs()),8)
        values=list(sources().values())
        self.assertEqual(len(values),len(set(values)))

    def test_every_binary_schedule_and_stopping(self):
        self.assertTrue(decision_checks()['pass'])
        with self.assertRaises(ValueError): decide([{'arm':'P','pass':True,'valid':True}])

    def test_incomplete_claim_cannot_be_replaced(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'1').mkdir()
            with self.assertRaises(FileNotFoundError): audited_rows(root)

    def test_submission_crash_is_not_infrastructure_failure(self):
        with tempfile.TemporaryDirectory() as td:
            crash_checks(Path(td))

    def test_content_scan_ignores_names_and_detects_hash_only(self):
        from tmp_scan import SCANNER
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/'one').write_bytes(b'a'*(1024*1024-4)+b'TRANSFER-1')
            (root/'two').write_bytes(b'no marker here')
            request={'roots':[td],'markers_hex':[b'transfer-1'.hex()],
                     'digests':[hashlib.sha256(b'no marker here').hexdigest()]}
            result=subprocess.run([sys.executable,'-I','-c',SCANNER],input=json.dumps(request),
                                  text=True,capture_output=True,check=True,timeout=10)
            report=json.loads(result.stdout)
            self.assertEqual({Path(x['path']).name for x in report['matches']},{'one','two'})
            self.assertEqual(report['errors'],[])

    def test_receipt_cannot_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'receipt.json';write_json(path,{'first':True})
            with self.assertRaises(FileExistsError): write_json(path,{'first':False})
            self.assertTrue(json.loads(path.read_text())['first'])

if __name__=='__main__': unittest.main()
