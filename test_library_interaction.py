#!/usr/bin/env python3
"""Acceptance tests for LI-1 proposal intake.

Contract: docs/LIBRARY-INTERACTION-LI1.md. These hold the implementation to the
LI-1 acceptance list in docs/LIVING-LIBRARY-INTERACTION.md: a real CLI
subprocess produces a parseable, parent-bound proposal; a second parent cannot
consume it; malformed inputs are NAMED refusals; inputs and pre-existing output
stay byte-identical on refusal; the input PDF is never executed; and intake
never reports an accepted claim.

All keys are ephemeral throwaway fixtures generated per-test; no secret is
printed.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path
from pathlib import Path as pathlib_Path

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path[:1]:
    sys.path.insert(0, _HERE)

import crypto
import library_interaction as li
import warrant_kernel as wk

CLI = os.path.join(_HERE, "cli.py")
MPFX = li.MANIFEST_PREFIX


def _sha256(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _signed_claim(sk_hex, pk_hex, tau="🤍 🤍", term="🤍 🤍"):
    return wk.EdgeClaim.create_and_sign(
        parent_hash="a" * 64, tau=tau, omega="🤍", successor_hash="b" * 64,
        polarity=wk.Polarity.AFFIRM,
        witness=wk.GroundedWitness(term_expr=term, expected_hash="c" * 64,
                                   atp_budget=1000),
        secret_key_hex=sk_hex, public_key_hex=pk_hex)


class LI1Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.d = Path(self._tmp.name)
        # Claim AUTHOR and PROPOSER are deliberately DIFFERENT identities.
        self.a_sk, self.a_pk = crypto.generate_keypair()
        self.p_sk, self.p_pk = crypto.generate_keypair()
        self.claim = _signed_claim(self.a_sk, self.a_pk)
        self.claim_path = self.d / "claim.json"
        self.claim_path.write_text(json.dumps(self.claim.to_dict(), indent=2))
        self.key_path = self.d / "proposer.key"
        self.key_path.write_text(self.p_sk + "\n")
        self.parent = self.d / "parent.pdf"
        wk.generate_warrant_ledger_pdf([self.claim], str(self.parent), wk.TrustConfig())
        self.parent_sha = _sha256(self.parent)
        self.out = self.d / "proposal.json"

    def cli(self, *args):
        return subprocess.run([sys.executable, "-B", CLI, "library", *args],
                              capture_output=True, text=True, cwd=_HERE, timeout=120)

    def make_proposal(self):
        r = self.cli("add-claim", "--pdf", str(self.parent),
                     "--expect-parent-sha256", self.parent_sha,
                     "--claim", str(self.claim_path),
                     "--proposer-key-file", str(self.key_path),
                     "--out", str(self.out), "--json")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return json.loads(r.stdout)

    def second_parent(self):
        other = _signed_claim(self.a_sk, self.a_pk, tau="🖤", term="🖤")
        p2 = self.d / "parent2.pdf"
        wk.generate_warrant_ledger_pdf([other], str(p2), wk.TrustConfig())
        return p2


class ProfileParsingTest(LI1Base):
    """The measured profile, including the ambiguity the bare marker carries."""

    def test_honest_document_has_two_bare_markers_but_one_manifest_line(self):
        raw = self.parent.read_bytes()
        # Counting the BARE substring would refuse every genuine document: the
        # embedded runner's own source contains it too.
        self.assertEqual(raw.count(b" WARRANT_KERNEL_MANIFEST: "), 2)
        self.assertEqual(len(li.find_manifest_lines(raw)), 1)

    def test_profile_does_not_begin_with_pdf_magic(self):
        raw = self.parent.read_bytes()
        self.assertNotEqual(raw[:4], b"%PDF")
        self.assertGreater(raw.find(b"%PDF"), 0)

    def test_inspect_reports_exact_bytes_and_profile(self):
        res = li.inspect_parent(str(self.parent))
        self.assertTrue(res["ok"], res)
        self.assertEqual(res["pdf_sha256"], self.parent_sha)
        self.assertEqual(res["manifest_format"], "WARRANT-0.2")
        self.assertEqual(res["claim_count"], 1)
        self.assertFalse(res["executed_input_pdf"])

    def test_advertised_trust_config_is_reported_as_advertisement_only(self):
        res = li.inspect_parent(str(self.parent))
        self.assertIn("advertised_trust_config", res)
        self.assertIn("no authority", res["advertised_trust_config_note"])


class ManifestRefusalTest(LI1Base):
    """Named outcomes for every manifest defect the contract lists."""

    def _mutate_manifest(self, name, new_manifest=None, raw_payload=None, duplicate=False,
                         drop_marker=False):
        raw = self.parent.read_bytes()
        i = raw.find(MPFX)
        end = raw.find(b"\n", i)
        if drop_marker:
            out = raw.replace(MPFX, b"# %-- NOT_A_MANIFEST: ", 1)
        elif duplicate:
            out = raw[:end + 1] + raw[i:end + 1] + raw[end + 1:]
        else:
            payload = (raw_payload if raw_payload is not None
                       else json.dumps(new_manifest, sort_keys=True).encode())
            out = raw[:i + len(MPFX)] + payload + raw[end:]
        p = self.d / name
        p.write_bytes(out)
        return p

    def _manifest(self):
        raw = self.parent.read_bytes()
        i = raw.find(MPFX)
        end = raw.find(b"\n", i)
        return json.loads(raw[i + len(MPFX):end].decode())

    def test_mid_line_manifest_prefix_is_ambiguous_and_refused(self):
        # The strict prefix planted INSIDE a line is not a manifest line here,
        # but a reader anchoring differently could select it. Refuse, never pick.
        raw = self.parent.read_bytes()
        i = raw.find(MPFX)
        planted = raw[:i] + b"junk " + MPFX + b'{"format":"WARRANT-0.2",' \
                  b'"claims":[],"trust_config":{}} ' + raw[i:]
        p = self.d / "midline.pdf"
        p.write_bytes(planted)
        res = li.read_parent(str(p))
        self.assertEqual(res["refusal"], "MANIFEST_AMBIGUOUS")

    def test_anchored_count_and_total_count_agree_on_an_honest_document(self):
        raw = self.parent.read_bytes()
        self.assertEqual(li.find_manifest_lines(raw), li.find_prefix_offsets(raw))
        self.assertEqual(len(li.find_manifest_lines(raw)), 1)

    def test_absent_manifest(self):
        p = self._mutate_manifest("a.pdf", drop_marker=True)
        self.assertEqual(li.read_parent(str(p))["refusal"], "MANIFEST_ABSENT")

    def test_duplicate_manifest_lines(self):
        p = self._mutate_manifest("b.pdf", duplicate=True)
        self.assertEqual(li.read_parent(str(p))["refusal"], "MANIFEST_DUPLICATE")

    def test_missing_claims_is_a_refusal_not_an_empty_list(self):
        # The embedded runner does manifest.get("claims", []); LI-1 must not.
        m = self._manifest()
        m.pop("claims")
        p = self._mutate_manifest("c.pdf", m)
        res = li.read_parent(str(p))
        self.assertEqual(res["refusal"], "MANIFEST_FIELD_MISSING")
        self.assertIn("claims", res["detail"])

    def test_missing_format_and_trust_config_are_refusals(self):
        for field in ("format", "trust_config"):
            m = self._manifest()
            m.pop(field)
            p = self._mutate_manifest(f"d_{field}.pdf", m)
            self.assertEqual(li.read_parent(str(p))["refusal"], "MANIFEST_FIELD_MISSING")

    def test_wrong_field_types_are_named(self):
        table = [("claims", "not-a-list"), ("claims", {}), ("format", 5),
                 ("trust_config", []), ("claims", True)]
        for field, value in table:
            with self.subTest(field=field, value=value):
                m = self._manifest()
                m[field] = value
                p = self._mutate_manifest("e.pdf", m)
                self.assertEqual(li.read_parent(str(p))["refusal"], "MANIFEST_FIELD_TYPE")

    def test_unsupported_format(self):
        m = self._manifest()
        m["format"] = "WARRANT-9.9"
        p = self._mutate_manifest("f.pdf", m)
        self.assertEqual(li.read_parent(str(p))["refusal"], "MANIFEST_UNSUPPORTED_FORMAT")

    def test_duplicate_json_keys(self):
        p = self._mutate_manifest(
            "g.pdf", raw_payload=b'{"format":"WARRANT-0.2","format":"x",'
                                 b'"claims":[],"trust_config":{}}')
        self.assertEqual(li.read_parent(str(p))["refusal"], "MANIFEST_DUPLICATE_KEYS")

    def test_manifest_not_json_and_not_object(self):
        p = self._mutate_manifest("h.pdf", raw_payload=b"{not json")
        self.assertEqual(li.read_parent(str(p))["refusal"], "MANIFEST_NOT_JSON")
        p = self._mutate_manifest("i.pdf", raw_payload=b"[1,2,3]")
        self.assertEqual(li.read_parent(str(p))["refusal"], "MANIFEST_NOT_OBJECT")

    def test_unreadable_and_oversize_parent_are_named(self):
        self.assertEqual(li.read_parent(str(self.d / "nope.pdf"))["refusal"],
                         "PARENT_UNREADABLE")
        big = self.d / "big.pdf"
        big.write_bytes(b"\0" * 16)
        real_limit = li.MAX_PARENT_BYTES
        try:
            li.MAX_PARENT_BYTES = 4
            self.assertEqual(li.read_parent(str(big))["refusal"], "PARENT_TOO_LARGE")
        finally:
            li.MAX_PARENT_BYTES = real_limit


class ClaimAuthenticationTest(LI1Base):
    """The supplied claim is authenticated (not evaluated)."""

    def test_valid_claim_loads(self):
        res = li.load_claim(str(self.claim_path))
        self.assertTrue(res["ok"], res)
        self.assertEqual(res["author_pk_hex"], self.a_pk)

    def test_invalid_signature_is_refused(self):
        d = json.loads(self.claim_path.read_text())
        d["signature_hex"] = "0" * 8 + d["signature_hex"][8:]
        p = self.d / "bad.json"
        p.write_text(json.dumps(d))
        self.assertEqual(li.load_claim(str(p))["refusal"], "CLAIM_SIGNATURE_INVALID")

    def test_claim_id_disagreeing_with_body_is_refused(self):
        # from_dict trusts a supplied claim_id and __post_init__ only fills an
        # EMPTY one, so the signature could cover a different body.
        d = json.loads(self.claim_path.read_text())
        d["claim_id"] = "f" * 64
        p = self.d / "badid.json"
        p.write_text(json.dumps(d))
        self.assertEqual(li.load_claim(str(p))["refusal"], "CLAIM_ID_MISMATCH")

    def test_body_tampering_is_caught(self):
        d = json.loads(self.claim_path.read_text())
        d["body"]["tau"] = "🖤"            # changes the body, id no longer matches
        p = self.d / "tampered.json"
        p.write_text(json.dumps(d))
        self.assertEqual(li.load_claim(str(p))["refusal"], "CLAIM_ID_MISMATCH")

    def test_malformed_claim_inputs_are_named_not_exceptions(self):
        cases = {"notjson.json": b"{oops", "dup.json": b'{"a":1,"a":2}',
                 "list.json": b"[]", "empty.json": b"{}"}
        for name, blob in cases.items():
            with self.subTest(name=name):
                p = self.d / name
                p.write_bytes(blob)
                res = li.load_claim(str(p))          # must not raise
                self.assertFalse(res["ok"])
                self.assertTrue(res["refusal"].startswith("CLAIM_"))

    def test_proposer_key_refusals(self):
        self.assertEqual(li.load_proposer_key(str(self.d / "none.key"))["refusal"],
                         "PROPOSER_KEY_UNREADABLE")
        bad = self.d / "bad.key"
        bad.write_text("zz\n")
        self.assertEqual(li.load_proposer_key(str(bad))["refusal"],
                         "PROPOSER_KEY_MALFORMED")


class EnvelopeTest(LI1Base):
    """The envelope binds parent, operation, claim and proposer under one
    signature, with its own domain separation."""

    def test_envelope_domain_is_distinct_from_the_claim_domain(self):
        self.assertNotEqual(li.ENVELOPE_SIG_DOMAIN, b"warrant-sig-v1:")
        msg = li.envelope_message("ab" * 32)
        self.assertTrue(msg.startswith(li.ENVELOPE_SIG_DOMAIN))

    def test_claim_signature_cannot_be_replayed_as_an_envelope_signature(self):
        prop = self.make_proposal()
        raw = json.loads(self.out.read_text())
        raw["envelope_signature_hex"] = self.claim.signature_hex
        p = self.d / "replay.json"
        p.write_text(json.dumps(raw))
        res = li.verify_proposal(p.read_bytes())
        self.assertEqual(res["refusal"], "PROPOSAL_SIGNATURE_INVALID")
        self.assertEqual(prop["status"], "PROPOSAL_ONLY")

    def test_retargeting_the_parent_breaks_the_envelope(self):
        self.make_proposal()
        doc = json.loads(self.out.read_text())
        doc["body"]["parent_pdf_sha256"] = "0" * 64
        p = self.d / "retarget.json"
        p.write_text(json.dumps(doc))
        # The id no longer matches the body; re-deriving it then fails the signature.
        self.assertEqual(li.verify_proposal(p.read_bytes())["refusal"],
                         "PROPOSAL_ID_MISMATCH")
        doc["proposal_id"] = li.compute_proposal_id(doc["body"])
        p.write_text(json.dumps(doc))
        self.assertEqual(li.verify_proposal(p.read_bytes())["refusal"],
                         "PROPOSAL_SIGNATURE_INVALID")

    def test_author_and_proposer_are_recorded_separately(self):
        prop = self.make_proposal()
        self.assertEqual(prop["proposer_pk_hex"], self.p_pk)
        self.assertEqual(prop["claim_author_pk_hex"], self.a_pk)
        self.assertNotEqual(prop["proposer_pk_hex"], prop["claim_author_pk_hex"])

    def test_no_file_paths_in_the_signed_body(self):
        self.make_proposal()
        body = json.loads(self.out.read_text())["body"]
        blob = json.dumps(body)
        for locator in (str(self.parent), str(self.claim_path), str(self.key_path),
                        "parent.pdf", "claim.json", "proposer.key"):
            self.assertNotIn(locator, blob)

    def test_malformed_proposals_are_named_not_exceptions(self):
        for blob in (b"", b"{", b"[]", b"null", b'{"a":1,"a":2}', b'{"profile":"x"}'):
            with self.subTest(blob=blob):
                res = li.verify_proposal(blob)       # must not raise
                self.assertFalse(res["ok"])
                self.assertTrue(res["refusal"].startswith(("PROPOSAL_", "UNSUPPORTED_")))

    def test_secret_key_never_appears_in_the_proposal(self):
        self.make_proposal()
        self.assertNotIn(self.p_sk, self.out.read_text())


class EnvelopeReaderAuthenticatesClaimTest(LI1Base):
    """A receiver of an EXTERNAL envelope cannot assume it came through our own
    add_claim. The reader must repeat the full claim authentication, not lean on
    the proposer's signature -- which only proves who sealed the envelope."""

    def setUp(self):
        super().setUp()
        self.good_claim = json.loads(self.claim_path.read_text())

    def sealed(self, claim_value, fmt="WARRANT-0.2", operation="add-claim"):
        """A genuinely proposer-signed envelope around arbitrary content."""
        body = {"operation": operation, "parent_pdf_sha256": self.parent_sha,
                "parent_manifest_format": fmt, "claim": claim_value,
                "proposer_pk_hex": self.p_pk}
        pid = li.compute_proposal_id(body)
        return json.dumps({
            "profile": li.PROPOSAL_PROFILE, "body": body, "proposal_id": pid,
            "envelope_signature_hex": crypto.sign_hex(self.p_sk,
                                                      li.envelope_message(pid)),
        }).encode()

    def _bad_claims(self):
        import copy
        bad_sig = copy.deepcopy(self.good_claim)
        bad_sig["signature_hex"] = "0" * 8 + bad_sig["signature_hex"][8:]
        bad_id = copy.deepcopy(self.good_claim)
        bad_id["claim_id"] = "f" * 64
        tampered = copy.deepcopy(self.good_claim)
        tampered["body"]["tau"] = "🖤"
        no_witness = copy.deepcopy(self.good_claim)
        no_witness["body"].pop("witness")
        return {
            "null": (None, "CLAIM_MALFORMED"),
            "empty_object": ({}, "CLAIM_MALFORMED"),
            "list": ([], "CLAIM_MALFORMED"),
            "string": ("text", "CLAIM_MALFORMED"),
            "missing_witness": (no_witness, "CLAIM_MALFORMED"),
            "invalid_author_signature": (bad_sig, "CLAIM_SIGNATURE_INVALID"),
            "wrong_claim_id": (bad_id, "CLAIM_ID_MISMATCH"),
            "tampered_body": (tampered, "CLAIM_ID_MISMATCH"),
        }

    def test_a_real_proposer_signature_does_not_launder_a_bad_claim(self):
        for label, (value, want) in self._bad_claims().items():
            with self.subTest(claim=label):
                res = li.verify_proposal(self.sealed(value))
                self.assertFalse(res["ok"], f"{label} was accepted")
                self.assertEqual(res["refusal"], want)

    def test_both_paths_reject_the_same_claim_documents_identically(self):
        """The shared check is actually shared: intake and the envelope reader
        return the SAME named refusal for the same claim document."""
        for label, (value, want) in self._bad_claims().items():
            with self.subTest(claim=label):
                intake = li.authenticate_claim_document(value)
                reader = li.verify_proposal(self.sealed(value))
                self.assertEqual(intake["refusal"], want)
                self.assertEqual(reader["refusal"], intake["refusal"])

    def test_intake_file_path_and_envelope_path_agree_on_disk_too(self):
        for label, (value, want) in self._bad_claims().items():
            with self.subTest(claim=label):
                p = self.d / f"c_{label}.json"
                p.write_text(json.dumps(value))
                self.assertEqual(li.load_claim(str(p))["refusal"], want)

    def test_signed_but_unsupported_parent_manifest_format_is_refused(self):
        # A real signature over an unknown profile does not make it supported.
        res = li.verify_proposal(self.sealed(self.good_claim, fmt="unsupported.v99"))
        self.assertFalse(res["ok"])
        self.assertEqual(res["refusal"], "PROPOSAL_UNSUPPORTED_MANIFEST_FORMAT")

    def test_signed_but_unsupported_operation_is_refused(self):
        res = li.verify_proposal(self.sealed(self.good_claim, operation="apply"))
        self.assertFalse(res["ok"])
        self.assertEqual(res["refusal"], "UNSUPPORTED_OPERATION")

    def test_honest_positive_with_distinct_author_and_proposer_keys(self):
        res = li.verify_proposal(self.sealed(self.good_claim), self.parent_sha)
        self.assertTrue(res["ok"], res)
        self.assertEqual(res["status"], "PROPOSAL_ONLY")
        self.assertNotEqual(res["claim_author_pk_hex"], res["proposer_pk_hex"])
        self.assertEqual(res["claim_author_pk_hex"], self.a_pk)
        self.assertEqual(res["proposer_pk_hex"], self.p_pk)
        # authenticated != evaluated != admitted
        self.assertTrue(res["claim_authenticated"])
        self.assertFalse(res["evaluated"])
        self.assertFalse(res["admitted"])

    def test_every_signed_body_field_is_validated_by_the_reader(self):
        """Exhaust the class: each field of the signed body must have at least
        one value the reader refuses. A field nobody can break is a field nobody
        checks."""
        breakers = {
            "operation": ("apply", "UNSUPPORTED_OPERATION"),
            "parent_pdf_sha256": ("zz" * 32, "PROPOSAL_MALFORMED"),
            "parent_manifest_format": ("unsupported.v99",
                                       "PROPOSAL_UNSUPPORTED_MANIFEST_FORMAT"),
            "claim": (None, "CLAIM_MALFORMED"),
            "proposer_pk_hex": ("00" * 32, "PROPOSAL_MALFORMED"),
        }
        body_fields = set(json.loads(self.sealed(self.good_claim))["body"].keys())
        self.assertEqual(set(breakers), body_fields,
                         "a signed body field has no refusal control")
        for field, (value, want) in breakers.items():
            with self.subTest(field=field):
                body = {"operation": "add-claim", "parent_pdf_sha256": self.parent_sha,
                        "parent_manifest_format": "WARRANT-0.2",
                        "claim": self.good_claim, "proposer_pk_hex": self.p_pk}
                body[field] = value
                pid = li.compute_proposal_id(body)
                raw = json.dumps({
                    "profile": li.PROPOSAL_PROFILE, "body": body, "proposal_id": pid,
                    "envelope_signature_hex": crypto.sign_hex(
                        self.p_sk, li.envelope_message(pid))}).encode()
                res = li.verify_proposal(raw)
                self.assertFalse(res["ok"], f"{field} accepted a broken value")
                self.assertEqual(res["refusal"], want)


