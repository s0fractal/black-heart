#!/usr/bin/env python3
"""
test_living_ledger.py — Comprehensive Unit Tests for:
  1. Zero-dependency Pure-Python Ed25519 Engine (crypto.py)
  2. Vector Proof Net & String Diagram Compiler (vector_net.py)
  3. Living Polyglot Ledger & Standalone Auditor (living_ledger.py)
Part of Project Black-Heart (%🖤).
"""

import os
import sys
import unittest
import tempfile
import subprocess
import json
import hashlib

from crypto import (
    generate_keypair,
    public_key_from_secret,
    sign_bytes,
    verify_bytes,
    CryptographicSeal
)
from glyph import parse, evaluate
from vector_net import VectorNetRenderer
from living_ledger import LivingLedger, LedgerBlock

class TestEd25519Cryptography(unittest.TestCase):
    """Verifies correctness and tamper-evidence of the pure-Python RFC 8032 engine."""

    def test_keypair_and_sign_verify(self):
        sk_hex, pk_hex = generate_keypair()
        sk = bytes.fromhex(sk_hex)
        pk = bytes.fromhex(pk_hex)

        self.assertEqual(len(sk), 32)
        self.assertEqual(len(pk), 32)

        msg = b"Black-Heart: The Proof-Carrying Polyglot"
        sig = sign_bytes(sk, msg)
        self.assertEqual(len(sig), 64)

        # Valid signature must pass
        self.assertTrue(verify_bytes(pk, msg, sig))

        # Tampered message must fail
        self.assertFalse(verify_bytes(pk, msg + b"!", sig))

        # Tampered signature must fail
        tampered_sig = bytearray(sig)
        tampered_sig[0] ^= 0xFF
        self.assertFalse(verify_bytes(pk, msg, bytes(tampered_sig)))

    def test_cryptographic_seal(self):
        sk_hex, pk_hex = generate_keypair()
        payload = b"{\"action\":\"SETTLEMENT\",\"amount\":500}"
        seal = CryptographicSeal.create(
            signer_role="ARBITER",
            signer_name="Settlement Node #1",
            secret_key_hex=sk_hex,
            payload_bytes=payload
        )

        self.assertTrue(seal.verify(payload))
        self.assertFalse(seal.verify(payload + b"tamper"))

        # Check dictionary conversion
        d = seal.to_dict()
        self.assertEqual(d["signer_role"], "ARBITER")
        self.assertEqual(d["public_key_hex"], pk_hex)


class TestVectorNetRenderer(unittest.TestCase):
    """Verifies that VectorNetRenderer produces valid PDF vector operator streams."""

    def setUp(self):
        self.renderer = VectorNetRenderer()

    def test_layout_and_render_term(self):
        term = parse("🌿 🖤 🖤 InvariantCarrier")
        layout = self.renderer.layout_tree(term, 200, 500)
        self.assertGreater(layout.width, 50)
        self.assertGreater(layout.height, 40)

        pdf_ops = self.renderer.render_tree_to_pdf_stream(layout)
        self.assertIn("1.5 w", pdf_ops) # line width
        self.assertIn(" m ", pdf_ops)   # moveto
        self.assertIn(" c ", pdf_ops)   # curveto
        self.assertIn("Td (K) Tj", pdf_ops) # K combinator label
        self.assertIn("Td (S) Tj", pdf_ops) # S combinator label

    def test_render_reduction_step(self):
        lhs = parse("🖤 Left Right")
        rhs = parse("Left")
        diagram = self.renderer.render_reduction_step(
            lhs=lhs,
            rhs=rhs,
            x=50,
            y=200,
            width=400,
            height=150,
            atp_cost=1,
            rule_name="K-Reduction"
        )
        self.assertIn("Proof Net: K-Reduction", diagram)
        self.assertIn("Cost: 1 ATP", diagram)
        self.assertIn("reduces", diagram)


class TestLivingLedger(unittest.TestCase):
    """Verifies creation, chaining, and standalone execution of the Living Polyglot Ledger."""

    def test_ledger_creation_and_execution(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "test_ledger.pdf")

            alice_sk, alice_pk = generate_keypair()
            bob_sk, bob_pk = generate_keypair()

            ledger = LivingLedger(title="TEST LIVING LEDGER")

            # Genesis
            b0 = ledger.create_genesis(
                signer_name="Alice",
                signer_role="ORIGINATOR",
                secret_key_hex=alice_sk,
                description="Genesis block activation."
            )
            self.assertEqual(b0.height, 0)
            self.assertEqual(b0.prev_hash, "00" * 32)
            self.assertGreater(len(b0.signature_hex), 64)

            # Block 1
            b1 = ledger.append_block(
                signer_name="Bob",
                signer_role="ARBITER",
                secret_key_hex=bob_sk,
                action_type="DEPOSIT",
                description="Escrow 500 ATP.",
                combinator_claim={"expr": "🖤 Alpha Beta", "expected": "Alpha", "atp": 1}
            )
            self.assertEqual(b1.height, 1)
            self.assertEqual(b1.prev_hash, b0.block_hash)

            # Compile polyglot PDF
            ledger.compile(pdf_path)
            self.assertTrue(os.path.exists(pdf_path))
            self.assertGreater(os.path.getsize(pdf_path), 5000)

            # Roundtrip load test
            loaded = LivingLedger.load_from_polyglot(pdf_path)
            self.assertEqual(len(loaded.blocks), 2)
            self.assertEqual(loaded.blocks[0].description, "Genesis block activation.")
            self.assertEqual(loaded.blocks[1].action_type, "DEPOSIT")

            # Subprocess standalone execution: python3 test_ledger.pdf
            res = subprocess.run(
                [sys.executable, pdf_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            self.assertEqual(res.returncode, 0, f"Ledger execution failed: {res.stderr}")
            self.assertIn("BLACK-HEART — LIVING POLYGLOT LEDGER AUDITOR", res.stdout)
            self.assertIn("BLOCK #0000 [GENESIS]", res.stdout)
            self.assertIn("BLOCK #0001 [DEPOSIT]", res.stdout)
            self.assertIn("Ed25519 Sig: \x1b[1;32m[✓ SOUND]\x1b[0m", res.stdout)
            self.assertIn("ALL 2/2 BLOCKS AUDITED SOUND & VERIFIED", res.stdout)

if __name__ == "__main__":
    unittest.main()
