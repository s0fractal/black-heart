#!/usr/bin/env python3
# coding: utf-8
"""
test_dialectic_kernel.py — Rigorous Test Suite for Engine #31: Dialectical Discovery
& Automated Hypothesis Generation.
Part of Project Black-Heart (%🖤).

Validates:
  1. Boundary frontier exploration and minimal context delta extrapolation.
  2. SMT weakest precondition synthesis with verified UNSAT proof DAG.
  3. Dialectical triad resolution (Thesis -> Antithesis -> Synthesis).
  4. Automated ReevaluationRequest construction and budget bounds.
  5. Scoped Admission promotion with zero epistemic leakage to past contexts.
  6. Permanent refusal immutability for semantic counterexamples.
  7. Retest quota containment under MAX_ATTEMPTS_PER_REFUSAL_FAMILY.
  8. Warrant elevation to Grade A (Axiomatic) via SMT certificates.
  9. ISO 32000 polyglot PDF generation and standalone Python auditor execution.
 10. Append-only physicality preservation.
"""

from __future__ import annotations
import os
import sys
import tempfile
import subprocess
import unittest
from typing import Dict, Any, Tuple

import crypto
import warrant_kernel
from warrant_kernel import EvidenceGrade, Polarity, WarrantVerifier, TrustConfig
import smt_kernel
from smt_kernel import verify_unsat_certificate
import scoped_admission
from scoped_admission import (
    RefusalRecord, RefusalReason, ReevaluationRequest,
    RetestResult, RetestOutcome, ScopedAdmission, ScopedAdmissionRegistry,
    sha256_hex
)
import dialectic_kernel
from dialectic_kernel import (
    DialecticalStatus, ContextDelta, PreconditionGuard, DialecticalTriad,
    DialecticalDiscoveryReport, BoundaryExplorer, PreconditionSynthesizer,
    DialecticalOrchestrator, elevate_triad_to_warrant,
    generate_dialectic_pdf, append_dialectic_hud
)


class StepCountingCandidate:
    """Candidate requiring 120 steps to settle."""
    def __init__(self, required_steps: int = 120):
        self.required_steps = required_steps
        self.code_bytes = f"CANDIDATE_STEPS_{required_steps}".encode("utf-8")
        self.digest = sha256_hex(self.code_bytes)

    def evaluate(self, context: Dict[str, Any]) -> Tuple[RetestOutcome, int, bytes]:
        budget = context.get("budget_steps", 0)
        steps_executed = min(budget, self.required_steps)
        if steps_executed < self.required_steps:
            return (RetestOutcome.FAILURE, steps_executed, b"RESOURCE_LIMIT: steps_exhausted")
        return (RetestOutcome.SUCCESS, steps_executed, b"SUCCESS: settled_in_120_steps")


class OrderViolatingCandidate:
    """Candidate that permanently violates order invariant."""
    def __init__(self):
        self.code_bytes = b"CANDIDATE_ORDER_VIOLATION"
        self.digest = sha256_hex(self.code_bytes)

    def evaluate(self, context: Dict[str, Any]) -> Tuple[RetestOutcome, int, bytes]:
        return (RetestOutcome.FAILURE, 10, b"INVARIANT_VIOLATION: order_mismatch")


