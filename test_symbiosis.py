#!/usr/bin/env python3
"""
test_symbiosis.py — Unit & Integration Test Suite for Dialectical Symbiosis & Topological Knot Morphogenesis.
Part of Project Black-Heart (%🖤).
"""

import os
import sys
import io
import json
import copy
import tempfile
import subprocess
import unittest
from pathlib import Path

from symbiosis import (
    BraidWord,
    BraidCrossing,
    trefoil_knot,
    figure_eight_knot,
    hopf_link,
    render_braid_knot_pdf_stream,
    dialectical_crossover,
    dialectical_combinatory_synthesis,
    amalgamate_dual_vaults,
    SymbiosisPolyglotCompiler,
    synthesize_polyglots,
)
from organism import create_genesis_organism, Organism, Chromosome
import vault as V
import crypto as C

class TestDialecticalSymbiosis(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="blackheart_symbiosis_test_")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    # ========================================================================
    # 1. Braid Group Algebra & Knot Invariants
    # ========================================================================
    def test_braid_algebra_and_invariants(self):
        """Validates Artin braid group operations and topological invariants."""
        # 1. Trefoil knot: σ_1^3 on 2 strands
        trefoil = trefoil_knot()
        self.assertEqual(trefoil.num_strands, 2)
        self.assertEqual(trefoil.crossing_number, 3)
        self.assertEqual(trefoil.writhe, 3)
        self.assertEqual(trefoil.count_link_components(), 1)  # Knot
        self.assertIn("σ_1", trefoil.to_artin_notation())

        # 2. Figure-eight knot: σ_1 σ_2^(-1) σ_1 σ_2^(-1) on 3 strands
        fig8 = figure_eight_knot()
        self.assertEqual(fig8.num_strands, 3)
        self.assertEqual(fig8.crossing_number, 4)
        self.assertEqual(fig8.writhe, 0)  # Amphicheiral knot has zero writhe
        self.assertEqual(fig8.count_link_components(), 1)  # Knot

        # 3. Hopf link: σ_1^2 on 2 strands
        hopf = hopf_link()
        self.assertEqual(hopf.num_strands, 2)
        self.assertEqual(hopf.crossing_number, 2)
        self.assertEqual(hopf.writhe, 2)
        self.assertEqual(hopf.count_link_components(), 2)  # Link with 2 components

        # 4. Invalid generator bounds must raise ValueError
        with self.assertRaises(ValueError):
            BraidWord.from_generators(2, [2])  # generator 2 on 2 strands invalid
        with self.assertRaises(ValueError):
            BraidWord.from_generators(3, [0])  # generator 0 invalid

    # ========================================================================
    # 2. Native ISO 32000 PDF Vector Ribbon Knot Renderer
    # ========================================================================
    def test_pdf_bezier_knot_rendering(self):
        """Validates that knot renderer outputs valid ISO 32000 vector stream operators."""
        fig8 = figure_eight_knot()
        stream = render_braid_knot_pdf_stream(fig8, x=50, y=200, width=400, height=200)

        self.assertIsInstance(stream, str)
        self.assertTrue(stream.startswith("q"))
        self.assertTrue(stream.endswith("Q"))
        # Must contain cubic bezier curves (c operator)
        self.assertIn(" c ", stream)
        # Must contain moveto and stroke operators
        self.assertIn(" m\n", stream)
        self.assertIn(" S", stream)
        # Must contain color operators
        self.assertIn(" RG", stream)

    # ========================================================================
    # 3. Homologous Crossover & Dialectical Synthesis
    # ========================================================================
    def test_dialectical_crossover_and_metabolism(self):
        """Parent A (Thesis) + Parent B (Antithesis) produce viable offspring with combined genome."""
        parent_a = create_genesis_organism()
        parent_b = create_genesis_organism()

        # Give Parent B a distinct identity and extra chromosome
        sk_b, pk_b = C.generate_keypair()
        parent_b.secret_key_hex = sk_b
        parent_b.public_key_hex = pk_b
        parent_b.chromosomes.append(
            Chromosome(
                gene_id="GENE_ANTITHESIS_SIGNAL",
                gene_name="Antithetical Sensor",
                expression="🖤 Truth Mirage",
                expected_normal_form="Truth",
                max_atp=100,
                atp_burned=1,
                vital=True
            )
        )
        parent_b.organism_hash = parent_b.compute_hash()

        child, braid = dialectical_crossover(parent_a, parent_b)

        self.assertEqual(child.generation, 1)
        self.assertNotEqual(child.public_key_hex, parent_a.public_key_hex)
        self.assertNotEqual(child.public_key_hex, parent_b.public_key_hex)
        self.assertTrue(child.verify())

        # Child inherits chromosomes from both parents
        gene_ids = [c.gene_id for c in child.chromosomes]
        self.assertIn("GENE_ANTITHESIS_SIGNAL", gene_ids)
        self.assertIn("GENE_DIALECTICAL_SYNTHESIS", gene_ids)

        # Child metabolism must be sound and viable
        viable, total_atp = child.run_metabolism()
        self.assertTrue(viable)
        self.assertGreater(total_atp, 0)

        # Braid must be non-trivial
        self.assertGreaterEqual(braid.crossing_number, 3)

        # Tampering with parent must be fail-closed
        tampered_parent = copy.deepcopy(parent_a)
        tampered_parent.public_key_hex = "0" * 64
        with self.assertRaises(ValueError):
            dialectical_crossover(tampered_parent, parent_b)

    # ========================================================================
    # 4. Dual-Vault Amalgamation
    # ========================================================================
    def test_dual_vault_amalgamation(self):
        """Merges two independent parental code vaults into a single deterministic vault."""
        # Create vault A
        dir_a = os.path.join(self.tmp_dir, "vault_src_a")
        os.makedirs(dir_a)
        with open(os.path.join(dir_a, "module_a.py"), "w") as f:
            f.write("# Module A from Thesis\nALPHA = 42\n")
        vault_a, _, _ = V.pack_files_to_vault(["module_a.py"], dir_a)

        # Create vault B
        dir_b = os.path.join(self.tmp_dir, "vault_src_b")
        os.makedirs(dir_b)
        with open(os.path.join(dir_b, "module_b.py"), "w") as f:
            f.write("# Module B from Antithesis\nBETA = 100\n")
        vault_b, _, _ = V.pack_files_to_vault(["module_b.py"], dir_b)

        merged_vault, v_hash = amalgamate_dual_vaults(vault_a, vault_b)
        self.assertIsInstance(merged_vault, bytes)
        self.assertEqual(len(v_hash), 64)

        # Unpack merged vault and verify both modules exist
        dest_unpack = os.path.join(self.tmp_dir, "unpacked_merged")
        unpacked = V.unpack_vault_bytes(merged_vault, dest_unpack)
        self.assertIn("module_a.py", unpacked)
        self.assertIn("module_b.py", unpacked)

        with open(os.path.join(dest_unpack, "module_a.py")) as f:
            self.assertIn("ALPHA = 42", f.read())
        with open(os.path.join(dest_unpack, "module_b.py")) as f:
            self.assertIn("BETA = 100", f.read())

    # ========================================================================
    # 5. Full Symbiotic Polyglot Compiler & Execution
    # ========================================================================
    def test_symbiosis_polyglot_compiler_and_execution(self):
        """Compiles a child polyglot document and verifies standalone Python execution."""
        parent_a = create_genesis_organism()
        parent_b = create_genesis_organism()
        child, braid = dialectical_crossover(parent_a, parent_b)

        compiler = SymbiosisPolyglotCompiler(child, parent_a, parent_b, braid)
        pdf_bytes = compiler.compile_pdf()

        # Polyglot structure checks
        self.assertTrue(pdf_bytes.startswith(b"#!" + sys.executable.encode("utf-8")))
        self.assertIn(b"%PDF-1.7", pdf_bytes)
        self.assertIn(b"%%EOF", pdf_bytes)

        out_pdf = os.path.join(self.tmp_dir, "symbiotic_child.pdf")
        with open(out_pdf, "wb") as f:
            f.write(pdf_bytes)

        # Execute polyglot as standalone script
        proc = subprocess.run(
            [sys.executable, out_pdf, "--lineage"],
            capture_output=True,
            text=True,
            timeout=10
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn("BLACK-HEART DIALECTICAL SYMBIOSIS LINEAGE AUDITOR", proc.stdout)
        self.assertIn("SYMBIOTIC LINEAGE & METABOLIC PROVENANCE VERIFIED (Q.E.D.)", proc.stdout)

if __name__ == "__main__":
    unittest.main()
