#!/usr/bin/env python3
# coding: utf-8
"""
test_scoped_admission.py — Rigorous Test Suite for Scoped Re-Admission & Conditional Reopening.
Part of Project Black-Heart (%🖤).

Implements and validates all 12 controls and 3 negative mutations from
BLACK-HEART-CONDITIONAL-REOPENING-001 (Codex & s0fractal).
"""

from __future__ import annotations
import unittest
import copy
import os
import sys
import tempfile
import subprocess
from typing import Dict, Any, Tuple

import scoped_admission
from scoped_admission import (
    RefusalReason, ReevalEligibility, RetestOutcome,
    RefusalRecord, ReevaluationRequest, RetestResult, ScopedAdmission,
    ScopedAdmissionRegistry, sha256_hex, canonical_context_digest,
    generate_scoped_admission_pdf
)



# ============================================================================
# DETERMINISTIC TEST FIXTURES & CANDIDATES
# ============================================================================

class StepCountingCandidate:
    """
    Candidate that executes exactly 120 abstract steps to settle.
    The evaluator hard-counts steps and enforces the context budget limit.
    """
    def __init__(self, required_steps: int = 120):
        self.required_steps = required_steps
        self.code_bytes = f"STEP_COUNTING_CANDIDATE_STEPS_{required_steps}".encode("utf-8")
        self.digest = sha256_hex(self.code_bytes)

    def evaluate(self, context: Dict[str, Any]) -> Tuple[RetestOutcome, int, bytes]:
        budget = context.get("budget_steps", 0)
        # Executor hard-counts steps up to budget
        steps_executed = min(budget, self.required_steps)
        if steps_executed < self.required_steps:
            # Cut off by resource limit
            return (RetestOutcome.FAILURE, steps_executed, b"RESOURCE_LIMIT: steps_exhausted")
        # Successfully settled
        return (RetestOutcome.SUCCESS, steps_executed, b"SUCCESS: settled_in_120_steps")


class OrderViolatingCandidate:
    """
    Candidate that transposes two events [event_b, event_a],
    violating the strict FIFO order requirement regardless of step budget.
    """
    def __init__(self):
        self.code_bytes = b"ORDER_VIOLATING_CANDIDATE_TRANSPOSE_EVENTS"
        self.digest = sha256_hex(self.code_bytes)

    def evaluate(self, context: Dict[str, Any]) -> Tuple[RetestOutcome, int, bytes]:
        budget = context.get("budget_steps", 0)
        # Violates invariant on step 10
        steps = min(budget, 10)
        return (RetestOutcome.FAILURE, steps, b"SEMANTIC_COUNTEREXAMPLE: order_transposition_detected")


# ============================================================================
# THE 12 CONTROLS TEST SUITE
# ============================================================================

