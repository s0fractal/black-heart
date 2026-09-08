#!/usr/bin/env python3
"""
test_monad.py — Comprehensive Unit Tests for the Literate Polyglot Monad,
Dual-Spine Trees, and Self-Verifying Proof-Bearing Contracts.
Part of Project Black-Heart (%🖤).
"""

import os
import sys
import unittest
import tempfile
import subprocess
import json
import hashlib

from monad import (
    CodeSpineNode,
    VisualSpineNode,
    DualSpineTree,
    LiterateMonad,
    MonadState,
    SelfVerifyingContractPolyglot
)

class TestLiterateMonadLaws(unittest.TestCase):
    """Verifies that LiterateMonad satisfies the standard category-theoretic Monad Laws."""

    def test_left_identity(self):
        """unit(x) >>= f === f(x)"""
        x = 42
        def f(val: int) -> LiterateMonad[int]:
            return LiterateMonad(lambda s: (val * 2, s))

        state_init_1 = MonadState(atp_budget=1000, atp_spent=0, dual_tree=DualSpineTree())
        state_init_2 = MonadState(atp_budget=1000, atp_spent=0, dual_tree=DualSpineTree())

        res1, s1 = LiterateMonad.unit(x).bind(f).run(state_init_1)
        res2, s2 = f(x).run(state_init_2)

        self.assertEqual(res1, res2)
        self.assertEqual(res1, 84)

    def test_right_identity(self):
        """m >>= unit === m"""
        def computation(s: MonadState):
            s.atp_spent += 5
            return "hello", s

        m = LiterateMonad(computation)

        state_init_1 = MonadState(atp_budget=1000, atp_spent=0, dual_tree=DualSpineTree())
        state_init_2 = MonadState(atp_budget=1000, atp_spent=0, dual_tree=DualSpineTree())

        res1, s1 = m.bind(LiterateMonad.unit).run(state_init_1)
        res2, s2 = m.run(state_init_2)

        self.assertEqual(res1, res2)
        self.assertEqual(s1.atp_spent, s2.atp_spent)

    def test_associativity(self):
        """(m >>= f) >>= g === m >>= (\\x -> f(x) >>= g)"""
        m = LiterateMonad.unit(10)
        f = lambda x: LiterateMonad(lambda s: (x + 5, s))
        g = lambda y: LiterateMonad(lambda s: (y * 3, s))

        res1, _ = m.bind(f).bind(g).run()
        res2, _ = m.bind(lambda x: f(x).bind(g)).run()

        self.assertEqual(res1, res2)
        self.assertEqual(res1, 45)


class TestDualSpineTree(unittest.TestCase):
    """Verifies that DualSpineTree maintains tamper-evident homomorphic coupling."""

    def setUp(self):
        self.tree = DualSpineTree()

    def test_joint_anchor_deterministic(self):
        code_1 = CodeSpineNode(
            clause_id="C1",
            predicate_name="pred1",
            expression="🖤 a b",
            expected_normal_form="a"
        )
        vis_1 = VisualSpineNode(
            node_type="clause",
            title="Article 1",
            text_content="Constant selector clause."
        )
        self.tree.append_node_pair(code_1, vis_1)

        anchor1 = self.tree.joint_anchor()
        self.assertEqual(len(anchor1), 64)

        # Build second identical tree
        tree2 = DualSpineTree()
        tree2.append_node_pair(code_1, vis_1)
        anchor2 = tree2.joint_anchor()

        self.assertEqual(anchor1, anchor2)

    def test_tamper_detection_on_code(self):
        """Altering code expression changes code_root_hash and joint_anchor."""
        c1 = CodeSpineNode("C1", "p", "🖤 a b", "a")
        v1 = VisualSpineNode("clause", "Art 1", "Text")
        self.tree.append_node_pair(c1, v1)
        orig_anchor = self.tree.joint_anchor()

        # Modified code expression
        tampered_tree = DualSpineTree()
        c1_tampered = CodeSpineNode("C1", "p", "🤍 a", "a")
        tampered_tree.append_node_pair(c1_tampered, v1)

        self.assertNotEqual(orig_anchor, tampered_tree.joint_anchor())

    def test_tamper_detection_on_prose(self):
        """Altering legal prose changes visual_root_hash and joint_anchor."""
        c1 = CodeSpineNode("C1", "p", "🖤 a b", "a")
        v1 = VisualSpineNode("clause", "Art 1", "Provider pays 100 USD")
        self.tree.append_node_pair(c1, v1)
        orig_anchor = self.tree.joint_anchor()

        # Altered legal prose text
        tampered_tree = DualSpineTree()
        v1_tampered = VisualSpineNode("clause", "Art 1", "Provider pays 0 USD")
        tampered_tree.append_node_pair(c1, v1_tampered)

        self.assertNotEqual(orig_anchor, tampered_tree.joint_anchor())


class TestSelfVerifyingContractPolyglot(unittest.TestCase):
    """Verifies compilation and independent execution of the proof-carrying contract PDF."""

    def test_contract_compilation_and_execution(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "test_agreement.pdf")

            contract = SelfVerifyingContractPolyglot(
                title="TEST SLA AGREEMENT",
                jurisdiction="Test Jurisdiction"
            )
            contract.add_party("PROVIDER", "TestCloud Inc.", "ed25519:test01")
            contract.add_party("CLIENT", "TestClient Corp.", "ed25519:test02")
            contract.add_preamble("This is a formal test agreement.")
            contract.add_clause(
                clause_id="TEST-01",
                article_title="Article 1. Target Uptime",
                legal_prose="99.5% uptime required.",
                predicate_name="uptime_check",
                expression="uptime >= 99.5",
                expected_normal_form="TRUE"
            )
            contract.attach_evidence(
                record_id="INC-001",
                timestamp="2026-09-01T00:00:00Z",
                event_type="Test Outage",
                duration_min=300,
                description="Sample simulated outage."
            )

            contract.compile(pdf_path)
            self.assertTrue(os.path.exists(pdf_path))
            self.assertGreater(os.path.getsize(pdf_path), 5000)

            # Test standalone execution via python3 <pdf_path>
            res = subprocess.run(
                [sys.executable, pdf_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            self.assertEqual(res.returncode, 0, f"Polyglot execution failed with stderr: {res.stderr}")
            self.assertIn("BLACK-HEART — SELF-VERIFYING PROOF-BEARING CONTRACT ADJUDICATOR", res.stdout)
            self.assertIn("Document integrity sound. Dual-spine anchor verified.", res.stdout)
            self.assertIn("SETTLED: SLA BREACH CONFIRMED", res.stdout)
            self.assertIn("$500 USD", res.stdout)
            self.assertIn("⚓ ⟨atp:42", res.stdout)

if __name__ == "__main__":
    unittest.main()