class CliAcceptanceTest(LI1Base):
    """The LI-1 acceptance list, exercised through the REAL CLI subprocess."""

    def test_cli_creates_a_parseable_parent_bound_proposal(self):
        prop = self.make_proposal()
        self.assertEqual(prop["parent_pdf_sha256"], self.parent_sha)
        saved = json.loads(self.out.read_text())
        self.assertEqual(saved["profile"], li.PROPOSAL_PROFILE)
        self.assertTrue(li.verify_proposal(self.out.read_bytes(), self.parent_sha)["ok"])

    def test_a_second_parent_cannot_consume_the_proposal(self):
        self.make_proposal()
        p2 = self.second_parent()
        r = self.cli("inspect", "--pdf", str(p2), "--proposal", str(self.out))
        self.assertEqual(r.returncode, 2, r.stdout)
        self.assertIn("PROPOSAL_PARENT_MISMATCH", r.stdout)

    def test_cli_refuses_a_wrong_parent_pin(self):
        r = self.cli("add-claim", "--pdf", str(self.parent),
                     "--expect-parent-sha256", "0" * 64,
                     "--claim", str(self.claim_path),
                     "--proposer-key-file", str(self.key_path),
                     "--out", str(self.d / "never.json"))
        self.assertEqual(r.returncode, 2)
        self.assertIn("PARENT_PIN_MISMATCH", r.stdout)
        self.assertFalse((self.d / "never.json").exists())

    def test_cli_refuses_a_pre_existing_output_and_leaves_it_unchanged(self):
        self.make_proposal()
        before = self.out.read_bytes()
        r = self.cli("add-claim", "--pdf", str(self.parent),
                     "--expect-parent-sha256", self.parent_sha,
                     "--claim", str(self.claim_path),
                     "--proposer-key-file", str(self.key_path),
                     "--out", str(self.out))
        self.assertEqual(r.returncode, 2)
        self.assertIn("OUTPUT_EXISTS", r.stdout)
        self.assertEqual(self.out.read_bytes(), before)

    def test_inputs_are_byte_identical_after_every_refusal(self):
        digests = {p: _sha256(p) for p in (self.parent, self.claim_path, self.key_path)}
        bad_claim = self.d / "badsig.json"
        d = json.loads(self.claim_path.read_text())
        d["signature_hex"] = "0" * 8 + d["signature_hex"][8:]
        bad_claim.write_text(json.dumps(d))
        for args in (
            ("--expect-parent-sha256", "0" * 64, "--claim", str(self.claim_path)),
            ("--expect-parent-sha256", self.parent_sha, "--claim", str(bad_claim)),
            ("--expect-parent-sha256", self.parent_sha, "--claim", str(self.d / "absent.json")),
        ):
            r = self.cli("add-claim", "--pdf", str(self.parent), *args,
                         "--proposer-key-file", str(self.key_path),
                         "--out", str(self.d / "o.json"))
            self.assertEqual(r.returncode, 2, r.stdout)
        for p, want in digests.items():
            self.assertEqual(_sha256(p), want, f"{p} changed during a refusal")

    def test_intake_never_reports_an_accepted_claim(self):
        r = self.cli("add-claim", "--pdf", str(self.parent),
                     "--expect-parent-sha256", self.parent_sha,
                     "--claim", str(self.claim_path),
                     "--proposer-key-file", str(self.key_path),
                     "--out", str(self.out))
        self.assertEqual(r.returncode, 0)
        low = r.stdout.lower()
        # Only ASSERTIONS of acceptance are forbidden. "nothing admitted" is the
        # honest wording, so the predicate is the claim, not the bare word.
        for forbidden in ("accepted claim", "claim accepted", "admitted claim",
                          "claim admitted", "verified claim", "claim is true",
                          "proven", "admitted: true", "evaluated: true"):
            self.assertNotIn(forbidden, low)
        self.assertIn("PROPOSAL ONLY", r.stdout)
        self.assertIn("evaluated: False", r.stdout)
        self.assertIn("admitted: False", r.stdout)

    def test_structured_result_states_nothing_was_evaluated_or_admitted(self):
        prop = self.make_proposal()
        self.assertFalse(prop["evaluated"])
        self.assertFalse(prop["admitted"])
        self.assertEqual(prop["status"], "PROPOSAL_ONLY")

    def test_input_pdf_is_never_executed(self):
        # A parent whose embedded python would drop a sentinel if it ever ran.
        sentinel = self.d / "EXECUTED"
        raw = self.parent.read_bytes()
        payload = (b"\nimport pathlib; pathlib.Path(%r).write_text('x')\n"
                   % str(sentinel).encode())
        booby = self.d / "booby.pdf"
        booby.write_bytes(raw + payload)
        for args in (("inspect", "--pdf", str(booby)),
                     ("add-claim", "--pdf", str(booby),
                      "--expect-parent-sha256", _sha256(booby),
                      "--claim", str(self.claim_path),
                      "--proposer-key-file", str(self.key_path),
                      "--out", str(self.d / "b.json"))):
            self.cli(*args)
            self.assertFalse(sentinel.exists(),
                             "the input PDF's embedded code was executed")

    def test_same_inputs_twice_produce_the_same_proposal_bytes(self):
        self.make_proposal()
        first = self.out.read_bytes()
        second_path = self.d / "again.json"
        r = self.cli("add-claim", "--pdf", str(self.parent),
                     "--expect-parent-sha256", self.parent_sha,
                     "--claim", str(self.claim_path),
                     "--proposer-key-file", str(self.key_path),
                     "--out", str(second_path))
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(second_path.read_bytes(), first)


