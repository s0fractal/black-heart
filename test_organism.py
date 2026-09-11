#!/usr/bin/env python3
"""
test_organism.py — Unit Tests for Autonomous Self-Replicating Polyglot Organisms.
Part of Project Black-Heart (%🖤).
"""

import os
import sys
import unittest
import tempfile
import subprocess
import json

from crypto import generate_keypair
from keystore import PRIVATE_KEY_SUFFIX
from organism import Organism, Chromosome, PolyglotOrganismCompiler

class TestAutonomousOrganism(unittest.TestCase):
    """Verifies metabolic fitness, genetic mutation, and quine polyglot replication."""

    def setUp(self):
        self.sk, self.pk = generate_keypair()
        self.chromosomes = [
            Chromosome(
                gene_id="G1",
                gene_name="Identity Gene",
                expression="🌿 🖤 🖤 Core",
                expected_normal_form="Core",
                max_atp=20
            ),
            Chromosome(
                gene_id="G2",
                gene_name="Entropy Filter",
                expression="🖤 Clean Waste",
                expected_normal_form="Clean",
                max_atp=10
            )
        ]
        self.org = Organism(
            generation=0,
            parent_hash="00" * 32,
            public_key_hex=self.pk,
            secret_key_hex=self.sk,
            chromosomes=self.chromosomes
        )

    def test_metabolic_fitness_sound(self):
        """Healthy organism must pass metabolic fitness check."""
        viable, atp = self.org.run_metabolism()
        self.assertTrue(viable)
        self.assertGreater(atp, 0)
        self.assertTrue(all(c.vital for c in self.org.chromosomes))

    def test_metabolic_fitness_lethal_mutation(self):
        """Organism with diverging or refuted chromosome must fail fitness test."""
        sick_org = Organism(
            generation=0,
            parent_hash="00" * 32,
            public_key_hex=self.pk,
            secret_key_hex=self.sk,
            chromosomes=[
                Chromosome("G_FAIL", "Refuted Gene", "🖤 False Truth", "Truth") # expects Truth, but K gives False
            ]
        )
        viable, _ = sick_org.run_metabolism()
        self.assertFalse(viable)

    def test_reproduction_lineage(self):
        """Child organism must inherit parent hash, have generation + 1, and unique keys."""
        child = self.org.reproduce(mutation_rate=0.0)
        self.assertEqual(child.generation, 1)
        self.assertEqual(child.parent_hash, self.org.organism_hash)
        self.assertNotEqual(child.public_key_hex, self.org.public_key_hex)
        self.assertEqual(len(child.chromosomes), len(self.org.chromosomes))

    def test_quine_polyglot_execution_and_reproduction(self):
        """Validates standalone subprocess execution of the compiled organism PDF."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "organism_gen0.pdf")
            PolyglotOrganismCompiler.compile(self.org, pdf_path)
            self.assertTrue(os.path.exists(pdf_path))

            # 1. Test --status
            res_status = subprocess.run(
                [sys.executable, pdf_path, "--status"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            self.assertEqual(res_status.returncode, 0)
            self.assertIn("BLACK-HEART — AUTONOMOUS SELF-REPRODUCING ORGANISM", res_status.stdout)
            self.assertIn("#0000", res_status.stdout)

            # 2. Test --reproduce
            res_rep = subprocess.run(
                [sys.executable, pdf_path, "--reproduce"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            self.assertEqual(res_rep.returncode, 0)
            self.assertIn("[✓ METABOLISM SOUND]", res_rep.stdout)
            self.assertIn("[⚓ SUCCESS] BORN OFFSPRING: Gen #0001!", res_rep.stdout)

            # Verify child file exists in tempdir. Since S5a the child's secret
            # key is written to its own sidecar, not into the public PDF, so the
            # directory holds the child document and, separately, its key.
            files = [f for f in os.listdir(tmpdir)
                     if f.startswith("organism_gen0001_") and f.endswith(".pdf")]
            self.assertEqual(len(files), 1)
            child_pdf = os.path.join(tmpdir, files[0])
            self.assertEqual(os.stat(child_pdf + PRIVATE_KEY_SUFFIX).st_mode & 0o777, 0o600)

            # Child must be runnable and able to report its own status
            res_child = subprocess.run(
                [sys.executable, child_pdf, "--status"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            self.assertEqual(res_child.returncode, 0)
            self.assertIn("#0001", res_child.stdout)

if __name__ == "__main__":
    unittest.main()
