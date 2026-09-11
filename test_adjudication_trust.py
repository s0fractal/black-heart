#!/usr/bin/env python3
"""
Regression: a document pair that confirms only itself never earns a trusted settlement.

Measured at 6570ec5 through the real entry points. The ordinary CLI was already
partly guarded: without a pin it refused, and a foreign author, a foreign
oracle or a swapped party were refused. What still granted trust:

  embedded runner  `python3 agreement.pdf --adjudicate-with oracle.pdf`
      on a pair made entirely by a stranger       GREEN, AUTHENTICATED_PINNED
      (it pinned the author that the document itself names; the historical
       examples/bilateral_agreement.pdf does the same)
  `cli.py adjudicate --allow-untrusted-issuer` on that pair
                                                   "[✓] VERIFIED & SETTLED", exit 0
  `adjudicate_bilateral()` with no pin             status SETTLED_BREACH
  a trusted oracle signs uptime NaN or 250         SETTLED_COMPLIANT, full fee
  an author-pinned agreement with zero parties     settled as bilateral
  the author pin spelled in upper case             refused as another author

Sections:
  A  the four controls: honest pinned pair, foreign author, party substitution, no pin
  B  the residual paths: runner, historical runner, outcome domain, signers,
     key spelling, the removed self-pinning keywords
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
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

import cross_proof as X
from cross_proof import AdjudicationTrust, adjudicate_bilateral
from crypto import generate_keypair, public_key_from_secret, sign_bytes

if os.path.dirname(os.path.abspath(X.__file__)) != _HERE:
    raise ImportError(f"cross_proof resolved to {X.__file__}, outside {_HERE}")

CLI = os.path.join(_HERE, "cli.py")
ENV = dict(os.environ, PYTHONPATH=_HERE, PYTHONDONTWRITEBYTECODE="1")


def edit_manifest(path, prefix, change):
    raw = open(path, "rb").read()
    pre = prefix.encode("utf-8")
    start = raw.index(pre) + len(pre)
    end = raw.index(b"\n", start)
    manifest = json.loads(raw[start:end])
    change(manifest)
    with open(path, "wb") as fh:
        fh.write(raw[:start] + json.dumps(manifest, ensure_ascii=False).encode("utf-8") + raw[end:])


def terms_bytes(m):
    terms = {
        "base_fee_usd": m["base_fee_usd"],
        "parties": [{"name": p["name"], "public_key_hex": p["public_key_hex"], "role": p["role"]}
                    for p in m["parties"]],
        "penalty_rate_usd": m["penalty_rate_usd"],
        "target_uptime_percent": m["target_uptime_percent"],
        "title": m["title"],
        "trusted_oracle_pk_hex": m["trusted_oracle_pk_hex"],
    }
    return json.dumps(terms, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


class _Pairs(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.d = self._tmp.name
        self.author_sk, self.author_pk = generate_keypair()   # the author this caller trusts
        self.oracle_sk, _ = generate_keypair()

    def pair(self, tag="honest", author_sk=None, oracle_sk=None, parties=("CLIENT", "PROVIDER"),
             party_keys=None, target=99.5, fee=10000, rate=500):
        author_sk = author_sk or self.author_sk
        oracle_sk = oracle_sk or self.oracle_sk
        oracle = X.TelemetryOraclePolyglot(f"Oracle {tag}")
        oracle.add_incident("I", "2026-09-01", "outage", 300)
        op = os.path.join(self.d, f"oracle_{tag}.pdf")
        oracle.compile(op, oracle_sk)
        oracle_pk = public_key_from_secret(bytes.fromhex(oracle_sk)).hex()
        ag = X.BilateralAgreementPolyglot(f"SLA {tag}", oracle_pk, target_uptime_percent=target,
                                          base_fee_usd=fee, penalty_rate_usd=rate,
                                          agreement_secret_key_hex=author_sk)
        for i, role in enumerate(parties):
            sk, pk = party_keys[i] if party_keys else generate_keypair()
            ag.add_party(role, f"{role.title()} {tag}", pk, secret_key_hex=sk)
        ap = os.path.join(self.d, f"agreement_{tag}.pdf")
        ag.compile(ap)
        return ap, op

    def forged(self):
        """A complete, self-consistent pair made by a stranger."""
        stranger_sk, _ = generate_keypair()
        stranger_oracle_sk, _ = generate_keypair()
        return self.pair("forged", author_sk=stranger_sk, oracle_sk=stranger_oracle_sk)

    def pinned(self):
        return AdjudicationTrust(expected_author_pk_hex=self.author_pk)

    def resign_oracle(self, op, **payload):
        def change(m):
            m["payload"].update(payload)
            pb = json.dumps(m["payload"], sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
            sig = sign_bytes(bytes.fromhex(self.oracle_sk), pb)
            m["signature_hex"] = sig.hex()
            m["oracle_anchor"] = hashlib.sha256(pb + sig).hexdigest()
        edit_manifest(op, X.ORACLE_MANIFEST_PREFIX, change)

    def cli(self, *args):
        return subprocess.run([sys.executable, "-B", CLI, "adjudicate", *args], capture_output=True,
                              text=True, env=ENV, cwd=_HERE, timeout=300)

    def runner(self, ap, op, *args):
        return subprocess.run([sys.executable, ap, "--adjudicate-with", op, *args], capture_output=True,
                              text=True, env=ENV, timeout=300)


class ControlTest(_Pairs):
    """Section A: the four controls named in the plan."""

    def test_A1_an_honest_pinned_pair_settles_with_four_separate_checks(self):
        ap, op = self.pair()
        r = adjudicate_bilateral(ap, op, trust=self.pinned())
        self.assertEqual(r.status, "SETTLED_BREACH")
        self.assertEqual((r.outcome, r.net_service_due_usd, r.trust_status), ("BREACH", 9500, "AUTHENTICATED_PINNED"))
        self.assertEqual(set(r.checks), {"integrity", "signatures", "authorization", "outcome"})
        self.assertTrue(all(v.startswith("PASS") for v in r.checks.values()), r.checks)
        self.assertEqual(r.untrusted_reasons, [])
        digest = hashlib.sha256(open(ap, "rb").read()).hexdigest()
        by_hash = adjudicate_bilateral(ap, op, trust=AdjudicationTrust(expected_agreement_sha256=digest))
        self.assertEqual(by_hash.status, "SETTLED_BREACH")
        self.assertIn("pinned by caller", by_hash.checks["integrity"])
        c = self.cli(ap, op, "--pinned-author-pk", self.author_pk)
        self.assertEqual(c.returncode, 0, c.stdout + c.stderr)
        self.assertIn("VERIFIED & SETTLED: SETTLED_BREACH", c.stdout)
        run = self.runner(ap, op, "--pinned-author-pk", self.author_pk)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertIn("GREEN", run.stdout)

    def test_A2_a_foreign_author_is_refused(self):
        ap, op = self.pair()
        digest = hashlib.sha256(open(ap, "rb").read()).hexdigest()
        fap, fop = self.forged()
        with self.assertRaisesRegex(PermissionError, "author PK mismatch"):
            adjudicate_bilateral(fap, fop, trust=self.pinned())
        with self.assertRaisesRegex(PermissionError, "anchor mismatch"):
            adjudicate_bilateral(fap, fop, trust=AdjudicationTrust(expected_agreement_sha256=digest))
        self.assertEqual(self.cli(fap, fop, "--pinned-author-pk", self.author_pk).returncode, 1)
        run = self.runner(fap, fop, "--pinned-author-pk", self.author_pk)
        self.assertEqual(run.returncode, 1, run.stdout)
        self.assertIn("REFUTED", run.stdout)

    def test_A3_a_substituted_party_is_refused(self):
        ap, op = self.pair()
        sub_sk, sub_pk = generate_keypair()

        def swap(m):
            m["parties"][0]["public_key_hex"] = sub_pk
            m["parties"][0]["signature_hex"] = sign_bytes(bytes.fromhex(sub_sk), terms_bytes(m)).hex()

        edit_manifest(ap, X.AGREEMENT_MANIFEST_PREFIX, swap)
        with self.assertRaisesRegex(PermissionError, "signature invalid"):
            adjudicate_bilateral(ap, op, trust=self.pinned())
        self.assertEqual(self.cli(ap, op, "--pinned-author-pk", self.author_pk).returncode, 1)

    def test_A4_no_pin_is_never_a_settlement(self):
        fap, fop = self.forged()
        r = adjudicate_bilateral(fap, fop)
        self.assertEqual(r.status, "EVALUATION_ONLY")
        self.assertEqual(r.outcome, "BREACH")
        self.assertTrue(any("no caller-supplied trust pin" in x for x in r.untrusted_reasons))
        self.assertTrue(r.checks["authorization"].startswith("NOT_ESTABLISHED"))
        refused = self.cli(fap, fop)
        self.assertEqual(refused.returncode, 1)
        self.assertIn("REJECTED", refused.stdout)
        evaluated = self.cli(fap, fop, "--allow-untrusted-issuer")
        self.assertEqual(evaluated.returncode, 2, evaluated.stdout + evaluated.stderr)
        self.assertIn("EVALUATION ONLY — NOT A SETTLEMENT", evaluated.stdout)
        self.assertNotIn("VERIFIED & SETTLED", evaluated.stdout)


class ResidualTest(_Pairs):
    """Section B: the paths that still granted trust at 6570ec5."""

    def test_B1_the_runner_takes_trust_from_the_command_line_only(self):
        fap, fop = self.forged()
        run = self.runner(fap, fop)
        self.assertEqual(run.returncode, 2, run.stdout + run.stderr)
        self.assertIn("EVALUATION ONLY", run.stdout)
        self.assertNotIn("GREEN", run.stdout)
        self.assertNotIn("AUTHENTICATED_PINNED", run.stdout)

    def test_B2_the_historical_example_no_longer_vouches_for_itself(self):
        """Its old runner passes the removed keyword with its own key; it now fails closed.
        The file is not rewritten."""
        ha = os.path.join(_HERE, "examples", "bilateral_agreement.pdf")
        ho = os.path.join(_HERE, "examples", "provider_telemetry_oracle.pdf")
        if not (os.path.exists(ha) and os.path.exists(ho)):
            self.skipTest("historical example not present")
        before = (open(ha, "rb").read(), open(ho, "rb").read())
        run = subprocess.run([sys.executable, ha, "--adjudicate-with", ho], capture_output=True,
                             text=True, env=ENV, timeout=300)
        self.assertNotEqual(run.returncode, 0, run.stdout)
        self.assertNotIn("GREEN", run.stdout)
        self.assertEqual((open(ha, "rb").read(), open(ho, "rb").read()), before)

    def test_B3_outcome_inputs_out_of_domain_are_refused(self):
        for i, value in enumerate((float("nan"), 250.0, -1.0, "99", True)):
            with self.subTest(uptime=value):
                ap, op = self.pair(f"u{i}")
                self.resign_oracle(op, measured_uptime_percent=value)
                with self.assertRaisesRegex(ValueError, "out of domain"):
                    adjudicate_bilateral(ap, op, trust=self.pinned())
        for tag, kwargs in (("target", {"target": 150.0}), ("fee", {"fee": -1}), ("rate", {"rate": 1.5})):
            with self.subTest(agreement=tag):
                ap, op = self.pair(tag, **kwargs)
                with self.assertRaisesRegex(ValueError, "out of domain"):
                    adjudicate_bilateral(ap, op, trust=self.pinned())
        ap, op = self.pair("cli-nan")
        self.resign_oracle(op, measured_uptime_percent=float("nan"))
        c = self.cli(ap, op, "--pinned-author-pk", self.author_pk)
        self.assertEqual(c.returncode, 1, c.stdout)
        self.assertNotIn("SETTLED", c.stdout)

    def test_B4_a_settlement_needs_two_distinct_signers(self):
        ap, op = self.pair("none", parties=())
        r = adjudicate_bilateral(ap, op, trust=self.pinned())
        self.assertEqual(r.status, "EVALUATION_ONLY")
        self.assertTrue(any("1 distinct signer" in x for x in r.untrusted_reasons))
        self.assertEqual(self.cli(ap, op, "--pinned-author-pk", self.author_pk).returncode, 2)
        ap, op = self.pair("self", parties=("CLIENT",), party_keys=[(self.author_sk, self.author_pk)])
        self.assertEqual(adjudicate_bilateral(ap, op, trust=self.pinned()).status, "EVALUATION_ONLY")
        ap, op = self.pair("one", parties=("CLIENT",))
        self.assertEqual(adjudicate_bilateral(ap, op, trust=self.pinned()).status, "SETTLED_BREACH")

    def test_B5_a_key_is_the_same_key_in_any_spelling_and_a_bad_pin_is_refused(self):
        ap, op = self.pair()
        upper = AdjudicationTrust(expected_author_pk_hex=self.author_pk.upper())
        self.assertEqual(adjudicate_bilateral(ap, op, trust=upper).status, "SETTLED_BREACH")
        self.assertEqual(self.cli(ap, op, "--pinned-author-pk", self.author_pk.upper()).returncode, 0)
        for bad in ({"expected_author_pk_hex": "zz"}, {"expected_author_pk_hex": ""},
                    {"expected_agreement_sha256": "abc"}):
            with self.subTest(pin=bad):
                with self.assertRaises(ValueError):
                    AdjudicationTrust(**bad)
        c = self.cli(ap, op, "--pinned-author-pk", "zz")
        self.assertEqual(c.returncode, 1)
        self.assertIn("invalid pin", c.stdout)

    def test_B6_the_self_pinning_keywords_are_gone(self):
        ap, op = self.pair()
        with self.assertRaises(TypeError):
            adjudicate_bilateral(ap, op, expected_author_pk_hex=self.author_pk)
        with self.assertRaises(TypeError):
            adjudicate_bilateral(ap, op, expected_agreement_hash="0" * 64)
        with self.assertRaises(TypeError):
            adjudicate_bilateral(ap, op, trust={"expected_author_pk_hex": self.author_pk})

    def test_B7_only_trust_changes_between_an_evaluation_and_a_settlement(self):
        ap, op = self.pair()
        evaluated = adjudicate_bilateral(ap, op)
        settled = adjudicate_bilateral(ap, op, trust=self.pinned())
        same = lambda r: (r.outcome, r.penalty_due_usd, r.net_service_due_usd, r.agreement_anchor, r.oracle_anchor)
        self.assertEqual(same(evaluated), same(settled))
        self.assertEqual((evaluated.status, settled.status), ("EVALUATION_ONLY", "SETTLED_BREACH"))


if __name__ == "__main__":
    unittest.main()
