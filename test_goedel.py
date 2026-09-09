#!/usr/bin/env python3
"""
test_goedel.py — Unit Tests for Gödelian Incompleteness & Event Horizon Engine.
Part of Project Black-Heart (%🖤).

Verifies:
  1. Black Cone 🖤 (K) event horizon phase transitions (Singularity Collapse vs Attractor Cycles vs Divergence).
  2. Exact limit-cycle detection and AttractorWitness generation (e.g. Y(I) period-2 oscillator).
  3. Ed25519 signing, verification, and tamper detection on GoedelSettlementReceipt.
  4. ISO 32000 compliant PDF polyglot structure with embedded Python runner.
  5. Subprocess self-settlement execution ('python3 goedel.pdf --verify').
  6. In-memory fail-closed static auditing via audit_goedel_polyglot.
"""

import os
import sys
import json
import tempfile
import unittest
import subprocess

from crypto import generate_keypair
from glyph import parse, TRUE, FALSE
from goedel import (
    TruthGrade,
    EventHorizonClass,
    AttractorWitness,
    GoedelSettlementReceipt,
    evaluate_with_cycle_detection,
    probe_black_cone_horizon,
    GoedelPolyglotCompiler,
    construct_goedel_polyglot,
    audit_goedel_polyglot,
    GOEDEL_MANIFEST_PREFIX
)

