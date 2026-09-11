#!/usr/bin/env python3
"""
Regression: a Grade C verdict is earned by the divergence the witness describes.

`audit_claim`'s COUNTEREXAMPLE branch replayed the input through parent and
successor, compared the two outputs to each other, and returned PASS when they
differed. Three things followed from that, all measured on the base commit:

  * `except Exception: return PASS` — a malformed `input_expr` such as `((`
    produced "Refutation confirmed: execution divergence / exception", so a
    syntax error in the witness became a confirmed refutation;
  * `expected_normal_form` and `actual_divergence` were never read, so a witness
    could declare TOTAL NONSENSE and still pass;
  * neither reduction had to terminate. With both sides suspended at the ATP
    ceiling, two arbitrary intermediate states differ, and that was reported as
    "Divergence independently reproduced".

`atp_to_diverge` was likewise never read: -999 passed.

What the sections pin:

  A  a real, terminating, correctly described divergence passes, and each defect
     above is refused with its own status and reason, including the one-sided
     cases: one unfinished side, and a budget that covers only the cheaper side
  B  the operands are checked in their stated roles, the claim's own endpoints
     must denote terms, and polarity must be REFUTE
  C  what is NOT a refutation: a coincidence, a crash, an unfinished reduction
  E  an endpoint must be a term in its own right: the replay joins ASTs instead
     of composing source text, in this branch and in the empirical twin
  D  the reason names the disagreeing side, and the three statuses stay distinct
     — FAIL means the evidence contradicts the claim, UNVERIFIED means the check
     never reached a verdict, and neither is PASS

The predicate, in full: the claim is refuted when parent and successor both
reduce to normal form inside the configured budget, those normal forms differ,
they are the two the witness named in the roles it named them, and the declared
`atp_to_diverge` covers the costlier side. Nothing here says the divergence is
interesting, or that the successor is wrong to produce it.
"""
from __future__ import annotations

import os
import sys
import unittest

# Same import guard, and same reason, as test_retirement_binding.py.
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

import crypto
import glyph
import warrant_kernel as wk
from warrant_kernel import (
    EdgeClaim, CounterexampleWitness, EmpiricalWitness, Polarity, EvidenceGrade,
    WarrantVerifier, TrustConfig, VerificationStatus,
)

if os.path.dirname(os.path.abspath(wk.__file__)) != _HERE:
    raise ImportError(f"warrant_kernel resolved to {wk.__file__}, outside {_HERE}")

# A real divergence, computed rather than asserted:
#   omega = K,      K (I (K I))      -> K (K I)
#   tau   = K I,    K I (I (K I))    -> I
OMEGA, TAU, INPUT = "🖤", "🖤 🤍", "🤍 (🖤 🤍)"
PARENT_OUT, SUCCESSOR_OUT = "🖤 (🖤 🤍)", "🤍"

# A second divergence whose two sides cost different amounts, so that "the
# declared budget suffices" can be told apart from "it suffices for one side":
#   omega = S I I,  S I I (S (K I) I) -> S (K I) I   in 7 ATP
#   tau   = K I,    K I (S (K I) I)   -> I           in 1 ATP
ASYM = dict(omega="🌿 🤍 🤍", tau="🖤 🤍",
            input_expr="🌿 (🖤 🤍) 🤍",
            parent_out="🌿 (🖤 🤍) 🤍", successor_out="🤍",
            parent_atp=7, successor_atp=1)


def replay(head: str, inp: str, atp: int = 10_000):
    return glyph.evaluate(glyph.parse(f"{head} ({inp})"), max_atp=atp)


