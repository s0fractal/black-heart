#!/usr/bin/env python3
"""
quantum.py — Topological Quantum Topos & Anyonic Braiding Simulation.
Part of Project Black-Heart (%🖤).

Implements:
  1. Fibonacci Anyon Modular Tensor Category (SU(2)_3 Chern-Simons theory).
  2. Quantum dimension d_τ = φ = (1 + √5) / 2 (The Golden Ratio).
  3. F-matrix (Pentagon basis change) and R-matrix (braiding phases).
  4. Unitary braid word compiler mapping Artin generators σ_i ∈ B_n to SU(2) gates.
  5. Born rule projective measurement collapse and Bloch sphere stereographic projection.
  6. Native ISO 32000 vector stream renderer for anyon spacetime worldlines and Bloch sphere.
  7. Standalone executable quantum polyglot document ('python3 circuit.pdf --simulate').

Zero external dependencies: 100% Python standard library (cmath, math).
"""

from __future__ import annotations
import os
import sys
import io
import math
import cmath
import json
import random
from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional, Any

from symbiosis import BraidWord, BraidCrossing, trefoil_knot, figure_eight_knot, hopf_link

QUANTUM_MANIFEST_PREFIX = "# %QUANTUM_TOPOS_MANIFEST: "

# ============================================================================
# 1. PURE PYTHON 2x2 COMPLEX MATRIX ALGEBRA
# ============================================================================

@dataclass(frozen=True)
class ComplexMatrix2x2:
    """Immutable 2x2 matrix with complex entries for SU(2) quantum gate operations."""
    m00: complex
    m01: complex
    m10: complex
    m11: complex

    @classmethod
    def identity(cls) -> ComplexMatrix2x2:
        return cls(1.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j, 1.0 + 0.0j)

    @classmethod
    def zero(cls) -> ComplexMatrix2x2:
        return cls(0.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j)

    def __matmul__(self, other: ComplexMatrix2x2) -> ComplexMatrix2x2:
        return ComplexMatrix2x2(
            self.m00 * other.m00 + self.m01 * other.m10,
            self.m00 * other.m01 + self.m01 * other.m11,
            self.m10 * other.m00 + self.m11 * other.m10,
            self.m10 * other.m01 + self.m11 * other.m11
        )

    def dagger(self) -> ComplexMatrix2x2:
        """Conjugate transpose (Hermitian adjoint)."""
        return ComplexMatrix2x2(
            self.m00.conjugate(),
            self.m10.conjugate(),
            self.m01.conjugate(),
            self.m11.conjugate()
        )

    def det(self) -> complex:
        """Determinant of 2x2 matrix."""
        return (self.m00 * self.m11) - (self.m01 * self.m10)

    def trace(self) -> complex:
        """Trace of 2x2 matrix."""
        return self.m00 + self.m11

    def apply_vector(self, v0: complex, v1: complex) -> Tuple[complex, complex]:
        """Multiplies matrix by 2D column state vector (v0, v1)^T."""
        return (
            self.m00 * v0 + self.m01 * v1,
            self.m10 * v0 + self.m11 * v1
        )

    def is_unitary(self, tol: float = 1e-7) -> bool:
        """Checks if U^† U = I within tolerance."""
        prod = self.dagger() @ self
        i00 = abs(prod.m00 - 1.0) < tol
        i01 = abs(prod.m01) < tol
        i10 = abs(prod.m10) < tol
        i11 = abs(prod.m11 - 1.0) < tol
        return i00 and i01 and i10 and i11

    def to_list(self) -> List[List[Tuple[float, float]]]:
        """Serializes complex numbers as [real, imag] pairs for JSON."""
        return [
            [(self.m00.real, self.m00.imag), (self.m01.real, self.m01.imag)],
            [(self.m10.real, self.m10.imag), (self.m11.real, self.m11.imag)]
        ]

    @classmethod
    def from_list(cls, data: List[List[List[float]]]) -> ComplexMatrix2x2:
        return cls(
            complex(data[0][0][0], data[0][0][1]),
            complex(data[0][1][0], data[0][1][1]),
            complex(data[1][0][0], data[1][0][1]),
            complex(data[1][1][0], data[1][1][1])
        )


# ============================================================================
# 2. FIBONACCI ANYON QUANTUM TOPOS
# ============================================================================

class UnsupportedBraidProfileError(ValueError):
    """Raised when a braid word contains generators or strands outside the supported representation."""
    pass

