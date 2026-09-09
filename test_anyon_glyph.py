#!/usr/bin/env python3
"""
test_anyon_glyph.py — Unit Tests for Topological Anyonic Combinators & Braided Rewriting.
Part of Project Black-Heart (%🖤).

Verifies:
  1. Compilation of SKIY glyph ASTs into 3-strand Artin braid words in B_3.
  2. Exact SU(2) Fibonacci modular tensor category unitary evolution.
  3. Golden ratio Born probability invariants P(0) = 1/φ², P(1) = 1/φ.
  4. Cryptographic Ed25519 signing, verification, and tamper detection on AnyonSettlementReceipt.
  5. Single-file ISO 32000 PDF polyglot compilation with embedded vector worldlines.
  6. Subprocess execution of the generated polyglot ('python3 anyon.pdf --simulate').
  7. In-memory static auditing and fail-closed security controls.
"""

import os
import sys
import json
import tempfile
import unittest
import subprocess

from crypto import generate_keypair
from glyph import parse, GLYPH_K, GLYPH_I, GLYPH_S, GLYPH_Y
from anyon_glyph import (
    compile_glyph_to_anyon_braid,
    settle_anyon_glyph,
    AnyonSettlementReceipt,
    AnyonPolyglotCompiler,
    construct_anyon_polyglot,
    audit_anyon_polyglot,
    ANYON_MANIFEST_PREFIX
)

