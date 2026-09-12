#!/usr/bin/env python3
"""
Acceptance tests for EXP-LIB-001 (docs/EXP-LIB-001.md rev 4).

The predictions in experiments/EXP-LIB-001/README.md are pre-registered and not
rewritten; these tests hold the runner to them. A green sequence alone is not
acceptance -- criteria 2-5 (replay to the oldest ancestor, content re-audit,
controls failing closed, linkage, provenance separation) are the substance.
"""
from __future__ import annotations

import hashlib
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path[:1]:
    sys.path.insert(0, _HERE)
for _name, _mod in list(sys.modules.items()):
    _file = getattr(_mod, "__file__", None)
    if not _file:
        continue
    if os.path.dirname(os.path.abspath(_file)) != _HERE and \
            os.path.exists(os.path.join(_HERE, os.path.basename(_file))):
        del sys.modules[_name]

sys.path.insert(0, os.path.join(_HERE, "experiments", "EXP-LIB-001"))
import run as EXP
import crypto


def _resign(ev, sk=EXP.AUTHOR_SK):
    """Rebuild event_hash + signature for a mutated core (honest re-signing)."""
    core = {k: ev[k] for k in EXP._CORE_ORDER}
    cb = EXP.canonical_core_bytes(core)
    return {**core, "event_hash": hashlib.sha256(cb).hexdigest(),
            "signature_hex": crypto.sign_bytes(sk, cb).hex()}


class LoopTest(unittest.TestCase):
    """Criterion 1."""

    def test_1_honest_loop_is_pass_pass_pass_recorded_and_replayed(self):
        r = EXP.run_experiment()
        self.assertEqual(r["loop"]["recorded"], ["PASS", "PASS", "PASS"])
        self.assertEqual(r["loop"]["replayed"], ["PASS", "PASS", "PASS"])
        self.assertTrue(r["loop"]["ok"])

    def test_1b_a_reproduced_unverified_is_not_loop_success(self):
        """Even with all three RECORDED as PASS, if replay reproduces an
        UNVERIFIED the loop did not succeed -- the replayed verdicts are a
        required conjunct."""
        recorded = ["PASS", "PASS", "PASS"]
        rep = {"verdicts": ["PASS", "PASS", "UNVERIFIED"], "chain_ok": True,
               "confirmed_through_index": 2}
        self.assertFalse(EXP.loop_success(recorded, rep))
        self.assertTrue(EXP.loop_success(recorded,
            {"verdicts": ["PASS", "PASS", "PASS"], "chain_ok": True,
             "confirmed_through_index": 2}))


class ReplayTest(unittest.TestCase):
    """Criterion 2 + content re-audit."""

    def test_2_replay_confirms_to_the_oldest_ancestor(self):
        j = EXP.build_journal()
        rep = EXP.replay(j, EXP.caller_trust(), j[0]["event_hash"], j[-1]["event_hash"])
        self.assertTrue(rep["chain_ok"])
        self.assertEqual(rep["confirmed_through_index"], 2)
        self.assertTrue(rep["root_matches"] and rep["tip_matches"])

    def test_2b_wrong_expected_root_is_reported_not_silently_passed(self):
        j = EXP.build_journal()
        rep = EXP.replay(j, EXP.caller_trust(), "00" * 32, j[-1]["event_hash"])
        self.assertFalse(rep["root_matches"])

    def test_2c_replay_reaudits_content_not_just_hash_and_signature(self):
        """A properly re-signed event whose recorded verdict contradicts a fresh
        audit must be refused -- replay checks the claim's content, not only
        that the bytes are consistent and signed."""
        j = EXP.build_journal()
        forged = _resign({**j[1], "expected_verdict": "FAIL"})   # C2 truly PASSes
        self.assertTrue(crypto.verify_bytes(bytes.fromhex(forged["author_pk_hex"]),
                        EXP.canonical_core_bytes({k: forged[k] for k in EXP._CORE_ORDER}),
                        bytes.fromhex(forged["signature_hex"])),
                        "the forgery is honestly signed; content is what must refuse it")
        j2 = [j[0], forged, j[2]]
        # fix the chain link so only the CONTENT is wrong
        j2[2] = _resign({**j2[2], "prev_event_hash": forged["event_hash"]})
        rep = EXP.replay(j2, EXP.caller_trust(), j2[0]["event_hash"], j2[2]["event_hash"])
        self.assertEqual(rep["confirmed_through_index"], 0, "content mismatch not caught")
        self.assertIn("verdict", rep["boundary"])


class ControlsTest(unittest.TestCase):
    """Criterion 3 — each control fails closed, asserted individually."""

    def setUp(self):
        self.c = EXP.run_controls()

    def test_3a_foreign_author_is_unverified(self):
        self.assertTrue(self.c["foreign_author_unverified"])

    def test_3b_recycled_witness_does_not_pass(self):
        self.assertTrue(self.c["recycled_witness_not_pass"])

    def test_3c_nonterminating_claim_is_unverified(self):
        self.assertTrue(self.c["nonterminating_unverified"])

    def test_3d_history_tamper_breaks_replay(self):
        self.assertTrue(self.c["tamper_breaks_replay"])


class LinkageTest(unittest.TestCase):
    """Criterion 3 (linkage) — the C1-C3 relations, not three loose claims."""

    def test_linkage_holds_on_the_honest_journal(self):
        self.assertTrue(EXP.linkage_ok(EXP.build_journal())["all"])

    def test_linkage_fails_if_c3_reuses_the_buggy_candidate(self):
        j = EXP.build_journal()
        # rebuild C3 with the buggy candidate K I -> linkage must reject
        broken = _resign({**j[2], "claim": {**j[2]["claim"],
                          "body": {**j[2]["claim"]["body"], "tau": f"{EXP.K} {EXP.I}"}}})
        self.assertFalse(EXP.linkage_ok([j[0], j[1], broken])["all"])


class ProvenanceSeparationTest(unittest.TestCase):
    """Criterion 4."""

    def test_4_r1_r2_r3_are_distinct_results(self):
        r = EXP.run_experiment()
        self.assertTrue(r["R1_local_replay"]["chain_ok"])
        self.assertEqual(r["R2_external_anchor"]["status"], "NOT_DEMONSTRATED")
        self.assertEqual(r["R3_publication"]["status"], "NOT_RELEASED")
        # R2/R3 do not stand in for R1: loop ok does not depend on them
        self.assertTrue(r["loop"]["ok"])


class DeterminismTest(unittest.TestCase):
    """Criterion 6 + encoding profile."""

    def test_6_two_builds_are_byte_identical(self):
        self.assertEqual(EXP.journal_to_bytes(EXP.build_journal()),
                         EXP.journal_to_bytes(EXP.build_journal()))

    def test_encoding_rejects_floats_and_out_of_range_ints(self):
        with self.assertRaises(ValueError):
            EXP._encode(1.5)
        with self.assertRaises(ValueError):
            EXP._encode(2 ** 53)

    def test_journal_from_bytes_rejects_duplicate_keys(self):
        with self.assertRaises(ValueError):
            EXP.journal_from_bytes(b'[{"a":1,"a":2}]')


if __name__ == "__main__":
    unittest.main()
