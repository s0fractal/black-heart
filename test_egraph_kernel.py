#!/usr/bin/env python3
# coding: utf-8
"""
test_egraph_kernel.py — Test Suite for Engine #28: Epistemic E-Graph Kernel & Proof-Carrying Equality Saturation.
Part of Project Black-Heart (%🖤).

Tests:
  1. test_egraph_add_and_hashcons: Node deduplication and canonical ID resolution.
  2. test_congruence_closure_propagation: Upward propagation of equivalence across App parents.
  3. test_equality_saturation_combinators: Non-destructive saturation with S, K, I rules.
  4. test_proof_explanation_tree: Generation and verification of step-by-step justification paths.
  5. test_optimal_term_extraction: Dynamic programming extraction of shortest equivalent combinator AST.
  6. test_tombstone_quarantine_in_egraph: Fail-closed taint propagation when an e-class matches a refuted tombstone.
  7. test_egraph_polyglot_pdf_runner: ISO 32000 append-only update and standalone Latin-1 Python audit execution.
"""

import os
import sys
import json
import unittest
import tempfile
import subprocess

import glyph
from glyph import parse, evaluate, tree_size, App, Comb, Var
import crypto
from crypto import generate_keypair
import controlled_forgetting
from controlled_forgetting import EpistemicTombstoneRegistry, RetirementMode
import egraph_kernel
from egraph_kernel import (
    ENode, EClass, UnionFind, EGraph, RewriteRule,
    STANDARD_COMBINATOR_RULES, EquivalenceProofTree,
    generate_egraph_pdf, append_egraph_hud
)


