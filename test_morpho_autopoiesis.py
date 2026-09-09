#!/usr/bin/env python3
# coding: utf-8
"""
test_morpho_autopoiesis.py — Unit Tests for Morphogenetic Autopoiesis & Agora Federation.
Part of Project Black-Heart (%🖤). Engine #23 Test Suite.
"""

from __future__ import annotations
import os
import sys
import shutil
import tempfile
import unittest
import subprocess

from morpho_autopoiesis import (
    MorphoAutopoiesisReceipt,
    MorphoAutopoieticOrganism,
    create_morpho_autopoietic_seed,
    init_morpho_autopoietic_organism,
    evolve_morpho_autopoietic_organism,
    table_to_agora,
    audit_morpho_autopoietic_organism,
    MORPHO_AUTOPOIESIS_MANIFEST_PREFIX,
)
from agora import initialize_agora_assembly, audit_agora_parliament

class TestMorphoAutopoiesis(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="black_heart_morpho_auto_")
        self.org_pdf = os.path.join(self.test_dir, "morpho_quine.pdf")
        self.agora_pdf = os.path.join(self.test_dir, "agora_parliament.pdf")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_01_genesis_creation(self):
        """Tests that Genesis (Gen 0) organism is compiled with valid keys, PDF, and HUD."""
        org, rec = init_morpho_autopoietic_organism(self.org_pdf)
        self.assertTrue(os.path.exists(self.org_pdf))
        self.assertEqual(org.generation, 0)
        self.assertEqual(rec.generation, 0)
        self.assertTrue(rec.verify())
        self.assertTrue(rec.verify_integrity())

        # Check sidecar key exists
        key_path = f"{self.org_pdf}.key"
        self.assertTrue(os.path.exists(key_path))
        with open(key_path, "r") as kf:
            sk_hex = kf.read().strip()
        self.assertEqual(len(sk_hex), 64)

        # Ensure NO private key bytes in PDF
        with open(self.org_pdf, "rb") as f:
            pdf_bytes = f.read()
        self.assertNotIn(sk_hex.encode("utf-8"), pdf_bytes)

        # Audit passes
        self.assertTrue(audit_morpho_autopoietic_organism(self.org_pdf))

    def test_02_inplace_evolution_append_only(self):
        """Tests that evolution appends revision pages strictly preserving ISO 32000 append-only invariant."""
        org0, rec0 = init_morpho_autopoietic_organism(self.org_pdf)
        with open(self.org_pdf, "rb") as f:
            bytes_gen0 = f.read()

        org1, rec1 = evolve_morpho_autopoietic_organism(self.org_pdf)
        with open(self.org_pdf, "rb") as f:
            bytes_gen1 = f.read()

        self.assertEqual(org1.generation, 1)
        self.assertEqual(rec1.generation, 1)
        self.assertEqual(rec1.parent_hash, rec0.organism_hash)

        # ISO 32000 §7.5.6 invariant: new bytes strictly start with prior bytes
        self.assertTrue(bytes_gen1.startswith(bytes_gen0))
        self.assertGreater(len(bytes_gen1), len(bytes_gen0))

        # Check audit passes on Gen 1
        self.assertTrue(audit_morpho_autopoietic_organism(self.org_pdf))

    def test_03_multi_generational_kinetic_drift(self):
        """Tests multi-generational evolution, kinetic parameter drift, and WL digest calculation."""
        org0, _ = init_morpho_autopoietic_organism(self.org_pdf)
        org1, rec1 = evolve_morpho_autopoietic_organism(self.org_pdf)
        org2, rec2 = evolve_morpho_autopoietic_organism(self.org_pdf)

        self.assertEqual(org2.generation, 2)
        self.assertEqual(len(org2.receipt_chain), 3)

        # Check WL digest length
        self.assertEqual(len(rec2.weisfeiler_lehman_digest), 64)

        # Check kinetic drift
        self.assertGreater(rec2.feed_rate_f, 0.0)
        self.assertGreater(rec2.kill_rate_k, 0.0)

        # Full audit
        self.assertTrue(audit_morpho_autopoietic_organism(self.org_pdf))

    def test_04_tampered_genome_fails_audit(self):
        """Tests that tampering with active combinator chromosomes is caught fail-closed."""
        init_morpho_autopoietic_organism(self.org_pdf)
        evolve_morpho_autopoietic_organism(self.org_pdf)

        with open(self.org_pdf, "rb") as f:
            content = f.read()

        prefix = MORPHO_AUTOPOIESIS_MANIFEST_PREFIX.encode("utf-8")
        idx = content.rfind(prefix)
        manifest = content[idx + len(prefix):].split(b"\n", 1)[0]
        d = manifest.decode("utf-8")

        # Tamper with gene expression
        tampered_d = d.replace("alpha", "corrupted_alpha")
        self.assertNotEqual(d, tampered_d)
        tampered_content = content[:idx + len(prefix)] + tampered_d.encode("utf-8") + content[idx + len(prefix) + len(manifest):]

        with open(self.org_pdf, "wb") as f:
            f.write(tampered_content)

        # Audit must fail
        self.assertFalse(audit_morpho_autopoietic_organism(self.org_pdf))

        # Evolution on tampered file must raise ValueError
        with self.assertRaises(ValueError):
            evolve_morpho_autopoietic_organism(self.org_pdf)

    def test_05_agora_federation_tabling(self):
        """Tests tabling an evolved theorem onto the Mycelial Agora parliament floor."""
        init_morpho_autopoietic_organism(self.org_pdf)
        # Advance generation to produce an algebraic rewrite
        org, rec = evolve_morpho_autopoietic_organism(self.org_pdf)

        # Initialize Agora parliament
        initialize_agora_assembly(self.agora_pdf)
        self.assertTrue(audit_agora_parliament(self.agora_pdf))

        # Table theorem to Agora
        proposal, prop_id = table_to_agora(self.org_pdf, self.agora_pdf, stake_atp=150)
        self.assertTrue(prop_id.startswith("prop_morpho_"))
        self.assertEqual(proposal.stake_atp, 150)
        self.assertTrue(proposal.verify_signature())

        # Agora parliament reflects the new proposal
        self.assertTrue(audit_agora_parliament(self.agora_pdf))

    def test_06_standalone_quine_execution(self):
        """Tests executing the polyglot quine directly via Python subprocess."""
        init_morpho_autopoietic_organism(self.org_pdf)
        evolve_morpho_autopoietic_organism(self.org_pdf)

        # Execute python3 quine.pdf (HUD)
        res = subprocess.run(
            [sys.executable, self.org_pdf],
            capture_output=True,
            text=True
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("PROJECT BLACK-HEART", res.stdout)
        self.assertIn("Generation:        #1", res.stdout)

        # Execute python3 quine.pdf --audit
        res_audit = subprocess.run(
            [sys.executable, self.org_pdf, "--audit"],
            capture_output=True,
            text=True
        )
        self.assertEqual(res_audit.returncode, 0)
        self.assertIn("[+ SOUND]", res_audit.stdout)

if __name__ == "__main__":
    unittest.main()