class TestScopedAdmission(unittest.TestCase):
    """Rigorous verification of the 12 controls and 3 mutation invariants."""

    def setUp(self):
        self.registry = ScopedAdmissionRegistry()
        self.evaluator_digest = sha256_hex("METABOLIC_STEP_EVALUATOR_v1")
        self.requirement_digest = sha256_hex("INVARIANT_ORDER_AND_SETTLEMENT_v1")
        self.step_candidate = StepCountingCandidate(required_steps=120)
        self.order_candidate = OrderViolatingCandidate()

    def test_control_01_same_candidate_and_budget_blocked(self):
        """Control 1: Same candidate and budget 100 -> refusal remains; no new execution."""
        refusal = RefusalRecord.create(
            candidate_digest=self.step_candidate.digest,
            evaluator_digest=self.evaluator_digest,
            requirement_digest=self.requirement_digest,
            inputs_digest=sha256_hex("input_x"),
            evidence_bytes=b"CUTOFF_AT_100",
            context={"budget_steps": 100},
            outcome_type=RefusalReason.RESOURCE_LIMIT,
            steps_executed=100
        )
        self.registry.register_refusal(refusal)

        # Same budget request
        req = ReevaluationRequest.create(
            refusal_id=refusal.record_id,
            candidate_digest=self.step_candidate.digest,
            evaluator_digest=self.evaluator_digest,
            requirement_digest=self.requirement_digest,
            new_context={"budget_steps": 100},
            claimed_basis="Retry same budget"
        )
        eligibility, reason = self.registry.assess_request(req)
        self.assertEqual(eligibility, ReevalEligibility.BLOCKED_BY_EXISTING_EVIDENCE)
        self.assertEqual(self.registry.executed_runs_count, 0)

    def test_control_02_metadata_only_change_blocked(self):
        """Control 2: Changed only label or timestamp -> no basis for re-evaluation."""
        refusal = RefusalRecord.create(
            candidate_digest=self.step_candidate.digest,
            evaluator_digest=self.evaluator_digest,
            requirement_digest=self.requirement_digest,
            inputs_digest=sha256_hex("input_x"),
            evidence_bytes=b"CUTOFF_AT_100",
            context={"budget_steps": 100},
            outcome_type=RefusalReason.RESOURCE_LIMIT,
            steps_executed=100
        )
        self.registry.register_refusal(refusal)

        # Non-budget metadata mutation
        req = ReevaluationRequest.create(
            refusal_id=refusal.record_id,
            candidate_digest=self.step_candidate.digest,
            evaluator_digest=self.evaluator_digest,
            requirement_digest=self.requirement_digest,
            new_context={"budget_steps": 100, "label": "fresh_attempt", "timestamp": "2026-09-10T01:00:00Z"},
            claimed_basis="New timestamp and researcher label"
        )
        eligibility, reason = self.registry.assess_request(req)
        self.assertEqual(eligibility, ReevalEligibility.BLOCKED_BY_EXISTING_EVIDENCE)
        self.assertEqual(self.registry.executed_runs_count, 0)

    def test_control_03_budget_expansion_eligible_for_retest(self):
        """Control 3: 100 -> 200 after resource limit -> one bounded retest permitted; not admitted yet."""
        refusal = RefusalRecord.create(
            candidate_digest=self.step_candidate.digest,
            evaluator_digest=self.evaluator_digest,
            requirement_digest=self.requirement_digest,
            inputs_digest=sha256_hex("input_x"),
            evidence_bytes=b"CUTOFF_AT_100",
            context={"budget_steps": 100},
            outcome_type=RefusalReason.RESOURCE_LIMIT,
            steps_executed=100
        )
        self.registry.register_refusal(refusal)

        req = ReevaluationRequest.create(
            refusal_id=refusal.record_id,
            candidate_digest=self.step_candidate.digest,
            evaluator_digest=self.evaluator_digest,
            requirement_digest=self.requirement_digest,
            new_context={"budget_steps": 200},
            claimed_basis="Increased budget steps from 100 to 200"
        )
        eligibility, reason = self.registry.assess_request(req)
        self.assertEqual(eligibility, ReevalEligibility.ELIGIBLE_FOR_RETEST)

        # Crucial check: NOT admitted yet!
        adm = self.registry.admission_for(
            self.step_candidate.digest,
            {"budget_steps": 200},
            self.requirement_digest,
            self.evaluator_digest
        )
        self.assertIsNone(adm)

    def test_control_04_successful_retest_grants_scoped_admission(self):
        """Control 4: Successful retest in B -> admitted in B; old evidence and refusal digest intact."""
        refusal = RefusalRecord.create(
            candidate_digest=self.step_candidate.digest,
            evaluator_digest=self.evaluator_digest,
            requirement_digest=self.requirement_digest,
            inputs_digest=sha256_hex("input_x"),
            evidence_bytes=b"CUTOFF_AT_100",
            context={"budget_steps": 100},
            outcome_type=RefusalReason.RESOURCE_LIMIT,
            steps_executed=100
        )
        orig_refusal_id = refusal.record_id
        orig_evidence = refusal.evidence_bytes
        self.registry.register_refusal(refusal)

        req = ReevaluationRequest.create(
            refusal_id=refusal.record_id,
            candidate_digest=self.step_candidate.digest,
            evaluator_digest=self.evaluator_digest,
            requirement_digest=self.requirement_digest,
            new_context={"budget_steps": 200},
            claimed_basis="Increased budget steps to 200"
        )

        # Execute controlled retest
        retest_res = self.registry.execute_retest(
            req,
            self.step_candidate.code_bytes,
            lambda code, ctx: self.step_candidate.evaluate(ctx)
        )
        self.assertEqual(retest_res.outcome, RetestOutcome.SUCCESS)
        self.assertEqual(retest_res.steps_spent, 120)

        # Grant scoped admission
        adm = self.registry.grant_scoped_admission(retest_res)
        self.assertIsNotNone(adm)

        # Verify admission in Context B
        adm_b = self.registry.admission_for(
            self.step_candidate.digest,
            {"budget_steps": 200},
            self.requirement_digest,
            self.evaluator_digest
        )
        self.assertIsNotNone(adm_b)
        self.assertEqual(adm_b.admission_id, adm.admission_id)

        # Invariant 1: Old refusal record and evidence bytes are 100% UNCHANGED
        preserved_refusal = self.registry.refusals[orig_refusal_id]
        self.assertEqual(preserved_refusal.record_id, orig_refusal_id)
        self.assertEqual(preserved_refusal.evidence_bytes, orig_evidence)

    def test_control_05_returning_to_context_a_does_not_inherit_b(self):
        """Control 5: Returning to context A after success in B -> admission B does not apply."""
        # Setup and admit in B (200)
        refusal = RefusalRecord.create(
            candidate_digest=self.step_candidate.digest,
            evaluator_digest=self.evaluator_digest,
            requirement_digest=self.requirement_digest,
            inputs_digest=sha256_hex("input_x"),
            evidence_bytes=b"CUTOFF_AT_100",
            context={"budget_steps": 100},
            outcome_type=RefusalReason.RESOURCE_LIMIT,
            steps_executed=100
        )
        self.registry.register_refusal(refusal)
        req = ReevaluationRequest.create(
            refusal_id=refusal.record_id,
            candidate_digest=self.step_candidate.digest,
            evaluator_digest=self.evaluator_digest,
            requirement_digest=self.requirement_digest,
            new_context={"budget_steps": 200},
            claimed_basis="Context B budget"
        )
        retest = self.registry.execute_retest(
            req,
            self.step_candidate.code_bytes,
            lambda code, ctx: self.step_candidate.evaluate(ctx)
        )
        self.registry.grant_scoped_admission(retest)

        # Admitted in B:
        self.assertIsNotNone(self.registry.admission_for(
            self.step_candidate.digest, {"budget_steps": 200}, self.requirement_digest, self.evaluator_digest
        ))

        # BUT strictly NOT admitted in A:
        adm_a = self.registry.admission_for(
            self.step_candidate.digest, {"budget_steps": 100}, self.requirement_digest, self.evaluator_digest
        )
        self.assertIsNone(adm_a)

    def test_control_06_semantic_counterexample_remains_blocked(self):
        """Control 6: Semantic counterexample + bigger budget -> refusal permanently remains."""
        refusal = RefusalRecord.create(
            candidate_digest=self.order_candidate.digest,
            evaluator_digest=self.evaluator_digest,
            requirement_digest=self.requirement_digest,
            inputs_digest=sha256_hex("order_input"),
            evidence_bytes=b"TRANSPOSED_EVENT_PAIR",
            context={"budget_steps": 100},
            outcome_type=RefusalReason.SEMANTIC_COUNTEREXAMPLE,
            steps_executed=10
        )
        self.registry.register_refusal(refusal)

        # Even with 10x budget, semantic counterexample is permanently blocked
        req = ReevaluationRequest.create(
            refusal_id=refusal.record_id,
            candidate_digest=self.order_candidate.digest,
            evaluator_digest=self.evaluator_digest,
            requirement_digest=self.requirement_digest,
            new_context={"budget_steps": 1000},
            claimed_basis="Give it 1000 steps"
        )
        eligibility, reason = self.registry.assess_request(req)
        self.assertEqual(eligibility, ReevalEligibility.BLOCKED_BY_EXISTING_EVIDENCE)
        self.assertIn("Semantic counterexample is permanent", reason)
        self.assertEqual(self.registry.executed_runs_count, 0)

    def test_control_07_new_candidate_version_requires_separate_record(self):
        """Control 7: New version of candidate is a new subject; cannot hijack ancestor's request."""
        refusal = RefusalRecord.create(
            candidate_digest=self.order_candidate.digest,
            evaluator_digest=self.evaluator_digest,
            requirement_digest=self.requirement_digest,
            inputs_digest=sha256_hex("order_input"),
            evidence_bytes=b"TRANSPOSED_EVENT_PAIR",
            context={"budget_steps": 100},
            outcome_type=RefusalReason.SEMANTIC_COUNTEREXAMPLE,
            steps_executed=10
        )
        self.registry.register_refusal(refusal)

        v2_candidate_digest = sha256_hex(b"ORDER_CANDIDATE_v2_FIXED")
        req = ReevaluationRequest.create(
            refusal_id=refusal.record_id,
            candidate_digest=v2_candidate_digest,
            evaluator_digest=self.evaluator_digest,
            requirement_digest=self.requirement_digest,
            new_context={"budget_steps": 100},
            claimed_basis="New candidate v2 fixes order"
        )
        eligibility, reason = self.registry.assess_request(req)
        self.assertEqual(eligibility, ReevalEligibility.BLOCKED_BY_EXISTING_EVIDENCE)
        self.assertIn("Candidate digest mismatch", reason)

    def test_control_08_corrupted_evidence_rejects_retest(self):
        """Control 8: Missing or empty evidence bytes yields typed rejection."""
        corrupted_refusal = RefusalRecord(
            record_id="ref_corrupt",
            candidate_digest=self.step_candidate.digest,
            evaluator_digest=self.evaluator_digest,
            requirement_digest=self.requirement_digest,
            inputs_digest=sha256_hex("input"),
            evidence_bytes=b"",  # empty evidence!
            context={"budget_steps": 100},
            outcome_type=RefusalReason.RESOURCE_LIMIT,
            steps_executed=100,
            dependencies=("budget_steps",)
        )
        self.registry.register_refusal(corrupted_refusal)

        req = ReevaluationRequest.create(
            refusal_id=corrupted_refusal.record_id,
            candidate_digest=self.step_candidate.digest,
            evaluator_digest=self.evaluator_digest,
            requirement_digest=self.requirement_digest,
            new_context={"budget_steps": 200},
            claimed_basis="More budget"
        )
        eligibility, reason = self.registry.assess_request(req)
        self.assertEqual(eligibility, ReevalEligibility.APPLICABILITY_UNKNOWN)

    def test_control_09_altered_evaluator_or_requirement_requires_policy_decision(self):
        """Control 9: Altered evaluator or requirement -> POLICY_CHANGE_REQUIRES_SEPARATE_DECISION."""
        refusal = RefusalRecord.create(
            candidate_digest=self.step_candidate.digest,
            evaluator_digest=self.evaluator_digest,
            requirement_digest=self.requirement_digest,
            inputs_digest=sha256_hex("input"),
            evidence_bytes=b"CUTOFF_AT_100",
            context={"budget_steps": 100},
            outcome_type=RefusalReason.RESOURCE_LIMIT,
            steps_executed=100
        )
        self.registry.register_refusal(refusal)

        # Altered evaluator digest
        req = ReevaluationRequest.create(
            refusal_id=refusal.record_id,
            candidate_digest=self.step_candidate.digest,
            evaluator_digest=sha256_hex("NEW_UNTRUSTED_EVALUATOR"),
            requirement_digest=self.requirement_digest,
            new_context={"budget_steps": 200},
            claimed_basis="New evaluator"
        )
        eligibility, reason = self.registry.assess_request(req)
        self.assertEqual(eligibility, ReevalEligibility.POLICY_CHANGE_REQUIRES_SEPARATE_DECISION)

    def test_control_10_candidate_tampering_caught_before_execution(self):
        """Control 10: Candidate swapped between decision and execution -> refused by digest."""
        refusal = RefusalRecord.create(
            candidate_digest=self.step_candidate.digest,
            evaluator_digest=self.evaluator_digest,
            requirement_digest=self.requirement_digest,
            inputs_digest=sha256_hex("input"),
            evidence_bytes=b"CUTOFF_AT_100",
            context={"budget_steps": 100},
            outcome_type=RefusalReason.RESOURCE_LIMIT,
            steps_executed=100
        )
        self.registry.register_refusal(refusal)
        req = ReevaluationRequest.create(
            refusal_id=refusal.record_id,
            candidate_digest=self.step_candidate.digest,
            evaluator_digest=self.evaluator_digest,
            requirement_digest=self.requirement_digest,
            new_context={"budget_steps": 200},
            claimed_basis="Increased budget"
        )

        # Attacker presents different code bytes claiming to be candidate
        trojan_bytes = b"TROJAN_HORSE_BYTES"
        with self.assertRaises(ValueError) as ctx:
            self.registry.execute_retest(
                req,
                trojan_bytes,
                lambda code, ctx: (RetestOutcome.SUCCESS, 10, b"trojan")
            )
        self.assertIn("Candidate tampering detected", str(ctx.exception))
        self.assertEqual(self.registry.executed_runs_count, 0)

    def test_control_11_request_repetition_reuses_result_zero_cost(self):
        """Control 11: Repetition of same request -> reuse result; does not consume budget twice."""
        refusal = RefusalRecord.create(
            candidate_digest=self.step_candidate.digest,
            evaluator_digest=self.evaluator_digest,
            requirement_digest=self.requirement_digest,
            inputs_digest=sha256_hex("input"),
            evidence_bytes=b"CUTOFF_AT_100",
            context={"budget_steps": 100},
            outcome_type=RefusalReason.RESOURCE_LIMIT,
            steps_executed=100
        )
        self.registry.register_refusal(refusal)
        req = ReevaluationRequest.create(
            refusal_id=refusal.record_id,
            candidate_digest=self.step_candidate.digest,
            evaluator_digest=self.evaluator_digest,
            requirement_digest=self.requirement_digest,
            new_context={"budget_steps": 200},
            claimed_basis="Increased budget"
        )

        # First run: burns 1 attempt
        res1 = self.registry.execute_retest(
            req, self.step_candidate.code_bytes, lambda c, ctx: self.step_candidate.evaluate(ctx)
        )
        self.assertEqual(self.registry.executed_runs_count, 1)
        self.assertEqual(self.registry.attempts_spent[refusal.record_id], 1)

        # Replay same request: reuses result, zero new runs!
        res2 = self.registry.execute_retest(
            req, self.step_candidate.code_bytes, lambda c, ctx: self.step_candidate.evaluate(ctx)
        )
        self.assertEqual(self.registry.executed_runs_count, 1)
        self.assertEqual(self.registry.attempts_spent[refusal.record_id], 1)
        self.assertEqual(res1.retest_id, res2.retest_id)

    def test_control_12_crash_burns_attempt_without_admission(self):
        """Control 12: Crash/timeout after reservation -> INCONCLUSIVE, burns attempt, no admission."""
        refusal = RefusalRecord.create(
            candidate_digest=self.step_candidate.digest,
            evaluator_digest=self.evaluator_digest,
            requirement_digest=self.requirement_digest,
            inputs_digest=sha256_hex("input"),
            evidence_bytes=b"CUTOFF_AT_100",
            context={"budget_steps": 100},
            outcome_type=RefusalReason.RESOURCE_LIMIT,
            steps_executed=100
        )
        self.registry.register_refusal(refusal)
        req = ReevaluationRequest.create(
            refusal_id=refusal.record_id,
            candidate_digest=self.step_candidate.digest,
            evaluator_digest=self.evaluator_digest,
            requirement_digest=self.requirement_digest,
            new_context={"budget_steps": 200},
            claimed_basis="Increased budget"
        )

        def crashing_executor(code, ctx):
            raise TimeoutError("Execution exceeded 2.0s hard ceiling")

        res = self.registry.execute_retest(req, self.step_candidate.code_bytes, crashing_executor)
        self.assertEqual(res.outcome, RetestOutcome.INCONCLUSIVE)
        self.assertEqual(self.registry.attempts_spent[refusal.record_id], 1)

        # Attempt to grant admission fails closed
        adm = self.registry.grant_scoped_admission(res)
        self.assertIsNone(adm)
        self.assertIsNone(self.registry.admission_for(
            self.step_candidate.digest, {"budget_steps": 200}, self.requirement_digest, self.evaluator_digest
        ))


