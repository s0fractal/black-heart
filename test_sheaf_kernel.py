#!/usr/bin/env python3
# coding: utf-8
"""
test_sheaf_kernel.py — Rigorous Test Suite for Engine #33: Epistemic Sheaf Kernel (SHEAF-0.1).
Part of Project Black-Heart (%🖤).

Validates all sheaf axioms, Čech cohomology obstructions, restriction functoriality,
and ISO 32000 vector polyglot generation.
"""

from __future__ import annotations
import os
import sys
import tempfile
import subprocess
import unittest

import sheaf_kernel
from sheaf_kernel import (
    EpistemicContext, LocalSection, SectionStatus,
    SheafDescentReport, EpistemicSheafKernel,
    generate_sheaf_pdf, sha256_hex
)


class TestEpistemicSheafKernel(unittest.TestCase):
    """Rigorous unit and integration test suite for Engine #33."""

    def setUp(self):
        # 3 Context Charts forming an open cover
        self.ctx_a = EpistemicContext.create(
            name="Context_A",
            domains=["domain_alpha", "domain_beta"],
            budget_ceiling=150,
            invariants=["INV_DETERMINISTIC"]
        )
        self.ctx_b = EpistemicContext.create(
            name="Context_B",
            domains=["domain_beta", "domain_gamma"],
            budget_ceiling=180,
            invariants=["INV_DETERMINISTIC"]
        )
        self.ctx_c = EpistemicContext.create(
            name="Context_C",
            domains=["domain_alpha", "domain_gamma"],
            budget_ceiling=200,
            invariants=["INV_DETERMINISTIC"]
        )
        self.kernel = EpistemicSheafKernel()
        self.kernel.register_context(self.ctx_a)
        self.kernel.register_context(self.ctx_b)
        self.kernel.register_context(self.ctx_c)

    def test_01_topological_poset_and_intersections(self):
        """Invariant SH1: Epistemic topology obeys sub-context specialization and intersection laws."""
        # Intersection of A and B shares domain_beta
        ab = self.ctx_a.intersection(self.ctx_b)
        self.assertIsNotNone(ab)
        self.assertIn("domain_beta", ab.domains)
        self.assertNotIn("domain_gamma", ab.domains)
        self.assertEqual(ab.budget_ceiling, 150)  # min(150, 180)
        self.assertTrue(ab.is_subcontext_of(self.ctx_a))
        self.assertTrue(ab.is_subcontext_of(self.ctx_b))

        # Disjoint contexts have no open intersection
        disjoint_1 = EpistemicContext.create("D1", ["zone_x"], 100)
        disjoint_2 = EpistemicContext.create("D2", ["zone_y"], 100)
        self.assertIsNone(disjoint_1.intersection(disjoint_2))

    def test_02_presheaf_restriction_functoriality(self):
        """Invariant SH2: Restriction map res_{V, U} is strictly functorial (identity and composition)."""
        sec_a = LocalSection.create(
            context=self.ctx_a,
            claim_name="SKK_IDENTITY",
            term_expression="S K K x",
            normal_form="x",
            verified_steps=2
        )

        # 1. Identity: res_{U, U}(s) == s normal form
        res_self = sec_a.restrict(self.ctx_a, self.ctx_a)
        self.assertEqual(res_self.normal_form, sec_a.normal_form)

        # 2. Composition: res_{W, V} o res_{V, U} == res_{W, U}
        ab = self.ctx_a.intersection(self.ctx_b)
        sub_w = EpistemicContext.create("W", ["domain_beta"], 100, ["INV_DETERMINISTIC"])

        res_ab = sec_a.restrict(ab, self.ctx_a)
        res_w_via_ab = res_ab.restrict(sub_w, ab)
        res_w_direct = sec_a.restrict(sub_w, self.ctx_a)

        self.assertEqual(res_w_via_ab.normal_form, res_w_direct.normal_form)
        self.assertEqual(res_w_via_ab.term_expression, res_w_direct.term_expression)

        # 3. Illegal restriction raises ValueError
        foreign_ctx = EpistemicContext.create("Foreign", ["alien_domain"], 500)
        with self.assertRaises(ValueError):
            sec_a.restrict(foreign_ctx, self.ctx_a)

        # 4. Budget overflow raises ValueError
        tight_ctx = EpistemicContext.create("Tight", ["domain_alpha"], 1, ["INV_DETERMINISTIC"])
        with self.assertRaises(ValueError):
            sec_a.restrict(tight_ctx, self.ctx_a)

    def test_03_sheaf_gluing_compatible_descent(self):
        """Invariant SH3: Compatible local sections on overlaps synthesize unique global section (H^1 = 0)."""
        claim = "SKK_IDENTITY"
        sec_a = LocalSection.create(self.ctx_a, claim, "S K K x", "x", 2)
        sec_b = LocalSection.create(self.ctx_b, claim, "I x", "x", 1)
        sec_c = LocalSection.create(self.ctx_c, claim, "S K K (I x)", "x", 3)

        self.kernel.register_section(sec_a)
        self.kernel.register_section(sec_b)
        self.kernel.register_section(sec_c)

        cover = [self.ctx_a, self.ctx_b, self.ctx_c]
        report = self.kernel.verify_descent(claim, cover)

        self.assertTrue(report.is_gluing_admissible)
        self.assertEqual(report.h1_dimension, 0)
        self.assertIsNotNone(report.global_section)
        self.assertEqual(report.global_section.normal_form, "x")
        self.assertEqual(report.global_section.status, SectionStatus.GLUED_GLOBAL)

        # Overlaps all yielded zero cocycle
        for coc in report.cocycles:
            self.assertTrue(coc.is_zero)
            self.assertEqual(coc.discrepancy_digest, "0")

    def test_04_cech_cohomology_obstruction_and_fail_closed_rejection(self):
        """Invariant SH4: Contradictory local sections yield non-zero Čech 1-cocycle (H^1 > 0) and reject gluing."""
        claim = "TRUTH_EVAL"
        # Context A proves TRUE (K)
        sec_a = LocalSection.create(self.ctx_a, claim, "K Truth Mirage", "Truth", 1)
        # Context B proves FALSE (K I) on overlapping domain_beta!
        sec_b = LocalSection.create(self.ctx_b, claim, "K I Truth Mirage", "Mirage", 2)

        self.kernel.register_section(sec_a)
        self.kernel.register_section(sec_b)

        cover = [self.ctx_a, self.ctx_b]
        report = self.kernel.verify_descent(claim, cover)

        # Must fail closed
        self.assertFalse(report.is_gluing_admissible)
        self.assertGreater(report.h1_dimension, 0)
        self.assertIsNone(report.global_section)
        self.assertIn("Epistemic obstruction detected", report.rejection_reason)

        # Non-zero cocycle recorded
        self.assertEqual(len(report.cocycles), 1)
        coc = report.cocycles[0]
        self.assertFalse(coc.is_zero)
        self.assertNotEqual(coc.discrepancy_digest, "0")
        self.assertEqual(coc.normal_form_i, "Truth")
        self.assertEqual(coc.normal_form_j, "Mirage")

    def test_05_missing_section_fails_closed(self):
        """Invariant SH5: Missing local chart in covering halts descent fail-closed."""
        claim = "ORPHAN_CLAIM"
        # Was ("S K K", "I"): S K K is already in normal form and does not
        # reduce to I, so that section was false and only passed because the
        # local check never ran. The case is about the missing chart.
        sec_a = LocalSection.create(self.ctx_a, claim, "S K K x", "x", 2)
        self.kernel.register_section(sec_a)

        # Cover includes ctx_b which lacks a section for ORPHAN_CLAIM
        cover = [self.ctx_a, self.ctx_b]
        report = self.kernel.verify_descent(claim, cover)

        self.assertFalse(report.is_gluing_admissible)
        self.assertIn("Missing local section", report.rejection_reason)

    def test_06_iso32000_polyglot_and_standalone_audit(self):
        """Invariant SH6: ISO 32000 vector polyglot compiles and verifies under standalone Python auditor."""
        claim = "SKK_IDENTITY"
        sec_a = LocalSection.create(self.ctx_a, claim, "S K K x", "x", 2)
        sec_b = LocalSection.create(self.ctx_b, claim, "I x", "x", 1)
        self.kernel.register_section(sec_a)
        self.kernel.register_section(sec_b)

        report = self.kernel.verify_descent(claim, [self.ctx_a, self.ctx_b])
        self.assertTrue(report.is_gluing_admissible)

        with tempfile.TemporaryDirectory() as td:
            pdf_path = os.path.join(td, "sheaf_certificate.pdf")
            generate_sheaf_pdf(report, pdf_path)
            self.assertTrue(os.path.exists(pdf_path))

            with open(pdf_path, "rb") as f:
                content = f.read()
                self.assertIn(b"%PDF-1.7", content)

            # Standalone audit execution
            proc = subprocess.run([sys.executable, pdf_path], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, f"Standalone audit error: {proc.stderr}")
            self.assertIn("EPISTEMIC SHEAF KERNEL & CECH COHOMOLOGY", proc.stdout)
            self.assertIn("Manifest self-consistency: OK", proc.stdout)
            # The runner reports the recorded verdict and names its scope; it no
            # longer claims "ALL INVARIANTS SATISFIED" (S7).
            self.assertIn("Recorded verdict: GLUING ADMISSIBLE", proc.stdout)
            self.assertNotIn("ALL INVARIANTS SATISFIED", proc.stdout)
            self.assertIn("did NOT re-derive", proc.stdout)

            # Tamper defense: mutate manifest payload without recomputing the hash
            tampered = content.replace(b'"is_admissible":true', b'"is_admissible":false')
            with open(pdf_path, "wb") as f:
                f.write(tampered)

            proc_tamper = subprocess.run([sys.executable, pdf_path], capture_output=True, text=True)
            self.assertNotEqual(proc_tamper.returncode, 0)
            self.assertIn("self-consistency check failed", proc_tamper.stdout)


if __name__ == "__main__":
    unittest.main()