# --------------------------------------------------------------------------- #
# LI-2: evidence evaluation and an attributed admission decision
# --------------------------------------------------------------------------- #
import glyph

I_G, S_G = "🤍", "🌿"
SETTLED = f"{I_G} {I_G}"
OMEGA = f"{S_G} {I_G} {I_G} ({S_G} {I_G} {I_G})"      # does not settle


class LI2Base(LI1Base):
    def setUp(self):
        super().setUp()
        self.d_sk, self.d_pk = crypto.generate_keypair()      # DECIDER identity
        self.decider_key = self.d / "decider.key"
        self.decider_key.write_text(self.d_sk + "\n")
        self.policy_path = self.d / "policy.json"
        self.policy_path.write_text(json.dumps(self.policy_doc(), indent=2))

    def policy_doc(self, **over):
        pol = {"profile": li.POLICY_PROFILE,
               "trust_config": {"trusted_author_pks": [self.a_pk],
                                "admitted_grades": ["GROUNDED"],
                                "max_atp_budget": 10000,
                                "require_bound_signature": True},
               "allowed_operations": ["add-claim"],
               "allowed_grades": ["GROUNDED"]}
        for k, v in over.items():
            if k.startswith("tc_"):
                pol["trust_config"][k[3:]] = v
            else:
                pol[k] = v
        return pol

    def write_policy(self, name, **over):
        p = self.d / name
        p.write_text(json.dumps(self.policy_doc(**over), indent=2))
        return p

    def grounded_claim(self, term, expected_hash, budget=100):
        ph = glyph.term_hash(glyph.parse(term))
        return wk.EdgeClaim.create_and_sign(
            ph, term, term, ph, wk.Polarity.AFFIRM,
            wk.GroundedWitness(term_expr=term, expected_hash=expected_hash,
                               atp_budget=budget),
            self.a_sk, self.a_pk)

    def case_claim(self, kind):
        if kind == "pass":
            h = glyph.evaluate(glyph.parse(SETTLED), max_atp=100).hash
            return self.grounded_claim(SETTLED, h)
        if kind == "fail":
            return self.grounded_claim(SETTLED, "0" * 64)
        if kind == "unverified":
            h = glyph.evaluate(glyph.parse(OMEGA), max_atp=100).hash
            return self.grounded_claim(OMEGA, h)
        raise AssertionError(kind)

    def proposal_for(self, claim, name="p.json"):
        cp = self.d / f"claim_{name}"
        cp.write_text(json.dumps(claim.to_dict(), indent=2))
        out = self.d / name
        r = self.cli("add-claim", "--pdf", str(self.parent),
                     "--expect-parent-sha256", self.parent_sha,
                     "--claim", str(cp), "--proposer-key-file", str(self.key_path),
                     "--out", str(out), "--json")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return out

    def evaluate_cli(self, proposal_path, policy_path=None, out_name="d.json"):
        out = self.d / out_name
        r = self.cli("evaluate", "--pdf", str(self.parent),
                     "--proposal", str(proposal_path),
                     "--policy", str(policy_path or self.policy_path),
                     "--decider-key-file", str(self.decider_key),
                     "--out", str(out), "--json")
        return r, out