class TestAnyonicGlyphQuantum(unittest.TestCase):
    """Verifies anyon braid compilation, unitary evolution, Born collapse, and polyglots."""

    def setUp(self):
        self.sk_hex, self.pk_hex = generate_keypair()

    def test_glyph_to_braid_compilation(self):
        """Combinator trees must compile into valid 3-strand Artin braids in B_3."""
        # 1. Single Black Cone 🖤 -> σ_1
        t_k = parse(GLYPH_K)
        b_k = compile_glyph_to_anyon_braid(t_k)
        self.assertEqual(b_k.num_strands, 3)
        self.assertEqual(b_k.to_artin_notation(), "σ_1")

        # 2. Spore application 🌿 🖤 🤍
        t_app = parse("🌿 🖤 🤍")
        b_app = compile_glyph_to_anyon_braid(t_app)
        self.assertEqual(b_app.num_strands, 3)
        self.assertGreater(len(b_app.crossings), 2)
        self.assertIn("σ_2", b_app.to_artin_notation())

        # 3. Recurrent Loop 🔁 🤍 (contains central element of B_3)
        t_loop = parse("🔁 🤍")
        b_loop = compile_glyph_to_anyon_braid(t_loop)
        self.assertGreaterEqual(b_loop.crossing_number, 6)

    def test_fibonacci_unitary_and_golden_ratio_probabilities(self):
        """Unitary gate must preserve unitarity and exhibit golden ratio probability distributions."""
        t = parse("🌿 🖤 🤍")
        rec = settle_anyon_glyph(t, secret_key_hex=self.sk_hex, seed_hex="42" * 32)

        # Unitary determinant magnitude must be exactly 1.0 within tolerance
        self.assertAlmostEqual(rec.unitary_det_mag, 1.0, places=5)

        # Born probabilities must sum to 1.0
        self.assertAlmostEqual(rec.born_p0_vacuum + rec.born_p1_anyon, 1.0, places=5)

        # Fibonacci golden ratio probabilities for 🌿 🖤 🤍:
        # P(0) = 1/φ² ≈ 0.381966, P(1) = 1/φ ≈ 0.618034
        self.assertAlmostEqual(rec.born_p0_vacuum, 0.381966, places=4)
        self.assertAlmostEqual(rec.born_p1_anyon, 0.618034, places=4)

        # Von Neumann entropy must be positive
        self.assertGreater(rec.von_neumann_entropy, 0.9)

    def test_anyon_settlement_receipt_cryptography(self):
        """Anyon receipts must sign and verify correctly, failing closed on tampering."""
        t = parse("🖤 🤍")
        rec = settle_anyon_glyph(t, secret_key_hex=self.sk_hex, seed_hex="99" * 32)

        self.assertTrue(rec.verify(), "Valid signed receipt must verify")
        self.assertEqual(len(rec.signature_hex), 128)
        self.assertEqual(len(rec.receipt_hash), 64)

        # Serialization round-trip
        d = rec.to_dict()
        restored = AnyonSettlementReceipt.from_dict(d)
        self.assertTrue(restored.verify())
        self.assertEqual(restored.receipt_hash, rec.receipt_hash)

        # Tampering with Born probabilities must fail verification
        restored.born_p0_vacuum = 0.999
        self.assertFalse(restored.verify(), "Tampered receipt must fail verification")

    def test_polyglot_compiler_structure(self):
        """Anyon polyglot must satisfy ISO 32000 and contain Python runner."""
        t = parse("🌿 🖤 🤍")
        rec = settle_anyon_glyph(t, secret_key_hex=self.sk_hex, seed_hex="77" * 32)

        compiler = AnyonPolyglotCompiler()
        pdf_bytes = compiler.compile_bytes(rec)

        self.assertTrue(pdf_bytes.startswith(b"# coding: utf-8\nr\"\"\"%PDF-1.7"))
        self.assertIn(b"%%EOF", pdf_bytes)
        self.assertIn(ANYON_MANIFEST_PREFIX.encode("utf-8"), pdf_bytes)
        self.assertIn(b"def cmd_simulate(filepath):", pdf_bytes)
        self.assertIn(b"def cmd_status(filepath):", pdf_bytes)

    def test_subprocess_simulation_execution(self):
        """Polyglot file must run under python3 to replay simulation and status."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "anyon_circuit.pdf")
            rec = construct_anyon_polyglot(
                output_pdf_path=pdf_path,
                secret_key_hex=self.sk_hex,
                term_expr="🌿 🖤 🤍",
                seed_hex="1234" * 16
            )

            # 1. Run --status
            res_stat = subprocess.run(
                [sys.executable, pdf_path, "--status"],
                capture_output=True,
                text=True,
                timeout=15
            )
            self.assertEqual(res_stat.returncode, 0, f"Status failed: {res_stat.stderr}")
            self.assertIn("Circuit Term:        🌿 🖤 🤍", res_stat.stdout)
            self.assertIn("Born P(|0> Vacuum):  38.20%", res_stat.stdout)

            # 2. Run --simulate
            res_sim = subprocess.run(
                [sys.executable, pdf_path, "--simulate"],
                capture_output=True,
                text=True,
                timeout=15
            )
            self.assertEqual(res_sim.returncode, 0, f"Simulate failed: {res_sim.stderr}")
            self.assertIn("TOPOLOGICAL ANYON CIRCUIT SIMULATION COMPLETE", res_sim.stdout)
            self.assertIn("Topological Invariance: 100% SOUND", res_sim.stdout)

    def test_static_polyglot_audit_fail_closed(self):
        """audit_anyon_polyglot must verify valid files and fail-closed on tampered bytes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "audit_anyon.pdf")
            rec = construct_anyon_polyglot(
                output_pdf_path=pdf_path,
                secret_key_hex=self.sk_hex,
                term_expr="🔁 🤍",
                seed_hex="abcd" * 16
            )

            with open(pdf_path, "rb") as f:
                valid_bytes = f.read()

            # 1. Clean audit must pass
            ok, msg, info = audit_anyon_polyglot(valid_bytes)
            self.assertTrue(ok, f"Clean audit failed: {msg}")
            self.assertEqual(info["term_expr"], "🔁 🤍")

            # 2. Tampered signature in manifest must fail audit
            tampered_bytes = valid_bytes.replace(
                rec.signature_hex.encode("utf-8"),
                b"f" * 128
            )
            self.assertNotEqual(valid_bytes, tampered_bytes)
            ok_t, msg_t, _ = audit_anyon_polyglot(tampered_bytes)
            self.assertFalse(ok_t, "Tampered audit must fail closed")
            self.assertIn("invalid", msg_t.lower())

if __name__ == "__main__":
    unittest.main()