class CounterexampleAuditTest(unittest.TestCase):

    def setUp(self):
        self.sk, self.pk = crypto.generate_keypair()
        self.verifier = WarrantVerifier(TrustConfig())

    def audit(self, witness, polarity=Polarity.REFUTE, tau=TAU, omega=OMEGA, verifier=None):
        claim = EdgeClaim.create_and_sign(
            "0" * 64, tau, omega, "a" * 64, polarity, witness, self.sk, self.pk)
        return (verifier or self.verifier).audit_claim(claim)

    def witness(self, **over):
        kw = dict(input_expr=INPUT, expected_normal_form=PARENT_OUT,
                  actual_divergence=SUCCESSOR_OUT, atp_to_diverge=4)
        kw.update(over)
        return CounterexampleWitness(**kw)

    # ---------------------------------------------------------------- A ---

    def test_transport_cannot_normalize_invalid_cost_into_signed_integer(self):
        import copy
        claim = EdgeClaim.create_and_sign(
            "0" * 64, TAU, OMEGA, "a" * 64, Polarity.REFUTE,
            self.witness(atp_to_diverge=1), self.sk, self.pk)
        honest = EdgeClaim.from_dict(claim.to_dict())
        self.assertEqual(self.verifier.audit_claim(honest).status, VerificationStatus.PASS)
        for value in (True, 1.9, "1", None, -1):
            with self.subTest(value=value):
                raw = copy.deepcopy(claim.to_dict())
                raw["body"]["witness"]["atp_to_diverge"] = value
                with self.assertRaises(ValueError):
                    EdgeClaim.from_dict(raw)
        raw = copy.deepcopy(claim.to_dict())
        del raw["body"]["witness"]["atp_to_diverge"]
        with self.assertRaises(ValueError):
            EdgeClaim.from_dict(raw)

    def test_A0_the_fixture_is_what_the_engine_actually_computes(self):
        """The operands are measured here, so the rest of the suite rests on fact."""
        p, s = replay(OMEGA, INPUT), replay(TAU, INPUT)
        self.assertTrue(p.is_settled() and s.is_settled())
        self.assertEqual(str(p.term), PARENT_OUT)
        self.assertEqual(str(s.term), SUCCESSOR_OUT)
        self.assertNotEqual(str(p.term), str(s.term))

    def test_A1_a_real_and_correctly_described_divergence_passes(self):
        v = self.audit(self.witness())
        self.assertEqual(v.status, VerificationStatus.PASS, v.reason)
        self.assertEqual(v.grade, EvidenceGrade.COUNTEREXAMPLE)
        self.assertEqual(v.details["parent_output"], PARENT_OUT)
        self.assertEqual(v.details["successor_output"], SUCCESSOR_OUT)

    def test_A2_a_malformed_input_is_not_a_refutation(self):
        for bad in ("((", ")", "🖤 (", ""):
            with self.subTest(input_expr=bad):
                v = self.audit(self.witness(input_expr=bad))
                self.assertNotEqual(v.status, VerificationStatus.PASS)
                self.assertEqual(v.status, VerificationStatus.FAIL, v.reason)
                self.assertIn("parse", v.reason.lower())

    def test_A3_declared_operands_are_compared_to_the_replay(self):
        for field, value in (("expected_normal_form", "TOTAL NONSENSE"),
                             ("actual_divergence", "ALSO NONSENSE"),
                             ("expected_normal_form", SUCCESSOR_OUT),
                             ("actual_divergence", PARENT_OUT)):
            with self.subTest(field=field, value=value):
                v = self.audit(self.witness(**{field: value}))
                self.assertEqual(v.status, VerificationStatus.FAIL, v.reason)
                self.assertIn(field.replace("_", " ").split()[0], v.reason.lower())

    def test_A4_an_unfinished_reduction_decides_nothing(self):
        """Both sides suspended at the ceiling is not a reproduced divergence."""
        tight = WarrantVerifier(TrustConfig(max_atp_budget=300))
        v = self.audit(self.witness(), tau="🔁 🤍", omega="🔁 🖤", verifier=tight)
        self.assertEqual(v.status, VerificationStatus.UNVERIFIED, v.reason)
        self.assertIn("budget", v.reason.lower())

    def test_A4b_one_unfinished_side_is_enough_to_decide_nothing(self):
        """Either side alone. A settled parent does not license the successor."""
        tight = WarrantVerifier(TrustConfig(max_atp_budget=300))
        for tau, omega in (("🔁 🤍", OMEGA), (TAU, "🔁 🤍")):
            with self.subTest(tau=tau, omega=omega):
                v = self.audit(self.witness(), tau=tau, omega=omega, verifier=tight)
                self.assertEqual(v.status, VerificationStatus.UNVERIFIED, v.reason)
                self.assertIn("budget", v.reason.lower())

    def test_A5_a_declared_cost_that_does_not_cover_the_replay_fails(self):
        v = self.audit(self.witness(atp_to_diverge=0))
        self.assertEqual(v.status, VerificationStatus.FAIL, v.reason)
        self.assertIn("atp", v.reason.lower())

    def test_A5b_the_declared_cost_must_cover_the_costlier_side(self):
        """One side settling inside the declared budget is not both sides."""
        p = replay(ASYM["omega"], ASYM["input_expr"])
        s = replay(ASYM["tau"], ASYM["input_expr"])
        self.assertEqual((p.atp_spent, s.atp_spent),
                         (ASYM["parent_atp"], ASYM["successor_atp"]))
        w = lambda atp: CounterexampleWitness(
            input_expr=ASYM["input_expr"], expected_normal_form=ASYM["parent_out"],
            actual_divergence=ASYM["successor_out"], atp_to_diverge=atp)
        cheap = self.audit(w(ASYM["successor_atp"]),
                           tau=ASYM["tau"], omega=ASYM["omega"])
        self.assertEqual(cheap.status, VerificationStatus.FAIL, cheap.reason)
        self.assertIn(str(ASYM["parent_atp"]), cheap.reason)
        enough = self.audit(w(ASYM["parent_atp"]),
                            tau=ASYM["tau"], omega=ASYM["omega"])
        self.assertEqual(enough.status, VerificationStatus.PASS, enough.reason)

    def test_A6_a_nonsense_declared_cost_is_refused(self):
        for bad in (-999, -1, True, 1.5, "4"):
            with self.subTest(atp=bad):
                v = self.audit(self.witness(atp_to_diverge=bad))
                self.assertNotEqual(v.status, VerificationStatus.PASS)

    # ---------------------------------------------------------------- B ---

    def test_B1_the_roles_are_not_interchangeable(self):
        """expected_normal_form is the parent's output; swapping them fails."""
        v = self.audit(self.witness(expected_normal_form=SUCCESSOR_OUT,
                                    actual_divergence=PARENT_OUT))
        self.assertEqual(v.status, VerificationStatus.FAIL, v.reason)

    def test_B1b_an_unparsable_claim_endpoint_is_not_a_refutation(self):
        """The witness is well-formed; the claim's own endpoints are not."""
        for tau, omega in (("((", OMEGA), (TAU, "((")):
            with self.subTest(tau=tau, omega=omega):
                v = self.audit(self.witness(), tau=tau, omega=omega)
                self.assertEqual(v.status, VerificationStatus.FAIL, v.reason)
                self.assertIn("parse", v.reason.lower())

    def test_B2_polarity_must_be_refute(self):
        v = self.audit(self.witness(), polarity=Polarity.AFFIRM)
        self.assertEqual(v.status, VerificationStatus.FAIL)
        self.assertIn("REFUTE", v.reason)

    def test_B3_a_generous_declared_cost_is_allowed(self):
        """The claim is that this much ATP suffices, not that it is tight."""
        v = self.audit(self.witness(atp_to_diverge=10_000))
        self.assertEqual(v.status, VerificationStatus.PASS, v.reason)

    # ---------------------------------------------------------------- C ---

    def test_C1_outputs_that_coincide_are_not_a_refutation(self):
        """Unchanged behaviour, kept as a control."""
        v = self.audit(self.witness(expected_normal_form="🤍", actual_divergence="🤍"),
                       tau=OMEGA)
        self.assertEqual(v.status, VerificationStatus.FAIL, v.reason)
        self.assertIn("coincide", v.reason.lower())

    def test_C2_an_unexpected_error_is_unverified_not_passed(self):
        """A crash is not evidence. It is the absence of evidence."""
        original = glyph.evaluate

        def exploding(*a, **k):
            raise RuntimeError("engine failure")

        glyph.evaluate = exploding
        try:
            v = self.audit(self.witness())
        finally:
            glyph.evaluate = original
        self.assertEqual(v.status, VerificationStatus.UNVERIFIED, v.reason)
        self.assertIn("RuntimeError", v.reason)

    def test_C3_no_status_is_reached_by_accident(self):
        seen = {
            self.audit(self.witness()).status,
            self.audit(self.witness(input_expr="((")).status,
            WarrantVerifier(TrustConfig(max_atp_budget=300)).audit_claim(
                EdgeClaim.create_and_sign("0" * 64, "🔁 🤍", "🔁 🖤", "a" * 64,
                                          Polarity.REFUTE, self.witness(),
                                          self.sk, self.pk)).status,
        }
        self.assertEqual(seen, {VerificationStatus.PASS, VerificationStatus.FAIL,
                                VerificationStatus.UNVERIFIED})

    # ---------------------------------------------------------------- D ---

    def test_D1_the_reason_says_which_side_disagreed(self):
        v = self.audit(self.witness(expected_normal_form="WRONG"))
        self.assertIn("WRONG", v.reason)
        self.assertIn(PARENT_OUT, v.reason)


    # ---------------------------------------------------------------- E ---
    # An endpoint must be a term in its own right. The replay used to compose
    # source text, `f"{omega} ({input})"`, so an empty omega vanished into its
    # neighbours: the parent replay became the input alone, and the input's own
    # behaviour was credited to a function nobody supplied. Measured before the
    # fix: a signed Grade C claim with omega="" audited PASS.

    def test_E1_parse_application_joins_asts_not_source_text(self):
        for head, arg in ((OMEGA, INPUT), (TAU, INPUT), ("🌿 🤍 🤍", "🖤 🤍")):
            with self.subTest(head=head):
                self.assertEqual(glyph.parse_application(head, arg),
                                 glyph.parse(f"{head} ({arg})"))

    def test_E2_an_endpoint_that_is_not_a_term_is_refused(self):
        for bad in ("", " ", "\t", "(", "🖤 ("):
            with self.subTest(endpoint=bad):
                with self.assertRaises(Exception):
                    glyph.parse_application(bad, INPUT)
                with self.assertRaises(Exception):
                    glyph.parse_application(OMEGA, bad)

    def test_E3_a_signed_claim_with_an_empty_endpoint_fails(self):
        """Genuinely signed, and still refused: the signature is not the issue."""
        for omega, tau in (("", TAU), (OMEGA, ""), ("  ", TAU), (OMEGA, "\t")):
            with self.subTest(omega=omega, tau=tau):
                claim = EdgeClaim.create_and_sign(
                    "0" * 64, tau, omega, "a" * 64, Polarity.REFUTE,
                    self.witness(), self.sk, self.pk)
                self.assertTrue(claim.verify_signature())
                v = self.verifier.audit_claim(claim)
                self.assertNotEqual(v.status, VerificationStatus.PASS)
                self.assertEqual(v.status, VerificationStatus.FAIL, v.reason)
                self.assertIn("parse", v.reason.lower())

    def test_E4_the_empirical_branch_had_the_same_boundary(self):
        """The twin, fixed in the same pass: omega="" made the parent the fixture."""
        fixtures = ["🤍"]
        w = EmpiricalWitness(fixtures=fixtures, fixtures_fingerprint="",
                             delta_atp=0, delta_size=0)
        w.fixtures_fingerprint = w.compute_fixtures_fingerprint()

        def audit(omega, tau):
            claim = EdgeClaim.create_and_sign("0" * 64, tau, omega, "a" * 64,
                                              Polarity.AFFIRM, w, self.sk, self.pk)
            return self.verifier.audit_claim(claim)

        for omega, tau in (("", "🤍"), ("🤍", ""), ("  ", "🤍")):
            with self.subTest(omega=omega, tau=tau):
                v = audit(omega, tau)
                self.assertEqual(v.status, VerificationStatus.FAIL, v.reason)
                self.assertIn("parse", v.reason.lower())
        self.assertEqual(audit("🤍", "🤍").status, VerificationStatus.PASS)


if __name__ == "__main__":
    unittest.main(verbosity=2)