class VerdictVocabularyTest(LI2Base):
    """The verdict/grade vocabularies are taken FROM the enums, never restated:
    VerificationStatus values are lowercase while EvidenceGrade values are
    uppercase, and hand-written strings silently disabled admission."""

    def test_constants_match_the_enums(self):
        self.assertEqual(li.VERDICT_PASS, wk.VerificationStatus.PASS.value)
        self.assertEqual(li.VERDICT_VALUES,
                         frozenset(v.value for v in wk.VerificationStatus))
        self.assertEqual(li.SUPPORTED_GRADE, wk.EvidenceGrade.GROUNDED.value)

    def test_status_and_grade_cases_actually_differ(self):
        self.assertEqual(wk.VerificationStatus.PASS.value, "pass")
        self.assertEqual(wk.EvidenceGrade.GROUNDED.value, "GROUNDED")


class PolicyTest(LI2Base):
    """The caller's policy, and the two shapes the brief forbids."""

    def test_valid_policy_loads_and_digests(self):
        res = li.load_policy(str(self.policy_path))
        self.assertTrue(res["ok"], res)
        self.assertEqual(len(res["policy_sha256"]), 64)

    def test_trust_all_author_set_is_refused(self):
        for value in (None, "omit"):
            with self.subTest(value=value):
                doc = self.policy_doc()
                if value == "omit":
                    doc["trust_config"].pop("trusted_author_pks")
                else:
                    doc["trust_config"]["trusted_author_pks"] = None
                p = self.d / "trustall.json"
                p.write_text(json.dumps(doc))
                self.assertEqual(li.load_policy(str(p))["refusal"], "POLICY_TRUST_ALL")

    def test_empty_author_list_is_a_valid_deny_all(self):
        # None means trust-everyone; [] is a legitimate deny-all and is accepted.
        p = self.write_policy("deny.json", tc_trusted_author_pks=[])
        self.assertTrue(li.load_policy(str(p))["ok"])

    def test_waiving_signature_checks_is_refused(self):
        for value in (False, None, "yes", 1):
            with self.subTest(value=value):
                p = self.write_policy("nosig.json", tc_require_bound_signature=value)
                self.assertEqual(li.load_policy(str(p))["refusal"], "POLICY_NO_SIGNATURE")

    def test_other_grades_are_unsupported_operations(self):
        for field, value in (("tc_admitted_grades", ["AXIOMATIC"]),
                             ("allowed_grades", ["EMPIRICAL"]),
                             ("tc_admitted_grades", ["GROUNDED", "AXIOMATIC"])):
            with self.subTest(field=field, value=value):
                p = self.write_policy("grade.json", **{field: value})
                self.assertEqual(li.load_policy(str(p))["refusal"],
                                 "POLICY_UNSUPPORTED_GRADE")

    def test_other_operations_are_refused(self):
        p = self.write_policy("op.json", allowed_operations=["apply"])
        self.assertEqual(li.load_policy(str(p))["refusal"], "POLICY_UNSUPPORTED_OPERATION")

    def test_budget_must_be_a_positive_int(self):
        for value in (0, -1, "100", True, None, 1.5):
            with self.subTest(value=value):
                p = self.write_policy("budget.json", tc_max_atp_budget=value)
                self.assertEqual(li.load_policy(str(p))["refusal"], "POLICY_BUDGET_INVALID")

    def test_malformed_policies_are_named_not_exceptions(self):
        for name, blob in (("a.json", b"{"), ("b.json", b"[]"),
                           ("c.json", b'{"a":1,"a":2}'), ("d.json", b"{}")):
            with self.subTest(name=name):
                p = self.d / name
                p.write_bytes(blob)
                res = li.load_policy(str(p))
                self.assertFalse(res["ok"])
                self.assertTrue(res["refusal"].startswith("POLICY_"))


class EvaluationTest(LI2Base):
    """Grade G through the real verifier: the three outcomes, and admission as
    a SEPARATE quantity."""

    def test_settled_match_passes_and_can_be_admitted(self):
        r, out = self.evaluate_cli(self.proposal_for(self.case_claim("pass")))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        res = json.loads(r.stdout)
        self.assertEqual(res["evaluation_status"], wk.VerificationStatus.PASS.value)
        self.assertTrue(res["admitted"])

    def test_settled_mismatch_fails(self):
        r, _ = self.evaluate_cli(self.proposal_for(self.case_claim("fail"), "f.json"),
                                 out_name="df.json")
        res = json.loads(r.stdout)
        self.assertEqual(res["evaluation_status"], wk.VerificationStatus.FAIL.value)
        self.assertFalse(res["admitted"])

    def test_non_termination_stays_unverified(self):
        r, _ = self.evaluate_cli(self.proposal_for(self.case_claim("unverified"), "u.json"),
                                 out_name="du.json")
        res = json.loads(r.stdout)
        self.assertEqual(res["evaluation_status"],
                         wk.VerificationStatus.UNVERIFIED.value)
        self.assertFalse(res["admitted"])
        # UNVERIFIED is no verdict -- never reported as a refutation
        self.assertNotIn("refut", res["admission_reason"].lower())

    def test_same_claim_under_a_policy_not_authorizing_its_author(self):
        deny = self.write_policy("deny2.json", tc_trusted_author_pks=[])
        r, _ = self.evaluate_cli(self.proposal_for(self.case_claim("pass"), "p2.json"),
                                 deny, out_name="dd.json")
        res = json.loads(r.stdout)
        self.assertNotEqual(res["evaluation_status"], wk.VerificationStatus.PASS.value)
        self.assertFalse(res["admitted"])

    def test_evidence_and_admission_are_separate_fields(self):
        # A PASS that policy does not permit must still record the PASS.
        ev = {"status": wk.VerificationStatus.PASS.value, "grade": "GROUNDED",
              "reason": "x"}
        denied = li.decide_admission(ev, "add-claim", "GROUNDED", ["apply"], ["GROUNDED"])
        self.assertFalse(denied["admitted"])
        self.assertEqual(ev["status"], wk.VerificationStatus.PASS.value)
        allowed = li.decide_admission(ev, "add-claim", "GROUNDED",
                                      ["add-claim"], ["GROUNDED"])
        self.assertTrue(allowed["admitted"])

    def test_admission_refusal_is_never_a_mathematical_claim(self):
        for ev_status in (wk.VerificationStatus.FAIL.value,
                          wk.VerificationStatus.UNVERIFIED.value):
            out = li.decide_admission({"status": ev_status, "grade": "GROUNDED",
                                       "reason": "r"}, "add-claim", "GROUNDED",
                                      ["add-claim"], ["GROUNDED"])
            self.assertFalse(out["admitted"])
            self.assertNotIn("false", out["reason"].lower())
            self.assertNotIn("disproved", out["reason"].lower())

    def test_evaluate_refuses_a_proposal_bound_to_another_parent(self):
        """LI-2 re-runs the LI-1 binding against THIS parent's bytes. Without
        it a decision could be produced for a document the proposal never
        targeted. (No other test covers evaluate's own precondition.)"""
        prop = self.proposal_for(self.case_claim("pass"), "bound.json")
        p2 = self.second_parent()
        out = self.d / "never_dec.json"
        r = self.cli("evaluate", "--pdf", str(p2), "--proposal", str(prop),
                     "--policy", str(self.policy_path),
                     "--decider-key-file", str(self.decider_key), "--out", str(out))
        self.assertEqual(r.returncode, 2, r.stdout)
        self.assertIn("PROPOSAL_PARENT_MISMATCH", r.stdout)
        self.assertFalse(out.exists())

    def test_api_and_cli_agree(self):
        """Both must exercise the same authoritative check, no adapter defaults."""
        prop = self.proposal_for(self.case_claim("pass"), "p3.json")
        r, _ = self.evaluate_cli(prop, out_name="cli.json")
        api = li.evaluate(str(self.parent), str(prop), str(self.policy_path),
                          str(self.decider_key), str(self.d / "api.json"))
        cli_res = json.loads(r.stdout)
        self.assertEqual(api["evaluation_status"], cli_res["evaluation_status"])
        self.assertEqual(api["admitted"], cli_res["admitted"])
        self.assertEqual(api["decision_id"], cli_res["decision_id"])


