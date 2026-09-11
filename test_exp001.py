#!/usr/bin/env python3
"""
EXP-001 kept reproducible: run the experiment and hold it to its registration.

Three things are checked, and only these:

  1. the predictions the runner checks are the ones pre-registered in the
     experiment's README, parsed from the committed table rather than restated;
  2. a fresh run meets every prediction, including the side conditions on each
     refused step (key file unchanged, a refusal that says so, no traceback);
  3. the record never contains a secret key.

Digests are not compared across runs: keys are ephemeral and receipts carry
timestamps, so they differ every time. The README says so.
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path[:1]:
    sys.path.insert(0, _HERE)

EXP_DIR = os.path.join(_HERE, "experiments", "EXP-001-refusal-readoption")


def _load_runner():
    spec = importlib.util.spec_from_file_location("exp001_run", os.path.join(EXP_DIR, "run.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _registered_predictions():
    """The table in README.md, parsed. Columns: step | registry | flags | exit |
    scope | document."""
    with open(os.path.join(EXP_DIR, "README.md"), encoding="utf-8") as fh:
        rows = [line for line in fh if re.match(r"^\| S\d ", line)]
    table = {}
    for row in rows:
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        step, _registry, _flags, exit_code, scope, document = cells[:6]
        scope_match = re.search(r"`(\w+)`", scope)
        entry = {
            "exit": int(exit_code),
            "scope": scope_match.group(1) if scope_match else None,
            "document": "unchanged" if document.startswith("unchanged") else "changes",
        }
        generation = re.search(r"generation (\d+)", document)
        if generation:
            entry["generation"] = int(generation.group(1))
        table[step] = entry
    return table


class Exp001Test(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.runner = _load_runner()
        cls.workdir = tempfile.TemporaryDirectory()
        cls.result = cls.runner.run_experiment(cls.workdir.name)
        cls.keys = []
        for name in os.listdir(cls.workdir.name):
            if name.endswith(".key"):
                with open(os.path.join(cls.workdir.name, name), encoding="utf-8") as fh:
                    cls.keys.append(fh.read().strip())

    @classmethod
    def tearDownClass(cls):
        cls.workdir.cleanup()

    def test_1_the_runner_checks_the_registered_predictions(self):
        self.assertEqual(self.runner.PREDICTIONS, _registered_predictions())

    def test_2_every_prediction_holds(self):
        self.assertEqual(self.result["mismatches"], [])
        self.assertTrue(self.result["all_predictions_held"])
        self.assertEqual([s["step"] for s in self.result["steps"]],
                         ["S1", "S2", "S3", "S4", "S5", "S6"])
        self.assertTrue(self.result["main_document_unchanged_through_s3"])

    def test_3_the_record_holds_no_secret_key(self):
        self.assertTrue(self.keys, "the run should have left sidecar keys to compare")
        text = json.dumps(self.result)
        for key in self.keys:
            self.assertNotIn(key, text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
