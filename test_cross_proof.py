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
    adjudicate_bilateral,
    BilateralZKChallengerPolyglot,
    BilateralZKWitnessPolyglot,
    adjudicate_zk_bilateral,
    audit_zk_challenger_polyglot,
    audit_zk_witness_polyglot,
    BilateralZKSettlementReceipt
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


class TestBilateralZKCrossProof(unittest.TestCase):
    """Verifies Grok Experiment 4: Multi-document zero-knowledge cross-proof adjudication."""

    def setUp(self):
        self.challenger_sk, self.challenger_pk = generate_keypair()
        self.prover_sk, self.prover_pk = generate_keypair()
        self.rogue_sk, self.rogue_pk = generate_keypair()

    def test_schnorr_zk_cross_proof_sound(self):
        """Valid witness proving secret key knowledge against a contract must settle soundly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            challenger_pdf = os.path.join(tmpdir, "contract_a.pdf")
            witness_pdf = os.path.join(tmpdir, "witness_b.pdf")

            # 1. Compile Challenger Contract
            challenger = BilateralZKChallengerPolyglot(
                title="ESCROW SOVEREIGN IDENTITY CONTRACT",
                statement_id="CLAIM-ZK-991",
                target_prover_pk_hex=self.prover_pk,
                clause_text="Release 5000 ATP upon non-interactive zero-knowledge proof of sovereign key possession.",
                proof_type="SchnorrZKP",
                author_secret_key_hex=self.challenger_sk
            )
            challenger.compile(challenger_pdf)
            self.assertTrue(os.path.exists(challenger_pdf))
            self.assertTrue(audit_zk_challenger_polyglot(challenger_pdf))

            # 2. Compile Witness Prover
            witness = BilateralZKWitnessPolyglot(
                witness_name="Alice Autonomous Prover",
                challenger_pdf_path=challenger_pdf,
                prover_secret_key_hex=self.prover_sk
            )
            witness.compile(witness_pdf)
            self.assertTrue(os.path.exists(witness_pdf))
            self.assertTrue(audit_zk_witness_polyglot(witness_pdf))

            # 3. Adjudicate Bilateral Cross-Proof
            receipt = adjudicate_zk_bilateral(challenger_pdf, witness_pdf)
            self.assertEqual(receipt.status, "ZK_SETTLED_SOUND")
            self.assertEqual(receipt.statement_id, "CLAIM-ZK-991")
            self.assertEqual(receipt.target_prover_pk_hex, self.prover_pk)
            self.assertEqual(receipt.proof_type, "SchnorrZKP")
            self.assertTrue(receipt.challenger_cid.startswith("bafkrei"))
            self.assertTrue(receipt.witness_cid.startswith("bafkrei"))
            self.assertEqual(len(receipt.joint_bilateral_anchor), 64)

    def test_chaum_pedersen_zk_cross_proof_sound(self):
        """Valid witness proving discrete logarithm equality across generators must settle soundly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            challenger_pdf = os.path.join(tmpdir, "chaum_contract.pdf")
            witness_pdf = os.path.join(tmpdir, "chaum_witness.pdf")

            from zk_glyph import GENERATOR_H, _scalar_mult, _encode_point, L
            import hashlib
            h = hashlib.sha512(bytes.fromhex(self.prover_sk)).digest()
            scalar = int.from_bytes(h[:32], "little")
            scalar &= (1 << 254) - 8
            scalar |= (1 << 254)
            scalar %= L
            P2 = _scalar_mult(GENERATOR_H, scalar)
            P2_hex = _encode_point(P2).hex()

            # 1. Compile Challenger with Chaum-Pedersen requirement
            challenger = BilateralZKChallengerPolyglot(
                title="DUAL GENERATOR DISCRETE LOG EQUALITY CLAIM",
                statement_id="CLAIM-CP-404",
                target_prover_pk_hex=self.prover_pk,
                clause_text="Assert log_B(P1) == log_H(P2) without revealing secret exponent.",
                proof_type="ChaumPedersenZKP",
                second_point_hex=P2_hex,
                author_secret_key_hex=self.challenger_sk
            )
            challenger.compile(challenger_pdf)

            # 2. Compile Witness
            witness = BilateralZKWitnessPolyglot(
                witness_name="Bob Discrete Log Prover",
                challenger_pdf_path=challenger_pdf,
                prover_secret_key_hex=self.prover_sk
            )
            witness.compile(witness_pdf)

            # 3. Adjudicate
            receipt = adjudicate_zk_bilateral(challenger_pdf, witness_pdf)
            self.assertEqual(receipt.status, "ZK_SETTLED_SOUND")
            self.assertEqual(receipt.proof_type, "ChaumPedersenZKP")
            self.assertEqual(len(receipt.joint_bilateral_anchor), 64)

    def test_fail_closed_replay_attack_rejected(self):
        """A witness proof bound to Contract A must be strictly rejected when paired with Contract B."""
        with tempfile.TemporaryDirectory() as tmpdir:
            contract_a = os.path.join(tmpdir, "contract_a.pdf")
            contract_b = os.path.join(tmpdir, "contract_b.pdf")
            witness_pdf = os.path.join(tmpdir, "witness_for_a.pdf")

            # Contract A
            BilateralZKChallengerPolyglot(
                title="CONTRACT A",
                statement_id="CLAIM-A",
                target_prover_pk_hex=self.prover_pk,
                author_secret_key_hex=self.challenger_sk
            ).compile(contract_a)

            # Contract B (different statement & terms)
            BilateralZKChallengerPolyglot(
                title="CONTRACT B",
                statement_id="CLAIM-B",
                target_prover_pk_hex=self.prover_pk,
                author_secret_key_hex=self.challenger_sk
            ).compile(contract_b)

            # Witness specifically prepared for Contract A
            BilateralZKWitnessPolyglot(
                witness_name="Prover",
                challenger_pdf_path=contract_a,
                prover_secret_key_hex=self.prover_sk
            ).compile(witness_pdf)

            # Attempting to cross-prove witness against Contract B must raise PermissionError
            with self.assertRaises(PermissionError) as ctx:
                adjudicate_zk_bilateral(contract_b, witness_pdf)
            self.assertIn("Bilateral CID mismatch", str(ctx.exception))

    def test_fail_closed_wrong_secret_key(self):
        """If witness signs with rogue key not matching contract target PK, must be rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            contract_pdf = os.path.join(tmpdir, "contract.pdf")
            rogue_witness_pdf = os.path.join(tmpdir, "rogue_witness.pdf")

            # Contract expects self.prover_pk
            BilateralZKChallengerPolyglot(
                title="STRICT CONTRACT",
                statement_id="CLAIM-STRICT",
                target_prover_pk_hex=self.prover_pk,
                author_secret_key_hex=self.challenger_sk
            ).compile(contract_pdf)

            # Rogue prover attempts to submit proof using self.rogue_sk
            BilateralZKWitnessPolyglot(
                witness_name="Rogue Prover",
                challenger_pdf_path=contract_pdf,
                prover_secret_key_hex=self.rogue_sk
            ).compile(rogue_witness_pdf)

            with self.assertRaises(PermissionError) as ctx:
                adjudicate_zk_bilateral(contract_pdf, rogue_witness_pdf)
            self.assertIn("Prover public key mismatch", str(ctx.exception))

    def test_subprocess_standalone_runner(self):
        """Both polyglot PDFs must execute autonomously via Python CLI."""
        import subprocess
        project_root = os.path.abspath(os.path.dirname(__file__))
        sub_env = {**os.environ, "PYTHONPATH": project_root}

        with tempfile.TemporaryDirectory() as tmpdir:
            contract_pdf = os.path.join(tmpdir, "runner_contract.pdf")
            witness_pdf = os.path.join(tmpdir, "runner_witness.pdf")

            BilateralZKChallengerPolyglot(
                title="RUNNER CONTRACT",
                statement_id="CLAIM-RUNNER-1",
                target_prover_pk_hex=self.prover_pk,
                author_secret_key_hex=self.challenger_sk
            ).compile(contract_pdf)

            BilateralZKWitnessPolyglot(
                witness_name="Runner Prover",
                challenger_pdf_path=contract_pdf,
                prover_secret_key_hex=self.prover_sk
            ).compile(witness_pdf)

            # Run contract with --cross-prove witness
            proc = subprocess.run(
                [sys.executable, contract_pdf, "--cross-prove", witness_pdf],
                capture_output=True,
                text=True,
                env=sub_env
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("ZERO-KNOWLEDGE BILATERAL SETTLEMENT SOUND & RATIFIED!", proc.stdout)
            self.assertIn("ZK_SETTLED_SOUND", proc.stdout)
            self.assertIn("Joint Merkle Bilateral Settlement Anchor:", proc.stdout)

            # Run witness with --cross-prove contract (commutative execution)
            proc2 = subprocess.run(
                [sys.executable, witness_pdf, "--cross-prove", contract_pdf],
                capture_output=True,
                text=True,
                env=sub_env
            )
            self.assertEqual(proc2.returncode, 0, proc2.stderr)
            self.assertIn("ZERO-KNOWLEDGE BILATERAL SETTLEMENT SOUND & RATIFIED!", proc2.stdout)


if __name__ == "__main__":
    unittest.main()

