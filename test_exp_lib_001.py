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

    def test_2b_wrong_root_or_tip_is_not_accepted(self):
        """Pins gate acceptance, not just a reported flag: a reader must not see
        a successful loop for a history they did not select (root) or an
        incomplete one (tip). chain_ok (internal consistency) is separate."""
        j = EXP.build_journal()
        for root, tip in (("00" * 32, j[-1]["event_hash"]),
                          (j[0]["event_hash"], "00" * 32)):
            rep = EXP.replay(j, EXP.caller_trust(), root, tip)
            self.assertTrue(rep["chain_ok"], "chain is internally consistent")
            self.assertFalse(rep["accepted"], "wrong pin was accepted")

    def test_2d_unsupported_profile_is_refused_by_name(self):
        """A signature over an unsupported format is not acceptance."""
        j = EXP.build_journal()
        prev = EXP.GENESIS_PREV
        reprofiled = []
        for ev in j:
            reprofiled.append(EXP._resign_event({**ev, "profile": "unsupported.v99",
                                                 "prev_event_hash": prev}))
            prev = reprofiled[-1]["event_hash"]
        rep = EXP.replay(reprofiled, EXP.caller_trust(),
                         reprofiled[0]["event_hash"], reprofiled[-1]["event_hash"])
        self.assertFalse(rep["chain_ok"])
        self.assertIn("profile", rep["boundary"])

    def test_2f_missing_field_is_a_named_refusal_not_an_exception(self):
        """A malformed event (here, a missing event_hash on the root) must be
        refused by name -- replay must not read a field before validating it."""
        j = EXP.build_journal()
        broken = [dict(e) for e in j]
        broken[0] = dict(broken[0]); del broken[0]["event_hash"]
        rep = EXP.replay(broken, EXP.caller_trust(), "x", "y")
        self.assertFalse(rep["chain_ok"])
        self.assertIn("event_hash", rep["boundary"])
        self.assertFalse(rep["accepted"])

    def test_2g_a_non_int_index_is_refused(self):
        """index=False must not sneak through on `False == 0`: the type is
        checked, not just the value."""
        j = EXP.build_journal()
        chained, prev = [], EXP.GENESIS_PREV
        for i, e in enumerate(j):
            core = {**e, "prev_event_hash": prev}
            if i == 0:
                core["index"] = False
            r = EXP._resign_event(core); chained.append(r); prev = r["event_hash"]
        rep = EXP.replay(chained, EXP.caller_trust(),
                         chained[0]["event_hash"], chained[-1]["event_hash"])
        self.assertFalse(rep["accepted"])
        self.assertFalse(rep["chain_ok"])
        self.assertIn("int", rep["boundary"])

    def test_2e_resigned_broken_prev_link_is_refused(self):
        """The event_hash attests the recorded prev value, not that it matches
        the real predecessor -- re-pointing prev and re-signing must still be
        refused as a chain break."""
        j = EXP.build_journal()
        relinked = [dict(ev) for ev in j]
        relinked[1] = EXP._resign_event({**j[1], "prev_event_hash": EXP.GENESIS_PREV})
        rep = EXP.replay(relinked, EXP.caller_trust(),
                         j[0]["event_hash"], relinked[-1]["event_hash"])
        self.assertEqual(rep["confirmed_through_index"], 0)
        self.assertIn("prev", rep["boundary"])

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


class StructureTest(unittest.TestCase):
    """The complete format check: exact field set, correct type of every field
    (incl. nested claim), each a NAMED refusal and never an exception."""

    def _refused(self, ev_list, needle):
        """replay must refuse with a boundary mentioning `needle`, not raise."""
        try:
            rep = EXP.replay(ev_list, EXP.caller_trust(),
                             ev_list[0].get("event_hash", "x") if ev_list else "x",
                             ev_list[-1].get("event_hash", "y") if ev_list else "y")
        except Exception as e:
            self.fail(f"replay raised {type(e).__name__} instead of a named refusal: {e}")
        self.assertFalse(rep["chain_ok"])
        self.assertFalse(rep["accepted"])
        self.assertIsNotNone(rep["boundary"])
        self.assertIn(needle, rep["boundary"])

    def _mutate_event0(self, mutate, resign=True):
        j = EXP.build_journal()
        ev = [dict(e) for e in j]
        ev[0] = dict(ev[0]); mutate(ev[0])
        if resign:
            try:
                ev[0] = EXP._resign_event(ev[0])
            except Exception:
                pass  # a core too malformed to re-sign is used as-is
        return ev

    def test_S_honest_event_is_accepted(self):
        j = EXP.build_journal()
        rep = EXP.replay(j, EXP.caller_trust(), j[0]["event_hash"], j[-1]["event_hash"])
        self.assertTrue(rep["accepted"])

    def test_S_wrong_types_each_field_are_named_refusals(self):
        cases = [
            (lambda e: e.__setitem__("profile", 123), "profile"),
            (lambda e: e.__setitem__("index", []), "int"),
            (lambda e: e.__setitem__("index", False), "int"),
            (lambda e: e.__setitem__("kind", []), "kind"),
            (lambda e: e.__setitem__("kind", "NOPE"), "kind"),
            (lambda e: e.__setitem__("expected_verdict", {}), "expected_verdict"),
            (lambda e: e.__setitem__("author_pk_hex", 123), "author_pk_hex"),
            (lambda e: e.__setitem__("claim", None), "claim is not an object"),
            (lambda e: e.__setitem__("claim", {**e["claim"], "body": None}), "malformed claim"),
            (lambda e: e.__setitem__("claim", {**e["claim"], "body": {}}), "malformed claim"),
        ]
        for mutate, needle in cases:
            with self.subTest(needle=needle):
                self._refused(self._mutate_event0(mutate), needle)

    def test_S_prev_event_hash_wrong_type_refused(self):
        j = EXP.build_journal()
        ev = [dict(e) for e in j]
        ev[1] = dict(ev[1]); ev[1]["prev_event_hash"] = 123     # not re-signed
        self._refused(ev, "prev_event_hash")

    def test_S_extra_field_refused(self):
        self._refused(self._mutate_event0(lambda e: e.__setitem__("junk", 1), resign=False),
                      "unexpected field")

    def test_S_missing_field_refused(self):
        ev = self._mutate_event0(lambda e: e.pop("event_hash"), resign=False)
        self._refused(ev, "missing field")


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

    def test_3e_resigned_broken_prev_link_refused(self):
        self.assertTrue(self.c["broken_prev_link_refused"])

    def test_3f_unsupported_profile_refused(self):
        self.assertTrue(self.c["unsupported_profile_refused"])

    def test_3g_wrong_root_not_accepted(self):
        self.assertTrue(self.c["wrong_root_not_accepted"])


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
        self.assertTrue(r["R1_local_replay"]["accepted"])
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
