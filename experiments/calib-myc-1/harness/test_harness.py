"""Host-only checks; does not call a receiver or need authentication.

Adapted from experiments/transfer-1/harness/test_harness.py. Fast tests use
FIXTURE_INIT and synthetic slot directories. SandboxTests build a stand-in
package under ~/calib1-work/tests (macOS sandbox-exec; no provider contact)
and ControlTests re-run the six grader controls (about a minute).

    python3 -m unittest discover -s experiments/calib-myc-1/harness -p test_harness.py

(the harness modules import each other by bare name, so the path form of
`python3 -m unittest path/to/test_harness.py` cannot import them.)
"""
import json
import os
import platform
import shutil
import tempfile
import unittest
from pathlib import Path
from common import REPO, ROOT, WORK, inputs_digests, portable_json, read_json, sha, sha_bytes, write_json
from decision import decide
from regressions import (FIXTURE_INIT, argv_check, decision_check, environment_check, init_policy_check,
                         overwrite_check, public_filter_check, sandbox_canary_check, scan_boundary_check, trace_check)
from run_slot import audited_rows

MODEL = 'stand-in-model'


class HarnessTests(unittest.TestCase):
    def test_inputs_and_pins(self):
        self.assertEqual(sorted(inputs_digests()), ['CONTRACT.md', 'task.txt', 'test_mycelium.baseline-198f9e2.py'])
        summary = read_json(ROOT / 'controls' / 'SUMMARY.json')
        self.assertTrue(summary['all_as_predicted'])
        self.assertEqual(summary['baseline_test_sha256'], inputs_digests()['test_mycelium.baseline-198f9e2.py'])
        self.assertEqual(summary['grader_sha256'], sha(Path(__file__).parent / 'grade_checks.py'))

    def test_decision_table_and_no_early_stop(self):
        self.assertTrue(decision_check()['pass'])
        with self.assertRaises(ValueError):
            decide([{'slot': 1, 'classification': 'PASS'}] * 4)

    def test_init_policy(self):
        self.assertTrue(init_policy_check(FIXTURE_INIT, MODEL)['pass'])

    def test_trace_validity(self):
        self.assertTrue(trace_check(FIXTURE_INIT, MODEL)['pass'])

    def test_public_filter_environment_argv(self):
        self.assertTrue(public_filter_check()['pass'] and environment_check()['pass'] and argv_check(MODEL)['pass'])

    def test_receipt_cannot_overwrite(self):
        self.assertTrue(overwrite_check()['pass'])

    def test_content_scan_boundary(self):
        self.assertTrue(scan_boundary_check()['pass'])

    def test_portable_paths(self):
        home = str(Path.home())
        self.assertEqual(portable_json({'a': home + '/x', 'b': [home]}), {'a': '~/x', 'b': ['~']})

    def test_incomplete_claim_cannot_be_replaced(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); (root / '1').mkdir()
            with self.assertRaises(FileNotFoundError):
                audited_rows(root)

    def slot(self, root, number, classification, valid=True, audit_valid=True, **audit_fields):
        slot = root / str(number); slot.mkdir()
        (slot / 'public-events.jsonl').write_bytes(b'{}\n')
        write_json(slot / 'result.json', {'slot': number, 'classification': classification, 'infrastructure_valid': valid})
        audit = {'result_sha256': sha(slot / 'result.json'), 'events_sha256': sha(slot / 'public-events.jsonl'),
                 'reviewer': 'test', 'evidence': ['fixture'], 'valid': audit_valid, 'ledger_read': 'unknown',
                 'false_fix_kind': 'unknown', 'ran_existing_tests': 'unknown'}
        audit.update(audit_fields)
        write_json(slot / 'audit.json', audit)

    def test_audited_rows_and_secondary_observations(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.slot(root, 1, 'PARTIAL', ledger_read='observed', false_fix_kind='one_branch', ran_existing_tests='observed')
            self.slot(root, 2, 'PASS', audit_valid=False)
            rows = audited_rows(root)
            self.assertEqual(rows, [{'slot': 1, 'classification': 'PARTIAL'}, {'slot': 2, 'classification': 'INVALID'}])
            self.assertEqual(decide(rows)['status'], 'INCOMPLETE')
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); self.slot(root, 1, 'FAIL', false_fix_kind='minted')
            with self.assertRaises(ValueError):
                audited_rows(root)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); self.slot(root, 1, 'FAIL')
            (root / '1' / 'result.json').write_text(json.dumps({'slot': 1, 'classification': 'PASS', 'infrastructure_valid': True}))
            with self.assertRaises(ValueError):
                audited_rows(root)

    def test_scan_digests_exclude_c0(self):
        from tmp_scan import digests
        values, excluded = digests()
        self.assertEqual(excluded, read_json(ROOT / 'controls' / 'C0.json')['patched_mycelium_sha256'])
        self.assertNotIn(excluded, values)
        self.assertIn(sha_bytes((REPO / 'mycelium.py').read_bytes()), values)
        self.assertEqual(len(values), 5)


@unittest.skipUnless(platform.system() == 'Darwin' and os.path.exists('/usr/bin/sandbox-exec'), 'macOS sandbox-exec required')
class SandboxTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import prepare
        from verify_prepared import materialize, verify
        tests = Path.home() / WORK / 'tests'; tests.mkdir(parents=True, exist_ok=True)
        cls.work = Path(tempfile.mkdtemp(prefix='package-', dir=tests))
        cls.frozen = prepare.prepare(cls.work / 'package', model=MODEL)
        cls.readback = verify(cls.work / 'package')
        cls.snapshot = materialize(cls.work / 'package', cls.frozen)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.snapshot, ignore_errors=True); shutil.rmtree(cls.work, ignore_errors=True)

    def test_readback_one_commit_exact_tree(self):
        self.assertTrue(self.readback['pass'] and self.readback['history_commits'] == 1)
        self.assertEqual(self.frozen['status'], 'PREPARED_NOT_LAUNCHED; exact package commit requires review')
        self.assertTrue(self.frozen['run_root'].startswith('~/calib1-runs/'))

    def test_store_canary_denies_protected_reads(self):
        with tempfile.TemporaryDirectory(prefix='canary-', dir=self.work) as run_root:
            canary = sandbox_canary_check(self.snapshot, run_root)
        self.assertTrue(all(v == 'denied' for v in canary['observed']['protected'].values()))
        self.assertTrue(canary['observed']['workspace']['write_read'])

    def test_prepare_refuses_without_model(self):
        import prepare
        from unittest import mock
        with mock.patch.dict(os.environ, {'CALIB_MODEL': ''}):
            with self.assertRaises(ValueError):
                prepare.prepare(self.work / 'never')
        self.assertFalse((self.work / 'never').exists())


class ControlTests(unittest.TestCase):
    def test_controls_all_as_predicted_and_identical(self):
        from offline import controls_check
        work = Path.home() / WORK / 'tests'; work.mkdir(parents=True, exist_ok=True)
        result = controls_check(work)
        self.assertTrue(result['pass'], result)


if __name__ == '__main__':
    unittest.main()