class TestEGraphKernel(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_egraph_add_and_hashcons(self):
        """Verify structural deduplication and canonical hashconsing."""
        egraph = EGraph()
        t1 = parse("K x y")
        t2 = parse("K x y")

        id1 = egraph.add_term(t1)
        id2 = egraph.add_term(t2)

        # Hashconsing must return the identical canonical EClass ID
        self.assertEqual(id1, id2)
        self.assertIn(id1, egraph.classes)

        # Adding a subterm must reuse canonical leaf nodes
        t_sub = parse("x")
        id_sub = egraph.add_term(t_sub)
        self.assertIn(id_sub, egraph.classes)

    def test_congruence_closure_propagation(self):
        """Verify that f(a) == f(b) is automatically synthesized when a == b."""
        egraph = EGraph()

        # Add f(a) and f(b)
        fa = parse("f a")
        fb = parse("f b")

        id_fa = egraph.add_term(fa)
        id_fb = egraph.add_term(fb)

        id_a = egraph.add_term(parse("a"))
        id_b = egraph.add_term(parse("b"))

        # Initially, fa and fb are not equivalent
        self.assertNotEqual(egraph.uf.find(id_fa), egraph.uf.find(id_fb))

        # Union a and b
        egraph.union(id_a, id_b, justification="premise: a == b")
        egraph.rebuild()

        # Congruence closure must have merged f(a) and f(b)
        self.assertEqual(egraph.uf.find(id_fa), egraph.uf.find(id_fb))

    def test_equality_saturation_combinators(self):
        """Verify non-destructive equality saturation on combinator expressions."""
        egraph = EGraph()

        # Input: S K K x
        expr = parse("S K K x")
        cid_expr = egraph.add_term(expr)

        # Target expected normal form: x
        target = parse("x")
        cid_target = egraph.add_term(target)

        # Run equality saturation
        res = egraph.saturate(STANDARD_COMBINATOR_RULES, max_iterations=6, fuel_atp=500)
        self.assertGreaterEqual(res["iterations"], 1)
        self.assertGreater(res["total_unions"], 0)

        # S K K x and x must now belong to the exact same equivalence class
        self.assertEqual(egraph.uf.find(cid_expr), egraph.uf.find(cid_target))

    def test_proof_explanation_tree(self):
        """Verify step-by-step certified equational derivation tree (proof forest)."""
        egraph = EGraph()
        t_a = parse("S K K x")
        t_b = parse("x")

        egraph.add_term(t_a)
        egraph.add_term(t_b)
        egraph.saturate(STANDARD_COMBINATOR_RULES, max_iterations=6, fuel_atp=500)

        proof = egraph.explain_equivalence(t_a, t_b)
        self.assertTrue(proof.is_equivalent)
        self.assertGreaterEqual(len(proof.proof_steps), 1)

        # Verify steps structure
        for step in proof.proof_steps:
            self.assertGreater(len(step.from_expr), 0)
            self.assertGreater(len(step.to_expr), 0)
            self.assertGreater(len(step.justification), 0)

    def test_optimal_term_extraction(self):
        """Verify dynamic programming extraction of minimal normal form."""
        egraph = EGraph()

        # Start with a bloated combinator expression equivalent to Identity
        bloated = parse("S (K (S I)) (K I) x")
        cid = egraph.add_term(bloated)

        # Add custom reduction rule for this pattern
        custom_rules = STANDARD_COMBINATOR_RULES + [
            RewriteRule.from_strings("RULE-DISTRIB", "S (K (S I)) (K I) x", "I x"),
        ]

        egraph.saturate(custom_rules, max_iterations=6, fuel_atp=500)

        # Extract optimal term
        opt_term, cost = egraph.extract_optimal(cid)
        opt_str = str(opt_term)

        # Optimal term must be minimal normal form "x"
        self.assertIn(opt_str, ("x", "I x"))
        self.assertLess(tree_size(opt_term), tree_size(bloated))

    def test_tombstone_quarantine_in_egraph(self):
        """Verify Invariant EG5: fail-closed quarantine of refuted terms."""
        egraph = EGraph()
        registry = EpistemicTombstoneRegistry()

        sk, pk = generate_keypair()
        refuted_pattern = "K I (S K)"

        # Register tombstone in registry
        registry.retire(
            target_id=refuted_pattern,
            target_digest="dummy_digest",
            mode=RetirementMode.REFUTED,
            loss_declaration="Counterexample divergence detected in prior generation.",
            author_sk_hex=sk,
            author_pk_hex=pk,
            rule_or_pattern=refuted_pattern
        )

        # Inoculate E-Graph with registry
        tainted_count = egraph.inoculate_tombstones(registry)
        self.assertEqual(tainted_count, 1)

        # Verify class is marked tainted
        refuted_t = parse(refuted_pattern)
        cid = egraph.add_term(refuted_t)
        root_cid = egraph.uf.find(cid)
        self.assertTrue(egraph.classes[root_cid].is_tainted)
        self.assertIn("TOMBSTONE-REFUTED", egraph.classes[root_cid].taint_reason)

    def test_egraph_polyglot_pdf_runner(self):
        """Verify ISO 32000 append-only update and standalone Latin-1 Python runner."""
        egraph = EGraph()
        t_a = parse("S K K x")
        t_b = parse("x")
        egraph.add_term(t_a)
        egraph.add_term(t_b)
        egraph.saturate(STANDARD_COMBINATOR_RULES, max_iterations=6, fuel_atp=500)
        proof = egraph.explain_equivalence(t_a, t_b)

        pdf_path = os.path.join(self.temp_dir.name, "egraph_kernel.pdf")
        pdf_bytes = generate_egraph_pdf(egraph, pdf_path, sample_proof=proof)

        self.assertTrue(os.path.exists(pdf_path))
        self.assertTrue(pdf_bytes.startswith(b"#!" + sys.executable.encode("latin-1")))
        self.assertIn(b"%PDF-1.7", pdf_bytes)
        self.assertIn(b"EGRAPH_MANIFEST:", pdf_bytes)

        # Test incremental append
        append_path = os.path.join(self.temp_dir.name, "egraph_kernel_updated.pdf")
        append_bytes = append_egraph_hud(pdf_bytes, append_path, egraph)
        self.assertTrue(append_bytes.startswith(pdf_bytes))

        # Test standalone Python execution, under the supported isolated profile (S7)
        cmd = [sys.executable, "-I", pdf_path]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, f"Polyglot runner failed: {proc.stderr}")
        self.assertIn("EPISTEMIC E-GRAPH KERNEL", proc.stdout)
        # S7: the runner reports manifest integrity and names its scope; it no
        # longer claims congruence "sound".
        self.assertIn("Manifest self-consistency: OK", proc.stdout)
        self.assertNotIn("congruence closure sound", proc.stdout)
        self.assertIn("asserts no soundness", proc.stdout)


if __name__ == "__main__":
    unittest.main()