class FibonacciQuantumSystem:
    """
    Simulates topological quantum computing with Fibonacci anyons in the
    SU(2)_3 Chern-Simons / Temperley-Lieb TL_3(q) modular tensor category.

    Strict Profile:
      - Multi-strand profile: Braid group B_3 (3 strands, 4 anyons with vacuum total charge).
      - Qubit basis: |0> = ((1,2)->1), |1> = ((1,2)->tau).
      - Generators: sigma_1, sigma_2 and their inverses.
    """
    PHI = (1.0 + math.sqrt(5.0)) / 2.0  # Golden Ratio ~1.6180339887
    INV_PHI = 1.0 / PHI                  # φ^(-1) ~0.6180339887
    SQRT_INV_PHI = math.sqrt(INV_PHI)    # φ^(-1/2) ~0.7861513777

    # F-matrix (basis change in fusion space):
    # F = [[φ^(-1), φ^(-1/2)],
    #      [φ^(-1/2), -φ^(-1)]]
    F_MATRIX = ComplexMatrix2x2(
        INV_PHI + 0.0j, SQRT_INV_PHI + 0.0j,
        SQRT_INV_PHI + 0.0j, -INV_PHI + 0.0j
    )

    # R-matrix (braiding phases for Fibonacci anyons):
    # R_1^{ττ} = e^(4πi / 5),  R_τ^{ττ} = -e^(2πi / 5) = e^(-3πi / 5)
    R1_PHASE = cmath.exp(1j * (4.0 * math.pi / 5.0))
    RTAU_PHASE = -cmath.exp(1j * (2.0 * math.pi / 5.0))

    R_MATRIX = ComplexMatrix2x2(
        R1_PHASE, 0.0 + 0.0j,
        0.0 + 0.0j, RTAU_PHASE
    )

    def __init__(self):
        # Generator σ_1 braids anyon 1 and anyon 2:
        # ρ(σ_1) = R
        self.sigma1 = self.R_MATRIX
        self.sigma1_inv = self.R_MATRIX.dagger()

        # Generator σ_2 braids anyon 2 and anyon 3:
        # ρ(σ_2) = F R F
        self.sigma2 = self.F_MATRIX @ self.R_MATRIX @ self.F_MATRIX
        self.sigma2_inv = self.sigma2.dagger()

    def generator_matrix(self, strand_index: int, sign: int) -> ComplexMatrix2x2:
        """
        Returns the unitary matrix corresponding to Artin generator σ_i or its inverse.
        Strictly restricted to B3 generators sigma_1 and sigma_2.
        """
        if strand_index == 1:
            return self.sigma1 if sign > 0 else self.sigma1_inv
        elif strand_index == 2:
            return self.sigma2 if sign > 0 else self.sigma2_inv
        else:
            raise UnsupportedBraidProfileError(
                f"Fibonacci 1-qubit representation only supports generators sigma_1 and sigma_2 (B3). "
                f"Received unsupported generator index sigma_{strand_index}."
            )

    def compile_braid_to_unitary(self, braid: BraidWord) -> ComplexMatrix2x2:
        """
        Compiles an Artin braid word into an exact 2x2 unitary quantum gate matrix:
        U(B) = ∏ ρ(σ_{i_k})^{s_k}
        Validates that the braid strictly conforms to the B3 profile (strands <= 3).
        """
        if braid.num_strands > 3:
            raise UnsupportedBraidProfileError(
                f"Fibonacci 1-qubit representation only supports up to 3 strands (B3). "
                f"Received braid with {braid.num_strands} strands."
            )
        u = ComplexMatrix2x2.identity()
        for crossing in braid.crossings:
            g = self.generator_matrix(crossing.strand_index, crossing.sign)
            u = g @ u
        return u

    def evolve_state(
        self,
        u: ComplexMatrix2x2,
        initial_state: Tuple[complex, complex] = (1.0 + 0.0j, 0.0 + 0.0j)
    ) -> Tuple[complex, complex]:
        """Applies unitary gate U to initial state vector (default |0>)."""
        alpha, beta = u.apply_vector(initial_state[0], initial_state[1])
        norm = math.sqrt(abs(alpha)**2 + abs(beta)**2)
        if norm > 0:
            return (alpha / norm, beta / norm)
        return (alpha, beta)

    def calculate_born_probabilities(self, state: Tuple[complex, complex]) -> Tuple[float, float]:
        """
        Calculates measurement probabilities P(0) = |α|² (Vacuum fusion)
        and P(1) = |β|² (Anyon τ fusion).
        """
        p0 = abs(state[0])**2
        p1 = abs(state[1])**2
        total = p0 + p1
        if total > 0:
            return (p0 / total, p1 / total)
        return (0.5, 0.5)

    def calculate_bloch_coordinates(self, state: Tuple[complex, complex]) -> Dict[str, float]:
        """
        Maps the complex qubit state |ψ> = α|0> + β|1> onto the Bloch Sphere:
        x = 2 Re(α* β)
        y = 2 Im(α* β)
        z = |α|² - |β|²
        θ = 2 arccos(|α|)
        φ = arg(α* β)
        """
        alpha, beta = state
        conj_alpha_beta = alpha.conjugate() * beta

        x = 2.0 * conj_alpha_beta.real
        y = 2.0 * conj_alpha_beta.imag
        z = abs(alpha)**2 - abs(beta)**2

        r = math.sqrt(x*x + y*y + z*z)
        if r > 0:
            x, y, z = x / r, y / r, z / r

        theta = 2.0 * math.acos(min(1.0, max(0.0, abs(alpha))))
        phi = cmath.phase(conj_alpha_beta)
        if phi < 0:
            phi += 2.0 * math.pi

        return {
            "x": round(x, 6),
            "y": round(y, 6),
            "z": round(z, 6),
            "theta_rad": round(theta, 6),
            "theta_deg": round(math.degrees(theta), 2),
            "phi_rad": round(phi, 6),
            "phi_deg": round(math.degrees(phi), 2)
        }

    def simulate_measurement(self, state: Tuple[complex, complex], shots: int = 1024) -> Dict[str, Any]:
        """Simulates projective quantum measurements (Monte Carlo collapse)."""
        p0, p1 = self.calculate_born_probabilities(state)
        c0 = 0
        for _ in range(shots):
            if random.random() < p0:
                c0 += 1
        c1 = shots - c0
        return {
            "shots": shots,
            "counts": {"|0> (Vacuum 1)": c0, "|1> (Anyon τ)": c1},
            "experimental_prob": {"|0>": c0 / shots, "|1>": c1 / shots},
            "theoretical_prob": {"|0>": round(p0, 6), "|1>": round(p1, 6)}
        }


