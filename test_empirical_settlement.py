#!/usr/bin/env python3
"""DOC-F1: an EMPIRICAL replay that does not settle is not evidence.

Recorded from the floor-document review at 8fed8bb. `WarrantVerifier.audit_claim`
compared the term bytes of both applications on each fixture without checking
settlement, so two SUSPENDED sides produced PASS ("Equivalence verified") when
they happened to stop on the same intermediate term, and FAIL when they did
not. GROUNDED and COUNTEREXAMPLE already treat an unsettled replay as
UNVERIFIED; this holds EMPIRICAL to the same rule.

The rule, and why each case exists:
  - a SETTLED mismatch on ANY fixture is a checked negative -> FAIL, and an
    unsettled fixture elsewhere must not mask it (order-independent);
  - otherwise, ANY unsettled side on ANY fixture -> UNVERIFIED: a partial run
    is neither agreement nor refutation;
  - only when every fixture settles on both sides and agrees -> PASS.

Keys are ephemeral per test and never printed.
"""
from __future__ import annotations

import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path[:1]:
    sys.path.insert(0, _HERE)

import crypto
import glyph
from warrant_kernel import (EdgeClaim, EmpiricalWitness, Polarity, TrustConfig,
                            VerificationStatus, WarrantVerifier)

BUDGET = 50
I, K, S = "🤍", "🖤", "🌿"
SII = f"{S} {I} {I}"                      # ω
OMEGA = f"{SII} ({SII})"                  # ω ω: never settles


class EmpiricalSettlementTest(unittest.TestCase):
    def setUp(self):
        self.sk, self.pk = crypto.generate_keypair()
        self.verifier = WarrantVerifier(
            TrustConfig(trusted_author_pks={self.pk}, max_atp_budget=BUDGET))

    def claim(self, omega, tau, fixtures):
        w = EmpiricalWitness(fixtures=list(fixtures), fixtures_fingerprint="",
                             delta_atp=0, delta_size=0)
        w.fixtures_fingerprint = w.compute_fixtures_fingerprint()
        return EdgeClaim.create_and_sign("a" * 64, tau, omega, "b" * 64,
                                         Polarity.AFFIRM, w, self.sk, self.pk)

    def audit(self, omega, tau, fixtures):
        return self.verifier.audit_claim(self.claim(omega, tau, fixtures))

    def replay(self, omega, tau, fixture):
        f = glyph.parse(fixture)
        return (glyph.evaluate(glyph.App(glyph.parse(omega), f), max_atp=BUDGET),
                glyph.evaluate(glyph.App(glyph.parse(tau), f), max_atp=BUDGET))

    # ---- the arranged conditions are what the names say (not circular) ---- #
    def test_fixtures_really_produce_the_named_settlement_states(self):
        p, s = self.replay(f"{I} ({SII})", f"{K} ({SII}) {I}", SII)
        self.assertEqual((p.status.value, s.status.value), ("SUSPENDED", "SUSPENDED"))
        self.assertEqual(glyph.canonical_bytes(p.term), glyph.canonical_bytes(s.term))
        p, s = self.replay(SII, f"{I} ({SII})", SII)
        self.assertEqual((p.status.value, s.status.value), ("SUSPENDED", "SUSPENDED"))
        self.assertNotEqual(glyph.canonical_bytes(p.term), glyph.canonical_bytes(s.term))
        p, s = self.replay(I, SII, SII)
        self.assertEqual((p.status.value, s.status.value), ("SETTLED", "SUSPENDED"))
        p, s = self.replay(I, f"{K} {I}", K)
        self.assertEqual((p.status.value, s.status.value), ("SETTLED", "SETTLED"))
        self.assertNotEqual(glyph.canonical_bytes(p.term), glyph.canonical_bytes(s.term))

    # ---- the reported defect ---------------------------------------------- #
    def test_both_suspended_on_the_same_term_is_not_a_pass(self):
        v = self.audit(f"{I} ({SII})", f"{K} ({SII}) {I}", [SII])
        self.assertEqual(v.status, VerificationStatus.UNVERIFIED, v.reason)

    def test_both_suspended_on_different_terms_is_not_a_fail(self):
        v = self.audit(SII, f"{I} ({SII})", [SII])
        self.assertEqual(v.status, VerificationStatus.UNVERIFIED, v.reason)

    # ---- mixed: one side settles, the other does not ---------------------- #
    def test_parent_settles_successor_suspends(self):
        v = self.audit(I, SII, [SII])
        self.assertEqual(v.status, VerificationStatus.UNVERIFIED, v.reason)

    def test_parent_suspends_successor_settles(self):
        v = self.audit(SII, I, [SII])
        self.assertEqual(v.status, VerificationStatus.UNVERIFIED, v.reason)

    # ---- completed controls ----------------------------------------------- #
    def test_settled_agreement_on_every_fixture_passes(self):
        v = self.audit(I, f"{S} {K} {K}", [I, K, f"{I} {I}"])
        self.assertEqual(v.status, VerificationStatus.PASS, v.reason)

    def test_settled_mismatch_fails(self):
        v = self.audit(I, f"{K} {I}", [K])
        self.assertEqual(v.status, VerificationStatus.FAIL, v.reason)

    # ---- several fixtures: the verdict must not depend on their order ----- #
    def test_an_unsettled_fixture_does_not_mask_a_settled_mismatch(self):
        # On OMEGA the parent (I Ω) never settles while (K I) Ω settles; on K
        # both settle and disagree. The checked negative wins in either order.
        for fixtures in ([OMEGA, K], [K, OMEGA]):
            with self.subTest(order=fixtures):
                v = self.audit(I, f"{K} {I}", fixtures)
                self.assertEqual(v.status, VerificationStatus.FAIL, v.reason)

    def test_agreement_on_some_fixtures_plus_an_unsettled_one_is_not_a_pass(self):
        for fixtures in ([I, OMEGA], [OMEGA, I]):
            with self.subTest(order=fixtures):
                v = self.audit(I, f"{S} {K} {K}", fixtures)
                self.assertEqual(v.status, VerificationStatus.UNVERIFIED, v.reason)

    # ---- the refusal says what it is -------------------------------------- #
    def test_unverified_names_the_unsettled_fixture_and_is_not_a_verdict(self):
        v = self.audit(I, SII, [SII])
        self.assertEqual(v.status, VerificationStatus.UNVERIFIED)
        self.assertIn("not a verdict", v.reason)
        self.assertEqual(v.details.get("unsettled_fixtures"), [SII])


if __name__ == "__main__":
    unittest.main()
