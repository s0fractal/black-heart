#!/usr/bin/env python3
"""
test_morphogenesis.py — Comprehensive Unit Tests for Turing Morphogenesis Engine.
Part of Project Black-Heart (%🖤).

Tests:
  1. PDE Numerical Stability & Physical Bounds (u, v in [0.0, 1.0]).
  2. Spontaneous Turing Symmetry Breaking & Bifurcation Variance.
  3. Genotype-to-Phenotype Deterministic Translation.
  4. Generational Morphogenetic Drift & Mutation.
  5. Marching Squares Isocontour Generation.
  6. Standalone Executable Polyglot PDF Verification.
  7. Organism Phenotypic Integration.
"""

import os
import sys
import math
import json
import unittest
import subprocess
import tempfile

from morphogenesis import (
    TuringArchetype,
    MorphogeneticField,
    Phenotype,
    PhenotypeGenesis,
    MorphogeneticRenderer,
    MorphogeneticPolyglotCompiler,
    PALETTES,
)
from organism import create_genesis_organism


class TestTuringMorphogenesis(unittest.TestCase):
    """Rigorous verification suite for Turing Reaction-Diffusion Engine."""

    def test_pde_numerical_stability_and_bounds(self):
        """Verify that forward Euler integration preserves physical concentration bounds [0.0, 1.0]."""
        field = MorphogeneticField(width=32, height=32, F=0.038, k=0.061)
        field.seed_patch(16, 16, radius=5)

        for _ in range(250):
            field.step(dt=1.0)

        for u_val in field.u:
            self.assertFalse(math.isnan(u_val))
            self.assertFalse(math.isinf(u_val))
            self.assertGreaterEqual(u_val, 0.0)
            self.assertLessEqual(u_val, 1.0)

        for v_val in field.v:
            self.assertFalse(math.isnan(v_val))
            self.assertFalse(math.isinf(v_val))
            self.assertGreaterEqual(v_val, 0.0)
            self.assertLessEqual(v_val, 1.0)

    def test_spontaneous_symmetry_breaking(self):
        """Verify that uniform initial substrate undergoes Turing bifurcation into pattern formation."""
        field = MorphogeneticField(width=32, height=32, F=0.029, k=0.057)  # Labyrinth
        field.seed_patch(16, 16, radius=4)

        stats0 = field.statistics()
        field.evolve(steps=300)
        stats_final = field.statistics()

        # Initial variance was small; final variance must be sustained and non-trivial
        self.assertGreater(stats_final["var_v"], 0.005)
        self.assertGreater(stats_final["max_v"], 0.20)
        self.assertEqual(stats_final["steps"], 300)

    def test_deterministic_genotype_to_phenotype_translation(self):
        """Verify that identical genome hashes produce identical phenotypes."""
        hash_a = "0123456789abcdef" * 4
        hash_b = "fedcba9876543210" * 4

        p1, f1 = PhenotypeGenesis.from_hash(hash_a, steps=100, grid_size=24)
        p2, f2 = PhenotypeGenesis.from_hash(hash_a, steps=100, grid_size=24)
        p3, f3 = PhenotypeGenesis.from_hash(hash_b, steps=100, grid_size=24)

        # Determinism check
        self.assertEqual(p1.archetype_key, p2.archetype_key)
        self.assertEqual(p1.F, p2.F)
        self.assertEqual(p1.k, p2.k)
        self.assertEqual(p1.palette_name, p2.palette_name)
        self.assertEqual(f1.v, f2.v)

        # Diversity check
        self.assertNotEqual(p1.genomic_hash, p3.genomic_hash)
        self.assertNotEqual(f1.v, f3.v)

    def test_generational_morphogenetic_drift(self):
        """Verify that sexual/asexual reproduction introduces bounded phenotypic drift."""
        p_parent, f_parent = PhenotypeGenesis.from_hash("cafebabecafebabe" * 4, steps=100, grid_size=24)
        p_child, f_child = PhenotypeGenesis.mutate(p_parent, mutation_rate=0.05, steps=100)

        self.assertEqual(p_child.archetype_key, p_parent.archetype_key)
        self.assertEqual(p_child.grid_width, p_parent.grid_width)
        # Parameters have drifted slightly
        self.assertNotEqual(p_child.genomic_hash, p_parent.genomic_hash)
        self.assertAlmostEqual(p_child.F, p_parent.F, delta=0.005)
        self.assertAlmostEqual(p_child.k, p_parent.k, delta=0.005)

    def test_marching_squares_isocontours(self):
        """Verify that marching squares extracts topological isoline coordinates within [0, 1]."""
        field = MorphogeneticField(width=28, height=28, F=0.038, k=0.061)
        field.seed_patch(14, 14, radius=4)
        field.evolve(steps=150)

        max_v = field.statistics()["max_v"]
        isolines = field.marching_squares_isoline(threshold=max_v * 0.5)
        self.assertGreater(len(isolines), 0)

        for p1, p2 in isolines:
            self.assertGreaterEqual(p1[0], 0.0)
            self.assertLessEqual(p1[0], 1.0)
            self.assertGreaterEqual(p1[1], 0.0)
            self.assertLessEqual(p1[1], 1.0)
            self.assertGreaterEqual(p2[0], 0.0)
            self.assertLessEqual(p2[0], 1.0)
            self.assertGreaterEqual(p2[1], 0.0)
            self.assertLessEqual(p2[1], 1.0)

    def test_polyglot_compiler_dual_layer_execution(self):
        """Verify that compiled PDF is both a valid PDF and executable as Python."""
        phenotype, field = PhenotypeGenesis.from_hash("1122334455667788" * 4, steps=100, grid_size=24, forced_archetype="solitons")

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tf:
            temp_pdf = tf.name

        try:
            MorphogeneticPolyglotCompiler.compile_polyglot(phenotype, field, temp_pdf)
            self.assertTrue(os.path.exists(temp_pdf))
            self.assertGreater(os.path.getsize(temp_pdf), 1000)

            # Test Python execution
            proc = subprocess.run([sys.executable, temp_pdf, "--info"], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, f"Python execution failed:\n{proc.stderr}")
            self.assertIn("TURING MORPHOGENESIS PHENOTYPE", proc.stdout)
            self.assertIn("SOLITONS", proc.stdout)

            # Test PDF parser validation via pdfinfo if available, else assert PDF structure
            import shutil
            if shutil.which("pdfinfo"):
                proc_pdf = subprocess.run(["pdfinfo", temp_pdf], capture_output=True, text=True)
                self.assertEqual(proc_pdf.returncode, 0, f"pdfinfo failed:\n{proc_pdf.stderr}")
            else:
                with open(temp_pdf, "rb") as f:
                    content = f.read()
                self.assertIn(b"%PDF-1.", content)
                self.assertIn(b"%%EOF", content)
        finally:
            if os.path.exists(temp_pdf):
                os.remove(temp_pdf)

    def test_organism_phenotype_integration(self):
        """Verify that Organism can express its morphogenetic phenotype."""
        org = create_genesis_organism(0)
        phenotype, field = org.generate_phenotype(steps=100, grid_size=24)
        self.assertIsInstance(phenotype, Phenotype)
        self.assertIsInstance(field, MorphogeneticField)
        self.assertGreater(len(phenotype.normalized_v), 0)


if __name__ == "__main__":
    unittest.main()