class AtpMeasurementTest(LI2Base):
    """The recorded counter must be the counter that actually ran. Verdict
    .delta_atp defaults to 0, so a branch that omits the measurement is
    indistinguishable from one that measured zero -- the recorded figure is
    therefore taken only from an explicit measurement, and is null otherwise."""

    def recorded(self, kind, policy=None, name=None):
        prop = self.proposal_for(self.case_claim(kind), f"atp_{name or kind}.json")
        r, out = self.evaluate_cli(prop, policy, out_name=f"datp_{name or kind}.json")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        body = json.loads(out.read_bytes().decode())["body"]
        return body["evaluation"]["status"], body["evaluator"]

    def test_settled_pass_records_the_actual_counter(self):
        actual = glyph.evaluate(glyph.parse(SETTLED), max_atp=100)
        status, ev = self.recorded("pass")
        self.assertEqual(status, wk.VerificationStatus.PASS.value)
        self.assertTrue(ev["atp_spent_measured"])
        self.assertEqual(ev["atp_spent"], actual.atp_spent)

    def test_settled_mismatch_records_the_actual_counter(self):
        # The reduction DID run: recording 0 here was the reported defect.
        actual = glyph.evaluate(glyph.parse(SETTLED), max_atp=100)
        self.assertGreater(actual.atp_spent, 0)
        status, ev = self.recorded("fail")
        self.assertEqual(status, wk.VerificationStatus.FAIL.value)
        self.assertTrue(ev["atp_spent_measured"])
        self.assertEqual(ev["atp_spent"], actual.atp_spent)
        self.assertNotEqual(ev["atp_spent"], 0)

    def test_suspended_run_records_the_actual_counter(self):
        actual = glyph.evaluate(glyph.parse(OMEGA), max_atp=100)
        self.assertFalse(actual.is_settled())
        status, ev = self.recorded("unverified")
        self.assertEqual(status, wk.VerificationStatus.UNVERIFIED.value)
        self.assertTrue(ev["atp_spent_measured"])
        self.assertEqual(ev["atp_spent"], actual.atp_spent)

    def test_a_refusal_before_execution_records_null_not_zero(self):
        # Deny-all policy: audit_claim returns before any reduction runs, so
        # there is NO measurement. It must be null, never 0.
        deny = self.write_policy("deny_atp.json", tc_trusted_author_pks=[])
        status, ev = self.recorded("pass", deny, name="deny")
        self.assertEqual(status, wk.VerificationStatus.UNVERIFIED.value)
        self.assertFalse(ev["atp_spent_measured"])
        self.assertIsNone(ev["atp_spent"])

    def test_verdict_delta_atp_alone_cannot_be_trusted(self):
        """Why the measurement comes from details, not delta_atp: the field
        defaults to 0 on every verdict that never measured anything."""
        v = wk.Verdict(status=wk.VerificationStatus.UNVERIFIED,
                       grade=wk.EvidenceGrade.GROUNDED, reason="no run")
        self.assertEqual(v.delta_atp, 0)
        self.assertEqual(v.details, {})


class ProducerReaderAgreementTest(LI2Base):
    """Whatever `evaluate` writes, this host's own reader must accept under the
    matching pins. Anything else is a producer/reader contract defect, even when
    it grants nothing: here a negative witness budget produced a decision that
    verify_decision then refused."""

    def _write_and_read(self, claim, policy=None, tag="rt"):
        cp = self.d / f"claim_{tag}.json"
        cp.write_text(json.dumps(claim.to_dict(), indent=2))
        prop = self.d / f"prop_{tag}.json"
        r = self.cli("add-claim", "--pdf", str(self.parent),
                     "--expect-parent-sha256", self.parent_sha, "--claim", str(cp),
                     "--proposer-key-file", str(self.key_path), "--out", str(prop),
                     "--json")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        out = self.d / f"dec_{tag}.json"
        r2 = self.cli("evaluate", "--pdf", str(self.parent), "--proposal", str(prop),
                      "--policy", str(policy or self.policy_path),
                      "--decider-key-file", str(self.decider_key), "--out", str(out),
                      "--json")
        return r2, out, prop

    def test_every_written_decision_is_accepted_by_its_own_reader(self):
        """The general invariant, not just the reported case."""
        deny = self.write_policy("deny_rt.json", tc_trusted_author_pks=[])
        scenarios = [("pass", None), ("fail", None), ("unverified", None),
                     ("pass", deny)]
        for kind, policy in scenarios:
            with self.subTest(kind=kind, policy=bool(policy)):
                tag = f"{kind}{'_deny' if policy else ''}"
                r, out, prop = self._write_and_read(self.case_claim(kind), policy, tag)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                res = json.loads(r.stdout)
                back = li.verify_decision(out.read_bytes(),
                                          expect_proposal_id=res["proposal_id"],
                                          expect_parent_sha256=res["parent_pdf_sha256"],
                                          expect_policy_sha256=res["policy_sha256"])
                self.assertTrue(back["ok"],
                                f"{tag}: written decision refused by its own reader: {back}")

    def test_negative_witness_budget_is_refused_without_writing(self):
        claim = self.grounded_claim(SETTLED, "0" * 64, budget=-1)
        r, out, _ = self._write_and_read(claim, tag="negbudget")
        self.assertEqual(r.returncode, 2, r.stdout)
        self.assertIn("CLAIM_BUDGET_INVALID", r.stdout)
        self.assertFalse(out.exists(), "a refused evaluation still wrote a decision")

    def test_budget_boundary_values(self):
        for budget, ok in ((0, True), (1, True), (-1, False), (-1000, False)):
            with self.subTest(budget=budget):
                claim = self.grounded_claim(SETTLED, "0" * 64, budget=budget)
                r, out, _ = self._write_and_read(claim, tag=f"b{budget}")
                self.assertEqual(r.returncode, 0 if ok else 2, r.stdout)
                self.assertEqual(out.exists(), ok)
                if ok:
                    self.assertTrue(li.verify_decision(out.read_bytes())["ok"])

    def test_a_body_the_reader_would_reject_is_never_emitted(self):
        """The structural guarantee: evaluate runs the formed body through the
        reader's own validator before signing. Simulated by making that
        validator reject everything -- nothing may be written."""
        out = self.d / "selfcheck.json"
        prop = self.proposal_for(self.case_claim("pass"), "sc.json")
        with mock.patch.object(li, "validate_decision_body",
                               return_value={"ok": False, "refusal": "X", "detail": "y"}):
            res = li.evaluate(str(self.parent), str(prop), str(self.policy_path),
                              str(self.decider_key), str(out))
        self.assertFalse(res["ok"])
        self.assertEqual(res["refusal"], "DECISION_SELF_CHECK_FAILED")
        self.assertFalse(out.exists())


