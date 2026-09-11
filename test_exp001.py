#!/usr/bin/env python3
"""
EXP-001 kept reproducible: run the experiment and hold it to its registration.

Checked:

  1. the predictions the runner checks are the ones pre-registered in the
     experiment's README, parsed from the committed table rather than restated;
  2. a fresh run meets every registered prediction, including the side
     conditions on each refused step;
  3. neither the record nor the evidence bundle contains a secret key;
  4. amendment 1: the inputs the CLI consumed are the inputs the conclusion is
     about -- S5 holds the S2 retirement plus one valid, linked readoption, S6
     consumes the S2 registry, and S5 and S6 start from identical bytes;
  5-7. controls that must FAIL attribution while the registered outcome table
     can stay green: an empty S5 registry (review round 1's mutant), a changed
     retirement in S5, and a readoption linked to a different retirement;
  8. the evidence bundle reads back to the digests and ids in the record;
  9. the two attribution checks no file tamper can reach -- S6 reading the S2
     bytes, and S5 and S6 starting from the same document -- exercised
     directly on the recorded inputs, with the honest inputs as the positive.

Digests are not compared across runs: keys are ephemeral and receipts carry
timestamps, so they differ every time. The README says so.
"""
from __future__ import annotations

import hashlib
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

import crypto                                                    # noqa: E402
from controlled_forgetting import (                              # noqa: E402
    EpistemicTombstoneRegistry, RetirementMode, RuleIdentity,
)

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


def _secret_keys(directory):
    keys = []
    for name in os.listdir(directory):
        if name.endswith(".key"):
            with open(os.path.join(directory, name), encoding="utf-8") as fh:
                keys.append(fh.read().strip())
    return keys


def _write(path, doc):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, sort_keys=True)