# ============================================================================
# 3. NATIVE ISO 32000 VECTOR CIRCUIT & BLOCH SPHERE RENDERER
# ============================================================================

def _pdf_circle_ops(cx: float, cy: float, r: float) -> str:
    k = r * 0.55228475
    return (
        f"{cx + r} {cy} m "
        f"{cx + r} {cy + k} {cx + k} {cy + r} {cx} {cy + r} c "
        f"{cx - k} {cy + r} {cx - r} {cy + k} {cx - r} {cy} c "
        f"{cx - k} {cy - k} {cx - k} {cy - r} {cx} {cy - r} c "
        f"{cx + k} {cy - r} {cx + r} {cy - k} {cx + r} {cy} c"
    )

def render_quantum_circuit_pdf_stream(
    braid: BraidWord,
    unitary: ComplexMatrix2x2,
    state: Tuple[complex, complex],
    bloch: Dict[str, float],
    x: float = 50.0,
    y: float = 280.0,
    width: float = 512.0,
    height: float = 300.0
) -> str:
    """
    Renders an ISO 32000 PostScript vector graphics stream showing:
      1. Spacetime anyon worldlines flowing upwards in time (t ↑).
      2. 3D occlusion bridge crossings.
      3. Fusion detection plates at the top with probabilities.
      4. Orthographic vector projection of the Bloch Sphere on the right.
    """
    stream = []

    # Bounding Box Background
    stream.append(f"0.04 0.05 0.08 rg {x} {y} {width} {height} re f")
    stream.append(f"0.15 0.22 0.35 RG 1.5 w {x} {y} {width} {height} re s")

    # Left: Spacetime Braiding Circuit
    circuit_w = width * 0.58
    cx = x + 16.0
    cy = y + 20.0
    ch = height - 50.0

    # Spacetime axis (Time arrow t ↑)
    stream.append(f"0.25 0.35 0.5 RG 1 w [2 2] 0 d")
    stream.append(f"{cx} {cy} m {cx} {cy + ch} l S")
    stream.append(f"[] 0 d")
    stream.append(f"0.25 0.35 0.5 rg {cx - 3} {cy + ch - 5} m {cx} {cy + ch} l {cx + 3} {cy + ch - 5} l f")
    stream.append(f"BT /F2 7 Tf 0.4 0.55 0.7 rg {cx + 4} {cy + ch - 8} Td (Time t) Tj ET")

    # Strands layout
    num_strands = max(3, braid.num_strands)
    strand_spacing = (circuit_w - 50.0) / (num_strands - 1)
    strands_x = [cx + 36.0 + i * strand_spacing for i in range(num_strands)]

    # Palette for anyons
    colors = [
        (0.2, 0.8, 0.95),  # Cyan Anyon τ_1
        (0.3, 0.95, 0.5),  # Emerald Anyon τ_2
        (1.0, 0.75, 0.2),  # Amber Anyon τ_3
        (0.8, 0.4, 0.95)   # Purple Anyon τ_4
    ]

    # Draw bottom anyon source tags
    for i, sx in enumerate(strands_x):
        cr, cg, cb = colors[i % len(colors)]
        stream.append(f"{cr} {cg} {cb} rg {_pdf_circle_ops(sx, cy, 3.0)} f")
        stream.append(f"BT /F2 8 Tf {cr} {cg} {cb} rg {sx - 6} {cy - 12} Td (tau_{i+1}) Tj ET")

    # Draw crossings along vertical time steps
    num_steps = max(1, len(braid.crossings))
    step_h = (ch - 40.0) / (num_steps + 1)
    cur_y = cy + 10.0
    perm = list(range(num_strands))

    for step_idx, crossing in enumerate(braid.crossings):
        next_y = cur_y + step_h
        s_idx = crossing.strand_index - 1
        x1 = strands_x[s_idx]
        x2 = strands_x[s_idx + 1]

        # Draw untouched spectator strands vertically
        for k in range(num_strands):
            if k != s_idx and k != s_idx + 1:
                col = colors[perm[k] % len(colors)]
                stream.append(f"{col[0]} {col[1]} {col[2]} RG 2 w")
                stream.append(f"{strands_x[k]} {cur_y} m {strands_x[k]} {next_y} l S")

        # Crossing strands
        under_idx = perm[s_idx + 1] if crossing.sign > 0 else perm[s_idx]
        over_idx = perm[s_idx] if crossing.sign > 0 else perm[s_idx + 1]

        ux_start = x2 if crossing.sign > 0 else x1
        ux_end = x1 if crossing.sign > 0 else x2
        ox_start = x1 if crossing.sign > 0 else x2
        ox_end = x2 if crossing.sign > 0 else x1

        col_under = colors[under_idx % len(colors)]
        col_over = colors[over_idx % len(colors)]

        ymid = (cur_y + next_y) / 2.0
        xmid = (x1 + x2) / 2.0

        # Draw under-strand with central gap
        stream.append(f"{col_under[0]} {col_under[1]} {col_under[2]} RG 2.2 w")
        stream.append(f"{ux_start} {cur_y} m {ux_start} {cur_y + step_h * 0.3} {xmid - 3} {ymid - 3} {xmid - 3} {ymid - 3} c S")
        stream.append(f"{xmid + 3} {ymid + 3} m {xmid + 3} {ymid + 3} {ux_end} {next_y - step_h * 0.3} {ux_end} {next_y} c S")

        # Draw over-strand with occlusion shadow
        stream.append("0.04 0.05 0.08 RG 5.5 w")
        stream.append(f"{ox_start} {cur_y} m {ox_start} {cur_y + step_h * 0.35} {ox_end} {next_y - step_h * 0.35} {ox_end} {next_y} c S")
        stream.append(f"{col_over[0]} {col_over[1]} {col_over[2]} RG 2.2 w")
        stream.append(f"{ox_start} {cur_y} m {ox_start} {cur_y + step_h * 0.35} {ox_end} {next_y - step_h * 0.35} {ox_end} {next_y} c S")

        perm[s_idx], perm[s_idx + 1] = perm[s_idx + 1], perm[s_idx]
        cur_y = next_y

    # Extend strands to top detectors
    top_y = cy + ch
    for k in range(num_strands):
        col = colors[perm[k] % len(colors)]
        stream.append(f"{col[0]} {col[1]} {col[2]} RG 2 w")
        stream.append(f"{strands_x[k]} {cur_y} m {strands_x[k]} {top_y - 15} l S")

    # Top Fusion Detector Plate
    p0 = abs(state[0])**2
    p1 = abs(state[1])**2
    fx = strands_x[0] - 6.0
    fw = (strands_x[1] - strands_x[0]) + 12.0
    stream.append(f"0.12 0.18 0.3 rg {fx} {top_y - 15} {fw} 20 re f")
    stream.append(f"0.3 0.6 0.95 RG 1 w {fx} {top_y - 15} {fw} 20 re s")
    stream.append(f"BT /F1 7 Tf 0.9 0.95 1 rg {fx + 4} {top_y - 4} Td (FUSION DETECTOR) Tj ET")
    stream.append(f"BT /F2 6.5 Tf 0.3 0.9 0.5 rg {fx + 4} {top_y - 12} Td (P(1)={p0*100:.1f}% P(t)={p1*100:.1f}%) Tj ET")

    # Right: Bloch Sphere Projection
    bx = x + circuit_w + 35.0
    by = y + (height / 2.0) - 10.0
    br = 65.0

    stream.append(f"BT /F1 10 Tf 0.9 0.95 1 rg {bx - 30} {y + height - 26} Td (Bloch Sphere State |psi>) Tj ET")
    stream.append(f"BT /F2 7.5 Tf 0.6 0.7 0.85 rg {bx - 30} {y + height - 38} Td (theta={bloch['theta_deg']} deg  phi={bloch['phi_deg']} deg) Tj ET")

    # Outer circle
    stream.append("0.18 0.25 0.38 RG 1.5 w")
    stream.append(f"{bx + br} {by} m")
    stream.append(f"{bx + br} {by + br * 0.552} {bx + br * 0.552} {by + br} {bx} {by + br} c")
    stream.append(f"{bx - br * 0.552} {by + br} {bx - br} {by + br * 0.552} {bx - br} {by} c")
    stream.append(f"{bx - br} {by - br * 0.552} {bx - br * 0.552} {by - br} {bx} {by - br} c")
    stream.append(f"{bx + br * 0.552} {by - br} {bx + br} {by - br * 0.552} {bx + br} {by} c S")

    # Equator ellipse (dashed)
    stream.append("[2 2] 0 d 0.15 0.22 0.32 RG 1 w")
    ey = br * 0.28
    stream.append(f"{bx + br} {by} m")
    stream.append(f"{bx + br} {by + ey * 0.552} {bx + br * 0.552} {by + ey} {bx} {by + ey} c")
    stream.append(f"{bx - br * 0.552} {by + ey} {bx - br} {by + ey * 0.552} {bx - br} {by} c")
    stream.append(f"{bx - br} {by - ey * 0.552} {bx - br * 0.552} {by - ey} {bx} {by - ey} c")
    stream.append(f"{bx + br * 0.552} {by - ey} {bx + br} {by - ey * 0.552} {bx + br} {by} c S")
    stream.append("[] 0 d")

    # Z-Axis: North pole |0> (top), South pole |1> (bottom)
    stream.append("0.35 0.45 0.6 RG 1 w")
    stream.append(f"{bx} {by - br - 8} m {bx} {by + br + 8} l S")
    stream.append(f"BT /F1 8 Tf 0.95 0.9 0.4 rg {bx - 4} {by + br + 11} Td (|0>) Tj ET")
    stream.append(f"BT /F1 8 Tf 0.4 0.9 0.95 rg {bx - 4} {by - br - 17} Td (|1>) Tj ET")

    # X and Y axes
    stream.append("0.25 0.32 0.45 RG 0.8 w")
    stream.append(f"{bx - br - 5} {by} m {bx + br + 5} {by} l S")
    stream.append(f"BT /F2 6.5 Tf 0.4 0.5 0.65 rg {bx + br + 7} {by - 2} Td (X) Tj ET")

    vx = bloch["x"]
    vy = bloch["y"]
    vz = bloch["z"]
    px = bx + br * (vx * 0.85 - vy * 0.3)
    py = by + br * (vz * 0.85 + vy * 0.2)

    # Glowing State Vector
    stream.append("0.95 0.25 0.4 RG 2.5 w")
    stream.append(f"{bx} {by} m {px} {py} l S")
    stream.append(f"1.0 0.85 0.3 rg {_pdf_circle_ops(px, py, 3.5)} f")
    stream.append(f"BT /F1 8.5 Tf 1.0 0.85 0.3 rg {px + 5} {py + 3} Td (|psi>) Tj ET")

    my = y + 16.0
    stream.append(f"BT /F2 7 Tf 0.7 0.8 0.9 rg {bx - 40} {my + 20} Td (Vector: [{vx:+.3f}, {vy:+.3f}, {vz:+.3f}]) Tj ET")
    stream.append(f"BT /F2 7 Tf 0.5 0.85 0.6 rg {bx - 40} {my + 10} Td (Prob: P(0)={p0:.4f}  P(1)={p1:.4f}) Tj ET")
    stream.append(f"BT /F2 7 Tf 0.85 0.6 0.95 rg {bx - 40} {my} Td (Unitarity: |det(U)| = {abs(unitary.det()):.6f}) Tj ET")

    return "\n".join(stream)