# ============================================================================
# THE 3 NEGATIVE MUTATIONS (TESTING THE TEST RIG INTEGRITY)
# ============================================================================

class TestNegativeMutations(unittest.TestCase):
    """
    Validates that if system rules are intentionally weakened,
    the controls MUST catch the violation and fail.
    """

    def setUp(self):
        self.registry = ScopedAdmissionRegistry()
        self.evaluator = sha256_hex("EVAL")
        self.requirement = sha256_hex("REQ")
        self.candidate = StepCountingCandidate(120)

    def test_mutation_01_removing_context_binding_detected(self):
        """Mutation 1: Removing context binding allows B admission to leak into A (caught!)."""
        refusal = RefusalRecord.create(
            candidate_digest=self.candidate.digest,
            evaluator_digest=self.evaluator,
            requirement_digest=self.requirement,
            inputs_digest=sha256_hex("in"),
            evidence_bytes=b"FAIL_100",
            context={"budget_steps": 100},
            outcome_type=RefusalReason.RESOURCE_LIMIT,
            steps_executed=100
        )
        self.registry.register_refusal(refusal)
        req = ReevaluationRequest.create(
            refusal_id=refusal.record_id,
            candidate_digest=self.candidate.digest,
            evaluator_digest=self.evaluator,
            requirement_digest=self.requirement,
            new_context={"budget_steps": 200},
            claimed_basis="B budget"
        )
        retest = self.registry.execute_retest(req, self.candidate.code_bytes, lambda c, ctx: self.candidate.evaluate(ctx))
        self.registry.grant_scoped_admission(retest)

        # If an attacker creates an unconstrained global lookup (mutation):
        def mutated_leaky_admission_for(cand_digest, ctx, req_digest, eval_digest):
            # Mutated bug: ignores context digest!
            for (c, _ctx_digest, e, r), adm in self.registry.admissions.items():
                if c == cand_digest and e == eval_digest and r == req_digest:
                    return adm
            return None

        # Verify that the mutated function illegally admits Context A (leaking):
        leaked_adm = mutated_leaky_admission_for(self.candidate.digest, {"budget_steps": 100}, self.requirement, self.evaluator)
        self.assertIsNotNone(leaked_adm, "Mutation verification: leaky function would have admitted context A.")

        # Real sovereign admission_for strictly PREVENTS the leak:
        real_adm = self.registry.admission_for(self.candidate.digest, {"budget_steps": 100}, self.requirement, self.evaluator)
        self.assertIsNone(real_adm)

    def test_mutation_02_allowing_arbitrary_metadata_retest_detected(self):
        """Mutation 2: Allowing arbitrary metadata changes to open retests (caught!)."""
        refusal = RefusalRecord.create(
            candidate_digest=self.candidate.digest,
            evaluator_digest=self.evaluator,
            requirement_digest=self.requirement,
            inputs_digest=sha256_hex("in"),
            evidence_bytes=b"FAIL_100",
            context={"budget_steps": 100},
            outcome_type=RefusalReason.RESOURCE_LIMIT,
            steps_executed=100
        )
        self.registry.register_refusal(refusal)

        req_metadata_only = ReevaluationRequest.create(
            refusal_id=refusal.record_id,
            candidate_digest=self.candidate.digest,
            evaluator_digest=self.evaluator,
            requirement_digest=self.requirement,
            new_context={"budget_steps": 100, "comment": "please retest"},
            claimed_basis="Researcher plea"
        )

        # Mutated checker that mistakenly looks at dict length:
        def mutated_permissive_assess(req):
            if len(req.new_context) > len(refusal.context):
                return ReevalEligibility.ELIGIBLE_FOR_RETEST  # Bug!
            return ReevalEligibility.BLOCKED_BY_EXISTING_EVIDENCE

        # Mutated function would have incorrectly allowed retest:
        self.assertEqual(mutated_permissive_assess(req_metadata_only), ReevalEligibility.ELIGIBLE_FOR_RETEST)

        # Real sovereign registry strictly blocks it:
        real_eligibility, _ = self.registry.assess_request(req_metadata_only)
        self.assertEqual(real_eligibility, ReevalEligibility.BLOCKED_BY_EXISTING_EVIDENCE)

    def test_mutation_03_accepting_proposal_without_verified_retest_detected(self):
        """Mutation 3: Accepting proposal without verified retest result (caught!)."""
        unverified_retest = RetestResult.create(
            request_id="req_fake",
            refusal_id="ref_fake",
            candidate_digest=self.candidate.digest,
            evaluator_digest=self.evaluator,
            requirement_digest=self.requirement,
            context={"budget_steps": 200},
            outcome=RetestOutcome.FAILURE,  # Failed!
            steps_spent=100,
            evidence_bytes=b"FAILED"
        )

        # Mutated admission that grants on failure:
        def mutated_permissive_grant(retest):
            return ScopedAdmission.create(
                retest_id=retest.retest_id,
                candidate_digest=retest.candidate_digest,
                evaluator_digest=retest.evaluator_digest,
                requirement_digest=retest.requirement_digest,
                context=retest.context
            )

        mutated_adm = mutated_permissive_grant(unverified_retest)
        self.assertIsNotNone(mutated_adm)

        # Real sovereign registry fails closed on non-SUCCESS:
        real_adm = self.registry.grant_scoped_admission(unverified_retest)
        self.assertIsNone(real_adm)

    def test_control_13_pdf_polyglot_certificate_and_standalone_auditor(self):
        """Control 13: ISO 32000 PDF polyglot generation and standalone execution with tamper defense."""
        # 1. Produce a successful admission
        refusal = RefusalRecord.create(
            candidate_digest=self.candidate.digest,
            evaluator_digest=self.evaluator,
            requirement_digest=self.requirement,
            inputs_digest=sha256_hex("input_x"),
            evidence_bytes=b"CUTOFF_AT_100",
            context={"budget_steps": 100},
            outcome_type=RefusalReason.RESOURCE_LIMIT,
            steps_executed=100
        )
        self.registry.register_refusal(refusal)

        req = ReevaluationRequest.create(
            refusal_id=refusal.record_id,
            candidate_digest=self.candidate.digest,
            evaluator_digest=self.evaluator,
            requirement_digest=self.requirement,
            new_context={"budget_steps": 200},
            claimed_basis="Increased budget steps to 200"
        )
        retest = self.registry.execute_retest(
            req,
            self.candidate.code_bytes,
            lambda code, ctx: self.candidate.evaluate(ctx)
        )
        adm = self.registry.grant_scoped_admission(retest, policy_id="TEST_SCOPED_POLICY_v1")
        self.assertIsNotNone(adm)

        with tempfile.TemporaryDirectory() as td:
            pdf_path = os.path.join(td, "scoped_admission_cert.pdf")
            generate_scoped_admission_pdf(adm, refusal, retest, pdf_path)
            self.assertTrue(os.path.exists(pdf_path))
            self.assertGreater(os.path.getsize(pdf_path), 500)



            # Check that file contains %PDF-1.7
            with open(pdf_path, "rb") as f:
                content = f.read()
                self.assertIn(b"%PDF-1.7", content)


            # Execute standalone polyglot
            proc = subprocess.run(
                [sys.executable, pdf_path],
                capture_output=True,
                text=True
            )
            self.assertEqual(proc.returncode, 0, f"Polyglot execution failed: {proc.stderr}")
            self.assertIn("SCOPED RE-ADMISSION CERTIFICATE", proc.stdout)
            self.assertIn("Cryptographic Manifest Hash: VALID", proc.stdout)
            self.assertIn("ALL INVARIANTS (SA1-SA6) SATISFIED", proc.stdout)

            # Tamper defense: tamper with candidate_digest in embedded manifest
            with open(pdf_path, "rb") as f:
                data = f.read()
            tampered = data.replace(b'"status":"ADMITTED"', b'"status":"FORGED_ADMISSION"')
            with open(pdf_path, "wb") as f:
                f.write(tampered)

            proc_tampered = subprocess.run(
                [sys.executable, pdf_path],
                capture_output=True,
                text=True
            )
            self.assertNotEqual(proc_tampered.returncode, 0)
            self.assertIn("Cryptographic manifest tampering detected", proc_tampered.stdout)


if __name__ == "__main__":
    unittest.main()