class DecisionBindingTest(LI2Base):
    """A decision is a report bound to one subject; substituting anything must
    not transfer it."""

    def setUp(self):
        super().setUp()
        self.prop = self.proposal_for(self.case_claim("pass"))
        r, self.dec = self.evaluate_cli(self.prop)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.res = json.loads(r.stdout)
        self.raw = self.dec.read_bytes()

    def test_decision_verifies_against_its_own_pins(self):
        prop = json.loads(self.prop.read_text())
        out = li.verify_decision(self.raw, prop["proposal_id"], self.parent_sha,
                                 self.res["policy_sha256"])
        self.assertTrue(out["ok"], out)
        self.assertEqual(out["status"], "DECISION_ONLY")
        self.assertFalse(out["applied"])

    def test_each_substituted_pin_is_refused(self):
        for kwargs, want in (
            ({"expect_proposal_id": "0" * 64}, "DECISION_PROPOSAL_MISMATCH"),
            ({"expect_parent_sha256": "0" * 64}, "DECISION_PARENT_MISMATCH"),
            ({"expect_policy_sha256": "0" * 64}, "DECISION_POLICY_MISMATCH"),
        ):
            with self.subTest(want=want):
                self.assertEqual(li.verify_decision(self.raw, **kwargs)["refusal"], want)

    def test_flipping_the_verdict_or_admission_breaks_the_decision(self):
        # The flip must start from a NEGATIVE decision, otherwise setting
        # status="pass"/admitted=True on an already-passing decision changes
        # nothing and the control would be vacuous.
        negative_prop = self.proposal_for(self.case_claim("fail"), "neg.json")
        r, neg = self.evaluate_cli(negative_prop, out_name="dneg.json")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        neg_raw = neg.read_bytes()
        neg_body = json.loads(neg_raw.decode())["body"]
        self.assertNotEqual(neg_body["evaluation"]["status"],
                            wk.VerificationStatus.PASS.value)
        self.assertFalse(neg_body["admission"]["admitted"])

        # (source, path, value, refusal as-is, refusal after honest re-signing)
        cases = [
            (neg_raw, ("evaluation", "status"), wk.VerificationStatus.PASS.value,
             "DECISION_ID_MISMATCH", "DECISION_SIGNATURE_INVALID"),
            # admitted=true over a non-PASS verdict contradicts itself, so it is
            # caught by the consistency check even when honestly re-signed.
            (neg_raw, ("admission", "admitted"), True,
             "DECISION_INCONSISTENT", "DECISION_INCONSISTENT"),
            (self.raw, ("policy_sha256",), "0" * 64,
             "DECISION_ID_MISMATCH", "DECISION_SIGNATURE_INVALID"),
            (self.raw, ("parent_pdf_sha256",), "0" * 64,
             "DECISION_ID_MISMATCH", "DECISION_SIGNATURE_INVALID"),
            (self.raw, ("proposal_id",), "0" * 64,
             "DECISION_ID_MISMATCH", "DECISION_SIGNATURE_INVALID"),
        ]
        for source, path, value, want_raw, want_resigned in cases:
            with self.subTest(path=path):
                doc = json.loads(source.decode())
                target = doc["body"]
                for k in path[:-1]:
                    target = target[k]
                target[path[-1]] = value
                self.assertEqual(li.verify_decision(json.dumps(doc).encode())["refusal"],
                                 want_raw)
                doc["decision_id"] = li.compute_decision_id(doc["body"])
                self.assertEqual(li.verify_decision(json.dumps(doc).encode())["refusal"],
                                 want_resigned)

    def test_a_resigned_body_is_still_checked_for_content(self):
        """A decider signature is ATTRIBUTION, not evidence. Re-signing a body
        with the SAME key must not launder unsupported, malformed or
        self-contradictory content."""
        neg_prop = self.proposal_for(self.case_claim("fail"), "rs.json")
        r, neg = self.evaluate_cli(neg_prop, out_name="drs.json")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        base = json.loads(neg.read_bytes().decode())

        def resign(mutate):
            doc = json.loads(json.dumps(base))
            mutate(doc["body"])
            doc["decision_id"] = li.compute_decision_id(doc["body"])
            doc["decision_signature_hex"] = crypto.sign_hex(
                self.d_sk, li.decision_message(doc["decision_id"]))
            return json.dumps(doc).encode()

        def set_ev_profile(b):
            b["evaluator"]["profile"] = "unsupported.v99"

        def set_ev_version(b):
            b["evaluator"]["version"] = "99"

        def empty_evaluator(b):
            b["evaluator"] = {}

        def list_status(b):
            b["evaluation"]["status"] = []

        def drop_reason(b):
            b["admission"].pop("reason")

        def admit_on_fail(b):
            b["admission"]["admitted"] = True

        def fake_zero_atp(b):
            b["evaluator"]["atp_spent_measured"] = False
            b["evaluator"]["atp_spent"] = 0

        table = [(set_ev_profile, "DECISION_UNSUPPORTED_EVALUATOR"),
                 (set_ev_version, "DECISION_UNSUPPORTED_EVALUATOR"),
                 (empty_evaluator, "DECISION_FIELD_MISSING"),
                 (list_status, "DECISION_FIELD_TYPE"),
                 (drop_reason, "DECISION_FIELD_MISSING"),
                 (admit_on_fail, "DECISION_INCONSISTENT"),
                 (fake_zero_atp, "DECISION_FIELD_TYPE")]
        for mutate, want in table:
            with self.subTest(want=want, case=mutate.__name__):
                blob = resign(mutate)
                res = li.verify_decision(blob)          # must not raise
                self.assertFalse(res["ok"])
                self.assertEqual(res["refusal"], want)

    def test_verification_states_its_own_boundaries(self):
        out = li.verify_decision(self.raw)
        self.assertTrue(out["attribution_verified"])
        self.assertFalse(out["evidence_replayed_by_reader"])
        self.assertFalse(out["decider_authority_established"])

    def test_a_decision_for_one_proposal_does_not_cover_another(self):
        other = self.proposal_for(self.case_claim("fail"), "other.json")
        other_id = json.loads(other.read_text())["proposal_id"]
        self.assertEqual(li.verify_decision(self.raw, expect_proposal_id=other_id)["refusal"],
                         "DECISION_PROPOSAL_MISMATCH")

    def test_decision_records_the_actual_budget_figures(self):
        body = json.loads(self.raw.decode())["body"]
        ev = body["evaluator"]
        self.assertEqual(ev["profile"], li.EVALUATOR_PROFILE)
        self.assertEqual(ev["atp_budget_limit"], 10000)
        self.assertGreaterEqual(ev["atp_spent"], 0)
        self.assertIn("atp_budget_requested", ev)

    def test_decision_domain_is_distinct(self):
        self.assertNotEqual(li.DECISION_SIG_DOMAIN, li.ENVELOPE_SIG_DOMAIN)
        self.assertNotEqual(li.DECISION_SIG_DOMAIN, b"warrant-sig-v1:")

    def test_malformed_decisions_are_named_not_exceptions(self):
        for blob in (b"", b"{", b"[]", b"null", b'{"a":1,"a":2}',
                     b'{"profile":"x","body":{},"decision_id":"0",'
                     b'"decision_signature_hex":"0"}'):
            with self.subTest(blob=blob):
                res = li.verify_decision(blob)
                self.assertFalse(res["ok"])
                self.assertTrue(res["refusal"].startswith("DECISION_"))


class LI2StateEffectTest(LI2Base):
    """A decision is recorded and nothing else happens."""

    def test_refusals_write_nothing_and_preserve_inputs(self):
        prop = self.proposal_for(self.case_claim("pass"))
        digests = {p: _sha256(p) for p in (self.parent, prop, self.policy_path,
                                           self.decider_key)}
        bad_policy = self.write_policy("nosig2.json", tc_require_bound_signature=False)
        out = self.d / "never.json"
        r = self.cli("evaluate", "--pdf", str(self.parent), "--proposal", str(prop),
                     "--policy", str(bad_policy), "--decider-key-file",
                     str(self.decider_key), "--out", str(out))
        self.assertEqual(r.returncode, 2)
        self.assertIn("POLICY_NO_SIGNATURE", r.stdout)
        self.assertFalse(out.exists())
        for p, want in digests.items():
            self.assertEqual(_sha256(p), want)

    def test_parent_is_untouched_by_a_successful_evaluation(self):
        before = self.parent.read_bytes()
        self.evaluate_cli(self.proposal_for(self.case_claim("pass")))
        self.assertEqual(self.parent.read_bytes(), before)

    def test_existing_decision_output_is_not_overwritten(self):
        prop = self.proposal_for(self.case_claim("pass"))
        r, out = self.evaluate_cli(prop)
        self.assertEqual(r.returncode, 0)
        before = out.read_bytes()
        r2, _ = self.evaluate_cli(prop)
        self.assertEqual(r2.returncode, 2)
        self.assertIn("OUTPUT_EXISTS", r2.stdout)
        self.assertEqual(out.read_bytes(), before)

    def test_evaluate_produces_no_successor_pdf(self):
        before = sorted(p.name for p in self.d.iterdir())
        r, out = self.evaluate_cli(self.proposal_for(self.case_claim("pass")))
        self.assertEqual(r.returncode, 0)
        after = sorted(p.name for p in self.d.iterdir())
        new = set(after) - set(before)
        self.assertFalse([n for n in new if n.endswith(".pdf")],
                         f"evaluate created a PDF: {new}")

    def test_result_states_it_is_a_decision_only(self):
        r, _ = self.evaluate_cli(self.proposal_for(self.case_claim("pass")))
        res = json.loads(r.stdout)
        self.assertEqual(res["status"], "DECISION_ONLY")
        self.assertFalse(res["applied"])


# --------------------------------------------------------------------------- #
# LI-3: immutable successor and a readable transition
# --------------------------------------------------------------------------- #
class LI3Base(LI2Base):
    def setUp(self):
        super().setUp()
        self.i_sk, self.i_pk = crypto.generate_keypair()        # receipt ISSUER
        self.issuer_key = self.d / "issuer.key"
        self.issuer_key.write_text(self.i_sk + "\n")
        # a DIFFERENT pre-existing claim, so preservation is observable
        self.old_claim = self.grounded_claim("🖤", "f" * 64, budget=10)
        self.parent = self.d / "parent3.pdf"
        wk.generate_warrant_ledger_pdf([self.old_claim], str(self.parent),
                                       wk.TrustConfig())
        self.parent_sha = _sha256(self.parent)

    def pipeline(self, claim=None, tag="t", policy=None):
        """add-claim -> evaluate, returning (proposal, decision)."""
        claim = claim if claim is not None else self.case_claim("pass")
        cp = self.d / f"c_{tag}.json"
        cp.write_text(json.dumps(claim.to_dict(), indent=2))
        prop = self.d / f"p_{tag}.json"
        r = self.cli("add-claim", "--pdf", str(self.parent),
                     "--expect-parent-sha256", self.parent_sha, "--claim", str(cp),
                     "--proposer-key-file", str(self.key_path), "--out", str(prop))
        self.assertEqual(r.returncode, 0, r.stdout)
        dec = self.d / f"d_{tag}.json"
        r = self.cli("evaluate", "--pdf", str(self.parent), "--proposal", str(prop),
                     "--policy", str(policy or self.policy_path),
                     "--decider-key-file", str(self.decider_key), "--out", str(dec))
        self.assertEqual(r.returncode, 0, r.stdout)
        return prop, dec

    def apply_cli(self, prop, dec, tag="t", policy=None, parent=None):
        out = self.d / f"s_{tag}.pdf"
        rec = self.d / f"r_{tag}.json"
        r = self.cli("apply", "--pdf", str(parent or self.parent),
                     "--proposal", str(prop), "--decision", str(dec),
                     "--policy", str(policy or self.policy_path),
                     "--issuer-key-file", str(self.issuer_key),
                     "--out", str(out), "--receipt", str(rec), "--json")
        return r, out, rec

    def explain_cli(self, prop, dec, out, rec, issuer=None, parent=None):
        args = ["explain-transition", "--parent", str(parent or self.parent),
                "--successor", str(out), "--proposal", str(prop),
                "--decision", str(dec), "--receipt", str(rec), "--json"]
        if issuer is not None:
            args += ["--expect-issuer-pk", issuer]
        return self.cli(*args)


