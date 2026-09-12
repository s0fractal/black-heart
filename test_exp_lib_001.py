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
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

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


class PackageReaderTest(unittest.TestCase):
    """The independent reader: saved journal BYTES + separately-pinned trust,
    root and tip, replayed WITHOUT regenerating the journal. A specific set of
    controls (not a claim about arbitrary input)."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.pkg = os.path.join(self._tmp.name, "journal.pkg")
        self.meta = EXP.write_package(self.pkg)
        with open(self.pkg, "rb") as f:
            self.data = f.read()

    def test_reader_accepts_saved_package_without_regenerating(self):
        # build_journal is broken: the reader must confirm the SAVED bytes, not
        # a freshly generated journal.
        with mock.patch.object(EXP, "build_journal",
                               side_effect=RuntimeError("regeneration forbidden")):
            rep = EXP.verify_package(self.data, EXP.caller_trust(),
                                     self.meta["root"], self.meta["tip"])
        self.assertTrue(rep["accepted"])

    def test_reader_rejects_wrong_pinned_root(self):
        rep = EXP.verify_package(self.data, EXP.caller_trust(), "00" * 32, self.meta["tip"])
        self.assertFalse(rep["accepted"])

    def test_reader_rejects_wrong_pinned_tip(self):
        rep = EXP.verify_package(self.data, EXP.caller_trust(), self.meta["root"], "00" * 32)
        self.assertFalse(rep["accepted"])

    def test_reader_rejects_tampered_bytes_by_name(self):
        tam = bytearray(self.data)
        i = self.data.index(b'"event_hash"')
        tam[i + 20] ^= 0x01
        rep = EXP.verify_package(bytes(tam), EXP.caller_trust(),
                                 self.meta["root"], self.meta["tip"])
        self.assertFalse(rep["accepted"])
        self.assertIsNotNone(rep["boundary"])

    def test_reader_rejects_duplicate_keys_in_package(self):
        rep = EXP.verify_package(b'[{"a":1,"a":2}]', EXP.caller_trust(),
                                 self.meta["root"], self.meta["tip"])
        self.assertFalse(rep["accepted"])
        self.assertIn("parse", rep["boundary"])

    def test_reader_rejects_non_list_top_level_by_name(self):
        """Valid JSON that is not a list of events (scalar, bool, null, object)
        is a named refusal, not a TypeError from traversal."""
        for label, raw in [("number", b"1"), ("bool", b"true"), ("float", b"1.5"),
                           ("string", b'"x"'), ("null", b"null"), ("object", b"{}")]:
            with self.subTest(kind=label):
                try:
                    rep = EXP.verify_package(raw, EXP.caller_trust(),
                                             self.meta["root"], self.meta["tip"])
                except Exception as e:
                    self.fail(f"{label} raised {type(e).__name__} instead of a named refusal")
                self.assertFalse(rep["accepted"])
                self.assertIn("not a list of events", rep["boundary"])

    def test_reader_names_empty_journal_distinctly(self):
        rep = EXP.verify_package(b"[]", EXP.caller_trust(),
                                 self.meta["root"], self.meta["tip"])
        self.assertFalse(rep["accepted"])
        self.assertIn("empty journal", rep["boundary"])

    def test_written_package_is_deterministic(self):
        p2 = os.path.join(self._tmp.name, "journal2.pkg")
        EXP.write_package(p2)
        with open(p2, "rb") as f:
            self.assertEqual(f.read(), self.data)


# --------------------------------------------------------------------------- #
# R2 external-anchor reader (docs/EXP-LIB-001-R2.md rev 3)
# --------------------------------------------------------------------------- #
# opentimestamps is optional and offline-only. The state tests that need real
# .ots bytes are skipped where it is absent (as CI is, being zero-dependency),
# exactly like a shallow-clone git test skip -- never silently passed. The
# no-proof and file-shape checks below need no library and always run.

def _ots_modules():
    try:
        from opentimestamps.core.timestamp import (Timestamp, DetachedTimestampFile,
                                                    OpSHA256, OpAppend)
        from opentimestamps.core.op import OpKECCAK256
        from opentimestamps.core.notary import (PendingAttestation,
                                                 BitcoinBlockHeaderAttestation)
        from opentimestamps.core.serialize import BytesSerializationContext
        return dict(Timestamp=Timestamp, DetachedTimestampFile=DetachedTimestampFile,
                    OpSHA256=OpSHA256, OpAppend=OpAppend, OpKECCAK256=OpKECCAK256,
                    PendingAttestation=PendingAttestation,
                    BitcoinBlockHeaderAttestation=BitcoinBlockHeaderAttestation,
                    BytesSerializationContext=BytesSerializationContext)
    except Exception:
        return None


_OTS = _ots_modules()
_R2_COMMIT = bytes(range(32))          # a plausible 32-byte root event_hash


def _serialize(detached):
    ctx = _OTS["BytesSerializationContext"](); detached.serialize(ctx)
    return ctx.getbytes()


def _pending_proof(commitment=_R2_COMMIT):
    leaf = hashlib.sha256(commitment).digest()
    ts = _OTS["Timestamp"](leaf)
    ts.attestations.add(_OTS["PendingAttestation"]("https://calendar.example/"))
    return _serialize(_OTS["DetachedTimestampFile"](_OTS["OpSHA256"](), ts))


def _bitcoin_proof(commitment=_R2_COMMIT, height=700000, file_hash_op=None):
    """A detached proof carrying a Bitcoin block attestation. Returns
    (proof_bytes, height, merkle_root_hex). An OpSHA256 transforms the 32-byte
    leaf into a distinct 32-byte value -- a correctly-sized synthetic 'Merkle
    root' -- which the attestation then commits to. (A real proof reaches the
    block Merkle root through many ops; the size is what the reader checks.)"""
    leaf = hashlib.sha256(commitment).digest()
    ts = _OTS["Timestamp"](leaf)
    child = ts.ops.add(_OTS["OpSHA256"]())         # stays 32 bytes, unlike OpAppend
    merkle_root_hex = child.msg.hex()
    assert len(child.msg) == 32
    child.attestations.add(_OTS["BitcoinBlockHeaderAttestation"](height))
    op = file_hash_op if file_hash_op is not None else _OTS["OpSHA256"]()
    return (_serialize(_OTS["DetachedTimestampFile"](op, ts)),
            height, merkle_root_hex)


_SYNTH_TIME = 1600000000                            # explicitly synthetic nTime


def _synthetic_header(merkle_root, time_int=_SYNTH_TIME):
    """An explicitly SYNTHETIC 80-byte Bitcoin block header carrying the given
    32-byte Merkle root and nTime. Not a real block; the reader derives Merkle
    root and time from it and does not check proof-of-work."""
    assert len(merkle_root) == 32
    version = (1).to_bytes(4, "little")
    prev_block = b"\x11" * 32
    ntime = int(time_int).to_bytes(4, "little")
    bits = b"\xff\xff\x00\x1d"
    nonce = b"\x00\x00\x00\x00"
    header = version + prev_block + bytes(merkle_root) + ntime + bits + nonce
    assert len(header) == 80
    return header


def _header_source(name, height, merkle_root_hex, time_int=_SYNTH_TIME):
    hdr = _synthetic_header(bytes.fromhex(merkle_root_hex), time_int)
    return {"name": name, "block_headers": {height: hdr.hex()}}


class ExternalAnchorNoLibTest(unittest.TestCase):
    """Reader contract that needs no OTS library (always runs)."""

    def test_no_proof_is_not_demonstrated(self):
        r = EXP.verify_external_anchor(_R2_COMMIT, None)
        self.assertEqual(r["state"], "NOT_DEMONSTRATED")
        self.assertEqual(r["commitment_sha256"],
                         hashlib.sha256(_R2_COMMIT).hexdigest())
        self.assertEqual(r["accepted_source"], "none")

    def test_result_never_raises_and_always_has_the_reported_fields(self):
        for commit, proof in [(_R2_COMMIT, None), (b"x", b"junk"),
                              (None, None), (_R2_COMMIT, b"")]:
            r = EXP.verify_external_anchor(commit, proof)
            for field in ("state", "commitment_sha256", "proof_sha256",
                          "pending_calendars", "bitcoin_attestations",
                          "time_verified", "attested_time", "block_id",
                          "calendar_authenticity_verified",
                          "accepted_source", "network_calls"):
                self.assertIn(field, r)
            self.assertIn(r["state"], EXP._R2_STATES)
            self.assertEqual(r["network_calls"], 0)
            # a non-CONFIRMED result never carries a verified time
            self.assertFalse(r["time_verified"])
            self.assertIsNone(r["attested_time"])

    def test_commitment_file_is_exactly_32_raw_bytes(self):
        # profile §2/§9: the stamped file is exactly the 32 raw bytes, no hex,
        # no newline, and equals the pinned root.
        root_hex = "ab" * 32
        commitment = bytes.fromhex(root_hex)
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "root.commit")
            with open(p, "wb") as f:
                f.write(commitment)
            with open(p, "rb") as f:
                raw = f.read()
        self.assertEqual(len(raw), 32)
        self.assertEqual(raw, commitment)
        self.assertEqual(raw.hex(), root_hex)

    def test_block_header_parser_derives_root_time_and_id(self):
        # No OTS needed: the header contract is what makes time verifiable.
        mroot = bytes(range(100, 132))
        hdr = _synthetic_header(mroot, 1712345678)
        got = EXP._parse_block_header(hdr)
        self.assertIsNotNone(got)
        merkle_root, time_int, block_id = got
        self.assertEqual(merkle_root, mroot)
        self.assertEqual(time_int, 1712345678)
        self.assertEqual(len(bytes.fromhex(block_id)), 32)
        self.assertIsNone(EXP._parse_block_header(hdr[:-1]))   # not 80 bytes

    def test_validate_source_rejects_malformed_before_matching(self):
        good = _header_source("s", 700000, "ab" * 32)
        self.assertIsNotNone(EXP._validate_source(good))
        for bad in [
            None, {}, {"block_headers": {700000: "ab" * 40 + ".."}},   # no name
            {"name": "", "block_headers": {700000: ("00" * 80)}},      # empty name
            {"name": "s", "block_headers": {}},                        # empty headers
            {"name": "s", "block_headers": {700000: "ab" * 32}},       # 32 != 80 bytes
            {"name": "s", "block_headers": {700000: "zz" * 80}},       # not hex
            {"name": "s", "block_merkle_roots": {700000: "ab" * 32}},  # old shape
            {"name": "s", "block_headers": {700000.9: ("00" * 80)}},   # float height
            {"name": "s", "block_headers": {True: ("00" * 80)}},       # bool height
            {"name": "s", "block_headers": {"0700000": ("00" * 80)}},  # leading zero
            {"name": "s", "block_headers": {-1: ("00" * 80)}},         # negative
            {"name": "s", "block_headers": {700000: ("00" * 80),
                                            "700000": ("00" * 80)}},   # collision
        ]:
            self.assertIsNone(EXP._validate_source(bad), bad)
        # a canonical decimal STRING height is accepted (equals the int form)
        self.assertIsNotNone(EXP._validate_source(
            {"name": "s", "block_headers": {"700000": ("00" * 80)}}))

    def test_coerce_height_is_strict(self):
        self.assertEqual(EXP._coerce_height(700000), 700000)
        self.assertEqual(EXP._coerce_height("700000"), 700000)
        self.assertEqual(EXP._coerce_height("0"), 0)
        self.assertEqual(EXP._coerce_height(0), 0)
        for bad in [True, False, 700000.9, -1, "0700", "700000.9", "+5", " 5",
                    "5 ", "0x10", "", None, b"5"]:
            self.assertIsNone(EXP._coerce_height(bad), bad)


@unittest.skipUnless(_OTS is not None,
                     "opentimestamps not importable (offline optional dep)")
class ExternalAnchorR2Test(unittest.TestCase):
    """The five OTS-backed states, each against a real detached proof."""

    def test_refused_for_malformed_proof(self):
        r = EXP.verify_external_anchor(_R2_COMMIT, b"not an ots proof at all")
        self.assertEqual(r["state"], "REFUSED")

    def test_refused_when_proof_binds_a_different_commitment(self):
        # A well-formed proof over OTHER bytes must not be accepted for ours:
        # non-binding is REFUSED, distinct from absent/PENDING.
        proof = _pending_proof(commitment=bytes([7]) * 32)
        r = EXP.verify_external_anchor(_R2_COMMIT, proof)
        self.assertEqual(r["state"], "REFUSED")
        self.assertIn("bind", r["reason"])

    def test_refused_for_non_32_byte_commitment(self):
        # Bind the proof to the SHORT commitment, so the binding check would
        # accept it -- only the explicit 32-byte length gate can refuse it.
        short = b"short"
        r = EXP.verify_external_anchor(short, _pending_proof(commitment=short))
        self.assertEqual(r["state"], "REFUSED")
        self.assertIn("32 raw bytes", r["reason"])

    def test_pending_for_calendar_only_proof(self):
        r = EXP.verify_external_anchor(_R2_COMMIT, _pending_proof())
        self.assertEqual(r["state"], "PENDING")
        self.assertEqual(r["pending_calendars"], ["https://calendar.example/"])
        self.assertFalse(r["time_verified"])

    def test_bitcoin_attestation_merkle_root_is_32_bytes(self):
        _proof, _height, root_hex = _bitcoin_proof()
        self.assertEqual(len(bytes.fromhex(root_hex)), 32)   # not 33 (no OpAppend)

    def test_anchored_unverified_when_bitcoin_present_no_source(self):
        proof, height, _root = _bitcoin_proof()
        r = EXP.verify_external_anchor(_R2_COMMIT, proof)
        self.assertEqual(r["state"], "ANCHORED_UNVERIFIED")
        self.assertEqual([b["height"] for b in r["bitcoin_attestations"]], [height])
        self.assertFalse(r["time_verified"])
        self.assertIsNone(r["attested_time"])
        self.assertEqual(r["accepted_source"], "none")

    def test_confirmed_against_accepted_pinned_source_offline(self):
        proof, height, root_hex = _bitcoin_proof()
        source = _header_source("pinned-headers-fixture", height, root_hex,
                                time_int=_SYNTH_TIME)
        r = EXP.verify_external_anchor(_R2_COMMIT, proof, source)
        self.assertEqual(r["state"], "CONFIRMED")
        self.assertTrue(r["time_verified"])
        # the reported time is DERIVED from the pinned header, not invented
        self.assertEqual(r["attested_time"], _SYNTH_TIME)
        self.assertEqual(len(bytes.fromhex(r["block_id"])), 32)
        self.assertEqual(r["network_calls"], 0)          # offline confirmation
        self.assertFalse(r["calendar_authenticity_verified"])
        self.assertEqual(r["accepted_source"], "pinned-headers-fixture")

    # ---- the REQUIRED adjacent negative (profile §7 / Codex) -------------- #
    def test_same_accepted_source_but_mismatched_attestation_is_not_confirmed(self):
        proof, height, _root = _bitcoin_proof()
        # SAME well-formed source shape and height, but the pinned header holds
        # a DIFFERENT Merkle root. Passing a source must not, by itself,
        # confirm: this must NOT be CONFIRMED, and no time is reported.
        source = _header_source("pinned-headers-fixture", height, "00" * 32)
        r = EXP.verify_external_anchor(_R2_COMMIT, proof, source)
        self.assertNotEqual(r["state"], "CONFIRMED")
        self.assertEqual(r["state"], "ANCHORED_UNVERIFIED")
        self.assertFalse(r["time_verified"])
        self.assertIsNone(r["attested_time"])
        self.assertEqual(r["accepted_source"], "pinned-headers-fixture")

    def test_accepted_source_with_missing_height_is_not_confirmed(self):
        proof, height, root_hex = _bitcoin_proof()
        source = _header_source("pinned-headers-fixture", height + 1, root_hex)
        r = EXP.verify_external_anchor(_R2_COMMIT, proof, source)
        self.assertEqual(r["state"], "ANCHORED_UNVERIFIED")

    def test_malformed_source_never_confirms_even_with_matching_data(self):
        # Codex blocker 2: a source WITHOUT a name must not earn CONFIRMED, even
        # when it carries a header whose Merkle root matches the attestation.
        proof, height, root_hex = _bitcoin_proof()
        hdr = _synthetic_header(bytes.fromhex(root_hex))
        no_name = {"block_headers": {height: hdr.hex()}}          # name removed
        r = EXP.verify_external_anchor(_R2_COMMIT, proof, no_name)
        self.assertNotEqual(r["state"], "CONFIRMED")
        self.assertEqual(r["state"], "ANCHORED_UNVERIFIED")
        self.assertFalse(r["time_verified"])
        self.assertEqual(r["accepted_source"], "none")           # not "unnamed-source"

    def test_non_sha256_file_hash_op_is_refused(self):
        # Codex R2 blocker 1: a proof declaring a non-SHA-256 file-hash op is a
        # format mismatch (profile §2), even if its leaf bytes equal our SHA-256
        # leaf. It must be REFUSED, never CONFIRMED. (Not a break of SHA-256.)
        proof, height, root_hex = _bitcoin_proof(file_hash_op=_OTS["OpKECCAK256"]())
        source = _header_source("pinned-headers-fixture", height, root_hex)
        r = EXP.verify_external_anchor(_R2_COMMIT, proof, source)
        self.assertEqual(r["state"], "REFUSED")
        self.assertIn("SHA-256", r["reason"])
        self.assertFalse(r["time_verified"])

    def test_fractional_height_in_source_never_confirms(self):
        # Codex R2 blocker 2: a fractional height must not be truncated to match
        # an integer attestation height -- that would silently change the pin.
        proof, height, root_hex = _bitcoin_proof()
        hdr = _synthetic_header(bytes.fromhex(root_hex))
        source = {"name": "pinned-headers-fixture",
                  "block_headers": {height + 0.9: hdr.hex()}}
        r = EXP.verify_external_anchor(_R2_COMMIT, proof, source)
        self.assertNotEqual(r["state"], "CONFIRMED")
        self.assertEqual(r["state"], "ANCHORED_UNVERIFIED")
        self.assertEqual(r["accepted_source"], "none")   # malformed source: not used

    def test_canonical_string_height_confirms(self):
        # The accepted form (canonical decimal string) still reaches CONFIRMED.
        proof, height, root_hex = _bitcoin_proof()
        hdr = _synthetic_header(bytes.fromhex(root_hex))
        source = {"name": "pinned-headers-fixture",
                  "block_headers": {str(height): hdr.hex()}}
        r = EXP.verify_external_anchor(_R2_COMMIT, proof, source)
        self.assertEqual(r["state"], "CONFIRMED")
        self.assertEqual(r["attested_time"], _SYNTH_TIME)

    def test_old_merkle_root_only_source_shape_never_confirms(self):
        # The bare {height: merkle_root_hex} shape carries no time and must not
        # confirm -- the very shape the earlier revision wrongly accepted.
        proof, height, root_hex = _bitcoin_proof()
        old_shape = {"name": "roots-only",
                     "block_merkle_roots": {height: root_hex}}
        r = EXP.verify_external_anchor(_R2_COMMIT, proof, old_shape)
        self.assertNotEqual(r["state"], "CONFIRMED")
        self.assertEqual(r["accepted_source"], "none")


class FrozenAnchorPackageTest(unittest.TestCase):
    """The frozen R2 anchoring package (experiments/EXP-LIB-001/r2-anchor) stays
    bound to the runner: if the journal changes, the frozen commitment no longer
    corresponds to main and this fails. No OTS or network needed."""

    def setUp(self):
        self.dir = os.path.join(_HERE, "experiments", "EXP-LIB-001", "r2-anchor")
        self.man = json.load(open(os.path.join(self.dir, "MANIFEST.json")))
        self.pkg = open(os.path.join(self.dir, "journal.pkg"), "rb").read()
        self.commitment = open(os.path.join(self.dir, "root.commitment"), "rb").read()

    def test_current_runner_reproduces_the_frozen_package(self):
        self.assertEqual(EXP.journal_to_bytes(EXP.build_journal()), self.pkg)
        self.assertEqual(hashlib.sha256(self.pkg).hexdigest(),
                         self.man["package_sha256"])

    def test_commitment_is_32_raw_bytes_equal_to_the_package_root(self):
        self.assertEqual(len(self.commitment), 32)
        parsed = EXP.journal_from_bytes(self.pkg)
        self.assertEqual(self.commitment.hex(), parsed[0]["event_hash"])
        self.assertEqual(self.commitment.hex(), self.man["root_event_hash"])
        self.assertEqual(parsed[-1]["event_hash"], self.man["tip_event_hash"])

    def test_r1_reader_accepts_the_frozen_bytes(self):
        rep = EXP.verify_package(self.pkg, EXP.caller_trust(),
                                 self.man["root_event_hash"], self.man["tip_event_hash"])
        self.assertTrue(rep["accepted"])

    def test_posture_is_not_demonstrated_until_a_real_anchor(self):
        # The frozen package is only a stamp target; it is not an anchor.
        self.assertEqual(self.man["r2_status"], "NOT_DEMONSTRATED")
        self.assertEqual(self.man["r3_status"], "NOT_RELEASED")


if __name__ == "__main__":
    unittest.main()
