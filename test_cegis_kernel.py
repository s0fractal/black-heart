#!/usr/bin/env python3
# coding: utf-8
"""
test_cegis_kernel.py — Rigorous Test Suite for Counterexample-Guided Inductive Synthesis (CEGIS).
Part of Project Black-Heart (%🖤). Engine #30.
"""

import os
import sys
import tempfile
import subprocess
import unittest

import glyph
from glyph import K, I, S, parse, evaluate, tree_size, App, Comb, Var
import smt_kernel
from smt_kernel import check_proof_dag_structure
import cegis_kernel
from cegis_kernel import (
    Example, SynthesisStatus, CertifiedSynthesisResult,
    ObservationalEquivalence, BottomUpSynthesizer, CEGISLoop,
    superoptimize_combinator, generate_cegis_pdf, append_cegis_hud,
    parse_term, _clean_latin1
)
from controlled_forgetting import (
    EpistemicTombstoneRegistry, RetirementRecord, RetirementMode
)


class TestCEGISKernel(unittest.TestCase):
    """Rigorous unit and integration tests for Engine #30."""

    def test_01_observational_equivalence_pruning(self):
        """Verify observational equivalence caching and signature pruning."""
        oe = ObservationalEquivalence()
        t1 = parse("S K K")
        t2 = parse("I")
        sig = ("a", "b", "c")

        # First term with signature
        is_dup1 = oe.is_equivalent(t1, sig)
        self.assertFalse(is_dup1)

        # Second term with same signature must be detected as duplicate
        is_dup2 = oe.is_equivalent(t2, sig)
        self.assertTrue(is_dup2)

        # After clearing, signature is fresh again
        oe.clear()
        self.assertFalse(oe.is_equivalent(t2, sig))

    def test_02_bottom_up_inductive_synthesis_base(self):
        """Test inductive synthesis satisfying initial finite examples."""
        synth = BottomUpSynthesizer(primitives=[K, I, S], variables=[])
        examples = [
            Example(inputs=("a",), expected_output="a"),
            Example(inputs=("b",), expected_output="b")
        ]
        candidate = synth.synthesize_inductive(examples, max_size=5)
        self.assertIsNotNone(candidate)
        self.assertEqual(str(candidate), str(I))
        self.assertGreater(synth.explored_count, 0)

    def test_03_cegis_loop_identity(self):
        """Synthesize the identity combinator; the SMT proof object is shape-checked only."""
        cegis = CEGISLoop(verifier_domain=["a", "b", "c"])
        result = cegis.synthesize(lambda inp: inp[0], input_arity=1)

        self.assertEqual(result.status, SynthesisStatus.PROVED_CORRECT)
        self.assertIsNotNone(result.program)
        self.assertEqual(result.program_str, str(I))
        self.assertIsNotNone(result.proof_dag)
        self.assertTrue(check_proof_dag_structure(result.proof_dag))  # shape only; not a checked refutation
        self.assertGreater(result.smt_verifications, 0)

    def test_04_cegis_loop_identity_skk(self):
        """Synthesize identity S K K from scratch when I is omitted from primitives."""
        cegis = CEGISLoop(verifier_domain=["a", "b", "c"])
        result = cegis.synthesize(
            lambda inp: inp[0],
            input_arity=1,
            primitives=[K, S],
            max_ast_size=6
        )

        self.assertEqual(result.status, SynthesisStatus.PROVED_CORRECT)
        self.assertIsNotNone(result.program)
        # S K K is App(App(S, K), K)
        self.assertEqual(result.program, App(App(S, K), K))
        self.assertTrue(check_proof_dag_structure(result.proof_dag))  # shape only; not a checked refutation
        self.assertGreater(result.candidates_pruned_oe, 0)

    def test_05_cegis_loop_constant_selectors(self):
        """Synthesize binary selectors: K (first argument) and K I (second argument)."""
        cegis = CEGISLoop(verifier_domain=["a", "b"])

        # 1. First argument projection: (x, y) -> x
        res_k = cegis.synthesize(lambda inp: inp[0], input_arity=2, primitives=[K, I, S], max_ast_size=5)
        self.assertEqual(res_k.status, SynthesisStatus.PROVED_CORRECT)
        self.assertEqual(res_k.program, K)

        # 2. Second argument projection: (x, y) -> y
        res_ki = cegis.synthesize(lambda inp: inp[1], input_arity=2, primitives=[K, I, S], max_ast_size=5)
        self.assertEqual(res_ki.status, SynthesisStatus.PROVED_CORRECT)
        self.assertEqual(res_ki.program, App(K, I))

    def test_06_cegis_multi_iteration_refinement(self):
        """Test multi-iteration counterexample generation and feedback convergence."""
        cegis = CEGISLoop(verifier_domain=["a", "b"])
        # Target: constant function returning 'a' on all inputs
        # Initial seed only has (a) -> a
        init_ex = [Example(inputs=("a",), expected_output="a")]
        result = cegis.synthesize(
            specification_fn=lambda inp: "a",
            input_arity=1,
            initial_examples=init_ex,
            primitives=[K, I, S, parse("a")],
            max_ast_size=5
        )

        self.assertEqual(result.status, SynthesisStatus.PROVED_CORRECT)
        # SMT Verifier must have found counterexample (b) -> a in iteration 1
        self.assertGreaterEqual(result.iterations, 2)
        self.assertEqual(len(result.counterexamples), 2)
        self.assertEqual(result.program, App(K, Var("a")))

    def test_07_combinator_superoptimizer(self):
        """Superoptimize bloated combinator S K K into minimal normal form I.

        The accompanying SMT proof object is shape-checked only; whether it
        carries any formal credit is a separate question.
        """
        res_opt = superoptimize_combinator("S K K")
        self.assertEqual(res_opt.status, SynthesisStatus.PROVED_CORRECT)
        self.assertEqual(res_opt.program, I)
        self.assertAlmostEqual(res_opt.ast_size_reduction, 0.8, places=2)
        self.assertTrue(check_proof_dag_structure(res_opt.proof_dag))  # shape only

        # Also test Python constructor string format
        res_opt2 = superoptimize_combinator("App(App(Comb('🌿'), Comb('🖤')), Comb('🖤'))")
        self.assertEqual(res_opt2.status, SynthesisStatus.PROVED_CORRECT)
        self.assertEqual(res_opt2.program, I)

    def test_08_epistemic_tombstone_quarantine(self):
        """Ensure synthesizer avoids quarantined tombstone alleles in active candidate ASTs."""
        registry = EpistemicTombstoneRegistry()
        tomb = RetirementRecord(
            record_id="tomb_001",
            target_id=str(I),
            target_digest="dummy_digest",
            mode=RetirementMode.QUARANTINED,
            loss_declaration="I combinator quarantined for testing sector",
            negative_space_coverage=0.4,
            atp_gas_recovered=15,
            author_pk_hex="0" * 64,
            signature_hex="0" * 128
        )
        registry.tombstones[tomb.target_id] = tomb

        cegis = CEGISLoop(verifier_domain=["a", "b"], tombstone_registry=registry)
        # Even with I in primitives, synthesizer must skip I and find S K K
        res = cegis.synthesize(lambda inp: inp[0], input_arity=1, primitives=[K, I, S], max_ast_size=6)
        self.assertEqual(res.status, SynthesisStatus.PROVED_CORRECT)
        self.assertNotIn(str(I), res.program_str)
        self.assertEqual(res.program, App(App(S, K), K))

    def test_09_resource_bounds_and_unknown(self):
        """Ensure bounded fuel and depth gracefully terminate without hanging."""
        cegis = CEGISLoop(
            verifier_domain=["a", "b", "c"],
            max_iterations=2,
            candidate_fuel_budget=10
        )
        # Impossible to synthesize complex behavior within 10 candidate explorations
        res = cegis.synthesize(
            lambda inp: f"{inp[0]}_{inp[0]}",
            input_arity=1,
            primitives=[K, I],
            max_ast_size=2
        )
        self.assertEqual(res.status, SynthesisStatus.RESOURCE_EXHAUSTED)
        self.assertIsNone(res.program)
        self.assertLess(res.elapsed_sec, 2.0)

    def test_10_iso32000_polyglot_pdf_and_append(self):
        """Verify ISO 32000 PDF generation, append-only physicality, and standalone Python execution."""
        res = superoptimize_combinator("S K K")
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            pdf1 = f.name
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            pdf2 = f.name

        try:
            generate_cegis_pdf(res, pdf1)
            self.assertTrue(os.path.exists(pdf1))
            self.assertGreater(os.path.getsize(pdf1), 1000)

            # 1. Standalone Python polyglot execution
            proc = subprocess.run(
                [sys.executable, pdf1],
                capture_output=True,
                text=True,
                timeout=10
            )
            self.assertEqual(proc.returncode, 0)
            self.assertIn("ALL INVARIANTS SATISFIED", proc.stdout)
            self.assertIn("SHA-256:", proc.stdout)
            self.assertIn("SMT Proof Verified:  True", proc.stdout)

            # 2. Append-only physicality
            with open(pdf1, "rb") as f:
                before = f.read()

            append_cegis_hud(pdf1, res, pdf2)
            with open(pdf2, "rb") as f:
                after = f.read()

            self.assertTrue(after.startswith(before))
            self.assertGreater(len(after), len(before))
        finally:
            if os.path.exists(pdf1):
                os.remove(pdf1)
            if os.path.exists(pdf2):
                os.remove(pdf2)


if __name__ == "__main__":
    unittest.main()
