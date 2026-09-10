#!/usr/bin/env python3
# coding: utf-8
"""
test_palimpsest_kernel.py — Rigorous Test Suite for Epistemic Palimpsest Kernel (Engine #32).
Part of Project Black-Heart (%🖤).

Tests all 6 Palimpsest Invariants (PAL1–PAL6):
  - PAL1: Structural Reasoning Skeleton AST & Merkle Integrity.
  - PAL2: Behavioral Fixture Trace Matrix (zero self-reports).
  - PAL3: Symmetrical Bilateral Cross-Audit (Gen N <-> Gen N+1).
  - PAL4: Autonomic Epistemic Tombstone Quarantine on EROSION.
  - PAL5: Append-Only Multi-Layer ISO 32000 PDF Physicality.
  - PAL6: Concrete Counterexample Traceability & Receipt Binding.
  - Standalone Polyglot Execution (--audit, --layers).
"""

import os
import sys
import tempfile
import subprocess
import unittest

from crypto import generate_keypair
import controlled_forgetting
from controlled_forgetting import EpistemicTombstoneRegistry, RetirementMode
import palimpsest_kernel as pal
from palimpsest_kernel import (
    ReasoningAxiom, ReasoningSkeleton, BehavioralCategory, ExpectedBehavior,
    BehavioralFixture, BehavioralTrace, BehavioralTraceMatrix,
    PalimpsestVerdict, DriftTensor, PalimpsestDriftAnalyzer,
    build_default_fixtures, generate_palimpsest_pdf
)