class SuccessorProfileTest(LI3Base):
    """The successor is data-only, and it composes."""

    def test_successor_is_data_only_and_starts_at_pdf(self):
        prop, dec = self.pipeline()
        r, out, _rec = self.apply_cli(prop, dec)
        self.assertEqual(r.returncode, 0, r.stdout)
        raw = out.read_bytes()
        self.assertEqual(raw[:8], b"%PDF-1.7")
        self.assertNotIn(b"#!/", raw)
        self.assertNotIn(b"import sys", raw)
        self.assertNotIn(b"__file__", raw)

    def test_successor_xref_offsets_are_correct(self):
        # The parent profile's offsets are wrong by its prologue length; the
        # successor's must actually point at the objects.
        prop, dec = self.pipeline(tag="x")
        r, out, _ = self.apply_cli(prop, dec, tag="x")
        self.assertEqual(r.returncode, 0, r.stdout)
        raw = out.read_bytes()
        sx = int(re.search(rb"startxref\s+(\d+)", raw).group(1))
        self.assertEqual(raw[sx:sx + 4], b"xref")
        xr = raw.find(b"xref")
        first = int(raw[xr + 11:xr + 41].split()[3])
        self.assertEqual(raw[first:first + 7], b"1 0 obj")

    def test_a_successor_can_be_the_parent_of_the_next_proposal(self):
        prop, dec = self.pipeline(tag="c")
        r, out, _ = self.apply_cli(prop, dec, tag="c")
        self.assertEqual(r.returncode, 0, r.stdout)
        res = li.read_parent(str(out))
        self.assertTrue(res["ok"], res)
        self.assertEqual(res["claim_count"], 2)

    def test_parent_file_is_never_written_to(self):
        before = self.parent.read_bytes()
        prop, dec = self.pipeline(tag="pu")
        r, _out, _rec = self.apply_cli(prop, dec, tag="pu")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(self.parent.read_bytes(), before)


class TransitionVerificationTest(LI3Base):
    """A fresh verifier confirms preservation and exactly-one addition."""

    def setUp(self):
        super().setUp()
        self.prop, self.dec = self.pipeline(tag="v")
        r, self.out, self.rec = self.apply_cli(self.prop, self.dec, tag="v")
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_old_claims_remain_and_exactly_one_is_added(self):
        r = self.explain_cli(self.prop, self.dec, self.out, self.rec, self.i_pk)
        self.assertEqual(r.returncode, 0, r.stdout)
        res = json.loads(r.stdout)
        self.assertEqual(res["claims_preserved"], 1)
        self.assertEqual(res["claims_after"], 2)
        self.assertEqual(len(res["admitted_claim_ids"]), 1)
        self.assertFalse(res["regenerated"])
        self.assertFalse(res["evidence_replayed_by_reader"])

    def test_verification_does_not_regenerate_the_successor(self):
        with mock.patch.object(li, "render_successor_pdf",
                               side_effect=AssertionError("regeneration forbidden")):
            res = li.explain_transition(str(self.parent), str(self.out), str(self.prop),
                                        str(self.dec), str(self.rec), self.i_pk)
        self.assertTrue(res["ok"], res)

    def test_issuer_is_not_self_declaring(self):
        # Without a caller-pinned issuer, authority is reported as NOT established.
        r = self.explain_cli(self.prop, self.dec, self.out, self.rec, issuer=None)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertFalse(json.loads(r.stdout)["issuer_authorized_by_caller"])
        # A different pinned issuer is a refusal.
        _other_sk, other_pk = crypto.generate_keypair()
        r2 = self.explain_cli(self.prop, self.dec, self.out, self.rec, other_pk)
        self.assertEqual(r2.returncode, 2)
        self.assertIn("RECEIPT_ISSUER_MISMATCH", r2.stdout)

    def test_altering_each_artifact_is_detected(self):
        table = {}

        def flip(path):
            b = bytearray(path.read_bytes())
            i = len(b) // 2
            b[i] = b[i] ^ 0x01
            return bytes(b)

        for label, path in (("successor", self.out), ("receipt", self.rec)):
            with self.subTest(artifact=label):
                original = path.read_bytes()
                path.write_bytes(flip(path))
                try:
                    r = self.explain_cli(self.prop, self.dec, self.out, self.rec, self.i_pk)
                    self.assertEqual(r.returncode, 2, f"{label} tamper not detected")
                    table[label] = r.stdout
                finally:
                    path.write_bytes(original)
        self.assertEqual(len(table), 2)

    def test_a_successor_with_a_dropped_parent_claim_is_refused(self):
        # Build a successor that keeps only the NEW claim: preservation broken.
        added = json.loads(self.prop.read_text())["body"]["claim"]
        forged = self.d / "forged.pdf"
        forged.write_bytes(li.render_successor_pdf([added], ["forged"]))
        res = li.explain_transition(str(self.parent), str(forged), str(self.prop),
                                    str(self.dec), str(self.rec), self.i_pk)
        self.assertFalse(res["ok"])
        # the receipt binds the real successor bytes, so this is caught there
        self.assertEqual(res["refusal"], "RECEIPT_SUCCESSOR_MISMATCH")

    def test_claim_preservation_is_checked_independently_of_the_receipt(self):
        """Re-issue a receipt for the forged successor: preservation must still
        be the thing that refuses it."""
        added = json.loads(self.prop.read_text())["body"]["claim"]
        forged = self.d / "forged2.pdf"
        forged.write_bytes(li.render_successor_pdf([added], ["forged"]))
        body = li.receipt_body(self.parent_sha, _sha256(forged),
                               json.loads(self.prop.read_text())["proposal_id"],
                               json.loads(self.rec.read_text())["body"]["decision_id"],
                               json.loads(self.rec.read_text())["body"]["policy_sha256"],
                               added["claim_id"], self.i_pk)
        rid = li.compute_receipt_id(body)
        doc = {"profile": li.TRANSITION_PROFILE, "body": body, "receipt_id": rid,
               "receipt_signature_hex": crypto.sign_hex(self.i_sk, li.receipt_message(rid))}
        rec2 = self.d / "rec2.json"
        rec2.write_text(json.dumps(doc))
        res = li.explain_transition(str(self.parent), str(forged), str(self.prop),
                                    str(self.dec), str(rec2), self.i_pk)
        self.assertFalse(res["ok"])
        self.assertEqual(res["refusal"], "PARENT_CLAIMS_DROPPED")


