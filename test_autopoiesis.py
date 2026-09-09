#!/usr/bin/env python3
# coding: utf-8
"""
test_autopoiesis.py — Comprehensive Test Suite for Autopoietic Quine Organisms.
Part of Project Black-Heart (%🖤). Realizing Grok Experiment 1.
"""

from __future__ import annotations
import os
import sys
import json
import tempfile
import unittest
import subprocess

from autopoiesis import (
    init_autopoietic_organism,
    evolve_autopoietic_organism,
    audit_autopoietic_organism,
    AutopoiesisReceipt,
    AUTOPOIESIS_MANIFEST_PREFIX,
    create_autopoietic_seed,
    organism_to_dict,
    organism_from_dict,
)
from crypto import generate_keypair
from metamorphosis import MutationVerdict


class TestAutopoiesisEngine(unittest.TestCase):
    """Test suite verifying autopoietic quine evolution, append-only invariance, and security."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.pdf_path = os.path.join(self.temp_dir.name, "autopoietic_quine.pdf")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_01_genesis_creation(self):
        """Validates that Genesis (Gen #0) initializes with sound cryptographic attestation."""
        org0, rec0 = init_autopoietic_organism(self.pdf_path)

        self.assertTrue(os.path.exists(self.pdf_path))
        self.assertEqual(org0.generation, 0)
        self.assertEqual(rec0.generation, 0)
        self.assertEqual(rec0.parent_hash, "0" * 64)
        self.assertEqual(rec0.organism_hash, org0.organism_hash)
        self.assertTrue(rec0.is_attested())
        self.assertTrue(rec0.verify())

        with open(self.pdf_path, "rb") as f:
            content = f.read()

        # Dual-spine assertions
        self.assertTrue(content.startswith(b"%PDF-1.4\n") or b"%PDF-1.4" in content[:1024])
        self.assertIn(b"%%EOF", content)
        self.assertIn(b"AUTOPOIESIS_RECEIPT_CHAIN:", content)

    def test_02_inplace_evolution_and_append_only(self):
        """Verifies multi-generational in-place self-evolution preserves ISO 32000 append-only bytes."""
        # 1. Genesis
        org0, rec0 = init_autopoietic_organism(self.pdf_path)
        with open(self.pdf_path, "rb") as f:
            bytes0 = f.read()

        # 2. Generation 1
        org1, rec1 = evolve_autopoietic_organism(self.pdf_path)
        with open(self.pdf_path, "rb") as f:
            bytes1 = f.read()

        self.assertTrue(bytes1.startswith(bytes0), "Gen 1 must strictly preserve all Gen 0 bytes")
        self.assertEqual(org1.generation, 1)
        self.assertEqual(rec1.parent_hash, org0.organism_hash)
        self.assertEqual(rec1.organism_hash, org1.organism_hash)
        self.assertTrue(rec1.verify())
        self.assertGreater(rec1.atp_saved, 0)

        # 3. Generation 2
        org2, rec2 = evolve_autopoietic_organism(self.pdf_path)
        with open(self.pdf_path, "rb") as f:
            bytes2 = f.read()

        self.assertTrue(bytes2.startswith(bytes1), "Gen 2 must strictly preserve all Gen 1 bytes")
        self.assertEqual(org2.generation, 2)
        self.assertEqual(rec2.parent_hash, org1.organism_hash)
        self.assertEqual(rec2.organism_hash, org2.organism_hash)
        self.assertTrue(rec2.verify())

        # 4. End-to-end audit
        ok, msg = audit_autopoietic_organism(self.pdf_path)
        self.assertTrue(ok)
        self.assertIn("ALL 3 GENERATIONS CRYPTOGRAPHICALLY & SEMANTICALLY SOUND", msg)

    def test_03_cumulative_scientific_ledger(self):
        """Verifies that the empirical ledger accumulates both accepted mutations and rejected counterexamples."""
        init_autopoietic_organism(self.pdf_path)
        evolve_autopoietic_organism(self.pdf_path)

        with open(self.pdf_path, "rb") as f:
            content = f.read()

        prefix = AUTOPOIESIS_MANIFEST_PREFIX.encode("utf-8")
        idx = content.rfind(prefix)
        end_idx = content.find(b"\n", idx)
        manifest = json.loads(content[idx + len(prefix):end_idx].decode("utf-8"))

        exps = manifest.get("experiments", [])
        self.assertGreater(len(exps), 5)

        accepted = [e for e in exps if e["verdict"] == MutationVerdict.ACCEPTED_MORE_EFFICIENT.value]
        rejected = [e for e in exps if e["verdict"] == MutationVerdict.REJECTED_SEMANTIC_MISMATCH.value]

        self.assertGreater(len(accepted), 0)
        self.assertGreater(len(rejected), 0)

        # Assert rejected counterexamples record divergence detail
        for r in rejected:
            self.assertIsNotNone(r.get("discrepancy_detail"))

    def test_04_fail_closed_tampered_receipt(self):
        """Asserts that modifying any receipt field fails closed."""
        init_autopoietic_organism(self.pdf_path)
        evolve_autopoietic_organism(self.pdf_path)

        with open(self.pdf_path, "rb") as f:
            content = f.read()

        prefix = AUTOPOIESIS_MANIFEST_PREFIX.encode("utf-8")
        idx = content.rfind(prefix)
        end_idx = content.find(b"\n", idx)
        manifest = json.loads(content[idx + len(prefix):end_idx].decode("utf-8"))

        # Tamper with ATP saved in latest receipt
        manifest["receipts"][-1]["atp_saved"] = 999

        tampered_bytes = (
            content[:idx + len(prefix)] +
            json.dumps(manifest, separators=(",", ":"), ensure_ascii=True).encode("utf-8") +
            content[end_idx:]
        )

        tampered_pdf = os.path.join(self.temp_dir.name, "tampered.pdf")
        with open(tampered_pdf, "wb") as f:
            f.write(tampered_bytes)

        with self.assertRaises(ValueError):
            audit_autopoietic_organism(tampered_pdf)

    def test_05_fail_closed_broken_lineage(self):
        """Asserts that breaking the parent hash linkage fails closed."""
        init_autopoietic_organism(self.pdf_path)
        evolve_autopoietic_organism(self.pdf_path)

        with open(self.pdf_path, "rb") as f:
            content = f.read()

        prefix = AUTOPOIESIS_MANIFEST_PREFIX.encode("utf-8")
        idx = content.rfind(prefix)
        end_idx = content.find(b"\n", idx)
        manifest = json.loads(content[idx + len(prefix):end_idx].decode("utf-8"))

        # Break parent hash
        manifest["receipts"][-1]["parent_hash"] = "deadbeef" * 8

        tampered_bytes = (
            content[:idx + len(prefix)] +
            json.dumps(manifest, separators=(",", ":"), ensure_ascii=True).encode("utf-8") +
            content[end_idx:]
        )

        tampered_pdf = os.path.join(self.temp_dir.name, "broken_lineage.pdf")
        with open(tampered_pdf, "wb") as f:
            f.write(tampered_bytes)

        with self.assertRaises(ValueError):
            audit_autopoietic_organism(tampered_pdf)

    def test_06_standalone_subprocess_execution(self):
        """Verifies that the polyglot executes directly with python3 without external dependencies."""
        init_autopoietic_organism(self.pdf_path)

        # 1. python3 quine.pdf (default self-evolution)
        res_evolve = subprocess.run([sys.executable, self.pdf_path], capture_output=True, text=True)
        self.assertEqual(res_evolve.returncode, 0, f"Error: {res_evolve.stderr}")
        self.assertIn("[EVOLUTION ACCOMPLISHED]", res_evolve.stdout)

        # 2. python3 quine.pdf --info
        res_info = subprocess.run([sys.executable, self.pdf_path, "--info"], capture_output=True, text=True)
        self.assertEqual(res_info.returncode, 0, f"Error: {res_info.stderr}")
        self.assertIn("Current Generation:   #1", res_info.stdout)

        # 3. python3 quine.pdf --audit
        res_audit = subprocess.run([sys.executable, self.pdf_path, "--audit"], capture_output=True, text=True)
        self.assertEqual(res_audit.returncode, 0, f"Error: {res_audit.stderr}")
        self.assertIn("ALL 2 GENERATIONS CRYPTOGRAPHICALLY & SEMANTICALLY SOUND", res_audit.stdout)

        # 4. python3 quine.pdf --experiments
        res_exp = subprocess.run([sys.executable, self.pdf_path, "--experiments"], capture_output=True, text=True)
        self.assertEqual(res_exp.returncode, 0, f"Error: {res_exp.stderr}")
        self.assertIn("EMPIRICAL SCIENTIFIC LEDGER", res_exp.stdout)

        # 5. python3 quine.pdf --genome
        res_gen = subprocess.run([sys.executable, self.pdf_path, "--genome"], capture_output=True, text=True)
        self.assertEqual(res_gen.returncode, 0, f"Error: {res_gen.stderr}")
        self.assertIn("COMBINATOR GENOME", res_gen.stdout)

    def test_07_cli_autopoiesis_commands(self):
        """Verifies cli.py autopoiesis {init, evolve, audit, experiments, genome}."""
        repo_root = os.path.dirname(os.path.abspath(__file__))
        cli_py = os.path.join(repo_root, "cli.py")
        cli_pdf = os.path.join(self.temp_dir.name, "cli_test_org.pdf")

        # init
        res_init = subprocess.run(
            [sys.executable, cli_py, "autopoiesis", "init", "-o", cli_pdf],
            capture_output=True, text=True
        )
        self.assertEqual(res_init.returncode, 0, f"Error: {res_init.stderr}")
        self.assertIn("Generation #0", res_init.stdout)

        # evolve
        res_ev = subprocess.run(
            [sys.executable, cli_py, "autopoiesis", "evolve", cli_pdf],
            capture_output=True, text=True
        )
        self.assertEqual(res_ev.returncode, 0, f"Error: {res_ev.stderr}")
        self.assertIn("Generation #1 Appended In-Place!", res_ev.stdout)

        # audit
        res_aud = subprocess.run(
            [sys.executable, cli_py, "autopoiesis", "audit", cli_pdf],
            capture_output=True, text=True
        )
        self.assertEqual(res_aud.returncode, 0, f"Error: {res_aud.stderr}")
        self.assertIn("CRYPTOGRAPHICALLY & SEMANTICALLY SOUND", res_aud.stdout)

        # experiments
        res_exp = subprocess.run(
            [sys.executable, cli_py, "autopoiesis", "experiments", cli_pdf],
            capture_output=True, text=True
        )
        self.assertEqual(res_exp.returncode, 0, f"Error: {res_exp.stderr}")
        self.assertIn("EMPIRICAL SCIENTIFIC LEDGER", res_exp.stdout)

        # genome
        res_gen = subprocess.run(
            [sys.executable, cli_py, "autopoiesis", "genome", cli_pdf],
            capture_output=True, text=True
        )
        self.assertEqual(res_gen.returncode, 0, f"Error: {res_gen.stderr}")
        self.assertIn("ACTIVE COMBINATOR GENOME", res_gen.stdout)


if __name__ == "__main__":
    unittest.main()
