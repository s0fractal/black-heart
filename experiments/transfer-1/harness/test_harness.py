"""Host-only checks; does not call a receiver or need authentication."""
import json
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

    def test_receipt_cannot_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'receipt.json';write_json(path,{'first':True})
            with self.assertRaises(FileExistsError): write_json(path,{'first':False})
            self.assertTrue(json.loads(path.read_text())['first'])

if __name__=='__main__': unittest.main()
