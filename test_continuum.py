#!/usr/bin/env python3
"""
test_continuum.py — Unit Tests for Suspended Continuum Computations & Checkpointing.
Part of Project Black-Heart (%🖤).
"""

import os
import sys
import unittest
import tempfile
import subprocess

from glyph import parse, evaluate, EvalStatus
from crypto import generate_keypair
from continuum import (
    ThunkCheckpoint, step_continuum,
    ResumableComputationPolyglot, resume_computation_in_pdf
)

class TestContinuumEngine(unittest.TestCase):

    def setUp(self):
        self.sk, self.pk = generate_keypair()
        self.tmp_dir = tempfile.mkdtemp()

    def test_eval_continuum_suspended(self):
        # Heavy combinator expression:
        # S (K (K I)) (K I) takes 4 steps to reduce completely
        expr = "🌿 (🖤 (🖤 🤍)) (🖤 🤍) Alpha Beta"
        term = parse(expr)

        # Budget = 2 steps: must suspend
        res = evaluate(term, max_atp=2, raise_on_limit=False)
        self.assertTrue(res.is_suspended())
        self.assertEqual(res.status, EvalStatus.SUSPENDED)
        self.assertEqual(res.atp_spent, 2)
        self.assertNotEqual(str(res.term), "Beta")

    def test_eval_continuum_resumption_invariance(self):
        expr = "🌿 (🖤 (🖤 🤍)) (🖤 🤍) Alpha Beta"
        term = parse(expr)

        # 1. One-shot evaluation
        oneshot_res = evaluate(term, max_atp=100)
        self.assertTrue(oneshot_res.is_settled())
        self.assertEqual(str(oneshot_res.term), "Beta")

        # 2. Stepped evaluation via Continuum thunks
        cp0 = ThunkCheckpoint(
            height=0,
            timestamp_utc="2026-09-08T00:00:00Z",
            initial_expr=expr,
            current_expr=expr,
            atp_spent_step=0,
            atp_accumulated=0,
            peak_size=0,
            status="SUSPENDED",
            prev_hash="0" * 64,
            public_key_hex=self.pk
        )
        cp0.sign(self.sk)

        # Step 1: 2 ATP
        cp1 = step_continuum(cp0, fuel=2, secret_key_hex=self.sk)
        self.assertEqual(cp1.status, "SUSPENDED")
        self.assertEqual(cp1.atp_accumulated, 2)
        self.assertTrue(cp1.verify())

        # Step 2: 5 ATP (more than enough to settle)
        cp2 = step_continuum(cp1, fuel=5, secret_key_hex=self.sk)
        self.assertEqual(cp2.status, "SETTLED")
        self.assertEqual(cp2.current_expr, "Beta")
        self.assertEqual(cp2.atp_accumulated, oneshot_res.atp_spent)
        self.assertTrue(cp2.verify())

    def test_thunk_checkpoint_tamper_detection(self):
        cp = ThunkCheckpoint(
            height=1,
            timestamp_utc="2026-09-08T00:00:00Z",
            initial_expr="🖤 Truth Mirage",
            current_expr="Truth",
            atp_spent_step=1,
            atp_accumulated=1,
            peak_size=5,
            status="SETTLED",
            prev_hash="0" * 64,
            public_key_hex=self.pk
        )
        cp.sign(self.sk)
        self.assertTrue(cp.verify())

        # Tamper expression
        cp.current_expr = "Lie"
        self.assertFalse(cp.verify())

    def test_polyglot_pdf_resumption(self):
        pdf_path = os.path.join(self.tmp_dir, "resumable_test.pdf")
        poly = ResumableComputationPolyglot("RESUMABLE TEST")
        expr = "🌿 (🖤 (🖤 🤍)) (🖤 🤍) Gamma Delta"

        cp0 = poly.initialize(expr, initial_fuel=2, secret_key_hex=self.sk, public_key_hex=self.pk)
        self.assertEqual(cp0.status, "SUSPENDED")
        poly.compile(pdf_path)

        self.assertTrue(os.path.exists(pdf_path))

        # Resume in PDF
        cp1 = resume_computation_in_pdf(pdf_path, additional_atp=10, secret_key_hex=self.sk)
        self.assertEqual(cp1.status, "SETTLED")
        self.assertEqual(cp1.current_expr, "Delta")

        # Execute as Python script
        cmd = [sys.executable, pdf_path]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("COMPUTATION REACHED NORMAL FORM", proc.stdout)

if __name__ == "__main__":
    unittest.main()
