#!/usr/bin/env python3
"""
test_metamorphosis.py — Comprehensive Unit Tests for Autonomous Form Metamorphosis.
Part of Project Black-Heart (%🖤).

Tests:
  1. AST Path Addressing & Subterm Substitution.
  2. Algebraic Rewrite Rule Soundness.
  3. Frozen Invariant Evaluator (Semantic Equivalence & ATP Deltas).
  4. Preservation of Negative Knowledge in Scientific Experiment Ledger.
  5. Successor Organism Minting & Transition Receipts.
  6. Independent Replay Auditor Fail-Closed Security (Rejection of Tampered Claims).
  7. Standalone Executable Polyglot PDF Verification.
"""

import os
import sys
import json
import tempfile
import unittest
import subprocess
from pathlib import Path

from glyph import parse, evaluate, App, Comb, Var, K, I, S, Y
from organism import create_genesis_organism, Chromosome, Organism
from metamorphosis import (
    get_subterm_at, replace_subterm_at, enumerate_subterm_addresses,
    match_and_rewrite, propose_form_metamorphoses,
    FrozenEvaluator, MutationVerdict, EvaluationReceipt,
    ExperimentLog, ExperimentRecord,
    MetamorphicTransitionReceipt, MetamorphicProvenanceError,
    contemplate_and_evolve, audit_metamorphic_transition,
    MetamorphicPolyglotCompiler, METAMORPHOSIS_MANIFEST_PREFIX
)


