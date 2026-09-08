#!/usr/bin/env python3
"""
test_zk_glyph.py — Unit Tests for Pure-Python Zero-Knowledge Proofs on Ed25519.
Part of Project Black-Heart (%🖤).
"""

import os
import sys
import unittest
import tempfile
import subprocess

from crypto import generate_keypair
from zk_glyph import (
    SchnorrProof, schnorr_prove, schnorr_verify,
    ChaumPedersenProof, chaum_pedersen_prove, chaum_pedersen_verify,
    ZKProofPolyglot
)

class TestZKGlyphEngine(unittest.TestCase):

    def setUp(self):
        self.sk, self.pk = generate_keypair()
        self.tmp_dir = tempfile.mkdtemp()

    def test_schnorr_completeness(self):
        proof = schnorr_prove(self.sk, context="TEST_SESSION_42")
        self.assertEqual(proof.prover_pk_hex, self.pk)
        self.assertTrue(schnorr_verify(proof))

    def test_schnorr_soundness_tampering(self):
        proof = schnorr_prove(self.sk, context="LEGITIMATE_CONTEXT")

        # Tampered context
        bad_context = SchnorrProof(
            prover_pk_hex=proof.prover_pk_hex,
            commitment_R_hex=proof.commitment_R_hex,
            response_z_hex=proof.response_z_hex,
            context="TAMPERED_CONTEXT"
        )
        self.assertFalse(schnorr_verify(bad_context))

        # Tampered public key (impersonation attempt)
        _, other_pk = generate_keypair()
        bad_pk = SchnorrProof(
            prover_pk_hex=other_pk,
            commitment_R_hex=proof.commitment_R_hex,
            response_z_hex=proof.response_z_hex,
            context=proof.context
        )
        self.assertFalse(schnorr_verify(bad_pk))

    def test_chaum_pedersen_completeness(self):
        secret_scalar = 9876543210987654321
        proof = chaum_pedersen_prove(secret_scalar, context="DLOG_TEST_CTX")
        self.assertTrue(chaum_pedersen_verify(proof))

    def test_chaum_pedersen_soundness_tampering(self):
        secret_scalar = 9876543210987654321
        proof = chaum_pedersen_prove(secret_scalar, context="DLOG_TEST_CTX")

        # Alter commitment R1
        bad_r1 = ChaumPedersenProof(
            point_P1_hex=proof.point_P1_hex,
            point_P2_hex=proof.point_P2_hex,
            commitment_R1_hex=proof.commitment_R2_hex,  # swapped!
            commitment_R2_hex=proof.commitment_R2_hex,
            response_z_hex=proof.response_z_hex,
            context=proof.context
        )
        self.assertFalse(chaum_pedersen_verify(bad_r1))

    def test_zk_polyglot_audit_execution(self):
        pdf_path = os.path.join(self.tmp_dir, "zk_contract_test.pdf")
        poly = ZKProofPolyglot("CONFIDENTIAL AUDIT CONTRACT")

        sp = schnorr_prove(self.sk, context="CONTRACT_MEMBERSHIP_PROOF")
        cpp = chaum_pedersen_prove(42424242, context="SOLVENCY_COMMITMENT_PROOF")

        poly.add_schnorr_proof(sp)
        poly.add_chaum_pedersen_proof(cpp)
        poly.compile(pdf_path)

        self.assertTrue(os.path.exists(pdf_path))

        # Execute the PDF via python
        cmd = [sys.executable, pdf_path]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("ALL ZERO-KNOWLEDGE PROOFS VERIFIED MATHEMATICALLY", proc.stdout)

if __name__ == "__main__":
    unittest.main()
