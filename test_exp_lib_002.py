#!/usr/bin/env python3
"""EXP-LIB-002: the saved two-transition history verifies without regeneration,
and a fresh run confirms every pre-registered H and N prediction."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
EXP = _HERE / "experiments" / "EXP-LIB-002"


def _runner():
    spec = importlib.util.spec_from_file_location("exp_lib_002_run", EXP / "run.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class SavedHistoryTest(unittest.TestCase):
    """The committed run/ is evidence of one recorded run; it must verify here,
    on any host, without regenerating anything."""

    @classmethod
    def setUpClass(cls):
        cls.R = _runner()
        cls.run_dir = EXP / "run"
        cls.result = json.loads((cls.run_dir / "RESULT.json").read_text())

    def test_saved_history_verifies_without_regeneration(self):
        out = self.R.verify_saved(self.run_dir)
        self.assertTrue(out["all_ok"], out)
        self.assertEqual(out["T1_transition"], "COMPLETE")
        self.assertEqual(out["T2_transition"], "COMPLETE")

    def test_recorded_run_confirmed_every_prediction(self):
        self.assertTrue(self.result["all_confirmed"])
        self.assertEqual(set(self.result["verdicts"].values()), {"CONFIRMED"})
        self.assertEqual(len(self.result["verdicts"]), 14)

    def test_recorded_run_names_a_clean_source_commit(self):
        self.assertRegex(self.result["source_commit"], r"^[0-9a-f]{40}$")
        self.assertTrue(self.result["source_tree_clean"])

    def test_saved_run_holds_no_fixture_secret_key(self):
        secrets = [bytes([n] * 32).hex() for n in self.R.ROLE_SEEDS.values()]
        for p in self.run_dir.rglob("*"):
            if p.is_file():
                blob = p.read_bytes().decode("latin-1")
                for s in secrets:
                    self.assertNotIn(s, blob, f"secret fixture key found in {p}")

    def test_reproducibility_record_confirmed(self):
        rep = json.loads((EXP / "REPRODUCIBILITY.json").read_text())
        self.assertEqual(set(rep["verdicts"].values()), {"CONFIRMED"})


class FreshRunTest(unittest.TestCase):
    """Re-run the history from scratch: every H and N prediction must hold."""

    def test_fresh_run_confirms_h_and_n(self):
        R = _runner()
        with tempfile.TemporaryDirectory() as tmp:
            res = R.run_once(Path(tmp) / "run")
        refuted = {k: v for k, v in res["verdicts"].items() if v != "CONFIRMED"}
        self.assertFalse(refuted, json.dumps({k: res["observed"][k] for k in refuted},
                                             indent=2, ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()