class TestMetamorphosisEngine(unittest.TestCase):
    """Rigorous verification suite for Program Self-Contemplation & Metamorphosis."""

    def test_ast_path_addressing_and_subterm_replacement(self):
        """Verify binary path addressing, subterm extraction, and immutable substitution."""
        # Term: (S (K I)) (K (S I))
        t = parse("🌿 (🖤 🤍) (🖤 (🌿 🤍))")
        addrs = enumerate_subterm_addresses(t)
        self.assertGreater(len(addrs), 3)

        # Root address ()
        self.assertEqual(get_subterm_at(t, ()), t)

        # Left child ('L',) -> S (K I)
        sub_l = get_subterm_at(t, ("L",))
        self.assertEqual(str(sub_l), "🌿 (🖤 🤍)")

        # Right child ('R',) -> K (S I)
        sub_r = get_subterm_at(t, ("R",))
        self.assertEqual(str(sub_r), "🖤 (🌿 🤍)")

        # Subterm at ('L', 'R') -> K I
        sub_lr = get_subterm_at(t, ("L", "R"))
        self.assertEqual(str(sub_lr), "🖤 🤍")

        # Replace ('L', 'R') with I
        t_replaced = replace_subterm_at(t, ("L", "R"), I)
        self.assertEqual(str(t_replaced), "🌿 🤍 (🖤 (🌿 🤍))")

        # Invalid address traversal raises IndexError
        with self.assertRaises(IndexError):
            get_subterm_at(I, ("L",))

    def test_algebraic_rewrite_rules_soundness(self):
        """Verify that algebraic simplifications preserve extensional equality while saving computation."""
        evaluator = FrozenEvaluator()

        # Rule 1: S (K x) (K y) -> K (x y)
        orig_1 = parse("🌿 (🖤 🌿) (🖤 🤍)")
        repl_1 = parse("🖤 (🌿 🤍)")
        receipt_1 = evaluator.evaluate_transformation(orig_1, repl_1)
        self.assertTrue(receipt_1.semantic_preserved)
        self.assertEqual(receipt_1.verdict, MutationVerdict.ACCEPTED_MORE_EFFICIENT)
        self.assertLess(receipt_1.atp_delta, 0)

        # Rule 2: S (K x) I -> x
        orig_2 = parse("🌿 (🖤 (🌿 🤍)) 🤍")
        repl_2 = parse("🌿 🤍")
        receipt_2 = evaluator.evaluate_transformation(orig_2, repl_2)
        self.assertTrue(receipt_2.semantic_preserved)
        self.assertEqual(receipt_2.verdict, MutationVerdict.ACCEPTED_MORE_EFFICIENT)
        self.assertLess(receipt_2.atp_delta, 0)

        # Rule 3: K x y -> x (closed redex)
        orig_3 = parse("🖤 (🌿 🤍) (🖤 🖤)")
        repl_3 = parse("🌿 🤍")
        receipt_3 = evaluator.evaluate_transformation(orig_3, repl_3)
        self.assertTrue(receipt_3.semantic_preserved)
        self.assertEqual(receipt_3.verdict, MutationVerdict.ACCEPTED_MORE_EFFICIENT)
        self.assertLess(receipt_3.atp_delta, 0)

    def test_frozen_evaluator_rejects_divergence_and_neutral_mutations(self):
        """Verify that FrozenEvaluator strictly discriminates semantic bugs and useless mutations."""
        evaluator = FrozenEvaluator()

        # Semantic Divergence: Swap operands of K
        orig = parse("🖤 🤍 (🌿 🤍)")  # (K I) (S I) -> I
        mutated = parse("🌿 🤍 (🖤 🤍)") # (S I) (K I) -> not equivalent!
        receipt_div = evaluator.evaluate_transformation(orig, mutated)
        self.assertFalse(receipt_div.semantic_preserved)
        self.assertEqual(receipt_div.verdict, MutationVerdict.REJECTED_SEMANTIC_MISMATCH)
        self.assertIsNotNone(receipt_div.discrepancy_input)

        # Inefficient / Neutral Mutation: replace x with (I x)
        # Adding an unnecessary identity wrapper increases ATP and size without benefit
        orig_id = parse("🌿 🤍")
        unoptimized = parse("🤍 (🌿 🤍)")
        receipt_neutral = evaluator.evaluate_transformation(orig_id, unoptimized)
        self.assertTrue(receipt_neutral.semantic_preserved)
        self.assertEqual(receipt_neutral.verdict, MutationVerdict.REJECTED_NO_EFFICIENCY_GAIN)
        self.assertGreater(receipt_neutral.atp_delta, 0)

    def test_scientific_experiment_ledger_preserves_negative_knowledge(self):
        """Crucial test: Confirm that rejected experiments are preserved as permanent empirical records."""
        org = create_genesis_organism()
        org.chromosomes.append(Chromosome(
            gene_id="GENE-OPT-01",
            gene_name="Adaptive Multiplexer",
            expression="🌿 (🖤 (🌿 🤍)) (🖤 🤍)",
            expected_normal_form="(🌿 🤍) 🤍",
            max_atp=100
        ))
        org.organism_hash = org.compute_hash()

        succ, log, receipt = contemplate_and_evolve(org)
        self.assertIsNotNone(succ)
        self.assertIsNotNone(receipt)

        # Scientific ledger must contain both accepted and rejected experiments
        accepted = log.accepted_records()
        rejected = log.rejected_records()

        self.assertGreater(len(accepted), 0)
        self.assertGreater(len(rejected), 0)
        self.assertEqual(len(log.records), len(accepted) + len(rejected))

        # Check that rejected records store the exact divergence reason
        mismatch_records = [r for r in rejected if r.verdict == MutationVerdict.REJECTED_SEMANTIC_MISMATCH]
        self.assertGreater(len(mismatch_records), 0)
        first_mismatch = mismatch_records[0]
        self.assertIn("diverged", first_mismatch.discrepancy_detail)
        self.assertNotEqual(first_mismatch.original_subterm, first_mismatch.proposed_subterm)

    def test_successor_organism_minting_and_transition_receipt(self):
        """Verify that accepted transition mints a valid, sound successor organism."""
        org = create_genesis_organism()
        org.chromosomes.append(Chromosome(
            gene_id="GENE-OPT-02",
            gene_name="Signal Compressor",
            expression="🌿 (🖤 (🌿 🤍)) 🤍",
            expected_normal_form="🌿 🤍",
            max_atp=100
        ))
        org.organism_hash = org.compute_hash()

        succ, log, receipt = contemplate_and_evolve(org)

        # Successor generation incremented
        self.assertEqual(succ.generation, org.generation + 1)
        # Successor parent points to parent hash
        self.assertEqual(succ.parent_hash, org.organism_hash)
        # Successor hash is non-empty and distinct
        self.assertNotEqual(succ.organism_hash, org.organism_hash)
        # Successor metabolism is completely sound
        viable, _ = succ.run_metabolism()
        self.assertTrue(viable)
        self.assertTrue(succ.verify())

        # Transition receipt matches claims
        self.assertEqual(receipt.parent_hash, org.organism_hash)
        self.assertEqual(receipt.successor_hash, succ.organism_hash)
        self.assertEqual(receipt.gene_id, "GENE-OPT-02")
        self.assertEqual(receipt.rule_name, "S(K x)I -> x")
        self.assertGreater(receipt.atp_saved, 0)

    def test_independent_replay_auditor_security_and_fail_closed(self):
        """Verify that audit_metamorphic_transition validates truth and fails closed on forged claims."""
        org = create_genesis_organism()
        org.chromosomes.append(Chromosome(
            gene_id="GENE-OPT-03",
            gene_name="Optimizer Target",
            expression="🌿 (🖤 (🌿 🤍)) (🖤 🤍)",
            expected_normal_form="(🌿 🤍) 🤍",
            max_atp=100
        ))
        org.organism_hash = org.compute_hash()

        succ, log, receipt = contemplate_and_evolve(org)

        # 1. Genuine transition must pass
        ok, msg = audit_metamorphic_transition(org, succ, receipt)
        self.assertTrue(ok)
        self.assertIn("TRANSITION VERIFIED", msg)

        # 2. Forged Parent Hash fails closed
        forged_parent_receipt = MetamorphicTransitionReceipt.from_dict(receipt.to_dict())
        forged_parent_receipt.parent_hash = "f" * 64
        with self.assertRaises(MetamorphicProvenanceError):
            audit_metamorphic_transition(org, succ, forged_parent_receipt)

        # 3. Forged Successor Hash fails closed
        forged_succ_receipt = MetamorphicTransitionReceipt.from_dict(receipt.to_dict())
        forged_succ_receipt.successor_hash = "0" * 64
        with self.assertRaises(MetamorphicProvenanceError):
            audit_metamorphic_transition(org, succ, forged_succ_receipt)

        # 4. Forged ATP Savings (inflated claim) fails closed
        forged_atp_receipt = MetamorphicTransitionReceipt.from_dict(receipt.to_dict())
        forged_atp_receipt.atp_saved = 99999
        with self.assertRaises(MetamorphicProvenanceError):
            audit_metamorphic_transition(org, succ, forged_atp_receipt)

        # 5. Tampered Post-Term fails closed
        tampered_succ = Organism(
            generation=succ.generation,
            parent_hash=succ.parent_hash,
            public_key_hex=succ.public_key_hex,
            secret_key_hex=succ.secret_key_hex,
            chromosomes=[
                Chromosome("GENE-OPT-03", "Optimizer Target", "🤍 🤍", "🤍", max_atp=100)
            ]
        )
        tampered_succ.organism_hash = tampered_succ.compute_hash()
        tampered_receipt = MetamorphicTransitionReceipt.from_dict(receipt.to_dict())
        tampered_receipt.successor_hash = tampered_succ.organism_hash
        tampered_receipt.post_term = "🤍 🤍"
        with self.assertRaises(MetamorphicProvenanceError):
            audit_metamorphic_transition(org, tampered_succ, tampered_receipt)

    def test_standalone_executable_polyglot_pdf(self):
        """Verify that MetamorphicPolyglotCompiler generates valid ISO 32000 PDF with executable Python runner."""
        org = create_genesis_organism()
        org.chromosomes.append(Chromosome(
            gene_id="GENE-OPT-04",
            gene_name="Signal Router",
            expression="🌿 (🖤 (🌿 🤍)) (🖤 🤍)",
            expected_normal_form="(🌿 🤍) 🤍",
            max_atp=100
        ))
        org.organism_hash = org.compute_hash()

        succ, log, receipt = contemplate_and_evolve(org)
        compiler = MetamorphicPolyglotCompiler(org, succ, receipt, log)
        pdf_bytes = compiler.compile_pdf()

        # PDF structure checks
        self.assertTrue(pdf_bytes.startswith(f"#!{sys.executable}\n".encode("latin1")))
        self.assertIn(b"%PDF-1.4", pdf_bytes)
        self.assertIn(b"%%EOF", pdf_bytes)
        self.assertIn(METAMORPHOSIS_MANIFEST_PREFIX.encode("latin1"), pdf_bytes)

        with tempfile.TemporaryDirectory() as td:
            pdf_path = os.path.join(td, "test_metamorph.pdf")
            with open(pdf_path, "wb") as f:
                f.write(pdf_bytes)

            # Test --info execution
            res_info = subprocess.run([sys.executable, pdf_path], capture_output=True, text=True, timeout=10)
            self.assertEqual(res_info.returncode, 0)
            self.assertIn("BLACK-HEART AUTONOMOUS FORM METAMORPHOSIS PASSPORT", res_info.stdout)

            # Test --experiments execution
            res_exp = subprocess.run([sys.executable, pdf_path, "--experiments"], capture_output=True, text=True, timeout=10)
            self.assertEqual(res_exp.returncode, 0)
            self.assertIn("SCIENTIFIC EXPERIMENT LEDGER", res_exp.stdout)
            self.assertIn("Total Experiments:", res_exp.stdout)

            # Test --audit execution
            res_audit = subprocess.run([sys.executable, pdf_path, "--audit"], capture_output=True, text=True, timeout=10)
            self.assertEqual(res_audit.returncode, 0)
            self.assertIn("METAMORPHIC PROVENANCE & ORACLE AUDITOR", res_audit.stdout)
            self.assertIn("TRANSITION VERIFIED", res_audit.stdout)


if __name__ == "__main__":
    unittest.main()
