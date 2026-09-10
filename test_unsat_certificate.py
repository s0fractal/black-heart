#!/usr/bin/env python3
"""
Regression: a refutation is checked against the formula it refutes, step by step.

`verify_unsat_certificate` walked the proof DAG for shape — an empty clause
somewhere, antecedents that resolve to existing ids, no cycle, and some path
back to a node labelled `input`. It never looked at a single clause. So it
accepted a certificate for a *satisfiable* formula, it accepted a step with one
parent and no pivot, and `rule="input"` made any clause an axiom, including one
the formula never contained.

What the sections pin:

  A  genuine refutations are accepted, including one that reuses a clause, so
     the checker is not simply refusing everything.
  B  forged certificates are refused, each for its own reason: a satisfiable
     input, a one-parent step, a substituted pivot, a resolvent with an extra
     or a missing literal, an "input" clause the formula does not contain, the
     same proof against a different formula, and a cycle.
  C  outcomes that are not "invalid" stay separate from it: an unchecked proof
     class and an exhausted traversal bound are their own answers, because
     "I did not check this" is not "this theorem is false".
  D  the structural check and the refutation check are different questions, and
     the structural one is no longer described as certifying anything.

The formula is always supplied explicitly. A certificate that is not bound to
the clause set it claims to refute is not a certificate about anything.
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

import smt_kernel as sm
from smt_kernel import (
    ResolutionProofNode as Node,
    RefutationStatus,
    check_resolution_refutation,
    check_proof_dag_structure,
)

if os.path.dirname(os.path.abspath(sm.__file__)) != _HERE:
    raise ImportError(f"smt_kernel resolved to {sm.__file__}, outside {_HERE}")


def dag(*nodes):
    return {n.clause_id: n for n in nodes}


def inp(cid, clause):
    return Node(clause_id=cid, clause=list(clause), rule="input")


def res(cid, clause, parents, pivot):
    return Node(clause_id=cid, clause=list(clause), rule="learned",
                antecedents=list(parents), pivot_vars=[pivot])


class GenuineRefutationTest(unittest.TestCase):
    """Positive controls. A checker that refuses everything fails here."""

    def test_A1_unit_contradiction(self):
        """{p}, {not p} |- [] on pivot p."""
        formula = [[1], [-1]]
        proof = dag(inp(1, [1]), inp(2, [-1]), res(3, [], [1, 2], 1))
        report = check_resolution_refutation(formula, proof)
        self.assertEqual(report.status, RefutationStatus.VERIFIED_REFUTATION, report.reason)
        self.assertEqual(report.checked_steps, 1)

    def test_A2_four_clause_refutation(self):
        """{p,q},{p,-q},{-p,q},{-p,-q} |- [], four resolutions."""
        formula = [[1, 2], [1, -2], [-1, 2], [-1, -2]]
        proof = dag(
            inp(1, [1, 2]), inp(2, [1, -2]), inp(3, [-1, 2]), inp(4, [-1, -2]),
            res(5, [1], [1, 2], 2),        # (p or q) x (p or -q) on q
            res(6, [-1], [3, 4], 2),       # (-p or q) x (-p or -q) on q
            res(7, [], [5, 6], 1),         # p x -p on p
        )
        report = check_resolution_refutation(formula, proof)
        self.assertEqual(report.status, RefutationStatus.VERIFIED_REFUTATION, report.reason)
        self.assertEqual(report.checked_steps, 3)

    def test_A3_a_clause_may_be_used_twice(self):
        """It is a DAG: reusing a parent is allowed, and still checked."""
        formula = [[1, 2], [-1], [-2]]
        proof = dag(
            inp(1, [1, 2]), inp(2, [-1]), inp(3, [-2]),
            res(4, [2], [1, 2], 1),
            res(5, [1], [1, 3], 2),
            res(6, [], [4, 3], 2),
        )
        report = check_resolution_refutation(formula, proof)
        self.assertEqual(report.status, RefutationStatus.VERIFIED_REFUTATION, report.reason)

    def test_A4_a_formula_containing_the_empty_clause_refutes_itself(self):
        formula = [[]]
        report = check_resolution_refutation(formula, dag(inp(1, [])))
        self.assertEqual(report.status, RefutationStatus.VERIFIED_REFUTATION, report.reason)
        self.assertEqual(report.checked_steps, 0)

    def test_A5_literal_order_and_duplicates_do_not_matter(self):
        """Clauses are sets of literals; the checker must not depend on order."""
        formula = [[2, 1, 1], [-2]]
        proof = dag(inp(1, [1, 2]), inp(2, [-2]), res(3, [1], [1, 2], 2))
        report = check_resolution_refutation(formula + [[-1]], dag(
            inp(1, [1, 2]), inp(2, [-2]), inp(4, [-1]),
            res(3, [1], [1, 2], 2), res(5, [], [3, 4], 1)))
        self.assertEqual(report.status, RefutationStatus.VERIFIED_REFUTATION, report.reason)
        self.assertEqual(check_resolution_refutation(formula, proof).status,
                         RefutationStatus.INVALID)   # no empty clause: not a refutation


class ForgedCertificateTest(unittest.TestCase):
    """Each forgery is refused, and the reason names what was wrong."""

    def assertInvalid(self, report, fragment):
        self.assertEqual(report.status, RefutationStatus.INVALID, report.reason)
        self.assertIn(fragment, report.reason.lower())

    def test_B1_certificate_for_a_satisfiable_formula(self):
        """The criterion for this package: {p} is satisfiable, so nothing refutes it."""
        formula = [[1]]
        proof = dag(inp(1, [1]), res(2, [], [1, 1], 1))
        self.assertInvalid(check_resolution_refutation(formula, proof), "resolv")

    def test_B1b_satisfiable_formula_with_a_well_formed_forgery(self):
        """The same criterion, but the forgery is flawless except for the conclusion.

        {p or q, -p or r} is satisfiable. The step has two antecedents and a
        pivot with the right polarities, so only comparing the resolvent to its
        parents catches it: resolving on p yields {q, r}, not the empty clause.
        """
        formula = [[1, 2], [-1, 3]]
        proof = dag(inp(1, [1, 2]), inp(2, [-1, 3]), res(3, [], [1, 2], 1))
        self.assertInvalid(check_resolution_refutation(formula, proof), "resolvent")

    def test_B2_single_parent_step_is_not_a_resolution(self):
        """The exact shape the old checker accepted, and the one the solver emits."""
        formula = [[1, 2], [-1], [-2]]
        proof = dag(inp(1, [1, 2]), inp(2, [-1]), inp(3, [-2]),
                    Node(clause_id=4, clause=[], rule="learned", antecedents=[1]))
        self.assertInvalid(check_resolution_refutation(formula, proof), "two antecedents")

    # In B3-B5 the forged node is an ancestor of the empty clause, so the step
    # check is what fires. A proof that simply never reaches [] is refused
    # earlier, for a different and less interesting reason (B9).
    FORMULA = [[1, 2], [-1, 3], [-2], [-3]]

    def with_final_steps(self, forged):
        """forged derives [2,3]; resolve it down to [] using the real clauses."""
        return dag(inp(1, [1, 2]), inp(2, [-1, 3]), inp(4, [-2]), inp(5, [-3]),
                   forged,
                   res(6, [3], [3, 4], 2),
                   res(7, [], [6, 5], 3))

    def test_B3_substituted_pivot(self):
        """Variable 2 does not occur with opposite signs in the two parents."""
        proof = self.with_final_steps(res(3, [2, 3], [1, 2], 2))
        self.assertInvalid(check_resolution_refutation(self.FORMULA, proof), "pivot")

    def test_B4_extra_literal_in_the_resolvent(self):
        proof = self.with_final_steps(res(3, [2, 3, 4], [1, 2], 1))
        self.assertInvalid(check_resolution_refutation(self.FORMULA, proof), "resolvent")

    def test_B5_missing_literal_in_the_resolvent(self):
        proof = self.with_final_steps(res(3, [2], [1, 2], 1))
        self.assertInvalid(check_resolution_refutation(self.FORMULA, proof), "resolvent")

    def test_B5b_the_same_skeleton_with_an_honest_step_verifies(self):
        """Positive control for B3-B5: only the forged node made them fail."""
        proof = self.with_final_steps(res(3, [2, 3], [1, 2], 1))
        self.assertEqual(check_resolution_refutation(self.FORMULA, proof).status,
                         RefutationStatus.VERIFIED_REFUTATION)

    def test_B6_input_label_does_not_make_a_clause_an_axiom(self):
        formula = [[1]]
        proof = dag(inp(1, [1]), inp(2, [-1]), res(3, [], [1, 2], 1))
        self.assertInvalid(check_resolution_refutation(formula, proof), "not in the formula")

    def test_B7_same_proof_against_a_different_formula(self):
        proof = dag(inp(1, [1]), inp(2, [-1]), res(3, [], [1, 2], 1))
        self.assertEqual(check_resolution_refutation([[1], [-1]], proof).status,
                         RefutationStatus.VERIFIED_REFUTATION)
        self.assertInvalid(check_resolution_refutation([[1], [2]], proof), "not in the formula")

    def test_B8_cycle_is_refused_without_looping(self):
        formula = [[1], [-1]]
        proof = dag(inp(1, [1]), inp(2, [-1]),
                    res(3, [], [4, 2], 1), res(4, [1], [3, 1], 1))
        report = check_resolution_refutation(formula, proof)
        self.assertIn(report.status, (RefutationStatus.INVALID, RefutationStatus.UNKNOWN))
        self.assertNotEqual(report.status, RefutationStatus.VERIFIED_REFUTATION)

    def test_B9_missing_empty_clause(self):
        formula = [[1], [-1]]
        proof = dag(inp(1, [1]), inp(2, [-1]))
        self.assertInvalid(check_resolution_refutation(formula, proof), "empty clause")

    def test_B10_dangling_antecedent(self):
        formula = [[1], [-1]]
        proof = dag(inp(1, [1]), res(3, [], [1, 99], 1))
        self.assertInvalid(check_resolution_refutation(formula, proof), "unknown antecedent")

    def test_B11_empty_clause_as_an_input_the_formula_does_not_have(self):
        self.assertInvalid(check_resolution_refutation([[1]], dag(inp(1, []))), "not in the formula")


class NotCheckedIsNotFalseTest(unittest.TestCase):
    """An answer the checker did not reach must not read as a refuted theorem."""

    def test_C1_theory_lemma_is_unsupported_not_verified(self):
        formula = [[1]]
        proof = dag(inp(1, [1]),
                    Node(clause_id=2, clause=[-1], rule="theory_lemma"),
                    res(3, [], [1, 2], 1))
        report = check_resolution_refutation(formula, proof)
        self.assertEqual(report.status, RefutationStatus.UNSUPPORTED, report.reason)
        self.assertIn("theory_lemma", report.reason)

    def test_C2_traversal_bound_is_unknown_not_invalid(self):
        formula = [[1, 2], [1, -2], [-1, 2], [-1, -2]]
        proof = dag(
            inp(1, [1, 2]), inp(2, [1, -2]), inp(3, [-1, 2]), inp(4, [-1, -2]),
            res(5, [1], [1, 2], 2), res(6, [-1], [3, 4], 2), res(7, [], [5, 6], 1))
        self.assertEqual(check_resolution_refutation(formula, proof).status,
                         RefutationStatus.VERIFIED_REFUTATION)
        report = check_resolution_refutation(formula, proof, max_steps=2)
        self.assertEqual(report.status, RefutationStatus.UNKNOWN, report.reason)
        self.assertIn("bound", report.reason.lower())

    def test_C3_unknown_rule_is_unsupported(self):
        formula = [[1], [-1]]
        proof = dag(inp(1, [1]), inp(2, [-1]),
                    Node(clause_id=3, clause=[], rule="magic", antecedents=[1, 2]))
        self.assertEqual(check_resolution_refutation(formula, proof).status,
                         RefutationStatus.UNSUPPORTED)


class StructureIsNotRefutationTest(unittest.TestCase):
    """The distinction this package exists to draw."""

    def test_D1_a_well_formed_shape_is_not_a_refutation(self):
        formula = [[1, 2], [-1], [-2]]
        proof = dag(inp(1, [1, 2]), inp(2, [-1]), inp(3, [-2]),
                    Node(clause_id=4, clause=[], rule="learned", antecedents=[1]))
        self.assertTrue(check_proof_dag_structure(proof),
                        "this shape is exactly what the structural check accepts")
        self.assertEqual(check_resolution_refutation(formula, proof).status,
                         RefutationStatus.INVALID)

    def test_D2_the_solvers_own_proof_is_shape_only(self):
        """Recorded as it is: the CDCL solver does not emit resolution steps.

        Its learned nodes carry one antecedent and no pivot, so a step-checking
        verifier cannot accept them. The formula really is unsatisfiable; the
        object it hands back is provenance, not a derivation.
        """
        result = sm.SMTSolver().solve_smt2(
            "(declare-const p Bool)\n(assert p)\n(assert (not p))\n(check-sat)")
        self.assertEqual(result.status, sm.SMTStatus.UNSAT)
        self.assertTrue(check_proof_dag_structure(result.proof_dag))
        report = check_resolution_refutation(
            [n.clause for n in result.proof_dag.values() if n.rule == "input"],
            result.proof_dag)
        self.assertNotEqual(report.status, RefutationStatus.VERIFIED_REFUTATION)
        self.assertEqual(report.status, RefutationStatus.INVALID)
        self.assertIn("two antecedents", report.reason.lower())

    def test_D3_the_deprecated_name_still_answers_but_warns(self):
        """Historical callers keep working; the name stops implying a refutation."""
        proof = dag(inp(1, [1]), Node(clause_id=2, clause=[], rule="learned", antecedents=[1]))
        with self.assertWarns(DeprecationWarning):
            self.assertTrue(sm.verify_unsat_certificate(proof))

    def test_D4_reported_surfaces_do_not_say_verified(self):
        """What a document or a caller reads must name the question answered."""
        result = sm.SMTSolver().solve_smt2(
            "(declare-const p Bool)\n(assert p)\n(assert (not p))\n(check-sat)")
        manifest = sm.smt_result_manifest(result)
        self.assertNotIn("is_verified", manifest)
        self.assertTrue(manifest["proof_structure_ok"])
        self.assertEqual(manifest["refutation_check"], RefutationStatus.INVALID.value)
        # The scope travels with the value, so a reader of the output alone
        # cannot take the adjacent formula text for the proven subject.
        self.assertEqual(manifest["refutation_check_scope"], "self_declared_input_nodes")
        self.assertIs(manifest["refutation_check_binds_formula_text"], False)


class IdentityBindingTest(unittest.TestCase):
    """A certificate may not rename its own nodes (F1)."""

    def test_F1_empty_node_cannot_redirect_to_a_nonempty_axiom(self):
        """{p} is satisfiable; the empty node in slot 2 points at the real axiom."""
        proof = {1: inp(1, [1]), 2: Node(clause_id=1, clause=[], rule="input")}
        report = check_resolution_refutation([[1]], proof)
        self.assertEqual(report.status, RefutationStatus.INVALID, report.reason)
        self.assertIn("clause_id", report.reason)

    def test_F1b_intermediate_node_key_mismatch(self):
        """Not only the endpoint: a renamed node anywhere breaks the chain."""
        proof = {1: inp(1, [1]), 2: inp(2, [-1]),
                 3: Node(clause_id=99, clause=[], rule="learned",
                         antecedents=[1, 2], pivot_vars=[1])}
        report = check_resolution_refutation([[1], [-1]], proof)
        self.assertEqual(report.status, RefutationStatus.INVALID, report.reason)

    def test_F1c_a_second_empty_node_does_not_rescue_a_broken_one(self):
        """Any endpoint with a fully checked derivation refutes; a bad one does not."""
        good = {1: inp(1, [1]), 2: inp(2, [-1]),
                3: Node(clause_id=3, clause=[], rule="learned", antecedents=[1], pivot_vars=[1]),
                4: res(4, [], [1, 2], 1)}
        self.assertEqual(check_resolution_refutation([[1], [-1]], good).status,
                         RefutationStatus.VERIFIED_REFUTATION)
        only_bad = {k: v for k, v in good.items() if k != 4}
        self.assertEqual(check_resolution_refutation([[1], [-1]], only_bad).status,
                         RefutationStatus.INVALID)

    def test_F1d_honest_proofs_are_unaffected(self):
        self.assertEqual(
            check_resolution_refutation([[1], [-1]],
                                        dag(inp(1, [1]), inp(2, [-1]), res(3, [], [1, 2], 1))).status,
            RefutationStatus.VERIFIED_REFUTATION)
        self.assertEqual(check_resolution_refutation([[]], dag(inp(1, []))).status,
                         RefutationStatus.VERIFIED_REFUTATION)


class ReceiptTest(unittest.TestCase):
    """A receipt is only worth the re-check a consumer performs with it."""

    def setUp(self):
        self.real = dag(inp(1, [1]), inp(2, [-1]), res(3, [], [1, 2], 1))
        self.invalid = dag(inp(1, [1]),
                           Node(clause_id=2, clause=[], rule="learned", antecedents=[1]))

    def test_G1_no_receipt_for_an_unverified_refutation(self):
        self.assertIsNone(sm.issue_refutation_receipt("s", [[1]], self.real))
        self.assertIsNone(sm.issue_refutation_receipt("s", [[1]], self.invalid))

    def test_G2_receipt_reverifies_only_for_its_own_subject_and_proof(self):
        receipt = sm.issue_refutation_receipt("subject-A", [[1], [-1]], self.real)
        self.assertIsNotNone(receipt)
        self.assertEqual(
            sm.verify_refutation_receipt(receipt, "subject-A", self.real).status,
            RefutationStatus.VERIFIED_REFUTATION)
        for label, args, fragment in (
            ("another subject", ("subject-B", self.real), "different subject"),
            ("another proof", ("subject-A", self.invalid), "different proof"),
        ):
            with self.subTest(case=label):
                out = sm.verify_refutation_receipt(receipt, *args)
                self.assertEqual(out.status, RefutationStatus.INVALID, out.reason)
                self.assertIn(fragment, out.reason)

    def test_G3_a_receipt_cannot_be_handcrafted_around_the_check(self):
        """The formula travels inside the receipt, so it is re-run, not trusted."""
        forged = sm.RefutationReceipt(
            subject_digest="subject-A",
            formula=(frozenset([1]),),
            proof_digest=sm.proof_dag_digest(self.invalid),
            checked_steps=99)
        out = sm.verify_refutation_receipt(forged, "subject-A", self.invalid)
        self.assertEqual(out.status, RefutationStatus.INVALID, out.reason)

    def test_G4_missing_receipt_is_its_own_answer(self):
        out = sm.verify_refutation_receipt(None, "subject-A", self.real)
        self.assertEqual(out.status, RefutationStatus.INVALID)
        self.assertIn("no refutation receipt", out.reason)


class FormalCreditGateTest(unittest.TestCase):
    """The admission this package exists to close, in its third form.

    Grade A rested first on proof shape, then on a mutable flag, then on a
    receipt whose subject label the same caller could set. Each time the thing
    being compared came out of the object being graded. The binding now arrives
    separately and stays fixed while everything in the report is attacked.
    """

    def setUp(self):
        import crypto
        self.sk, self.pk = crypto.generate_keypair()
        self.real = dag(inp(1, [1]), inp(2, [-1]), res(3, [], [1, 2], 1))
        self.invalid = dag(inp(1, [1]),
                           Node(clause_id=2, clause=[], rule="learned", antecedents=[1]))
        self.formula = [[1], [-1]]

    def _triad(self, **over):
        import dialectic_kernel as dk
        from scoped_admission import RefusalReason
        base = dict(
            thesis_candidate_digest="ab" * 32,
            antithesis_refusal_id="cd" * 32,
            refusal_reason=RefusalReason.RESOURCE_LIMIT,
            synthesis_delta=dk.ContextDelta(80, 140, 60, 1.75, 0.95),
            precondition=None,
            status=dk.DialecticalStatus.SYNTHESIS_ACHIEVED,
            settled_theorem="Settled under envelope budget_steps=140",
        )
        base.update(over)
        return dk.DialecticalTriad(**base)

    def _report(self, proof, smt_verified=False, receipt=None, triad=None):
        """Parameter order kept as it was: earlier reviewer probes call this
        positionally, and those runs are regression evidence worth preserving."""
        import dialectic_kernel as dk
        return dk.DialecticalDiscoveryReport(
            triad=triad if triad is not None else self._triad(),
            smt_verified=smt_verified,
            refutation_receipt=receipt, proof_dag=proof, elapsed_sec=0.01)

    def _binding(self, triad):
        """What a trusted caller asserts, computed by that caller, not by a report."""
        import dialectic_kernel as dk
        return dk.FormalCreditBinding(
            subject_digest=dk.triad_subject_digest(triad),
            formula_sha256=sm.formula_digest(self.formula))

    def _grade(self, triad, receipt, binding, proof=None, smt_verified=False):
        import dialectic_kernel as dk
        report = self._report(proof if proof is not None else self.real,
                              smt_verified=smt_verified, receipt=receipt, triad=triad)
        return dk.elevate_triad_to_warrant(report, self.sk, self.pk,
                                           credit_binding=binding).grade

    def _receipt_for(self, triad, formula=None, proof=None):
        import dialectic_kernel as dk
        return sm.issue_refutation_receipt(
            dk.triad_subject_digest(triad), formula or self.formula, proof or self.real)

    # ------------------------------------------------------------------ J ---

    def test_J1_no_caller_binding_means_no_formal_credit(self):
        from warrant_kernel import EvidenceGrade
        triad = self._triad()
        self.assertEqual(
            self._grade(triad, self._receipt_for(triad), binding=None, smt_verified=True),
            EvidenceGrade.EMPIRICAL)

    def test_J2_a_bound_caller_assertion_earns_grade_A(self):
        """Positive control: the caller supplies the binding it is entitled to make."""
        from warrant_kernel import EvidenceGrade
        triad = self._triad()
        self.assertEqual(
            self._grade(triad, self._receipt_for(triad), self._binding(triad)),
            EvidenceGrade.AXIOMATIC)

    def test_J3_a_retargeted_receipt_cannot_move_credit(self):
        """dataclasses.replace on the label is not an assertion by anyone."""
        import dataclasses
        import dialectic_kernel as dk
        from warrant_kernel import EvidenceGrade
        a = self._triad()
        b = self._triad(thesis_candidate_digest="ef" * 32,
                        settled_theorem="A different theorem")
        receipt_a = self._receipt_for(a)
        transplanted = dataclasses.replace(
            receipt_a, subject_digest=dk.triad_subject_digest(b))
        # The caller's binding stays fixed on A throughout.
        self.assertEqual(self._grade(b, transplanted, self._binding(a)),
                         EvidenceGrade.EMPIRICAL)
        # And even a caller binding for B does not help without a formula for B:
        # here it does, because the caller asserted this same CNF for B, which is
        # exactly the assertion the boundary now makes visible and attributable.
        self.assertEqual(self._grade(b, transplanted, self._binding(b)),
                         EvidenceGrade.AXIOMATIC)

    def test_J4_receipt_formula_and_proof_may_all_change_the_binding_still_holds(self):
        """The review's negative control: attack the report, keep the binding."""
        from warrant_kernel import EvidenceGrade
        triad = self._triad()
        binding = self._binding(triad)
        other_formula = [[2], [-2]]
        other_proof = dag(inp(1, [2]), inp(2, [-2]), res(3, [], [1, 2], 2))
        other_receipt = self._receipt_for(triad, formula=other_formula, proof=other_proof)
        self.assertIsNotNone(other_receipt)      # it is a genuine refutation
        self.assertEqual(
            self._grade(triad, other_receipt, binding, proof=other_proof),
            EvidenceGrade.EMPIRICAL,
            "another contradiction must not count merely because it verifies")

    def test_J5_changing_the_guard_or_the_delta_invalidates_old_credit(self):
        import dataclasses
        import dialectic_kernel as dk
        from warrant_kernel import EvidenceGrade
        a = self._triad()
        binding, receipt = self._binding(a), self._receipt_for(a)
        self.assertEqual(self._grade(a, receipt, binding), EvidenceGrade.AXIOMATIC)
        for label, changed in (
            ("guard", dataclasses.replace(a, precondition=dk.PreconditionGuard(
                "new-guard", ("other",), ("old",), "false"))),
            ("delta", dataclasses.replace(a, synthesis_delta=dk.ContextDelta(
                80, 10000, 9920, 125.0, 0.01))),
            ("status", dataclasses.replace(
                a, status=dk.DialecticalStatus.RESOURCE_BOUNDED)),
            ("refusal", dataclasses.replace(a, antithesis_refusal_id="99" * 32)),
        ):
            with self.subTest(operand=label):
                self.assertEqual(self._grade(changed, receipt, binding),
                                 EvidenceGrade.EMPIRICAL)

    def test_J6_unchanged_operands_still_work(self):
        """A digest that changes for everything would be no better than one that never does."""
        import dataclasses
        import dialectic_kernel as dk
        from warrant_kernel import EvidenceGrade
        a = self._triad()
        identical = dataclasses.replace(a)
        self.assertEqual(dk.triad_subject_digest(identical), dk.triad_subject_digest(a))
        self.assertEqual(self._grade(identical, self._receipt_for(a), self._binding(a)),
                         EvidenceGrade.AXIOMATIC)

    def test_J7_a_set_flag_and_an_invalid_proof_earn_nothing(self):
        from warrant_kernel import EvidenceGrade
        triad = self._triad()
        forged = sm.RefutationReceipt(
            subject_digest=self._binding(triad).subject_digest,
            formula=(frozenset([1]), frozenset([-1])),
            proof_digest=sm.proof_dag_digest(self.invalid),
            checked_steps=99)
        self.assertEqual(
            self._grade(triad, forged, self._binding(triad), proof=self.invalid,
                        smt_verified=True),
            EvidenceGrade.EMPIRICAL)

    def test_J8_the_binding_is_never_derived_from_the_report(self):
        """A structural guard: the decision function takes the binding as an argument."""
        import dialectic_kernel as dk
        import inspect
        sig = inspect.signature(dk.evaluate_formal_credit)
        self.assertEqual(list(sig.parameters), ["report", "binding"])
        decision = dk.evaluate_formal_credit(
            self._report(self.real, receipt=self._receipt_for(self._triad())), None)
        self.assertFalse(decision.granted)
        self.assertEqual(decision.reason, "NO_CALLER_BINDING")


