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
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