class Exp001Test(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.runner = _load_runner()
        cls.workdir = tempfile.TemporaryDirectory()
        cls.evidence = os.path.join(cls.workdir.name, "evidence")
        cls.result = cls.runner.run_experiment(cls.workdir.name, evidence_dir=cls.evidence)
        cls.keys = _secret_keys(cls.workdir.name)

    @classmethod
    def tearDownClass(cls):
        cls.workdir.cleanup()

    def run_with(self, tamper):
        with tempfile.TemporaryDirectory() as workdir:
            return self.runner.run_experiment(workdir, tamper=tamper)

    def checks(self, result):
        return {m["check"] for m in result["attribution_mismatches"]}

    def test_1_the_runner_checks_the_registered_predictions(self):
        self.assertEqual(self.runner.PREDICTIONS, _registered_predictions())

    def test_2_every_prediction_holds(self):
        self.assertEqual(self.result["mismatches"], [])
        self.assertTrue(self.result["all_predictions_held"])
        self.assertEqual([s["step"] for s in self.result["steps"]],
                         ["S1", "S2", "S3", "S4", "S5", "S6"])
        self.assertTrue(self.result["main_document_unchanged_through_s3"])

    def test_3_no_secret_key_in_the_record_or_the_evidence(self):
        self.assertTrue(self.keys, "the run should have left sidecar keys to compare")
        texts = [json.dumps(self.result)]
        for name in os.listdir(self.evidence):
            with open(os.path.join(self.evidence, name), encoding="utf-8") as fh:
                texts.append(fh.read())
        for key in self.keys:
            for text in texts:
                self.assertNotIn(key, text)

    def test_4_the_honest_run_attributes_s5_to_its_readoption(self):
        self.assertEqual(self.result["attribution_mismatches"], [])
        self.assertTrue(self.result["holds"])
        by = {s["step"]: s for s in self.result["steps"]}
        self.assertEqual(by["S5"]["document_sha256_before"], by["S6"]["document_sha256_before"])
        self.assertEqual(by["S6"]["registry_sha256"], by["S2"]["registry_sha256"])
        self.assertEqual(by["S6"]["start_from"], "main immediately before S5")
        readopted = self.result["registries"]["R_same_readopted"]
        self.assertEqual(readopted["retirement_record_id"],
                         self.result["registries"]["R_same"]["retirement_record_id"])
        self.assertIsNotNone(readopted["readoption_record_id"])

    def test_5_an_empty_s5_registry_is_caught(self):
        """Review round 1's mutant. The outcome table alone stays green."""
        def empty_s5(name, path, context):
            if name == "R_same_readopted":
                _write(path, {"tombstones": {}, "readoptions": {}})

        result = self.run_with(empty_s5)
        self.assertTrue(result["all_predictions_held"],
                        "why attribution is needed: the registered outcomes cannot see this")
        self.assertFalse(result["holds"])
        self.assertIn("S5 retains the S2 retirement unchanged", self.checks(result))
        self.assertIn("S5 adds exactly one readoption, for the refuted subject",
                      self.checks(result))
        self.assertIsNone(result["registries"]["R_same_readopted"]["readoption_record_id"])

    def test_6_a_changed_retirement_in_s5_is_caught(self):
        def other_retirement(name, path, context):
            if name != "R_same_readopted":
                return
            sk, pk = crypto.generate_keypair()
            registry = EpistemicTombstoneRegistry()
            registry.retire(context["label"], "d" * 64, RetirementMode.REFUTED,
                            "a different retirement", sk, pk,
                            rule_identity=RuleIdentity.from_terms(
                                context["label"], context["other_reference"],
                                context["candidate"], context["input"]))
            registry.readopt(target_id=context["label"], justification="linked to it",
                             new_evidence_claim_id="f" * 64,
                             author_sk_hex=sk, author_pk_hex=pk)
            _write(path, registry.to_dict())

        result = self.run_with(other_retirement)
        self.assertFalse(result["holds"])
        self.assertIn("S5 retains the S2 retirement unchanged", self.checks(result))

    def test_7_a_readoption_linked_to_another_retirement_is_caught(self):
        def mislinked(name, path, context):
            if name != "R_same_readopted":
                return
            with open(context["paths"]["R_same"], encoding="utf-8") as fh:
                same_doc = json.load(fh)
            sk, pk = crypto.generate_keypair()
            elsewhere = EpistemicTombstoneRegistry()
            elsewhere.retire(context["label"], "d" * 64, RetirementMode.REFUTED,
                             "another retirement", sk, pk)
            readoption = elsewhere.readopt(target_id=context["label"], justification="x",
                                           new_evidence_claim_id="f" * 64,
                                           author_sk_hex=sk, author_pk_hex=pk)
            _write(path, {"tombstones": same_doc["tombstones"],
                          "readoptions": {context["label"]: readoption.to_dict()}})

        result = self.run_with(mislinked)
        self.assertFalse(result["holds"])
        self.assertTrue(
            self.checks(result) & {"S5 readoption is valid and linked to that retirement",
                                   "S5 registry file loads"},
            result["attribution_mismatches"])

    def test_8_the_evidence_bundle_reads_back_to_the_record(self):
        for name in ("R_same", "R_other", "R_same_readopted"):
            with self.subTest(registry=name):
                with open(os.path.join(self.evidence, f"{name}.json"), "rb") as fh:
                    data = fh.read()
                summary = self.result["registries"][name]
                self.assertEqual(hashlib.sha256(data).hexdigest(), summary["sha256"])
                registry = EpistemicTombstoneRegistry.from_document(json.loads(data))
                label = self.runner.LABEL
                self.assertEqual(registry.tombstones[label].record_id,
                                 summary["retirement_record_id"])
                readoption = registry.readoptions.get(label)
                self.assertEqual(readoption.record_id if readoption else None,
                                 summary["readoption_record_id"])


    def test_9_checks_no_file_tamper_can_reach(self):
        """
        S2 and S6 read the same path, and the runner copies the forks itself,
        so no replacement of an input file can make S6 read other bytes or make
        S5 and S6 start apart. Found by the mutation harness: removing either
        check killed nothing. They are exercised here on the recorded inputs.
        """
        import copy
        evidence = {}
        for name in ("R_same", "R_other", "R_same_readopted"):
            with open(os.path.join(self.evidence, f"{name}.json"), "rb") as fh:
                evidence[name] = fh.read()
        consumed = {"S2": evidence["R_same"], "S3": evidence["R_other"],
                    "S4": evidence["R_other"], "S5": evidence["R_same_readopted"],
                    "S6": evidence["R_same"]}
        pair = self.result["pair"]

        def attribution(consumed_in, steps_in):
            return {m["check"] for m in self.runner._attribution(
                consumed_in, steps_in, self.result["genesis_document_sha256"],
                pair["reference"], pair["candidate"])}

        self.assertEqual(attribution(consumed, self.result["steps"]), set())

        swapped = dict(consumed, S6=evidence["R_same_readopted"])
        self.assertIn("S6 consumes exactly the S2 registry",
                      attribution(swapped, self.result["steps"]))

        steps = copy.deepcopy(self.result["steps"])
        steps[5]["document_sha256_before"] = "0" * 64
        self.assertIn("S5 and S6 start from identical document bytes",
                      attribution(consumed, steps))


if __name__ == "__main__":
    unittest.main(verbosity=2)
