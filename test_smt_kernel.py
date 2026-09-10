#!/usr/bin/env python3
# coding: utf-8
"""
test_smt_kernel.py — Rigorous Test Suite for Sovereign SMT Kernel & First-Order DPLL(T) Verifier.
Part of Project Black-Heart (%🖤). Engine #29.
"""

import os
import sys
import tempfile
import subprocess
import unittest

import smt_kernel
from smt_kernel import (
    Sort, BOOL_SORT, DEFAULT_SORT,
    SMTTerm, Const, BoolConst, App, Eq, Distinct, Not, And, Or, Implies, Xor, Ite,
    SMTLIBParser, TseitinTransformer, CDCLSolver, EUFTheorySolver,
    SMTSolver, SMTStatus, SMTResult,
    verify_unsat_certificate, smt_refute_tombstone,
    generate_smt_pdf, append_smt_hud
)
from controlled_forgetting import EpistemicTombstoneRegistry, RetirementRecord, RetirementMode


class TestSMTKernel(unittest.TestCase):
    """Rigorous unit and integration tests for Engine #29."""

    def test_01_smtlib_parser_declarations_and_terms(self):
        """Test parsing SMT-LIB 2 declarations, terms, and nested booleans."""
        script = """
        (set-logic QF_UF)
        (declare-sort CustomSort 0)
        (declare-const x CustomSort)
        (declare-const y CustomSort)
        (declare-fun f (CustomSort) CustomSort)
        (assert (= (f x) y))
        (assert (not (= x y)))
        (assert (and true (or false (= x x))))
        (check-sat)
        """
        parser = SMTLIBParser()
        assertions = parser.parse_script(script)
        self.assertEqual(len(assertions), 3)
        self.assertIsInstance(assertions[0], Eq)
        self.assertIsInstance(assertions[1], Not)
        self.assertIsInstance(assertions[2], And)
        self.assertEqual(parser.sorts["CustomSort"].name, "CustomSort")

    def test_02_cdcl_pure_sat_and_unsat(self):
        """Test propositional CDCL SAT solver with 2WL and 1-UIP conflict analysis."""
        # 1. Satisfiable: (1 or 2) and (-1 or 2)
        sat_solver = CDCLSolver(num_vars=2)
        sat_solver.add_clause([1, 2])
        sat_solver.add_clause([-1, 2])
        # Decision
        confl = sat_solver.propagate()
        self.assertIsNone(confl)
        b = sat_solver.pick_branch_lit()
        self.assertIsNotNone(b)
        sat_solver.new_decision_level()
        sat_solver._enqueue(b)
        confl = sat_solver.propagate()
        self.assertIsNone(confl)

        # 2. Unsatisfiable: 4 clauses over 2 vars
        unsat_solver = CDCLSolver(num_vars=2)
        unsat_solver.add_clause([1, 2])
        unsat_solver.add_clause([1, -2])
        unsat_solver.add_clause([-1, 2])
        unsat_solver.add_clause([-1, -2])

        is_unsat = False
        step_budget = 500
        while step_budget > 0:
            step_budget -= 1
            confl = unsat_solver.propagate()
            if confl is not None:
                if unsat_solver.curr_level == 0:
                    is_unsat = True
                    break
                learned, backjump_lvl, pivots = unsat_solver.analyze_conflict(confl)
                unsat_solver.backjump(backjump_lvl)
                unsat_solver.add_clause(learned, rule="learned")
                if learned:
                    unsat_solver._enqueue(learned[0], reason=len(unsat_solver.clauses) - 1)
                continue
            b = unsat_solver.pick_branch_lit()
            if b is None:
                break
            unsat_solver.new_decision_level()
            unsat_solver._enqueue(b)

        self.assertTrue(is_unsat, "All 4 combinations of 2 variables must be UNSAT")

    def test_03_tseitin_cnf_transformation(self):
        """Test Tseitin transformation of nested boolean formulas into equisatisfiable CNF."""
        transformer = TseitinTransformer()
        a = Const("a", BOOL_SORT)
        b = Const("b", BOOL_SORT)
        c = Const("c", BOOL_SORT)
        # formula: (a and b) => c
        formula = Implies(And((a, b)), c)
        top_lit = transformer.transform(formula)
        transformer.add_clause([top_lit])

        self.assertTrue(len(transformer.clauses) >= 4)
        # Solve with CDCL solver
        solver = CDCLSolver(transformer.next_var)
        for cl in transformer.clauses:
            solver.add_clause(cl)
        # Should be satisfiable (e.g. a=False, b=False, c=False => True)
        sat = SMTSolver()
        res = sat.solve_assertions([formula])
        self.assertEqual(res.status, SMTStatus.SAT)

    def test_04_euf_congruence_propagation(self):
        """Test backtrackable T_EUF theory solver congruence closure and transitivity."""
        var_to_atom = {}
        euf = EUFTheorySolver(var_to_atom)

        x = Const("x")
        y = Const("y")
        z = Const("z")
        fx = App("f", (x,))
        fy = App("f", (y,))

        # x = y
        confl = euf.assert_equality(x, y, lit=1, level=1)
        self.assertIsNone(confl)
        # Check congruence: find(f(x)) must equal find(f(y))
        id_fx = euf.intern_term(fx)
        id_fy = euf.intern_term(fy)
        self.assertEqual(euf.find(id_fx), euf.find(id_fy), "Congruence f(x) == f(y) must hold after x == y")

        # Assert disequality f(x) != f(y) => immediate conflict
        confl2 = euf.assert_disequality(fx, fy, lit=-2, level=1)
        self.assertIsNotNone(confl2, "Disequality between congruent terms must trigger theory conflict")
        self.assertIn(-1, confl2, "Theory lemma must cite asserted equality literal x=y")

        # Test backtracking
        euf.backtrack_to_level(0)
        id_x = euf.intern_term(x)
        id_y = euf.intern_term(y)
        self.assertNotEqual(euf.find(id_x), euf.find(id_y), "Backtracking to level 0 must undo unions")

    def test_05_dpllt_integration_classic_euf_unsat(self):
        """Test DPLL(T) on classic EUF UNSAT: x = y and y = z and f(x) != f(z)."""
        script = """
        (set-logic QF_UF)
        (declare-sort U 0)
        (declare-const x U)
        (declare-const y U)
        (declare-const z U)
        (declare-fun f (U) U)
        (assert (= x y))
        (assert (= y z))
        (assert (not (= (f x) (f z))))
        (check-sat)
        """
        solver = SMTSolver()
        res = solver.solve_smt2(script)
        self.assertEqual(res.status, SMTStatus.UNSAT)
        self.assertIsNotNone(res.proof_dag)
        self.assertTrue(verify_unsat_certificate(res.proof_dag))

    def test_06_dpllt_functional_cycle_unsat(self):
        """Test DPLL(T) on f^3(a) = a and f^5(a) = a and f(a) != a (UNSAT)."""
        script = """
        (set-logic QF_UF)
        (declare-sort U 0)
        (declare-const a U)
        (declare-fun f (U) U)
        (assert (= (f (f (f a))) a))
        (assert (= (f (f (f (f (f a))))) a))
        (assert (not (= (f a) a)))
        (check-sat)
        """
        solver = SMTSolver()
        res = solver.solve_smt2(script)
        self.assertEqual(res.status, SMTStatus.UNSAT)
        self.assertTrue(verify_unsat_certificate(res.proof_dag))

    def test_07_dpllt_disjunctive_reasoning_unsat(self):
        """Test DPLL(T) with disjunction: ((x = y) or (x = z)) and f(x) != f(y) and f(x) != f(z)."""
        script = """
        (set-logic QF_UF)
        (declare-sort U 0)
        (declare-const x U)
        (declare-const y U)
        (declare-const z U)
        (declare-fun f (U) U)
        (assert (or (= x y) (= x z)))
        (assert (not (= (f x) (f y))))
        (assert (not (= (f x) (f z))))
        (check-sat)
        """
        solver = SMTSolver()
        res = solver.solve_smt2(script)
        self.assertEqual(res.status, SMTStatus.UNSAT)

    def test_08_dpllt_satisfiable_finite_model(self):
        """Test DPLL(T) finding a finite model for satisfiable formula."""
        script = """
        (set-logic QF_UF)
        (declare-sort U 0)
        (declare-const a U)
        (declare-const b U)
        (declare-fun f (U) U)
        (assert (= (f a) b))
        (assert (not (= a b)))
        (check-sat)
        """
        solver = SMTSolver()
        res = solver.solve_smt2(script)
        self.assertEqual(res.status, SMTStatus.SAT)
        self.assertIsNotNone(res.model)
        self.assertIn("eclasses", res.model)

    def test_09_epistemic_tombstone_refutation(self):
        """Test epistemic tombstone quarantine integration."""
        registry = EpistemicTombstoneRegistry()
        tomb = RetirementRecord(
            record_id="tomb_001",
            target_id="poison_comb_001",
            target_digest="sha256_deadbeef",
            mode=RetirementMode.QUARANTINED,
            loss_declaration="Quarantined toxic combinator causing divergence.",
            negative_space_coverage=0.45,
            atp_gas_recovered=200,
            author_pk_hex="00" * 32,
            signature_hex="00" * 64
        )
        registry.tombstones[tomb.record_id] = tomb

        # Candidate formula that entails the poisoned tombstone
        toxic_formula = """
        (declare-const comb_poison_comb_00 U)
        (declare-const comb_poison U)
        (assert (= comb_poison_comb_00 comb_poison))
        """
        report = smt_refute_tombstone(toxic_formula, registry)
        self.assertFalse(report.is_safe)
        self.assertEqual(report.verdict, "QUARANTINED_EPISTEMIC_VIOLATION")

    def test_10_iso32000_polyglot_pdf_and_standalone_audit(self):
        """Test generating ISO 32000 polyglot PDF and executing Latin-1 audit runner."""
        script = """
        (set-logic QF_UF)
        (declare-sort U 0)
        (declare-const x U)
        (declare-const y U)
        (assert (= x y))
        (assert (not (= x y)))
        (check-sat)
        """
        solver = SMTSolver()
        res = solver.solve_smt2(script)
        self.assertEqual(res.status, SMTStatus.UNSAT)

        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "smt_proof.pdf")
            generate_smt_pdf(res, pdf_path, title="Unit Test SMT Refutation")

            # Verify PDF physicality
            with open(pdf_path, "rb") as f:
                content = f.read()
            self.assertIn(b"%PDF-1.7", content[:500])
            self.assertIn(b"%%EOF", content)

            # Test standalone Python execution of the polyglot PDF
            cmd = [sys.executable, pdf_path]
            proc = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=10)
            self.assertIn("SOVEREIGN SMT DPLL(T) THEOREM VERIFIER", proc.stdout)
            self.assertIn("SMT MANIFEST AUDIT COMPLETE", proc.stdout)
            # The document states which question was answered. The runner reads
            # back a manifest; it does not re-derive the proof, so it must not
            # report the refutation as checked when it was not.
            self.assertIn("Proof DAG structure:", proc.stdout)
            self.assertIn("Refutation check:", proc.stdout)
            self.assertNotIn("ALL INVARIANTS SATISFIED", proc.stdout)

            # Test append_smt_hud physicality: after.startswith(before)
            appended_path = os.path.join(tmpdir, "smt_appended.pdf")
            append_smt_hud(pdf_path, res, appended_path)
            with open(appended_path, "rb") as f:
                appended_bytes = f.read()
            self.assertTrue(appended_bytes.startswith(content))


if __name__ == "__main__":
    unittest.main()
