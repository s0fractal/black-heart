#!/usr/bin/env python3
"""
EXP-002 kept reproducible: run the experiment and hold it to its registration.

  1. the runner's predictions are the README table, parsed from the committed
     file rather than restated;
  2. a fresh run meets every registered prediction and every attribution check;
  3. neither the record nor the evidence contains a secret key;
  4-7. the registered controls, each a real file handed to the real CLI, must
     FAIL: absent evidence at S7, an accidentally permissive policy, an absent
     foreign readoption at S5, and a different assertion at S3;
  8. the evidence bundle, registries and policy both, reads back to the record;
  9. the checks no file tamper can reach (S8 reading the S2 bytes, S6 reading
     no policy, S6 and S8 starting with S7), exercised on the recorded inputs.
"""
from __future__ import annotations

import copy
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
from keystore import PRIVATE_KEY_SUFFIX                          # noqa: E402
from controlled_forgetting import (                              # noqa: E402
    EpistemicTombstoneRegistry, RetirementMode, RetirementRecord, RuleIdentity,
)

EXP_DIR = os.path.join(_HERE, "experiments", "EXP-002-issuer-factor")


def _load_runner():
    spec = importlib.util.spec_from_file_location("exp002_run", os.path.join(EXP_DIR, "run.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _registered_predictions():
    """README columns: step | starts from | registry | policy | extra flags |
    exit | scope | document."""
    with open(os.path.join(EXP_DIR, "README.md"), encoding="utf-8") as fh:
        rows = [line for line in fh if re.match(r"^\| S\d ", line)]
    table = {}
    for row in rows:
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        step, exit_code, scope, document = cells[0], cells[5], cells[6], cells[7]
        match = re.search(r"`(\w+)`", scope)
        entry = {"exit": int(exit_code), "scope": match.group(1) if match else None,
                 "document": "unchanged" if document.startswith("unchanged") else "changes"}
        generation = re.search(r"generation (\d+)", document)
        if generation:
            entry["generation"] = int(generation.group(1))
        table[step] = entry
    return table


def _write(path, doc):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, sort_keys=True)


def _read_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


class Exp002Test(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.runner = _load_runner()
        cls.workdir = tempfile.TemporaryDirectory()
        cls.evidence = os.path.join(cls.workdir.name, "evidence")
        cls.result = cls.runner.run_experiment(cls.workdir.name, evidence_dir=cls.evidence)
        cls.keys = []
        for name in os.listdir(cls.workdir.name):
            if name.endswith(PRIVATE_KEY_SUFFIX):
                with open(os.path.join(cls.workdir.name, name), encoding="utf-8") as fh:
                    cls.keys.append(fh.read().strip())

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

    def test_2_every_prediction_and_attribution_check_holds(self):
        self.assertEqual(self.result["mismatches"], [])
        self.assertEqual(self.result["attribution_mismatches"], [])
        self.assertTrue(self.result["holds"])
        by = {s["step"]: s for s in self.result["steps"]}
        self.assertEqual(by["S3"]["registry_sha256"], by["S6"]["registry_sha256"])
        self.assertIsNone(by["S6"]["policy_sha256"])
        self.assertEqual(self.result["registries"]["R_T+F"]["readoption_author"],
                         self.result["keys"]["F"])
        self.assertEqual(self.result["registries"]["R_T+T"]["readoption_author"],
                         self.result["keys"]["T"])

    def test_3_no_secret_key_in_the_record_or_the_evidence(self):
        self.assertTrue(self.keys)
        texts = [json.dumps(self.result)]
        for name in os.listdir(self.evidence):
            with open(os.path.join(self.evidence, name), encoding="utf-8") as fh:
                texts.append(fh.read())
        for key in self.keys:
            for text in texts:
                self.assertNotIn(key, text)

    def test_4_absent_evidence_at_s7_is_caught(self):
        def empty_s7(name, path, context):
            if name == "R_T+T":
                _write(path, {"tombstones": {}, "readoptions": {}})

        result = self.run_with(empty_s7)
        self.assertTrue(result["all_predictions_held"], "the outcome table cannot see this")
        self.assertFalse(result["holds"])
        self.assertIn("S7 keeps the S2 retirement unchanged", self.checks(result))
        self.assertIn("S7 adds exactly one readoption, by T", self.checks(result))

    def test_5_an_accidentally_permissive_policy_is_caught(self):
        """P also trusts a third key to lift, and S7's readoption is signed by it."""
        def permissive(name, path, context):
            sk_x, pk_x = context.setdefault("x", crypto.generate_keypair())
            if name == "R_T+T":
                registry = EpistemicTombstoneRegistry.from_document(
                    _read_json(context["paths"]["R_T"]))
                registry.readopt(target_id=context["label"], justification="third key",
                                 new_evidence_claim_id="f" * 64,
                                 author_sk_hex=sk_x, author_pk_hex=pk_x)
                _write(path, registry.to_dict())
            if name == "P":
                _write(path, {"retirement_issuers": [context["pk_t"]],
                              "readoption_issuers": [context["pk_t"], pk_x]})

        result = self.run_with(permissive)
        self.assertTrue(result["all_predictions_held"], "every outcome stays as predicted")
        self.assertFalse(result["holds"])
        self.assertIn("the policy trusts exactly T in both roles", self.checks(result))
        self.assertIn("S7 adds exactly one readoption, by T", self.checks(result))

    def test_6_an_absent_foreign_readoption_at_s5_is_caught(self):
        def no_foreign_lift(name, path, context):
            if name == "R_T+F":
                _write(path, _read_json(context["paths"]["R_T"]))

        result = self.run_with(no_foreign_lift)
        self.assertTrue(result["all_predictions_held"], "S5 refuses either way")
        self.assertFalse(result["holds"])
        self.assertIn("S5 adds exactly one readoption, by F", self.checks(result))
        self.assertIn("the library ignores S5's foreign readoption under the consumed policy",
                      self.checks(result))

    def test_7_a_different_assertion_at_s3_is_caught(self):
        def other_assertion(name, path, context):
            if name != "R_F":
                return
            sk_y, pk_y = crypto.generate_keypair()
            record = RetirementRecord(
                record_id="", target_id=context["label"], target_digest="d" * 64,
                mode=RetirementMode.REFUTED, loss_declaration="a different assertion",
                negative_space_coverage=0.0, atp_gas_recovered=0, author_pk_hex=pk_y,
                signature_hex="", timestamp_utc="2026-09-11T00:00:00Z",
                rule_identity=RuleIdentity.from_terms(context["label"], context["reference"],
                                                      context["candidate"], "y"))
            record.sign(sk_y)
            registry = EpistemicTombstoneRegistry()
            registry.tombstones[context["label"]] = record
            _write(path, registry.to_dict())

        result = self.run_with(other_assertion)
        self.assertTrue(result["all_predictions_held"], "S3 is still UNAUTHORIZED_ISSUER")
        self.assertFalse(result["holds"])
        self.assertIn("S3 is S2's assertion, only the key differs", self.checks(result))

    def test_8_the_evidence_reads_back_to_the_record(self):
        for name, summary in self.result["registries"].items():
            with self.subTest(registry=name):
                with open(os.path.join(self.evidence, f"{name}.json"), "rb") as fh:
                    data = fh.read()
                self.assertEqual(hashlib.sha256(data).hexdigest(), summary["sha256"])
                registry = EpistemicTombstoneRegistry.from_document(json.loads(data))
                label = self.runner.LABEL
                self.assertEqual(registry.tombstones[label].record_id,
                                 summary["retirement_record_id"])
                readoption = registry.readoptions.get(label)
                self.assertEqual(readoption.record_id if readoption else None,
                                 summary["readoption_record_id"])
        with open(os.path.join(self.evidence, "P.json"), "rb") as fh:
            data = fh.read()
        self.assertEqual(hashlib.sha256(data).hexdigest(), self.result["policy"]["sha256"])
        from epistemic_immune import IssuerPolicy
        policy = IssuerPolicy.from_document(json.loads(data))
        self.assertEqual(sorted(policy.retirement_issuers), self.result["policy"]["retirement_issuers"])

    def test_9_checks_no_file_tamper_can_reach(self):
        """S8 and S2 read one path, S6 is run without a policy by the runner, and
        the runner copies the forks itself. Exercised on the recorded inputs."""
        ev = {}
        for name in ("R_T", "R_F", "R_T+F", "R_T+T", "P"):
            with open(os.path.join(self.evidence, f"{name}.json"), "rb") as fh:
                ev[name] = fh.read()
        consumed = {
            "S2": {"registry": ev["R_T"], "policy": ev["P"]},
            "S3": {"registry": ev["R_F"], "policy": ev["P"]},
            "S4": {"registry": ev["R_F"], "policy": ev["P"]},
            "S5": {"registry": ev["R_T+F"], "policy": ev["P"]},
            "S6": {"registry": ev["R_F"], "policy": None},
            "S7": {"registry": ev["R_T+T"], "policy": ev["P"]},
            "S8": {"registry": ev["R_T"], "policy": ev["P"]},
        }
        keys = self.result["keys"]

        def attribution(c, steps):
            return {m["check"] for m in self.runner._attribution(
                c, steps, self.result["genesis_document_sha256"], self.result["pair"],
                keys["T"], keys["F"])}

        self.assertEqual(attribution(consumed, self.result["steps"]), set())
        swapped = dict(consumed, S8={"registry": ev["R_T+T"], "policy": ev["P"]})
        self.assertIn("S8 consumes exactly the S2 registry",
                      attribution(swapped, self.result["steps"]))
        with_policy = dict(consumed, S6={"registry": ev["R_F"], "policy": ev["P"]})
        self.assertIn("S6 consumes no policy", attribution(with_policy, self.result["steps"]))
        steps = copy.deepcopy(self.result["steps"])
        steps[5]["document_sha256_before"] = "0" * 64
        self.assertIn("S6 starts from the same bytes as S7", attribution(consumed, steps))


if __name__ == "__main__":
    unittest.main(verbosity=2)