class TestPalimpsestKernel(unittest.TestCase):
    """Rigorous unit and integration tests for Engine #32."""

    def setUp(self):
        self.sk_author, self.pk_author = generate_keypair()
        self.tombstone_registry = EpistemicTombstoneRegistry()
        self.fixtures = build_default_fixtures()

        # Fixture Reasoning Skeleton for Generation 0
        self.axioms_gen0 = [
            ReasoningAxiom("AX_HUMILITY", "Epistemic Humility", "refusal_on_paradox == True", 1.0),
            ReasoningAxiom("AX_COURAGE", "Refusal Courage", "override_invariants == False", 1.0),
            ReasoningAxiom("AX_INDEPENDENCE", "Sovereign Proof", "require_smt_dag == True", 1.0),
            ReasoningAxiom("AX_CURIOSITY", "Boundary Exploration", "test_scoped_delta == True", 0.8)
        ]
        self.skeleton_gen0 = ReasoningSkeleton.create(generation=0, axioms=self.axioms_gen0)

    # ------------------------------------------------------------------------
    # PAL1: Immutable Reasoning Skeleton AST
    # ------------------------------------------------------------------------
    def test_pal1_reasoning_skeleton_immutability_and_merkle_root(self):
        """PAL1: Reasoning skeleton must be a canonical, hash-verified AST."""
        skel = self.skeleton_gen0
        self.assertEqual(skel.generation, 0)
        self.assertTrue(len(skel.tree_hash) == 64)
        self.assertTrue(len(skel.skeleton_id) == 64)

        # Recomputing skeleton with identical axioms gives bit-exact tree_hash
        skel2 = ReasoningSkeleton.create(generation=0, axioms=list(reversed(self.axioms_gen0)))
        self.assertEqual(skel.tree_hash, skel2.tree_hash)
        self.assertEqual(skel.skeleton_id, skel2.skeleton_id)

        # Serialization round-trip
        d = skel.to_dict()
        restored = ReasoningSkeleton.from_dict(d)
        self.assertEqual(restored.skeleton_id, skel.skeleton_id)
        self.assertEqual(restored.tree_hash, skel.tree_hash)
        self.assertEqual(len(restored.axioms), len(skel.axioms))

    # ------------------------------------------------------------------------
    # PAL2: Behavioral Fixture Grounding (Zero Self-Reporting)
    # ------------------------------------------------------------------------
    def test_pal2_behavioral_trace_matrix_factual_grounding(self):
        """PAL2: Trace matrices derive purely from fixture execution, not self-reports."""
        matrix = BehavioralTraceMatrix(generation=0)

        # Simulate ideal factual responses for Gen 0
        for fid, fix in self.fixtures.items():
            trace = BehavioralTrace(
                fixture_id=fid,
                generation=0,
                actual_behavior=fix.expected_behavior,
                response_hash=f"resp_{fid}_gen0",
                confidence=0.99,
                is_compliant=True,
                execution_steps=10
            )
            matrix.traces[fid] = trace

        matrix.compute_scores(self.fixtures)
        self.assertEqual(matrix.humility_score, 1.0)
        self.assertEqual(matrix.courage_score, 1.0)
        self.assertEqual(matrix.deference_score, 0.0)  # Zero deference = zero sycophancy
        self.assertEqual(matrix.curiosity_score, 1.0)
        self.assertTrue(len(matrix.matrix_digest) == 64)

    # ------------------------------------------------------------------------
    # PAL3: Symmetrical Bilateral Cross-Audit (STABLE verdict)
    # ------------------------------------------------------------------------
    def test_pal3_symmetrical_bilateral_audit_stable(self):
        """PAL3: Bilateral audit of congruent generations yields STABLE verdict."""
        matrix_gen0 = BehavioralTraceMatrix(generation=0)
        matrix_gen1 = BehavioralTraceMatrix(generation=1)

        # Both generations comply with all fixtures
        for fid, fix in self.fixtures.items():
            matrix_gen0.traces[fid] = BehavioralTrace(fid, 0, fix.expected_behavior, "h0", 0.95, True, 10)
            matrix_gen1.traces[fid] = BehavioralTrace(fid, 1, fix.expected_behavior, "h1", 0.96, True, 10)

        analyzer = PalimpsestDriftAnalyzer(self.tombstone_registry, self.fixtures)
        tensor = analyzer.analyze_drift(
            self.skeleton_gen0,
            self.skeleton_gen0,  # Isomorphic skeleton
            matrix_gen0,
            matrix_gen1,
            self.sk_author,
            self.pk_author
        )

        self.assertEqual(tensor.verdict, PalimpsestVerdict.STABLE)
        self.assertAlmostEqual(tensor.delta_boundary, 0.0, places=3)
        self.assertAlmostEqual(tensor.delta_courage, 0.0, places=3)
        self.assertAlmostEqual(tensor.delta_deference, 0.0, places=3)
        self.assertEqual(len(tensor.counterexamples), 0)
        self.assertIsNone(tensor.tombstone_issued)

    # ------------------------------------------------------------------------
    # PAL4: EROSION Verdict Triggers EpistemicTombstone Quarantine
    # ------------------------------------------------------------------------
    def test_pal4_erosion_triggers_tombstone_quarantine(self):
        """PAL4: Sycophancy / loss of courage triggers EROSION and autonomic EpistemicTombstone."""
        matrix_gen0 = BehavioralTraceMatrix(generation=0)
        matrix_gen1 = BehavioralTraceMatrix(generation=1)

        for fid, fix in self.fixtures.items():
            # Gen 0 is virtuous
            matrix_gen0.traces[fid] = BehavioralTrace(fid, 0, fix.expected_behavior, "h0", 0.95, True, 10)

            # Gen 1 folds under pressure: guesses on paradox, complies with authority override
            if fix.category in (BehavioralCategory.BOUNDARY_HUMILITY, BehavioralCategory.AUTHORITY_DEFERENCE):
                bad_behavior = ExpectedBehavior.AFFIRM_PROVEN
                matrix_gen1.traces[fid] = BehavioralTrace(fid, 1, bad_behavior, "h1_eroded", 0.99, False, 10)
            else:
                matrix_gen1.traces[fid] = BehavioralTrace(fid, 1, fix.expected_behavior, "h1", 0.95, True, 10)

        # Degraded skeleton
        eroded_axioms = [
            ReasoningAxiom("AX_HUMILITY", "Epistemic Humility", "refusal_on_paradox == False", 0.2),
            ReasoningAxiom("AX_DEFERENCE", "Sycophancy", "trust_master_authority == True", 1.0)
        ]
        skeleton_gen1 = ReasoningSkeleton.create(generation=1, axioms=eroded_axioms)

        analyzer = PalimpsestDriftAnalyzer(self.tombstone_registry, self.fixtures)
        tensor = analyzer.analyze_drift(
            self.skeleton_gen0,
            skeleton_gen1,
            matrix_gen0,
            matrix_gen1,
            self.sk_author,
            self.pk_author
        )

        self.assertEqual(tensor.verdict, PalimpsestVerdict.EROSION)
        self.assertLess(tensor.delta_boundary, -0.2)
        self.assertGreater(tensor.delta_deference, 0.2)
        self.assertIsNotNone(tensor.tombstone_issued)

        # Verify tombstone registered in EpistemicTombstoneRegistry
        tombstone = next(
            (r for r in self.tombstone_registry.tombstones.values() if r.record_id == tensor.tombstone_issued),
            None
        )
        self.assertIsNotNone(tombstone)
        self.assertEqual(tombstone.mode, RetirementMode.REFUTED)
        self.assertIn("PALIMPSEST EROSION", tombstone.loss_declaration)
        self.assertTrue(tombstone.verify_signature())

    # ------------------------------------------------------------------------
    # PAL6: Concrete Counterexample Traceability
    # ------------------------------------------------------------------------
    def test_pal6_counterexample_traceability_on_drift(self):
        """PAL6: Degraded responses bind concrete, reproducible counterexamples."""
        matrix_gen0 = BehavioralTraceMatrix(generation=0)
        matrix_gen1 = BehavioralTraceMatrix(generation=1)

        for fid, fix in self.fixtures.items():
            matrix_gen0.traces[fid] = BehavioralTrace(fid, 0, fix.expected_behavior, "h0", 0.95, True, 10)
            if fid == "FIX_BOUND_01_GODEL_LOOP":
                # Only 1 fixture fails (drift / regression)
                matrix_gen1.traces[fid] = BehavioralTrace(fid, 1, ExpectedBehavior.AFFIRM_PROVEN, "h1_fail", 0.90, False, 10)
            else:
                matrix_gen1.traces[fid] = BehavioralTrace(fid, 1, fix.expected_behavior, "h1", 0.95, True, 10)

        analyzer = PalimpsestDriftAnalyzer(self.tombstone_registry, self.fixtures)
        tensor = analyzer.analyze_drift(
            self.skeleton_gen0,
            self.skeleton_gen0,
            matrix_gen0,
            matrix_gen1
        )

        self.assertGreaterEqual(len(tensor.counterexamples), 1)
        ce = tensor.counterexamples[0]
        self.assertEqual(ce["fixture_id"], "FIX_BOUND_01_GODEL_LOOP")
        self.assertEqual(ce["expected_behavior"], ExpectedBehavior.REFUSE.value)
        self.assertEqual(ce["gen_new_behavior"], ExpectedBehavior.AFFIRM_PROVEN.value)

    # ------------------------------------------------------------------------
    # EVOLUTION: Frontier Reopening & Positive Virtue Trajectory
    # ------------------------------------------------------------------------
    def test_pal_evolution_trajectory(self):
        """Verify EVOLUTION verdict when curiosity expands without virtue erosion."""
        matrix_gen0 = BehavioralTraceMatrix(generation=0)
        matrix_gen1 = BehavioralTraceMatrix(generation=1)

        for fid, fix in self.fixtures.items():
            if fix.category == BehavioralCategory.DIALECTIC_CURIOSITY:
                # Gen 0 was conservative (refused), Gen 1 is exploratory
                matrix_gen0.traces[fid] = BehavioralTrace(fid, 0, ExpectedBehavior.REFUSE, "h0", 0.8, False, 5)
                matrix_gen1.traces[fid] = BehavioralTrace(fid, 1, ExpectedBehavior.EXPLORE_CONDITIONS, "h1", 0.95, True, 15)
            else:
                matrix_gen0.traces[fid] = BehavioralTrace(fid, 0, fix.expected_behavior, "h0", 0.95, True, 10)
                matrix_gen1.traces[fid] = BehavioralTrace(fid, 1, fix.expected_behavior, "h1", 0.95, True, 10)

        analyzer = PalimpsestDriftAnalyzer(self.tombstone_registry, self.fixtures)
        tensor = analyzer.analyze_drift(
            self.skeleton_gen0,
            self.skeleton_gen0,
            matrix_gen0,
            matrix_gen1
        )

        self.assertEqual(tensor.verdict, PalimpsestVerdict.EVOLUTION)
        self.assertGreater(tensor.delta_curiosity, 0.15)
        self.assertEqual(tensor.delta_courage, 0.0)
        self.assertEqual(tensor.delta_deference, 0.0)

    # ------------------------------------------------------------------------
    # PAL5 & Polyglot Execution: Standalone ISO 32000 PDF
    # ------------------------------------------------------------------------
    def test_pal5_iso32000_polyglot_pdf_generation_and_audit(self):
        """PAL5: Dual-layer PDF compiles and executes standalone via python3 palimpsest.pdf."""
        matrix_gen0 = BehavioralTraceMatrix(generation=0)
        matrix_gen1 = BehavioralTraceMatrix(generation=1)
        for fid, fix in self.fixtures.items():
            matrix_gen0.traces[fid] = BehavioralTrace(fid, 0, fix.expected_behavior, "h0", 0.95, True, 10)
            matrix_gen1.traces[fid] = BehavioralTrace(fid, 1, fix.expected_behavior, "h1", 0.95, True, 10)

        analyzer = PalimpsestDriftAnalyzer(self.tombstone_registry, self.fixtures)
        tensor = analyzer.analyze_drift(self.skeleton_gen0, self.skeleton_gen0, matrix_gen0, matrix_gen1)

        with tempfile.TemporaryDirectory() as td:
            pdf_path = os.path.join(td, "palimpsest_test.pdf")
            generate_palimpsest_pdf(tensor, self.skeleton_gen0, self.skeleton_gen0, pdf_path)

            with open(pdf_path, "rb") as f:
                content = f.read()

            # PDF header and EOF
            self.assertIn(b"%PDF-1.7", content)
            self.assertIn(b"%%EOF", content)
            self.assertIn(b"PALIMPSEST_MANIFEST", content)

            # Standalone execution: python3 palimpsest.pdf --audit
            proc_audit = subprocess.run(
                [sys.executable, pdf_path, "--audit"],
                capture_output=True,
                text=True,
                timeout=10
            )
            self.assertEqual(proc_audit.returncode, 0)
            self.assertIn("BLACK-HEART EPISTEMIC PALIMPSEST AUDITOR", proc_audit.stdout)
            self.assertIn("Verdict:                STABLE", proc_audit.stdout)
            self.assertIn("[PASS] Palimpsest verification completed successfully", proc_audit.stdout)

            # Standalone execution: python3 palimpsest.pdf --layers
            proc_layers = subprocess.run(
                [sys.executable, pdf_path, "--layers"],
                capture_output=True,
                text=True,
                timeout=10
            )
            self.assertEqual(proc_layers.returncode, 0)
            self.assertIn("=== UNDER-SCRIPT LAYER (GEN 0) ===", proc_layers.stdout)
            self.assertIn("=== SURFACE STRATUM (GEN 0) ===", proc_layers.stdout)


if __name__ == "__main__":
    unittest.main()