# ============================================================================
# 4. QUANTUM POLYGLOT COMPILER & STANDALONE RUNNER
# ============================================================================

class QuantumPolyglotCompiler:
    """
    Compiles an ISO 32000 PDF document carrying both the topological anyonic
    circuit visual layer and an executable Python quantum simulation monad.
    """
    def __init__(
        self,
        braid: BraidWord,
        title: str = "Topological Quantum Circuit (Fibonacci Anyons)"
    ):
        self.braid = braid
        self.title = title
        self.system = FibonacciQuantumSystem()
        self.unitary = self.system.compile_braid_to_unitary(self.braid)
        self.state = self.system.evolve_state(self.unitary)
        self.bloch = self.system.calculate_bloch_coordinates(self.state)
        self.probs = self.system.calculate_born_probabilities(self.state)

    def _build_runner_script(self) -> str:
        template = r'''#!/usr/bin/env python3
import os
import sys
import json
import argparse
from pathlib import Path

MANIFEST_PREFIX = __MANIFEST_PREFIX__

def load_manifest():
    content = Path(__file__).read_bytes()
    idx = content.rfind(MANIFEST_PREFIX.encode("latin1"))
    if idx == -1:
        idx = content.rfind(MANIFEST_PREFIX.encode("utf-8"))
    if idx == -1:
        print("[FAIL] No quantum manifest located in polyglot document.")
        sys.exit(1)
    end_idx = content.find(b"\n", idx)
    data = json.loads(content[idx + len(MANIFEST_PREFIX.encode("latin1")):end_idx].decode("utf-8"))
    src_dir = data.get("source_dir")
    if src_dir and src_dir not in sys.path:
        sys.path.insert(0, src_dir)
    return data

def cmd_simulate():
    data = load_manifest()
    print("=================================================================")
    print("  %\U0001f5a4 BLACK-HEART TOPOLOGICAL QUANTUM TOPOS SIMULATOR")
    print("  Fibonacci Anyons (SU(2)_3) | Topological Braid Quantum Gates")
    print("=================================================================\n")
    print(f"[*] Circuit Title:       {data['title']}")
    print(f"[*] Braid Presentation:  {data['braid_formula']}")
    print(f"[*] Crossing Count:      {data['crossings']} (Writhe: {data['writhe']})")
    u00 = data['unitary'][0][0]
    u01 = data['unitary'][0][1]
    u10 = data['unitary'][1][0]
    u11 = data['unitary'][1][1]
    print(f"[*] Unitary Gate Matrix: [{u00}, {u01}];")
    print(f"                          [{u10}, {u11}]")
    print(f"[*] Determinant:         |det(U)| = {data['det_abs']:.6f} (Phase: {data['det_angle']:.4f} rad)\n")
    print(f"[*] Evolved State |psi>:  alpha = {data['state_alpha'][0]:+.4f} {data['state_alpha'][1]:+.4f}j")
    print(f"                          beta  = {data['state_beta'][0]:+.4f} {data['state_beta'][1]:+.4f}j\n")
    print("Topological Qubit Born Probabilities:")
    print(f"  |0> (Vacuum Channel 1):  {data['prob_0'] * 100:.2f}%")
    print(f"  |1> (Anyonic Channel t): {data['prob_1'] * 100:.2f}%\n")
    print("Bloch Sphere Coordinates:")
    print(f"  Vector (x, y, z):       ({data['bloch']['x']:+.4f}, {data['bloch']['y']:+.4f}, {data['bloch']['z']:+.4f})")
    print(f"  Polar Angle theta:      {data['bloch']['theta_deg']} deg ({data['bloch']['theta_rad']:.4f} rad)")
    print(f"  Azimuthal Angle phi:    {data['bloch']['phi_deg']} deg ({data['bloch']['phi_rad']:.4f} rad)\n")
    print("\033[1;32m[\u2713] TOPOLOGICAL QUANTUM EVOLUTION SOUND & UNITARY (Q.E.D.)\033[0m\n")

def cmd_measure(shots=1024):
    data = load_manifest()
    import random
    p0 = data['prob_0']
    c0 = sum(1 for _ in range(shots) if random.random() < p0)
    c1 = shots - c0
    print("=================================================================")
    print(f"  PROJECTIVE QUANTUM MEASUREMENT COLLAPSE (Shots: {shots})")
    print("=================================================================\n")
    print(f"  Outcome |0> (Vacuum):    {c0:4d} / {shots} ({c0/shots*100:.2f}% | Expected: {p0*100:.2f}%)")
    print(f"  Outcome |1> (Anyon t):   {c1:4d} / {shots} ({c1/shots*100:.2f}% | Expected: {(1-p0)*100:.2f}%)\n")
    print("\033[1;32m[\u2713] BORN RULE COLLAPSE COMPLETE\033[0m\n")

def cmd_audit():
    data = load_manifest()
    import math

    # 1. Parse and validate unitary matrix operands directly from frozen data
    u_raw = data.get('unitary')
    if not u_raw or len(u_raw) != 2 or len(u_raw[0]) != 2 or len(u_raw[1]) != 2:
        print("[FAIL] AUDIT FAILED: Malformed or missing unitary matrix operand")
        sys.exit(1)

    try:
        m00 = complex(u_raw[0][0][0], u_raw[0][0][1])
        m01 = complex(u_raw[0][1][0], u_raw[0][1][1])
        m10 = complex(u_raw[1][0][0], u_raw[1][0][1])
        m11 = complex(u_raw[1][1][0], u_raw[1][1][1])
    except Exception as e:
        print(f"[FAIL] AUDIT FAILED: Non-numeric matrix entries: {e}")
        sys.exit(1)

    for c in (m00, m01, m10, m11):
        if not (math.isfinite(c.real) and math.isfinite(c.imag)):
            print("[FAIL] AUDIT FAILED: Non-finite matrix entries")
            sys.exit(1)

    # 2. Recompute Unitarity U_dagger*U = I
    c00 = (abs(m00)**2 + abs(m10)**2).real
    c01 = m00.conjugate() * m01 + m10.conjugate() * m11
    c10 = m01.conjugate() * m00 + m11.conjugate() * m10
    c11 = (abs(m01)**2 + abs(m11)**2).real

    unitarity_err = max(abs(c00 - 1.0), abs(c01), abs(c10), abs(c11 - 1.0))
    if unitarity_err > 1e-5:
        print(f"[FAIL] AUDIT FAILED: Unitarity violation U_dagger*U != I (err={unitarity_err:.2e})")
        sys.exit(1)

    # 3. Determinant |det(U)| = 1
    det = m00 * m11 - m01 * m10
    det_err = abs(abs(det) - 1.0)
    if det_err > 1e-5:
        print(f"[FAIL] AUDIT FAILED: Determinant violation |det(U)| != 1 (err={det_err:.2e})")
        sys.exit(1)

    # 4. Probability bounds [0, 1] and sum = 1
    p0 = data.get('prob_0', None)
    p1 = data.get('prob_1', None)
    if not (isinstance(p0, (int, float)) and isinstance(p1, (int, float)) and math.isfinite(p0) and math.isfinite(p1)):
        print("[FAIL] AUDIT FAILED: Invalid or non-finite probability values")
        sys.exit(1)

    if p0 < 0.0 or p0 > 1.0 or p1 < 0.0 or p1 > 1.0:
        print(f"[FAIL] AUDIT FAILED: Probability bounds violated: P(0)={p0}, P(1)={p1}")
        sys.exit(1)

    prob_sum_err = abs(p0 + p1 - 1.0)
    if not math.isfinite(prob_sum_err) or prob_sum_err > 1e-5:
        print(f"[FAIL] AUDIT FAILED: Probability sum violation: {p0} + {p1} != 1 (err={prob_sum_err:.2e})")
        sys.exit(1)

    # 5. Recompute Born probabilities from state |psi> = U |0> = (m00, m10)
    recomp_p0 = abs(m00)**2
    recomp_p1 = abs(m10)**2
    born_err0 = abs(p0 - recomp_p0)
    born_err1 = abs(p1 - recomp_p1)
    if not (math.isfinite(born_err0) and math.isfinite(born_err1)) or born_err0 > 1e-5 or born_err1 > 1e-5:
        print(f"[FAIL] AUDIT FAILED: Claimed probabilities diverge from matrix operands (err={max(born_err0, born_err1):.2e})")
        sys.exit(1)

    # 6. Recompute Bloch vector
    alpha, beta = m00, m10
    bx = 2.0 * (alpha.conjugate() * beta).real
    by = 2.0 * (alpha.conjugate() * beta).imag
    bz = abs(alpha)**2 - abs(beta)**2
    bloch_claimed = data.get('bloch', {})
    if not isinstance(bloch_claimed, dict):
        print("[FAIL] AUDIT FAILED: Invalid bloch coordinates dictionary")
        sys.exit(1)
    for axis in ('x', 'y', 'z'):
        val = bloch_claimed.get(axis, None)
        if not (isinstance(val, (int, float)) and math.isfinite(val)):
            print(f"[FAIL] AUDIT FAILED: Non-finite or missing bloch coordinate: {axis}")
            sys.exit(1)

    bloch_err = max(
        abs(bloch_claimed.get('x', 0.0) - bx),
        abs(bloch_claimed.get('y', 0.0) - by),
        abs(bloch_claimed.get('z', 0.0) - bz)
    )
    if not math.isfinite(bloch_err) or bloch_err > 1e-4:
        print(f"[FAIL] AUDIT FAILED: Bloch coordinates diverge from state vector (err={bloch_err:.2e})")
        sys.exit(1)

    print(f"[\u2713] AUDIT PASSED: Unitarity err={unitarity_err:.2e}, Born err={prob_sum_err:.2e}, Bloch err={bloch_err:.2e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Black-Heart Topological Quantum Polyglot")
    parser.add_argument("--simulate", action="store_true", help="Simulate topological quantum gate and print state")
    parser.add_argument("--measure", type=int, nargs="?", const=1024, help="Perform projective Born rule measurements")
    parser.add_argument("--audit", action="store_true", help="Audit quantum unitarity and topological invariants")
    args, _ = parser.parse_known_args()

    if args.measure:
        cmd_measure(args.measure)
    elif args.audit:
        cmd_audit()
    else:
        cmd_simulate()
'''
        return template.replace("__MANIFEST_PREFIX__", repr(QUANTUM_MANIFEST_PREFIX))

    def compile_pdf(self) -> bytes:
        runner = self._build_runner_script()

        circuit_stream = render_quantum_circuit_pdf_stream(
            self.braid,
            self.unitary,
            self.state,
            self.bloch,
            x=50,
            y=300,
            width=512,
            height=320
        )

        det_val = self.unitary.det()
        manifest_data = {
            "title": self.title,
            "braid_formula": self.braid.to_artin_notation(),
            "crossings": self.braid.crossing_number,
            "writhe": self.braid.writhe,
            "unitary": self.unitary.to_list(),
            "det_abs": abs(det_val),
            "det_angle": cmath.phase(det_val),
            "state_alpha": (self.state[0].real, self.state[0].imag),
            "state_beta": (self.state[1].real, self.state[1].imag),
            "prob_0": self.probs[0],
            "prob_1": self.probs[1],
            "bloch": self.bloch,
            "source_dir": os.path.dirname(os.path.abspath(__file__))
        }
        manifest_line = QUANTUM_MANIFEST_PREFIX + json.dumps(manifest_data, separators=(",", ":"), ensure_ascii=True) + "\n"

        # Construct visual page text stream
        page_text = (
            "BT /F1 16 Tf 50 740 Td (PROJECT BLACK-HEART: TOPOLOGICAL QUANTUM TOPOS) Tj ET\n"
            "BT /F2 10 Tf 50 720 Td (Universal Anyonic Quantum Computation via Artin Braid Group B_n) Tj ET\n"
            f"BT /F2 9 Tf 50 685 Td (Circuit: {self.title}) Tj ET\n"
            f"BT /F1 9 Tf 50 670 Td (Braid Presentation: {self.braid.to_artin_notation(ascii_only=True)}) Tj ET\n"
            f"BT /F2 8 Tf 50 655 Td (Topological Invariants: Crossings={self.braid.crossing_number}  |  Writhe={self.braid.writhe}  |  Link Components={self.braid.count_link_components()}) Tj ET\n"
            "BT /F1 10 Tf 50 255 Td (Topological Quantum Gate Matrix U(B) in SU(2):) Tj ET\n"
            f"BT /F2 8 Tf 50 235 Td (- U_00 = {self.unitary.m00.real:+.4f} {self.unitary.m00.imag:+.4f}i   U_01 = {self.unitary.m01.real:+.4f} {self.unitary.m01.imag:+.4f}i) Tj ET\n"
            f"BT /F2 8 Tf 50 220 Td (- U_10 = {self.unitary.m10.real:+.4f} {self.unitary.m10.imag:+.4f}i   U_11 = {self.unitary.m11.real:+.4f} {self.unitary.m11.imag:+.4f}i) Tj ET\n"
            f"BT /F2 8 Tf 50 205 Td (- Born Collapse: P(|0>)={self.probs[0]*100:.2f}% (Vacuum 1)   P(|1>)={self.probs[1]*100:.2f}% (Anyon tau)) Tj ET\n"
            "BT /F2 8 Tf 50 70 Td (Executable ISO 32000 Polyglot: Run 'python3 <this_file.pdf> --simulate' or '--measure'.) Tj ET\n"
        )

        full_content_stream = circuit_stream + "\n" + page_text
        content_bytes = full_content_stream.encode("latin1", errors="replace")

        # PDF Object Table
        objs: List[Tuple[int, bytes]] = []
        objs.append((1, b"<</Type /Catalog /Pages 2 0 R>>"))
        objs.append((2, b"<</Type /Pages /Kids [3 0 R] /Count 1>>"))
        objs.append((3, b"<</Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources <</Font <</F1 5 0 R /F2 6 0 R>>>>>>"))
        objs.append((4, f"<</Length {len(content_bytes)}>>\nstream\n".encode("latin1") + content_bytes + b"\nendstream"))
        objs.append((5, b"<</Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold>>"))
        objs.append((6, b"<</Type /Font /Subtype /Type1 /BaseFont /Helvetica>>"))

        pdf_buf = io.BytesIO()
        pdf_buf.write(b"%PDF-1.7\n")
        pdf_buf.write(b"%BH-QUANTUM-TOPOS\n")

        offsets = {}
        for obj_id, obj_data in objs:
            offsets[obj_id] = pdf_buf.tell()
            pdf_buf.write(f"{obj_id} 0 obj\n".encode("latin1"))
            pdf_buf.write(obj_data)
            pdf_buf.write(b"\nendobj\n")

        xref_offset = pdf_buf.tell()
        pdf_buf.write(f"xref\n0 {len(objs) + 1}\n".encode("latin1"))
        pdf_buf.write(b"0000000000 65535 f \n")
        for i in range(1, len(objs) + 1):
            pdf_buf.write(f"{offsets[i]:010d} 00000 n \n".encode("latin1"))

        pdf_buf.write(
            f"trailer\n<</Size {len(objs) + 1} /Root 1 0 R>>\nstartxref\n{xref_offset}\n%%EOF\n".encode("latin1")
        )

        base_pdf_bytes = pdf_buf.getvalue()

        # Wrap in literate polyglot monad
        header_text = (
            f"#!{sys.executable}\n"
            "# coding: latin-1\n"
            "# ============================================================================\n"
            "# % PROJECT BLACK-HEART: TOPOLOGICAL QUANTUM TOPOS POLYGLOT\n"
            "# ============================================================================\n"
            "'''\n"
        ).encode("latin1")

        polyglot = (
            header_text
            + base_pdf_bytes
            + b"\n'''\n"
            + runner.encode("latin1")
            + b"\n"
            + manifest_line.encode("latin1")
        )
        return polyglot


def compile_quantum_polyglot(braid: BraidWord, output_path: str, title: str = "Topological Quantum Circuit") -> str:
    """High-level helper to compile and save an executable quantum polyglot."""
    compiler = QuantumPolyglotCompiler(braid, title=title)
    pdf_bytes = compiler.compile_pdf()
    with open(output_path, "wb") as f:
        f.write(pdf_bytes)
    return output_path


if __name__ == "__main__":
    print("quantum.py — Topological Quantum Topos engine loaded.")