class ProducerBindingTest(unittest.TestCase):
    """The producer does not invent the formula it then checks against."""

    def _orchestrator(self, proof):
        import dialectic_kernel as dk
        from types import SimpleNamespace as NS
        from unittest.mock import Mock
        from scoped_admission import RefusalReason, RetestOutcome
        refusal = NS(record_id="ab" * 32, candidate_digest="cd" * 32,
                     evaluator_digest="ef" * 32, requirement_digest="01" * 32,
                     context={"budget_steps": 80}, outcome_type=RefusalReason.RESOURCE_LIMIT)
        registry = NS(
            refusals={refusal.record_id: refusal},
            execute_retest=Mock(return_value=NS(outcome=RetestOutcome.SUCCESS, proof_dag=proof)),
            grant_scoped_admission=Mock(return_value=NS(admission_id="02" * 32)))
        orch = dk.DialecticalOrchestrator(registry)
        orch.explorer = NS(explore_boundary=lambda _: (
            dk.DialecticalStatus.SYNTHESIS_ACHIEVED,
            dk.ContextDelta(80, 140, 60, 1.75, 0.95), "probe"))
        return orch, refusal

    def test_I1_without_a_supplied_formula_there_is_no_credit(self):
        """A contradiction the proof selected for itself is not the theorem asked about."""
        real = dag(inp(1, [1]), inp(2, [-1]), res(3, [], [1, 2], 1))
        orch, refusal = self._orchestrator(real)
        report = orch.discover_and_promote(refusal.record_id, b"unrelated candidate", lambda *a: None)
        self.assertFalse(report.smt_verified)
        self.assertIsNone(report.refutation_receipt)
        self.assertEqual(report.smt_refutation_check, "MISSING_FORMULA_BINDING")

    def test_I2_a_supplied_formula_is_the_one_checked(self):
        """And the receipt it issues is bound to this triad, not to the proof."""
        import dialectic_kernel as dk
        real = dag(inp(1, [1]), inp(2, [-1]), res(3, [], [1, 2], 1))
        orch, refusal = self._orchestrator(real)
        report = orch.discover_and_promote(
            refusal.record_id, b"candidate", lambda *a: None, formula_clauses=[[1], [-1]])
        self.assertTrue(report.smt_verified)
        self.assertIsNotNone(report.refutation_receipt)
        self.assertEqual(report.refutation_receipt.subject_digest,
                         dk.triad_subject_digest(report.triad))
        self.assertEqual(report.refutation_receipt.formula_clauses(), [[1], [-1]])

    def test_I3_a_supplied_formula_that_is_not_refuted_earns_nothing(self):
        real = dag(inp(1, [1]), inp(2, [-1]), res(3, [], [1, 2], 1))
        orch, refusal = self._orchestrator(real)
        report = orch.discover_and_promote(
            refusal.record_id, b"candidate", lambda *a: None, formula_clauses=[[1]])
        self.assertFalse(report.smt_verified)
        self.assertIsNone(report.refutation_receipt)
        self.assertEqual(report.smt_refutation_check, RefutationStatus.INVALID.value)


if __name__ == "__main__":
    unittest.main(verbosity=2)
