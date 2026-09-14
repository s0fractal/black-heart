"""Offline route-artifact checks; no model session or evaluator run."""
import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parent
HERE=ROOT/'examples/model-experience/cm4/routes'
sys.path.insert(0,str(HERE))
import verify_retained

class CM4RoutesTest(unittest.TestCase):
    def test_retained_routes_restore_without_model_or_replay(self):
        report=verify_retained.main()
        self.assertTrue(report['ok'])
        self.assertFalse(report['model_invoked'])
        self.assertFalse(report['evaluator_replayed'])
        self.assertEqual(report['results']['save']['records_found'],1)
        self.assertEqual(report['results']['replay']['records_found'],3)

    def test_wrong_source_snapshot_is_rejected(self):
        # Even internally valid packets cannot substitute a different input HEAD.
        original=json.loads((HERE/'preparation.json').read_text())
        original['save']['head']='0'*40
        with tempfile.TemporaryDirectory() as td:
            p=Path(td); (p/'preparation.json').write_text(json.dumps(original))
            with patch('check_result.HERE',p):
                with self.assertRaises(AssertionError): verify_retained.main()

if __name__=='__main__': unittest.main()
