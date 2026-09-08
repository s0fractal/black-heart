#!/usr/bin/env python3
"""
test_cross_proof.py — Unit Tests for Bilateral Interlocking Documents & Embedded Code Vaults.
Part of Project Black-Heart (%🖤).
"""

import os
import sys
import unittest
import tempfile
import json

from crypto import generate_keypair
from cross_proof import (
    TelemetryOraclePolyglot,
    BilateralAgreementPolyglot,
    adjudicate_bilateral
)
from vault import embed_vault_into_polyglot, extract_vault_from_pdf

class TestBilateralCrossProof(unittest.TestCase):
    """Verifies mutual cross-verification and adjudication between independent polyglot PDFs."""

    def setUp(self):
        self.oracle_sk, self.oracle_pk = generate_keypair()
        self.forger_sk, self.forger_pk = generate_keypair()
        self.client_sk, self.client_pk = generate_keypair()

    def test_bilateral_adjudication_sound(self):
        """Bilateral adjudication with authenticated oracle must succeed with deterministic receipt."""
        with tempfile.TemporaryDirectory() as tmpdir:
            oracle_pdf = os.path.join(tmpdir, "oracle.pdf")
            agreement_pdf = os.path.join(tmpdir, "agreement.pdf")

            # 1. Compile Oracle PDF
            oracle = TelemetryOraclePolyglot(oracle_name="Test Datadog Oracle")
            oracle.add_incident("INC-101", "2026-09-01T00:00:00Z", "Network Glitch", 300)
            oracle.compile(oracle_pdf, self.oracle_sk)
            self.assertTrue(os.path.exists(oracle_pdf))

            # 2. Compile Agreement PDF
            agreement = BilateralAgreementPolyglot(
                title="TEST BILATERAL CONTRACT",
                trusted_oracle_pk_hex=self.oracle_pk,
                target_uptime_percent=99.5,
                base_fee_usd=10000,
                penalty_rate_usd=500
            )
            agreement.add_party("CLIENT", "Test Client", self.client_pk, secret_key_hex=self.client_sk)
            agreement.compile(agreement_pdf)
            self.assertTrue(os.path.exists(agreement_pdf))

            # 3. Adjudicate
            receipt = adjudicate_bilateral(agreement_pdf, oracle_pdf)
            self.assertEqual(receipt.status, "SETTLED_BREACH")
            self.assertEqual(receipt.penalty_due_usd, 500)
            self.assertEqual(receipt.net_service_due_usd, 9500)
            self.assertEqual(len(receipt.joint_bilateral_digest), 64)

    def test_reject_untrusted_oracle(self):
        """If oracle PDF was signed by a different key than trusted, adjudication must fail."""
        with tempfile.TemporaryDirectory() as tmpdir:
            forged_oracle_pdf = os.path.join(tmpdir, "forged_oracle.pdf")
            agreement_pdf = os.path.join(tmpdir, "agreement.pdf")

            # Oracle compiled by forger
            oracle = TelemetryOraclePolyglot(oracle_name="Untrusted Rogue Oracle")
            oracle.compile(forged_oracle_pdf, self.forger_sk)

            # Agreement trusts legitimate oracle_pk
            agreement = BilateralAgreementPolyglot(
                title="TEST CONTRACT",
                trusted_oracle_pk_hex=self.oracle_pk
            )
            agreement.compile(agreement_pdf)

            # Attempting adjudication must raise PermissionError
            with self.assertRaises(PermissionError):
                adjudicate_bilateral(agreement_pdf, forged_oracle_pdf)


class TestEmbeddedCodeVault(unittest.TestCase):
    """Verifies packing and unpacking of embedded code vaults inside polyglot PDFs."""

    def test_embed_and_extract_vault(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "sample.pdf")

            # Create dummy PDF
            with open(pdf_path, "wb") as f:
                f.write(b"%PDF-1.7\n%dummy\n%%EOF\n")

            # Embed files
            repo_root = os.path.dirname(os.path.abspath(__file__))
            files_to_embed = ["glyph.py", "crypto.py"]
            vault_hash = embed_vault_into_polyglot(pdf_path, files_to_embed, repo_root)
            self.assertEqual(len(vault_hash), 64)

            # Extract vault
            unpack_dir = os.path.join(tmpdir, "unpacked")
            extracted_files = extract_vault_from_pdf(pdf_path, unpack_dir)
            self.assertEqual(set(extracted_files), set(files_to_embed))

            # Verify content integrity of extracted files
            with open(os.path.join(unpack_dir, "glyph.py"), "rb") as f:
                extracted_content = f.read()
            with open(os.path.join(repo_root, "glyph.py"), "rb") as f:
                original_content = f.read()
            self.assertEqual(extracted_content, original_content)

if __name__ == "__main__":
    unittest.main()
