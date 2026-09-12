#!/usr/bin/env python3
"""
Regression: a budget-suspended grounded computation is UNVERIFIED, never PASS.

Security scan of e549de3, `improper-verification.grounded-suspension`
(warrant_kernel.py). The Grade-G branch replayed `glyph.evaluate(term,
max_atp=budget)` and returned PASS whenever `res.hash == expected_hash` --
without checking that the reduction actually SETTLED. `glyph.evaluate`
returns status SUSPENDED on budget exhaustion, so an attacker could submit
a non-terminating term and pin `expected_hash` to its suspended
intermediate, collecting a Grade-G PASS for a computation that never
completed. The cryptographic record authenticates the operands; it does not
establish termination.

Fix: the reduction must settle within budget. Not settled -> UNVERIFIED
(a refusal, not a verdict). Settled + hash match -> PASS; settled + hash
mismatch -> FAIL. The two positive controls are kept deliberately, so a
degenerate "refuse everything" change cannot pass this file.

Sections:
  A  a non-terminating (suspended) computation is refused, not passed
  B  the controls: completed+match -> PASS, completed+mismatch -> FAIL
"""
from __future__ import annotations

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

import glyph
import warrant_kernel as WK
from glyph import parse, evaluate
from warrant_kernel import (EdgeClaim, GroundedWitness, Polarity, TrustConfig,
                            WarrantVerifier, VerificationStatus)
from crypto import generate_keypair

if os.path.dirname(os.path.abspath(WK.__file__)) != _HERE:
    raise ImportError(f"warrant_kernel resolved to {WK.__file__}, outside {_HERE}")

# (S I I)(S I I): a closed term with no normal form -- it loops forever.
NONTERMINATING = "🌿 🤍 🤍 (🌿 🤍 🤍)"
SETTLING = "🤍 (🖤 🤍)"          # settles to a normal form quickly


class _Verifier(unittest.TestCase):
    def setUp(self):
        self.sk, self.pk = generate_keypair()
        # trust the author, so the ONLY thing under test is the grounded verdict
        self.verifier = WarrantVerifier(TrustConfig(trusted_author_pks={self.pk}))

    def grounded_claim(self, term_expr, expected_hash, atp_budget):
        w = GroundedWitness(term_expr=term_expr, expected_hash=expected_hash, atp_budget=atp_budget)
        return EdgeClaim.create_and_sign("p", "eval", "o", expected_hash,
                                         Polarity.AFFIRM, w, self.sk, self.pk)

    def audit(self, claim):
        return self.verifier.audit_claim(claim)


class SuspensionTest(_Verifier):
    """Section A."""

    def test_A1_a_suspended_computation_is_unverified_not_passed(self):
        budget = 500
        suspended = evaluate(parse(NONTERMINATING), max_atp=budget)
        self.assertFalse(suspended.is_settled(), "fixture must actually suspend")
        v = self.audit(self.grounded_claim(NONTERMINATING, suspended.hash, budget))
        self.assertEqual(v.status, VerificationStatus.UNVERIFIED,
                         "a non-settled grounded computation was not refused")
        self.assertNotEqual(v.status, VerificationStatus.PASS)
        self.assertIn("settle", v.reason.lower())

    def test_A2_a_larger_budget_that_still_does_not_settle_is_unverified(self):
        """Raising the budget does not turn non-termination into a proof."""
        budget = 5000
        suspended = evaluate(parse(NONTERMINATING), max_atp=budget)
        self.assertFalse(suspended.is_settled())
        v = self.audit(self.grounded_claim(NONTERMINATING, suspended.hash, budget))
        self.assertEqual(v.status, VerificationStatus.UNVERIFIED)


class ControlTest(_Verifier):
    """Section B: the settled cases must still work, or a blanket refusal would pass."""

    def test_B1_completed_matching_reduction_passes(self):
        r = evaluate(parse(SETTLING))
        self.assertTrue(r.is_settled())
        v = self.audit(self.grounded_claim(SETTLING, r.hash, 10000))
        self.assertEqual(v.status, VerificationStatus.PASS, v.reason)

    def test_B2_completed_mismatching_reduction_fails(self):
        r = evaluate(parse(SETTLING))
        self.assertTrue(r.is_settled())
        v = self.audit(self.grounded_claim(SETTLING, "0" * 64, 10000))
        self.assertEqual(v.status, VerificationStatus.FAIL, v.reason)

    def test_B3_the_three_outcomes_are_distinct(self):
        """Pins that the fix did not collapse the branch to one verdict."""
        susp = evaluate(parse(NONTERMINATING), max_atp=500)
        settled = evaluate(parse(SETTLING))
        outcomes = {
            self.audit(self.grounded_claim(NONTERMINATING, susp.hash, 500)).status,
            self.audit(self.grounded_claim(SETTLING, settled.hash, 10000)).status,
            self.audit(self.grounded_claim(SETTLING, "0" * 64, 10000)).status,
        }
        self.assertEqual(outcomes,
                         {VerificationStatus.UNVERIFIED, VerificationStatus.PASS, VerificationStatus.FAIL})


if __name__ == "__main__":
    unittest.main()
