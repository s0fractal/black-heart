#!/usr/bin/env python3
"""
Regression: a universal claim about a synthesized term names the terms it is about.

CEGIS granted PROVED_CORRECT from a fixed SMT-LIB2 script that mentioned
neither the candidate nor the specification:

    (assert (= cand_eval (eval x)))
    (assert (= spec_eval (eval x)))
    (assert (not (= cand_eval spec_eval)))

That is UNSAT by congruence for every possible candidate and every possible
spec, so it could not distinguish anything. Measured on the base commit: the
identity at arity 1 and a selector at arity 2 produced a BYTE-IDENTICAL proof
DAG, and no clause in it referred to either program.

What the sections pin:

  A  extensional equality is decided from the two terms, with the conditions of
     the claim checked rather than assumed: fresh probes, stated arity, and a
     reduction that completed.
  B  substituting the candidate, the spec, the arity or the output each removes
     the credit, independently.
  C  the loop reports what it established: a Python callable earns agreement on
     the inputs tried, never a theorem; a term spec can earn a universal claim.
  D  OE-pruning still prunes, and is not described as a proof of anything.

The claim this module defends is narrow and stated in full at the checker: two
SKIY terms applied to fresh variables reduce to the same normal form, therefore
they agree on every argument list of that arity. It says nothing about other
arities, and nothing about whether a term encodes anyone's intent.
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

import cegis_kernel as ck
from cegis_kernel import (
    CEGISLoop, SynthesisStatus, EquivalenceStatus,
    check_extensional_equality, fresh_variables, term_digest,
    SynthesisCreditBinding, verify_synthesis_credit,
)
from glyph import K, I, S, Y, App, Var

if os.path.dirname(os.path.abspath(ck.__file__)) != _HERE:
    raise ImportError(f"cegis_kernel resolved to {ck.__file__}, outside {_HERE}")

SKK = App(App(S, K), K)          # extensionally the identity
KI = App(K, I)                   # the second-argument selector at arity 2


class ExtensionalEqualityTest(unittest.TestCase):
    """The check reads both operands, so different operands give different answers."""

    def test_A1_equal_terms_and_equal_behaviour(self):
        for label, a, b, arity in (
            ("identity with itself", I, I, 1),
            ("S K K is the identity", SKK, I, 1),
            ("the identity is S K K", I, SKK, 1),
            ("K with itself at arity two", K, K, 2),
            ("K I selects the second argument", KI, App(K, I), 2),
        ):
            with self.subTest(case=label):
                w = check_extensional_equality(a, b, arity)
                self.assertIs(w.status, EquivalenceStatus.EXTENSIONALLY_EQUAL, w.reason)
                self.assertEqual(w.candidate_sha256, term_digest(a))
                self.assertEqual(w.spec_sha256, term_digest(b))
                self.assertEqual(w.arity, arity)
                self.assertTrue(w)

    def test_A2_different_behaviour_is_refuted_with_the_forms(self):
        for label, a, b, arity in (
            ("K is not the identity", K, I, 1),
            ("K I is not K", KI, K, 2),
            ("the identity is not K I", I, KI, 2),
        ):
            with self.subTest(case=label):
                w = check_extensional_equality(a, b, arity)
                self.assertIs(w.status, EquivalenceStatus.REFUTED, w.reason)
                self.assertIn("differ", w.reason)
                self.assertFalse(w)

    def test_A3_the_arity_is_part_of_the_claim(self):
        """K and K I agree nowhere at arity 2, and the check is asked per arity."""
        self.assertIs(check_extensional_equality(K, K, 1).status,
                      EquivalenceStatus.EXTENSIONALLY_EQUAL)
        self.assertIs(check_extensional_equality(K, KI, 1).status,
                      EquivalenceStatus.REFUTED)
        self.assertIs(check_extensional_equality(K, KI, 2).status,
                      EquivalenceStatus.REFUTED)

    def test_A4_probe_variables_are_fresh_and_it_matters(self):
        """A candidate that returns a constant named like the probe.

        `K _x0` ignores its argument and returns the variable `_x0`. Probed with
        a variable of that same name it would look like the identity. The probe
        is chosen to occur in neither term, so it does not.
        """
        impostor = App(K, Var("_x0"))
        probes = fresh_variables(1, impostor, I)
        self.assertNotIn("_x0", [v.name for v in probes])
        self.assertIs(check_extensional_equality(impostor, I, 1).status,
                      EquivalenceStatus.REFUTED)

    def test_A5_an_incomplete_reduction_decides_nothing(self):
        """A suspended reduction is its own answer, not equality and not refutation."""
        w = check_extensional_equality(App(Y, I), App(Y, I), 1, max_atp=25)
        self.assertIs(w.status, EquivalenceStatus.INCONCLUSIVE_BUDGET, w.reason)
        self.assertIn("did not complete", w.reason)
        self.assertFalse(w)

    def test_A6_a_callable_spec_is_not_a_term(self):
        for a, b in ((I, None), (None, I), (None, None)):
            self.assertIs(check_extensional_equality(a, b, 1).status,
                          EquivalenceStatus.NO_TERM_SPEC)

    def test_A7_arity_contract(self):
        for bad in (-1, True, 1.0, "1"):
            with self.subTest(arity=bad):
                self.assertIs(check_extensional_equality(I, I, bad).status,
                              EquivalenceStatus.NO_TERM_SPEC)


class CreditBindingTest(unittest.TestCase):
    """Each operand of the claim can be substituted, and each removes the credit."""

    def setUp(self):
        self.result = CEGISLoop(verifier_domain=["a", "b", "c"]).synthesize(
            lambda inp: inp[0], input_arity=1, spec_term=I)
        self.assertIsNotNone(self.result.program)
        self.binding = SynthesisCreditBinding(
            candidate_sha256=term_digest(self.result.program),
            spec_sha256=term_digest(I),
            arity=1,
            output_sha256=term_digest(self.result.program))

    def test_B1_the_bound_case_is_granted(self):
        d = verify_synthesis_credit(self.result, self.binding, spec_term=I)
        self.assertTrue(d.granted, d.reason)
        self.assertIn("arity 1", d.reason)

    def test_B2_no_binding_no_credit(self):
        self.assertFalse(verify_synthesis_credit(self.result, None, spec_term=I).granted)

    def test_B3_candidate_substitution(self):
        """The result carries another program while the binding stays fixed."""
        import dataclasses
        swapped = dataclasses.replace(self.result, program=K, program_str=str(K))
        d = verify_synthesis_credit(swapped, self.binding, spec_term=I)
        self.assertFalse(d.granted)
        self.assertIn("OUTPUT_MISMATCH", d.reason)

    def test_B4_spec_substitution(self):
        d = verify_synthesis_credit(self.result, self.binding, spec_term=K)
        self.assertFalse(d.granted)
        self.assertIn("SPEC_MISMATCH", d.reason)

    def test_B5_output_substitution(self):
        import dataclasses
        other_target = dataclasses.replace(self.binding, output_sha256=term_digest(K))
        d = verify_synthesis_credit(self.result, other_target, spec_term=I)
        self.assertFalse(d.granted)
        self.assertIn("OUTPUT_MISMATCH", d.reason)

    def test_B6_arity_substitution(self):
        """Lowering the arity refuses; raising it cannot, and that is a property.

        If two terms have the same normal form on n fresh variables, applying
        both to one more variable keeps them equal, so equality at arity n
        implies equality at n+1. Only a LOWER arity can withdraw the claim:
        `S K K` and `I` agree on one argument and are different terms on none.
        """
        import dataclasses
        res = dataclasses.replace(self.result, program=SKK, program_str=str(SKK))
        at_one = SynthesisCreditBinding(term_digest(SKK), term_digest(I), 1, term_digest(SKK))
        self.assertTrue(verify_synthesis_credit(res, at_one, spec_term=I).granted)

        at_zero = dataclasses.replace(at_one, arity=0)
        d = verify_synthesis_credit(res, at_zero, spec_term=I)
        self.assertFalse(d.granted)
        self.assertIn("REFUTED", d.reason)

        at_two = dataclasses.replace(at_one, arity=2)
        self.assertTrue(verify_synthesis_credit(res, at_two, spec_term=I).granted,
                        "equality at arity 1 carries to arity 2")

    def test_B7_a_set_status_earns_nothing(self):
        """The consumer re-derives; it does not read the result's own verdict."""
        import dataclasses
        lying = dataclasses.replace(
            CEGISLoop(verifier_domain=["a"]).synthesize(lambda inp: inp[0], input_arity=1),
            status=SynthesisStatus.PROVED_CORRECT, program=K, program_str=str(K))
        binding = SynthesisCreditBinding(term_digest(K), term_digest(I), 1, term_digest(K))
        self.assertFalse(verify_synthesis_credit(lying, binding, spec_term=I).granted)

    def test_B8_an_equal_program_under_a_different_encoding_still_verifies(self):
        """S K K is a different term from I, and is granted on its own merits."""
        binding = SynthesisCreditBinding(term_digest(SKK), term_digest(I), 1, term_digest(SKK))
        import dataclasses
        res = dataclasses.replace(self.result, program=SKK, program_str=str(SKK))
        self.assertTrue(verify_synthesis_credit(res, binding, spec_term=I).granted)