class ApplyStateEffectTest(LI3Base):
    """Repetition, staging, write failure and recovery."""

    def test_repeat_application_refuses_and_adds_nothing(self):
        prop, dec = self.pipeline(tag="r1")
        r1, out, rec = self.apply_cli(prop, dec, tag="r1")
        self.assertEqual(r1.returncode, 0, r1.stdout)
        before_out, before_rec = out.read_bytes(), rec.read_bytes()
        r2, _o, _r = self.apply_cli(prop, dec, tag="r1")
        self.assertEqual(r2.returncode, 2)
        self.assertIn("OUTPUT_EXISTS", r2.stdout)
        self.assertEqual(out.read_bytes(), before_out)
        self.assertEqual(rec.read_bytes(), before_rec)
        # and the successor still holds exactly 2 claims: nothing double-added
        self.assertEqual(li.read_parent(str(out))["claim_count"], 2)

    def test_applying_to_a_parent_that_already_has_the_claim_is_refused(self):
        prop, dec = self.pipeline(tag="ap")
        r, out, _rec = self.apply_cli(prop, dec, tag="ap")
        self.assertEqual(r.returncode, 0, r.stdout)
        # now use the successor as the parent: it already contains the claim
        succ_sha = _sha256(out)
        cp = self.d / "c_ap2.json"
        cp.write_text(json.dumps(self.case_claim("pass").to_dict(), indent=2))
        prop2 = self.d / "p_ap2.json"
        r2 = self.cli("add-claim", "--pdf", str(out), "--expect-parent-sha256", succ_sha,
                      "--claim", str(cp), "--proposer-key-file", str(self.key_path),
                      "--out", str(prop2))
        self.assertEqual(r2.returncode, 0, r2.stdout)
        dec2 = self.d / "d_ap2.json"
        r3 = self.cli("evaluate", "--pdf", str(out), "--proposal", str(prop2),
                      "--policy", str(self.policy_path), "--decider-key-file",
                      str(self.decider_key), "--out", str(dec2))
        self.assertEqual(r3.returncode, 0, r3.stdout)
        r4, out2, _ = self.apply_cli(prop2, dec2, tag="ap2", parent=out)
        self.assertEqual(r4.returncode, 2, r4.stdout)
        self.assertIn("CLAIM_ALREADY_PRESENT", r4.stdout)
        self.assertFalse(out2.exists())

    def test_leftover_staging_files_are_refused_not_reused(self):
        prop, dec = self.pipeline(tag="st")
        out = self.d / "s_st.pdf"
        stale = pathlib_Path(str(out) + li.STAGING_SUFFIX)
        stale.write_bytes(b"leftover from an interrupted run")
        r, _o, _rec = self.apply_cli(prop, dec, tag="st")
        self.assertEqual(r.returncode, 2, r.stdout)
        self.assertIn("STAGING_EXISTS", r.stdout)
        self.assertEqual(stale.read_bytes(), b"leftover from an interrupted run")
        self.assertFalse(out.exists())

    def test_leftover_receipt_staging_is_named_and_leaves_nothing_behind(self):
        """Here the staging pre-check is load-bearing: without it the exclusive
        create for the receipt raises inside the write path, giving a less
        precise name AND leaving a staged successor behind."""
        prop, dec = self.pipeline(tag="rs2")
        rec = self.d / "r_rs2.json"
        stale = pathlib_Path(str(rec) + li.STAGING_SUFFIX)
        stale.write_bytes(b"leftover receipt staging")
        out = self.d / "s_rs2.pdf"
        r = self.cli("apply", "--pdf", str(self.parent), "--proposal", str(prop),
                     "--decision", str(dec), "--policy", str(self.policy_path),
                     "--issuer-key-file", str(self.issuer_key),
                     "--out", str(out), "--receipt", str(rec))
        self.assertEqual(r.returncode, 2, r.stdout)
        self.assertIn("STAGING_EXISTS", r.stdout)
        self.assertFalse(out.exists())
        self.assertFalse(pathlib_Path(str(out) + li.STAGING_SUFFIX).exists(),
                         "a staged successor was left behind")
        self.assertEqual(stale.read_bytes(), b"leftover receipt staging")

    def test_write_failure_publishes_nothing(self):
        prop, dec = self.pipeline(tag="wf")
        out = self.d / "nodir" / "s.pdf"          # parent directory does not exist
        rec = self.d / "r_wf.json"
        r = self.cli("apply", "--pdf", str(self.parent), "--proposal", str(prop),
                     "--decision", str(dec), "--policy", str(self.policy_path),
                     "--issuer-key-file", str(self.issuer_key),
                     "--out", str(out), "--receipt", str(rec))
        self.assertEqual(r.returncode, 2, r.stdout)
        self.assertIn("OUTPUT_UNWRITABLE", r.stdout)
        self.assertFalse(rec.exists())
        self.assertFalse(out.exists())

    def test_a_successor_without_a_receipt_is_not_a_transition(self):
        """The crash point after publishing the successor: INCOMPLETE."""
        prop, dec = self.pipeline(tag="inc")
        r, out, rec = self.apply_cli(prop, dec, tag="inc")
        self.assertEqual(r.returncode, 0, r.stdout)
        rec.unlink()                               # as if interrupted before step 6
        res = li.explain_transition(str(self.parent), str(out), str(prop),
                                    str(dec), str(rec), self.i_pk)
        self.assertFalse(res["ok"])
        self.assertEqual(res["refusal"], "RECEIPT_UNREADABLE")

    def test_publish_order_leaves_incomplete_not_a_bare_receipt(self):
        """The receipt is the completion marker and is published LAST. Injected
        failure on the second rename must leave the successor published and NO
        receipt -- the INCOMPLETE state -- never a receipt naming a file that is
        not there."""
        prop, dec = self.pipeline(tag="ord")
        out = self.d / "s_ord.pdf"
        rec = self.d / "r_ord.json"
        real_rename = os.rename
        calls = {"n": 0}

        def failing_rename(src, dst):
            calls["n"] += 1
            if calls["n"] == 2:
                raise OSError("injected failure publishing the receipt")
            return real_rename(src, dst)

        with mock.patch.object(li.os, "rename", side_effect=failing_rename):
            res = li.apply_transition(str(self.parent), str(prop), str(dec),
                                      str(self.policy_path), str(self.issuer_key),
                                      str(out), str(rec))
        self.assertFalse(res["ok"])
        self.assertEqual(res["refusal"], "PUBLISH_FAILED")
        self.assertTrue(out.exists(), "successor should already be published")
        self.assertFalse(rec.exists(), "the receipt must not be published")
        # and that state is not a transition
        chk = li.explain_transition(str(self.parent), str(out), str(prop), str(dec),
                                    str(rec), self.i_pk)
        self.assertFalse(chk["ok"])
        self.assertEqual(chk["refusal"], "RECEIPT_UNREADABLE")

    def test_a_successor_adding_two_claims_is_refused(self):
        prop, dec = self.pipeline(tag="two")
        r, out, rec = self.apply_cli(prop, dec, tag="two")
        self.assertEqual(r.returncode, 0, r.stdout)
        parent_claims = li.read_parent(str(self.parent))["manifest"]["claims"]
        added = json.loads(prop.read_text())["body"]["claim"]
        extra = self.grounded_claim("🤍 (🤍 🤍)", "a" * 64, budget=10).to_dict()
        forged = self.d / "two.pdf"
        forged.write_bytes(li.render_successor_pdf(
            list(parent_claims) + [added, extra], ["forged: two additions"]))
        body = li.receipt_body(self.parent_sha, _sha256(forged),
                               json.loads(prop.read_text())["proposal_id"],
                               json.loads(rec.read_text())["body"]["decision_id"],
                               json.loads(rec.read_text())["body"]["policy_sha256"],
                               added["claim_id"], self.i_pk)
        rid = li.compute_receipt_id(body)
        doc = {"profile": li.TRANSITION_PROFILE, "body": body, "receipt_id": rid,
               "receipt_signature_hex": crypto.sign_hex(self.i_sk, li.receipt_message(rid))}
        rec2 = self.d / "two_rec.json"
        rec2.write_text(json.dumps(doc))
        res = li.explain_transition(str(self.parent), str(forged), str(prop),
                                    str(dec), str(rec2), self.i_pk)
        self.assertFalse(res["ok"])
        self.assertEqual(res["refusal"], "CLAIM_COUNT_UNEXPECTED")

    def test_two_proposals_against_one_parent_give_two_children(self):
        """Not a conflict: no election of a newest state, neither invalidates
        the other."""
        p1, d1 = self.pipeline(tag="f1")
        other = self.grounded_claim("🤍 (🤍 🤍)",
                                    glyph.evaluate(glyph.parse("🤍 (🤍 🤍)"),
                                                   max_atp=100).hash, budget=100)
        p2, d2 = self.pipeline(claim=other, tag="f2")
        r1, o1, rc1 = self.apply_cli(p1, d1, tag="f1")
        r2, o2, rc2 = self.apply_cli(p2, d2, tag="f2")
        self.assertEqual(r1.returncode, 0, r1.stdout)
        self.assertEqual(r2.returncode, 0, r2.stdout)
        self.assertNotEqual(_sha256(o1), _sha256(o2))
        for prop, dec, o, rc in ((p1, d1, o1, rc1), (p2, d2, o2, rc2)):
            res = self.explain_cli(prop, dec, o, rc, self.i_pk)
            self.assertEqual(res.returncode, 0, res.stdout)
        self.assertEqual(self.parent.read_bytes(), self.parent.read_bytes())


class ApplyReEvaluatesTest(LI3Base):
    """A saved admitted=true authorises nothing by itself."""

    def test_a_policy_changed_since_the_decision_is_caught(self):
        # NOTE: this is stopped by the decision's POLICY PIN, before any
        # re-evaluation. It is kept as a control for the pin, not as evidence
        # that apply re-evaluates -- see the two tests below for that.
        prop, dec = self.pipeline(tag="pc")
        deny = self.write_policy("deny_apply.json", tc_trusted_author_pks=[])
        r, out, rec = self.apply_cli(prop, dec, tag="pc", policy=deny)
        self.assertEqual(r.returncode, 2, r.stdout)
        self.assertIn("DECISION_POLICY_MISMATCH", r.stdout)
        self.assertFalse(out.exists())
        self.assertFalse(rec.exists())

    def test_a_non_admitting_decision_cannot_produce_a_successor(self):
        """Reaches the re-evaluation: the policy pin matches, the decision is
        genuine, and it simply does not admit."""
        prop, dec = self.pipeline(claim=self.case_claim("fail"), tag="na")
        body = json.loads(dec.read_text())["body"]
        self.assertFalse(body["admission"]["admitted"])
        r, out, rec = self.apply_cli(prop, dec, tag="na")
        self.assertEqual(r.returncode, 2, r.stdout)
        self.assertIn("NOT_ADMITTED_NOW", r.stdout)
        self.assertFalse(out.exists())
        self.assertFalse(rec.exists())

    def test_the_live_evaluation_governs_not_the_stored_decision(self):
        """The decision honestly says admitted; the evaluation run AT APPLY TIME
        says otherwise. The live result must win -- a saved admitted=true
        authorises nothing by itself."""
        prop, dec = self.pipeline(tag="live")
        self.assertTrue(json.loads(dec.read_text())["body"]["admission"]["admitted"])
        out = self.d / "s_live.pdf"
        rec = self.d / "r_live.json"
        with mock.patch.object(li, "evaluate_evidence", return_value={
                "status": wk.VerificationStatus.UNVERIFIED.value, "grade": "GROUNDED",
                "reason": "injected: the live run does not settle",
                "atp_spent": None, "atp_spent_measured": False}):
            res = li.apply_transition(str(self.parent), str(prop), str(dec),
                                      str(self.policy_path), str(self.issuer_key),
                                      str(out), str(rec))
        self.assertFalse(res["ok"])
        self.assertEqual(res["refusal"], "NOT_ADMITTED_NOW")
        self.assertFalse(out.exists())
        self.assertFalse(rec.exists())

    def test_a_stale_parent_is_refused(self):
        prop, dec = self.pipeline(tag="sp")
        r, out, rec = self.apply_cli(prop, dec, tag="sp", parent=self.second_parent())
        self.assertEqual(r.returncode, 2, r.stdout)
        self.assertIn("PROPOSAL_PARENT_MISMATCH", r.stdout)
        self.assertFalse(out.exists())

    def test_a_substituted_decision_does_not_carry_authority(self):
        """Saved-artifact substitution followed by the next operation."""
        prop, dec = self.pipeline(tag="sub")
        other_prop, other_dec = self.pipeline(
            claim=self.grounded_claim("🤍 (🤍 🤍)",
                                      glyph.evaluate(glyph.parse("🤍 (🤍 🤍)"),
                                                     max_atp=100).hash, budget=100),
            tag="sub2")
        r, out, rec = self.apply_cli(prop, other_dec, tag="sub")
        self.assertEqual(r.returncode, 2, r.stdout)
        self.assertIn("DECISION_PROPOSAL_MISMATCH", r.stdout)
        self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