class TestDialecticKernel(unittest.TestCase):

    def setUp(self):
        self.registry = ScopedAdmissionRegistry()
        self.evaluator_digest = sha256_hex(b"TEST_EVALUATOR_v1")
        self.req_digest = sha256_hex(b"TEST_REQUIREMENT_v1")
        self.candidate = StepCountingCandidate(required_steps=120)
        self.semantic_cand = OrderViolatingCandidate()
        self.sk_author, self.pk_author = crypto.generate_keypair()

    def _register_refusal(
        self,
        candidate_digest: str,
        context: Dict[str, Any],
        outcome_type: RefusalReason,
        trace: bytes,
        steps: int
    ) -> RefusalRecord:
        rec = RefusalRecord.create(
            candidate_digest=candidate_digest,
            evaluator_digest=self.evaluator_digest,
            requirement_digest=self.req_digest,
            inputs_digest=sha256_hex(b"inputs"),
            evidence_bytes=trace,
            context=context,
            outcome_type=outcome_type,
            steps_executed=steps
        )
        self.registry.register_refusal(rec)
        return rec

    def test_01_boundary_explorer_step_delta(self):
        """Test minimal context expansion delta calculation for resource-cutoff refusal."""
        old_ctx = {"budget_steps": 80}
        outcome, steps, trace = self.candidate.evaluate(old_ctx)
        self.assertEqual(outcome, RetestOutcome.FAILURE)

        refusal = self._register_refusal(
            candidate_digest=self.candidate.digest,
            context=old_ctx,
            outcome_type=RefusalReason.RESOURCE_LIMIT,
            trace=trace,
            steps=steps
        )

        explorer = BoundaryExplorer(self.registry)
        status, delta, msg = explorer.explore_boundary(refusal.record_id)

        self.assertEqual(status, DialecticalStatus.SYNTHESIS_ACHIEVED)
        self.assertIsNotNone(delta)
        self.assertEqual(delta.old_budget_steps, 80)
        self.assertGreater(delta.recommended_budget_steps, 80)
        self.assertEqual(delta.recommended_budget_steps, int(80 * 1.75))
        self.assertEqual(delta.delta_steps, delta.recommended_budget_steps - 80)
        self.assertGreaterEqual(delta.recommended_budget_steps, 120)

    def test_02_weakest_precondition_domain_guard(self):
        """Test SMT weakest precondition synthesis with verified UNSAT proof DAG."""
        synth = PreconditionSynthesizer()
        # Candidate is correct on inputs 1, 2, 3, fails on 4, 5
        cand_fn = lambda x: str(int(x) ** 2) if int(x) <= 3 else "0"
        spec_fn = lambda x: str(int(x) ** 2)
        domain = ["1", "2", "3", "4", "5"]

        guard, proof_dag = synth.synthesize_domain_guard(cand_fn, spec_fn, domain)

        self.assertIsNotNone(guard)
        self.assertIsNotNone(proof_dag)
        self.assertEqual(guard.admissible_domain, ("1", "2", "3"))
        self.assertEqual(guard.excluded_domain, ("4", "5"))
        self.assertTrue(guard.permits("1"))
        self.assertTrue(guard.permits("2"))
        self.assertTrue(guard.permits("3"))
        self.assertFalse(guard.permits("4"))
        self.assertFalse(guard.permits("5"))

        # Verify resolution proof DAG independently
        self.assertTrue(verify_unsat_certificate(proof_dag))

    def test_03_dialectical_triad_resolution(self):
        """Test full Thesis -> Antithesis -> Synthesis resolution cycle."""
        old_ctx = {"budget_steps": 80}
        outcome, steps, trace = self.candidate.evaluate(old_ctx)
        refusal = self._register_refusal(
            candidate_digest=self.candidate.digest,
            context=old_ctx,
            outcome_type=RefusalReason.RESOURCE_LIMIT,
            trace=trace,
            steps=steps
        )

        orchestrator = DialecticalOrchestrator(self.registry)
        report = orchestrator.discover_and_promote(
            refusal_id=refusal.record_id,
            candidate_bytes=self.candidate.code_bytes,
            executor_fn=lambda cbytes, ctx: self.candidate.evaluate(ctx),
            researcher_hypothesis="Step expansion resolves settlement."
        )

        self.assertEqual(report.triad.status, DialecticalStatus.SYNTHESIS_ACHIEVED)
        self.assertEqual(report.triad.thesis_candidate_digest, self.candidate.digest)
        self.assertEqual(report.triad.antithesis_refusal_id, refusal.record_id)
        self.assertEqual(report.triad.refusal_reason, RefusalReason.RESOURCE_LIMIT)
        self.assertIsNotNone(report.triad.synthesis_delta)
        self.assertIsNotNone(report.scoped_admission)

    def test_04_automated_reevaluation_request_generation(self):
        """Test formulation of valid ReevaluationRequest by DialecticalOrchestrator."""
        old_ctx = {"budget_steps": 80}
        outcome, steps, trace = self.candidate.evaluate(old_ctx)
        refusal = self._register_refusal(
            candidate_digest=self.candidate.digest,
            context=old_ctx,
            outcome_type=RefusalReason.RESOURCE_LIMIT,
            trace=trace,
            steps=steps
        )

        orchestrator = DialecticalOrchestrator(self.registry)
        report = orchestrator.discover_and_promote(
            refusal_id=refusal.record_id,
            candidate_bytes=self.candidate.code_bytes,
            executor_fn=lambda cbytes, ctx: self.candidate.evaluate(ctx)
        )

        req = report.request
        self.assertIsNotNone(req)
        self.assertEqual(req.refusal_id, refusal.record_id)
        self.assertEqual(req.candidate_digest, self.candidate.digest)
        self.assertEqual(req.new_context["budget_steps"], 140)
        self.assertIn("Dialectical delta expansion", req.claimed_basis)

    def test_05_scoped_admission_promotion(self):
        """Test admission granted under new context envelope without epistemic leakage."""
        old_ctx = {"budget_steps": 80}
        outcome, steps, trace = self.candidate.evaluate(old_ctx)
        refusal = self._register_refusal(
            candidate_digest=self.candidate.digest,
            context=old_ctx,
            outcome_type=RefusalReason.RESOURCE_LIMIT,
            trace=trace,
            steps=steps
        )

        orchestrator = DialecticalOrchestrator(self.registry)
        report = orchestrator.discover_and_promote(
            refusal_id=refusal.record_id,
            candidate_bytes=self.candidate.code_bytes,
            executor_fn=lambda cbytes, ctx: self.candidate.evaluate(ctx)
        )

        self.assertIsNotNone(report.scoped_admission)
        # Admitted in target envelope
        self.assertIsNotNone(self.registry.admission_for(
            candidate_digest=self.candidate.digest,
            context={"budget_steps": 140},
            evaluator_digest=self.evaluator_digest,
            requirement_digest=self.req_digest
        ))
        # NOT admitted in past failed envelope (anti-ossification / zero leakage)
        self.assertIsNone(self.registry.admission_for(
            candidate_digest=self.candidate.digest,
            context=old_ctx,
            evaluator_digest=self.evaluator_digest,
            requirement_digest=self.req_digest
        ))

    def test_06_semantic_refusal_non_promotability(self):
        """Invariant SA2/DIAL3: SEMANTIC_COUNTEREXAMPLE returns ANTITHESIS_UNYIELDING."""
        old_ctx = {"budget_steps": 80}
        outcome, steps, trace = self.semantic_cand.evaluate(old_ctx)
        refusal = self._register_refusal(
            candidate_digest=self.semantic_cand.digest,
            context=old_ctx,
            outcome_type=RefusalReason.SEMANTIC_COUNTEREXAMPLE,
            trace=trace,
            steps=steps
        )

        explorer = BoundaryExplorer(self.registry)
        status, delta, msg = explorer.explore_boundary(refusal.record_id)
        self.assertEqual(status, DialecticalStatus.ANTITHESIS_UNYIELDING)
        self.assertIsNone(delta)

        orchestrator = DialecticalOrchestrator(self.registry)
        report = orchestrator.discover_and_promote(
            refusal_id=refusal.record_id,
            candidate_bytes=self.semantic_cand.code_bytes,
            executor_fn=lambda cbytes, ctx: self.semantic_cand.evaluate(ctx)
        )
        self.assertEqual(report.triad.status, DialecticalStatus.ANTITHESIS_UNYIELDING)
        self.assertIsNone(report.scoped_admission)

    def test_07_quota_exhaustion_containment(self):
        """Invariant SA5/DIAL5: Explorer halts with RESOURCE_BOUNDED when quota is spent."""
        old_ctx = {"budget_steps": 50}
        refusal = self._register_refusal(
            candidate_digest=self.candidate.digest,
            context=old_ctx,
            outcome_type=RefusalReason.RESOURCE_LIMIT,
            trace=b"trace",
            steps=50
        )

        # Manually exhaust the 3 attempts
        self.registry.attempts_spent[refusal.record_id] = 3

        explorer = BoundaryExplorer(self.registry)
        status, delta, msg = explorer.explore_boundary(refusal.record_id)
        self.assertEqual(status, DialecticalStatus.RESOURCE_BOUNDED)
        self.assertIsNone(delta)

    def test_08_e_to_a_warrant_elevation(self):
        """Grade A warrant generation for SMT-certified dialectical synthesis."""
        synth = PreconditionSynthesizer()
        cand_fn = lambda x: str(int(x) ** 2) if int(x) <= 3 else "0"
        spec_fn = lambda x: str(int(x) ** 2)
        domain = ["1", "2", "3"]
        guard, proof_dag = synth.synthesize_domain_guard(cand_fn, spec_fn, domain)

        triad = DialecticalTriad(
            thesis_candidate_digest=sha256_hex(b"cand"),
            antithesis_refusal_id=sha256_hex(b"refusal_001"),
            refusal_reason=RefusalReason.RESOURCE_LIMIT,
            synthesis_delta=ContextDelta(80, 140, 60, 1.75, 0.95),
            precondition=guard,
            status=DialecticalStatus.SYNTHESIS_ACHIEVED,
            settled_theorem="Proved equivalence on admissible domain."
        )
        report = DialecticalDiscoveryReport(
            triad=triad,
            smt_verified=True,
            proof_dag=proof_dag,
            elapsed_sec=0.01
        )

        warrant = elevate_triad_to_warrant(report, self.sk_author, self.pk_author)
        self.assertEqual(warrant.grade, EvidenceGrade.AXIOMATIC)
        self.assertEqual(warrant.polarity, Polarity.AFFIRM)
        self.assertEqual(warrant.author_pk_hex, self.pk_author)

        self.assertTrue(warrant.verify_signature())

    def test_09_iso32000_polyglot_pdf_and_audit(self):
        """Test ISO 32000 vector polyglot generation and standalone Python auditor execution."""
        old_ctx = {"budget_steps": 80}
        outcome, steps, trace = self.candidate.evaluate(old_ctx)
        refusal = self._register_refusal(
            candidate_digest=self.candidate.digest,
            context=old_ctx,
            outcome_type=RefusalReason.RESOURCE_LIMIT,
            trace=trace,
            steps=steps
        )

        orchestrator = DialecticalOrchestrator(self.registry)
        report = orchestrator.discover_and_promote(
            refusal_id=refusal.record_id,
            candidate_bytes=self.candidate.code_bytes,
            executor_fn=lambda cbytes, ctx: self.candidate.evaluate(ctx)
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "dialectic_discovery.pdf")
            generate_dialectic_pdf(report, pdf_path)
            self.assertTrue(os.path.exists(pdf_path))

            with open(pdf_path, "rb") as f:
                content = f.read()
            self.assertIn(b"%PDF-1.7", content)
            self.assertIn(b"DIALECTICAL DISCOVERY & SCOPED ADMISSION", content)

            proc = subprocess.run(
                [sys.executable, pdf_path],
                capture_output=True,
                text=True,
                timeout=10
            )
            self.assertEqual(proc.returncode, 0, f"Auditor failed: {proc.stderr}")
            self.assertIn("DIALECTICAL DISCOVERY AUDIT COMPLETE: ALL INVARIANTS SATISFIED", proc.stdout)

    def test_10_append_only_physicality(self):
        """Verify append_dialectic_hud preserves document prefix byte-for-byte."""
        dummy_before = b"%PDF-1.7\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n"
        with tempfile.TemporaryDirectory() as tmpdir:
            orig_pdf = os.path.join(tmpdir, "orig.pdf")
            out_pdf = os.path.join(tmpdir, "appended.pdf")
            with open(orig_pdf, "wb") as f:
                f.write(dummy_before)

            triad = DialecticalTriad(
                thesis_candidate_digest="THESIS_DIGEST",
                antithesis_refusal_id="REFUSAL_001",
                refusal_reason=RefusalReason.RESOURCE_LIMIT,
                synthesis_delta=ContextDelta(50, 100, 50, 2.0, 0.95),
                precondition=None,
                status=DialecticalStatus.SYNTHESIS_ACHIEVED,
                settled_theorem="Theorem 1"
            )
            report = DialecticalDiscoveryReport(triad=triad)
            append_dialectic_hud(orig_pdf, report, out_pdf)

            with open(out_pdf, "rb") as f:
                appended_bytes = f.read()

            self.assertTrue(appended_bytes.startswith(dummy_before))
            self.assertIn(b"%=== DIALECTICAL DISCOVERY APPEND-ONLY BLOCK ===", appended_bytes)


if __name__ == "__main__":
    unittest.main()
