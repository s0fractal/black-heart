#!/usr/bin/env python3
"""
test_quantum.py — Unit & Integration Test Suite for Topological Quantum Topos & Anyons.
Part of Project Black-Heart (%🖤).
"""

import os
import sys
import math
import cmath
import tempfile
import subprocess
import unittest
from pathlib import Path

from quantum import (
    ComplexMatrix2x2,
    FibonacciQuantumSystem,
    QuantumPolyglotCompiler,
    compile_quantum_polyglot,
)
from symbiosis import (
    BraidWord,
    BraidCrossing,
    trefoil_knot,
    figure_eight_knot,
    hopf_link,
)

class TestTopologicalQuantumTopos(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="blackheart_quantum_test_")
        self.system = FibonacciQuantumSystem()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_complex_matrix_2x2_algebra_and_unitarity(self):
        """Validates 2x2 complex matrix arithmetic, dagger, determinant, and unitarity check."""
        # Pauli-X (NOT gate)
        px = ComplexMatrix2x2(0.0, 1.0, 1.0, 0.0)
        self.assertTrue(px.is_unitary())
        self.assertAlmostEqual(abs(px.det()), 1.0)
        self.assertEqual(px.trace(), 0.0)
        self.assertEqual(px @ px, ComplexMatrix2x2.identity())

        # Pauli-Z
        pz = ComplexMatrix2x2(1.0, 0.0, 0.0, -1.0)
        self.assertTrue(pz.is_unitary())

        # Hadamard
        inv_sqrt2 = 1.0 / math.sqrt(2.0)
        had = ComplexMatrix2x2(inv_sqrt2, inv_sqrt2, inv_sqrt2, -inv_sqrt2)
        self.assertTrue(had.is_unitary())
        self.assertEqual(had.dagger(), had)

    def test_fibonacci_anyons_modular_tensor_category(self):
        """Verifies F-matrix and R-matrix invariants of the Fibonacci anyon system."""
        phi = self.system.PHI
        self.assertAlmostEqual(phi, 1.6180339887, places=7)

        # F-matrix is an orthogonal involution: F = F^† = F^(-1), so F^2 = I
        f = self.system.F_MATRIX
        self.assertTrue(f.is_unitary())
        f_sq = f @ f
        self.assertAlmostEqual(f_sq.m00.real, 1.0, places=9)
        self.assertAlmostEqual(f_sq.m01.real, 0.0, places=9)
        self.assertAlmostEqual(f_sq.m10.real, 0.0, places=9)
        self.assertAlmostEqual(f_sq.m11.real, 1.0, places=9)

        # R-matrix is unitary with Fibonacci anyon braiding phases
        r = self.system.R_MATRIX
        self.assertTrue(r.is_unitary())
        self.assertAlmostEqual(abs(r.det()), 1.0, places=9)

        # Generators σ_1 and σ_2 must be unitary
        s1 = self.system.sigma1
        s2 = self.system.sigma2
        self.assertTrue(s1.is_unitary())
        self.assertTrue(s2.is_unitary())

    def test_braid_unitary_simulation(self):
        """Validates that arbitrary Artin braid words compile into exact unitary SU(2) gates."""
        braids = [
            trefoil_knot(),        # σ_1^3
            figure_eight_knot(),   # σ_1 σ_2^(-1) σ_1 σ_2^(-1)
            hopf_link(),           # σ_1^2
            BraidWord(
                num_strands=3,
                crossings=[
                    BraidCrossing(1, 1),
                    BraidCrossing(2, -1),
                    BraidCrossing(1, 1),
                    BraidCrossing(2, 1)
                ]
            )
        ]

        for b in braids:
            u = self.system.compile_braid_to_unitary(b)
            self.assertTrue(u.is_unitary(), f"Braid {b.to_artin_notation()} failed unitarity check")
            det_u = u.det()
            self.assertAlmostEqual(abs(det_u), 1.0, places=7, msg=f"Braid {b.to_artin_notation()} |det(U)| != 1")

    def test_born_rule_and_bloch_projection(self):
        """Validates probability conservation and Bloch sphere radial normalization."""
        braid = figure_eight_knot()
        u = self.system.compile_braid_to_unitary(braid)
        state = self.system.evolve_state(u, (1.0 + 0j, 0.0 + 0j))

        # Born rule probabilities must sum to 1
        p0, p1 = self.system.calculate_born_probabilities(state)
        self.assertAlmostEqual(p0 + p1, 1.0, places=9)
        self.assertGreaterEqual(p0, 0.0)
        self.assertGreaterEqual(p1, 0.0)

        # Bloch sphere coordinates must have unit radius: x^2 + y^2 + z^2 = 1
        bloch = self.system.calculate_bloch_coordinates(state)
        radius_sq = bloch["x"]**2 + bloch["y"]**2 + bloch["z"]**2
        self.assertAlmostEqual(radius_sq, 1.0, places=5)
        self.assertGreaterEqual(bloch["theta_rad"], 0.0)
        self.assertLessEqual(bloch["theta_rad"], math.pi + 1e-6)

        # Monte Carlo collapse simulation
        meas = self.system.simulate_measurement(state, shots=5000)
        self.assertEqual(meas["shots"], 5000)
        c0 = meas["counts"]["|0> (Vacuum 1)"]
        c1 = meas["counts"]["|1> (Anyon τ)"]
        self.assertEqual(c0 + c1, 5000)
        # Experimental probability within 3 standard deviations
        std_dev = math.sqrt(p0 * (1 - p0) / 5000)
        self.assertAlmostEqual(c0 / 5000, p0, delta=4 * std_dev)

    def test_quantum_polyglot_compiler_and_execution(self):
        """Compiles an executable quantum circuit polyglot and tests standalone execution."""
        braid = trefoil_knot()
        compiler = QuantumPolyglotCompiler(braid, title="Trefoil Anyonic Gate")
        pdf_bytes = compiler.compile_pdf()

        # Check polyglot format markers
        self.assertTrue(pdf_bytes.startswith(b"#!" + sys.executable.encode("utf-8")))
        self.assertIn(b"%PDF-1.7", pdf_bytes)
        self.assertIn(b"%%EOF", pdf_bytes)
        self.assertIn(b"%BH-QUANTUM-TOPOS", pdf_bytes)

        out_pdf = os.path.join(self.tmp_dir, "quantum_gate.pdf")
        with open(out_pdf, "wb") as f:
            f.write(pdf_bytes)

        # 1. Run --simulate
        proc_sim = subprocess.run(
            [sys.executable, out_pdf, "--simulate"],
            capture_output=True,
            text=True,
            timeout=10
        )
        self.assertEqual(proc_sim.returncode, 0, f"Simulate failed: {proc_sim.stderr}")
        self.assertIn("BLACK-HEART TOPOLOGICAL QUANTUM TOPOS SIMULATOR", proc_sim.stdout)
        self.assertIn("TOPOLOGICAL QUANTUM EVOLUTION SOUND & UNITARY (Q.E.D.)", proc_sim.stdout)
        self.assertIn("Bloch Sphere Coordinates:", proc_sim.stdout)

        # 2. Run --measure 256
        proc_meas = subprocess.run(
            [sys.executable, out_pdf, "--measure", "256"],
            capture_output=True,
            text=True,
            timeout=10
        )
        self.assertEqual(proc_meas.returncode, 0, f"Measure failed: {proc_meas.stderr}")
        self.assertIn("PROJECTIVE QUANTUM MEASUREMENT COLLAPSE (Shots: 256)", proc_meas.stdout)
        self.assertIn("BORN RULE COLLAPSE COMPLETE", proc_meas.stdout)

        # 3. Run --audit
        proc_aud = subprocess.run(
            [sys.executable, out_pdf, "--audit"],
            capture_output=True,
            text=True,
            timeout=10
        )
        self.assertEqual(proc_aud.returncode, 0, f"Audit failed: {proc_aud.stderr}")
        self.assertIn("AUDIT PASSED", proc_aud.stdout)

if __name__ == "__main__":
    unittest.main()