class TestGoedelIncompleteness(unittest.TestCase):
    """Verifies dynamical limit-cycle detection, receipts, and polyglot resolution."""

    def setUp(self):
        self.sk_hex, self.pk_hex = generate_keypair()

    def test_black_cone_event_horizon_classifications(self):
        """Pits 🖤, 🌿, 🔁, and 🤍 against each other and verifies dynamical fates."""
        probes = probe_black_cone_horizon(atp_budget=200)
        self.assertGreater(len(probes), 5)

        by_name = {p["name"]: p for p in probes}

        # 1. K Truth Mirage must collapse in 1 step into a constant normal form
        self.assertEqual(by_name["Black Cone Collapse"]["horizon_class"], EventHorizonClass.SINGULARITY_COLLAPSE.value)
        self.assertEqual(by_name["Black Cone Collapse"]["atp_spent"], 1)

        # 2. K must swallow infinite Omega recursion in 1 step
        self.assertEqual(by_name["Swallowed Infinity"]["horizon_class"], EventHorizonClass.SINGULARITY_COLLAPSE.value)
        self.assertEqual(by_name["Swallowed Infinity"]["atp_spent"], 1)

        # 3. Y(I) must enter an exact period-2 stable attractor limit cycle
        self.assertEqual(by_name["Loop Identity (Period-2)"]["horizon_class"], EventHorizonClass.STABLE_ATTRACTOR.value)
        self.assertEqual(by_name["Loop Identity (Period-2)"]["truth_grade"], TruthGrade.ATTRACTOR_CYCLE.value)
        self.assertEqual(by_name["Loop Identity (Period-2)"]["period"], 2)

    def test_cycle_detection_and_attractor_witness(self):
        """Attractor limit cycle must capture exact orbit states and produce deterministic witness hash."""
        term_yi = parse("🔁 🤍")
        res, witness, grade, horizon = evaluate_with_cycle_detection(term_yi, max_atp=100)

        self.assertIsNotNone(witness)
        self.assertEqual(witness.period, 2)
        self.assertEqual(len(witness.cycle_states), 2)
        self.assertEqual(grade, TruthGrade.ATTRACTOR_CYCLE)
        self.assertEqual(horizon, EventHorizonClass.STABLE_ATTRACTOR)
        self.assertEqual(len(witness.witness_hash), 64)

        # Re-running must produce identical hash (determinism)
        res2, witness2, _, _ = evaluate_with_cycle_detection(term_yi, max_atp=100)
        self.assertEqual(witness.witness_hash, witness2.witness_hash)

    def test_receipt_cryptography_and_tampering(self):
        """Receipts must sign and verify correctly, and fail-closed upon tampering."""
        rec = GoedelSettlementReceipt(
            sentence_id="G_TEST_01",
            truth_grade=TruthGrade.ATTRACTOR_CYCLE.value,
            horizon_class=EventHorizonClass.STABLE_ATTRACTOR.value,
            initial_term="🔁 🤍",
            settled_term="🔁 🤍",
            atp_spent=2,
            cycle_period=2,
            witness_hash="e" * 64,
            document_merkle_root="d" * 64,
            public_key_hex=self.pk_hex,
            timestamp_utc="2026-09-09T12:00:00Z"
        )
        rec.sign(self.sk_hex)
        self.assertTrue(rec.verify(), "Valid signed receipt must verify")

        # Round-trip JSON serialization
        d = rec.to_dict()
        restored = GoedelSettlementReceipt.from_dict(d)
        self.assertTrue(restored.verify())
        self.assertEqual(restored.receipt_hash, rec.receipt_hash)

        # Tampering with cycle period must invalidate receipt
        restored.cycle_period = 3
        self.assertFalse(restored.verify(), "Tampered cycle period must fail verification")

        # Tampering with truth grade must invalidate receipt
        restored2 = GoedelSettlementReceipt.from_dict(d)
        restored2.truth_grade = "TRUE"
        self.assertFalse(restored2.verify(), "Tampered truth grade must fail verification")

    def test_goedel_polyglot_compiler_structure(self):
        """Polyglot compiler must generate ISO 32000 compliant binary with embedded Python runner."""
        compiler = GoedelPolyglotCompiler(sentence_id="TEST_PARADOX")
        rec = GoedelSettlementReceipt(
            sentence_id="TEST_PARADOX",
            truth_grade=TruthGrade.ATTRACTOR_CYCLE.value,
            horizon_class=EventHorizonClass.STABLE_ATTRACTOR.value,
            initial_term="🔁 🤍",
            settled_term="🔁 🤍",
            atp_spent=2,
            cycle_period=2,
            witness_hash="7" * 64,
            document_merkle_root="8" * 64,
            public_key_hex=self.pk_hex,
            timestamp_utc="2026-09-09T12:00:00Z"
        )
        rec.sign(self.sk_hex)

        pdf_bytes = compiler.compile_bytes(rec)

        # Header and Trailer
        self.assertTrue(pdf_bytes.startswith(b"# coding: utf-8\nr\"\"\"%PDF-1.7"))
        self.assertIn(b"%%EOF", pdf_bytes)
        self.assertIn(b"/Type /Catalog", pdf_bytes)
        self.assertIn(b"/Type /Page", pdf_bytes)

        # Embedded Manifest & Runner
        self.assertIn(GOEDEL_MANIFEST_PREFIX.encode("utf-8"), pdf_bytes)
        self.assertIn(b"def cmd_verify(filepath):", pdf_bytes)
        self.assertIn(b"def cmd_status(filepath):", pdf_bytes)

    def test_subprocess_execution_and_self_settlement(self):
        """Generated Gödelian polyglot must execute via python3 and resolve the paradox."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "goedel_organism.pdf")

            rec = construct_goedel_polyglot(
                output_pdf_path=pdf_path,
                secret_key_hex=self.sk_hex,
                sentence_expr="🔁 🤍",
                sentence_id="DIAGONAL_OSCILLATOR"
            )

            # 1. Run --status
            res_stat = subprocess.run(
                [sys.executable, pdf_path, "--status"],
                capture_output=True,
                text=True,
                timeout=15
            )
            self.assertEqual(res_stat.returncode, 0, f"Status run failed: {res_stat.stderr}")
            self.assertIn("STABLE_ATTRACTOR", res_stat.stdout)
            self.assertIn("Cycle Period:      2 steps", res_stat.stdout)

            # 2. Run --verify
            res_ver = subprocess.run(
                [sys.executable, pdf_path, "--verify"],
                capture_output=True,
                text=True,
                timeout=15
            )
            self.assertEqual(res_ver.returncode, 0, f"Verify run failed: {res_ver.stderr}")
            self.assertIn("GÖDELIAN PARADOX CRYPTOGRAPHICALLY RESOLVED", res_ver.stdout)
            self.assertIn("PROVEN UNPROVABLE WITHIN CLASSICAL LIMITS", res_ver.stdout)

    def test_static_polyglot_audit_fail_closed(self):
        """audit_goedel_polyglot must verify valid files and fail-closed on tampered bytes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "audit_test.pdf")
            rec = construct_goedel_polyglot(
                output_pdf_path=pdf_path,
                secret_key_hex=self.sk_hex,
                sentence_expr="🔁 🤍",
                sentence_id="AUDIT_DIAGONAL"
            )

            with open(pdf_path, "rb") as f:
                valid_bytes = f.read()

            # 1. Clean audit must pass
            ok, msg, info = audit_goedel_polyglot(valid_bytes)
            self.assertTrue(ok, f"Clean audit failed: {msg}")
            self.assertEqual(info["sentence_id"], "AUDIT_DIAGONAL")
            self.assertEqual(info["cycle_period"], 2)

            # 2. Tampered witness hash in manifest must fail audit
            tampered_bytes = valid_bytes.replace(
                rec.witness_hash.encode("utf-8"),
                b"0" * 64
            )
            self.assertNotEqual(valid_bytes, tampered_bytes)
            ok_t, msg_t, _ = audit_goedel_polyglot(tampered_bytes)
            self.assertFalse(ok_t, "Tampered audit must fail-closed")
            self.assertIn("invalid", msg_t.lower())

if __name__ == "__main__":
    unittest.main()