class LoopReportsWhatItEstablishedTest(unittest.TestCase):

    def test_C1_a_callable_spec_never_earns_a_theorem(self):
        res = CEGISLoop(verifier_domain=["a", "b", "c"]).synthesize(
            lambda inp: inp[0], input_arity=1)
        self.assertEqual(res.status, SynthesisStatus.FINITE_DOMAIN_SATISFIED)
        self.assertIsNotNone(res.program)
        self.assertIsNone(res.equivalence_witness)

    def test_C2_a_term_spec_can_earn_one_and_names_its_operands(self):
        res = CEGISLoop(verifier_domain=["a", "b", "c"]).synthesize(
            lambda inp: inp[0], input_arity=1, spec_term=I)
        self.assertEqual(res.status, SynthesisStatus.PROVED_CORRECT)
        w = res.equivalence_witness
        self.assertIsNotNone(w)
        self.assertEqual(w.candidate_sha256, term_digest(res.program))
        self.assertEqual(w.spec_sha256, term_digest(I))

    def test_C3_two_different_problems_do_not_share_their_evidence(self):
        """The defect this replaces: one fixed query answered every question."""
        a = CEGISLoop(verifier_domain=["a", "b"]).synthesize(
            lambda inp: inp[0], input_arity=1, spec_term=I)
        b = CEGISLoop(verifier_domain=["a", "b"]).synthesize(
            lambda inp: inp[0], input_arity=2, spec_term=K)
        self.assertNotEqual(a.equivalence_witness.candidate_sha256,
                            b.equivalence_witness.candidate_sha256)
        self.assertNotEqual(a.equivalence_witness.spec_sha256,
                            b.equivalence_witness.spec_sha256)

    def test_C4_a_spec_the_candidate_does_not_match_is_not_proved(self):
        """Agreeing on the search domain is not agreeing everywhere."""
        res = CEGISLoop(verifier_domain=["a"]).synthesize(
            lambda inp: inp[0], input_arity=1, primitives=[I], max_ast_size=1, spec_term=K)
        self.assertNotEqual(res.status, SynthesisStatus.PROVED_CORRECT)

    def test_C5_the_manifest_names_the_scope_and_the_operands(self):
        res = CEGISLoop(verifier_domain=["a", "b"]).synthesize(
            lambda inp: inp[0], input_arity=1, spec_term=I)
        manifest = ck.cegis_result_manifest(res)
        self.assertNotIn("is_verified", manifest)
        self.assertEqual(manifest["equivalence_check"], "EXTENSIONALLY_EQUAL")
        self.assertIn("fresh free variables", manifest["equivalence_scope"])
        self.assertEqual(manifest["candidate_sha256"], term_digest(res.program))


class PruningIsStillPruningTest(unittest.TestCase):

    def test_D1_observational_equivalence_still_prunes(self):
        res = CEGISLoop(verifier_domain=["a", "b", "c"]).synthesize(
            lambda inp: inp[0], input_arity=1, primitives=[K, S], max_ast_size=6)
        self.assertGreater(res.candidates_pruned_oe, 0)
        self.assertIsNotNone(res.program)

    def test_D2_pruning_is_not_described_as_a_proof(self):
        """It is a search economy. The universal claim comes from the checker."""
        import inspect
        src = inspect.getsource(ck.ObservationalEquivalencePruner) \
            if hasattr(ck, "ObservationalEquivalencePruner") else ""
        self.assertNotIn("PROVED_CORRECT", src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
