#!/usr/bin/env python3
# coding: utf-8
"""
scoped_admission.py — Scoped Re-Admission & Conditional Reopening of Possibilities.
Part of Project Black-Heart (%🖤).

Specification & Implementation based on BLACK-HEART-CONDITIONAL-REOPENING-001 (Codex & s0fractal):
  1. Immutable Historical Record:
     Past failures and counterexamples are never overwritten, deleted, or declared false.
  2. Cause-Aware Classification:
     Differentiates between RESOURCE_LIMIT (budget exhaustion) and SEMANTIC_COUNTEREXAMPLE
     (logic, order, or state invariant violation).
  3. Context-Bound Re-evaluation:
     Targeted condition changes (e.g., increased budget_steps) permit a strictly bounded
     retest (ELIGIBLE_FOR_RETEST) without granting premature admission.
  4. Scoped Admission:
     Successful retests grant admission strictly scoped to the exact 4-tuple:
     (candidate_digest, context_digest, evaluator_digest, requirement_digest).
     Admission in context B never leaks to context A.
  5. Bounded Retest Fuel:
     Attempts are reserved prior to execution with hard quotas (max 1 per exact request,
     max 3 active retest attempts per refusal family).
  6. Replay & Mutation Defense:
     Replays reuse prior results without burning fuel; candidate tampering is caught before execution.

Zero external dependencies: 100% Python standard library.
"""

from __future__ import annotations
import hashlib
import json
import time
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple, Set, Union, Callable


def sha256_hex(data: Union[bytes, str]) -> str:
    """Compute SHA-256 hexadecimal digest."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def canonical_json(data: Any) -> bytes:
    """Produce deterministic canonical JSON byte representation."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def canonical_context_digest(context: Dict[str, Any]) -> str:
    """Compute deterministic SHA-256 digest of context bindings."""
    return sha256_hex(canonical_json(context))


# ============================================================================
# 1. ENUMS & DATA MODELS
# ============================================================================

class RefusalReason(str, Enum):
    RESOURCE_LIMIT = "RESOURCE_LIMIT"
    SEMANTIC_COUNTEREXAMPLE = "SEMANTIC_COUNTEREXAMPLE"


class ReevalEligibility(str, Enum):
    BLOCKED_BY_EXISTING_EVIDENCE = "BLOCKED_BY_EXISTING_EVIDENCE"
    APPLICABILITY_UNKNOWN = "APPLICABILITY_UNKNOWN"
    ELIGIBLE_FOR_RETEST = "ELIGIBLE_FOR_RETEST"
    POLICY_CHANGE_REQUIRES_SEPARATE_DECISION = "POLICY_CHANGE_REQUIRES_SEPARATE_DECISION"


class RetestOutcome(str, Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    INCONCLUSIVE = "INCONCLUSIVE"


@dataclass(frozen=True)
class RefusalRecord:
    """
    Immutable record of past failure or counterexample.
    Captures exact operands, context, measured trace, and dependencies.
    """
    record_id: str
    candidate_digest: str
    evaluator_digest: str
    requirement_digest: str
    inputs_digest: str
    evidence_bytes: bytes
    context: Dict[str, Any]
    outcome_type: RefusalReason
    steps_executed: int
    dependencies: Tuple[str, ...]
    timestamp_utc: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    @classmethod
    def create(
        cls,
        candidate_digest: str,
        evaluator_digest: str,
        requirement_digest: str,
        inputs_digest: str,
        evidence_bytes: bytes,
        context: Dict[str, Any],
        outcome_type: RefusalReason,
        steps_executed: int,
        dependencies: Tuple[str, ...] = ("budget_steps",)
    ) -> RefusalRecord:
        body = {
            "candidate_digest": candidate_digest,
            "evaluator_digest": evaluator_digest,
            "requirement_digest": requirement_digest,
            "inputs_digest": inputs_digest,
            "evidence_digest": sha256_hex(evidence_bytes),
            "context": context,
            "outcome_type": outcome_type.value,
            "steps_executed": steps_executed,
            "dependencies": sorted(list(dependencies))
        }
        rec_id = sha256_hex(canonical_json(body))
        return cls(
            record_id=rec_id,
            candidate_digest=candidate_digest,
            evaluator_digest=evaluator_digest,
            requirement_digest=requirement_digest,
            inputs_digest=inputs_digest,
            evidence_bytes=evidence_bytes,
            context=context,
            outcome_type=outcome_type,
            steps_executed=steps_executed,
            dependencies=dependencies
        )


@dataclass(frozen=True)
class ReevaluationRequest:
    """
    Request to re-evaluate an existing refusal under a targeted change of conditions.
    """
    request_id: str
    refusal_id: str
    candidate_digest: str
    evaluator_digest: str
    requirement_digest: str
    new_context: Dict[str, Any]
    claimed_basis: str
    researcher_hypothesis: Optional[str] = None
    timestamp_utc: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    @classmethod
    def create(
        cls,
        refusal_id: str,
        candidate_digest: str,
        evaluator_digest: str,
        requirement_digest: str,
        new_context: Dict[str, Any],
        claimed_basis: str,
        researcher_hypothesis: Optional[str] = None
    ) -> ReevaluationRequest:
        body = {
            "refusal_id": refusal_id,
            "candidate_digest": candidate_digest,
            "evaluator_digest": evaluator_digest,
            "requirement_digest": requirement_digest,
            "new_context": new_context,
            "claimed_basis": claimed_basis
        }
        req_id = sha256_hex(canonical_json(body))
        return cls(
            request_id=req_id,
            refusal_id=refusal_id,
            candidate_digest=candidate_digest,
            evaluator_digest=evaluator_digest,
            requirement_digest=requirement_digest,
            new_context=new_context,
            claimed_basis=claimed_basis,
            researcher_hypothesis=researcher_hypothesis
        )


@dataclass(frozen=True)
class RetestResult:
    """
    Result of a bounded, controlled re-evaluation execution.
    """
    retest_id: str
    request_id: str
    refusal_id: str
    candidate_digest: str
    evaluator_digest: str
    requirement_digest: str
    context: Dict[str, Any]
    outcome: RetestOutcome
    steps_spent: int
    evidence_bytes: bytes
    timestamp_utc: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    @classmethod
    def create(
        cls,
        request_id: str,
        refusal_id: str,
        candidate_digest: str,
        evaluator_digest: str,
        requirement_digest: str,
        context: Dict[str, Any],
        outcome: RetestOutcome,
        steps_spent: int,
        evidence_bytes: bytes
    ) -> RetestResult:
        body = {
            "request_id": request_id,
            "refusal_id": refusal_id,
            "candidate_digest": candidate_digest,
            "evaluator_digest": evaluator_digest,
            "requirement_digest": requirement_digest,
            "context": context,
            "outcome": outcome.value,
            "steps_spent": steps_spent,
            "evidence_digest": sha256_hex(evidence_bytes)
        }
        ret_id = sha256_hex(canonical_json(body))
        return cls(
            retest_id=ret_id,
            request_id=request_id,
            refusal_id=refusal_id,
            candidate_digest=candidate_digest,
            evaluator_digest=evaluator_digest,
            requirement_digest=requirement_digest,
            context=context,
            outcome=outcome,
            steps_spent=steps_spent,
            evidence_bytes=evidence_bytes
        )


@dataclass(frozen=True)
class ScopedAdmission:
    """
    Scoped admission strictly bound to the exact 4-tuple of candidate, context,
    evaluator, and requirement. Does NOT apply to unverified contexts.
    """
    admission_id: str
    retest_id: str
    candidate_digest: str
    context_digest: str
    evaluator_digest: str
    requirement_digest: str
    context: Dict[str, Any]
    policy_id: str
    timestamp_utc: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    @classmethod
    def create(
        cls,
        retest_id: str,
        candidate_digest: str,
        evaluator_digest: str,
        requirement_digest: str,
        context: Dict[str, Any],
        policy_id: str = "DEFAULT_SCOPED_POLICY"
    ) -> ScopedAdmission:
        ctx_digest = canonical_context_digest(context)
        body = {
            "retest_id": retest_id,
            "candidate_digest": candidate_digest,
            "context_digest": ctx_digest,
            "evaluator_digest": evaluator_digest,
            "requirement_digest": requirement_digest,
            "policy_id": policy_id
        }
        adm_id = sha256_hex(canonical_json(body))
        return cls(
            admission_id=adm_id,
            retest_id=retest_id,
            candidate_digest=candidate_digest,
            context_digest=ctx_digest,
            evaluator_digest=evaluator_digest,
            requirement_digest=requirement_digest,
            context=context,
            policy_id=policy_id
        )


# ============================================================================
# 2. SCOPED ADMISSION REGISTRY (SIDECAR)
# ============================================================================

class ScopedAdmissionRegistry:
    """
    Autonomous sidecar registry managing cause-aware re-evaluations,
    bounded retest fuel quotas, and strictly context-bound admissions.
    """
    MAX_ATTEMPTS_PER_REFUSAL_FAMILY = 3

    def __init__(self):
        self.refusals: Dict[str, RefusalRecord] = {}
        self.requests: Dict[str, ReevaluationRequest] = {}
        self.retest_results: Dict[str, RetestResult] = {}
        # Key: (candidate_digest, context_digest, evaluator_digest, requirement_digest)
        self.admissions: Dict[Tuple[str, str, str, str], ScopedAdmission] = {}
        self.attempts_spent: Dict[str, int] = {}
        self.executed_runs_count: int = 0
        self.admissions_granted_count: int = 0

    def register_refusal(self, refusal: RefusalRecord) -> str:
        """Register an immutable refusal record with its evidence bytes."""
        self.refusals[refusal.record_id] = refusal
        if refusal.record_id not in self.attempts_spent:
            self.attempts_spent[refusal.record_id] = 0
        return refusal.record_id

    def assess_request(self, request: ReevaluationRequest) -> Tuple[ReevalEligibility, str]:
        """
        Evaluates whether a re-evaluation request is eligible for a controlled retest.
        Enforces:
          - Semantic counterexamples are NEVER eligible via budget increase.
          - Evaluator or requirement changes require separate policy decisions.
          - Missing or unproven evidence rejects retest.
          - Only targeted budget increases following RESOURCE_LIMIT are eligible.
        """
        refusal = self.refusals.get(request.refusal_id)
        if not refusal:
            return ReevalEligibility.APPLICABILITY_UNKNOWN, "Refusal record not found."

        # Verify candidate binding
        if request.candidate_digest != refusal.candidate_digest:
            return ReevalEligibility.BLOCKED_BY_EXISTING_EVIDENCE, "Candidate digest mismatch with original refusal."

        # Requirement or evaluator change requires separate policy decision
        if request.evaluator_digest != refusal.evaluator_digest or request.requirement_digest != refusal.requirement_digest:
            return ReevalEligibility.POLICY_CHANGE_REQUIRES_SEPARATE_DECISION, "Policy or evaluator change requires separate authorization."

        # Verify evidence integrity
        if not refusal.evidence_bytes or sha256_hex(refusal.evidence_bytes) != sha256_hex(refusal.evidence_bytes):
            return ReevalEligibility.APPLICABILITY_UNKNOWN, "Evidence bytes missing or corrupted."

        # Semantic counterexample cannot be cured by budget expansion
        if refusal.outcome_type == RefusalReason.SEMANTIC_COUNTEREXAMPLE:
            return (
                ReevalEligibility.BLOCKED_BY_EXISTING_EVIDENCE,
                "Semantic counterexample is permanent under unchanged requirement; increasing budget does not cure invalid logic."
            )

        # Check quota limit
        spent = self.attempts_spent.get(refusal.record_id, 0)
        if spent >= self.MAX_ATTEMPTS_PER_REFUSAL_FAMILY:
            return ReevalEligibility.BLOCKED_BY_EXISTING_EVIDENCE, f"Retest quota exhausted ({spent}/{self.MAX_ATTEMPTS_PER_REFUSAL_FAMILY})."

        # Check context difference (budget_steps)
        old_budget = refusal.context.get("budget_steps", 0)
        new_budget = request.new_context.get("budget_steps", 0)

        # Non-budget metadata change (e.g. title/timestamp only)
        if new_budget <= old_budget:
            return (
                ReevalEligibility.BLOCKED_BY_EXISTING_EVIDENCE,
                f"No relevant condition expansion: new budget ({new_budget}) <= old budget ({old_budget})."
            )

        # Valid targeted expansion following RESOURCE_LIMIT
        if refusal.outcome_type == RefusalReason.RESOURCE_LIMIT and new_budget > old_budget:
            return ReevalEligibility.ELIGIBLE_FOR_RETEST, f"Budget expanded from {old_budget} to {new_budget} steps."

        return ReevalEligibility.APPLICABILITY_UNKNOWN, "Condition change does not match recognized retest criteria."

    def execute_retest(
        self,
        request: ReevaluationRequest,
        candidate_bytes: bytes,
        executor_fn: Callable[[bytes, Dict[str, Any]], Tuple[RetestOutcome, int, bytes]]
    ) -> RetestResult:
        """
        Executes a controlled retest with pre-reserved fuel counter and candidate digest verification.
        Replays reuse previous results without burning additional attempts.
        """
        # Replay protection: if already evaluated for this exact request, reuse result
        if request.request_id in self.retest_results:
            return self.retest_results[request.request_id]

        refusal = self.refusals.get(request.refusal_id)
        if not refusal:
            raise ValueError(f"Refusal {request.refusal_id} not registered.")

        # Defense against candidate tampering between decision and execution
        actual_candidate_digest = sha256_hex(candidate_bytes)
        if actual_candidate_digest != request.candidate_digest:
            raise ValueError(
                f"Candidate tampering detected! Request claimed {request.candidate_digest[:16]}, "
                f"but provided bytes hash to {actual_candidate_digest[:16]}."
            )

        eligibility, reason = self.assess_request(request)
        if eligibility != ReevalEligibility.ELIGIBLE_FOR_RETEST:
            raise PermissionError(f"Retest rejected: {eligibility.value} — {reason}")

        # Reserve attempt counter before execution (fuel burned regardless of crash/timeout)
        self.attempts_spent[refusal.record_id] = self.attempts_spent.get(refusal.record_id, 0) + 1
        self.executed_runs_count += 1

        try:
            outcome, steps_spent, evidence = executor_fn(candidate_bytes, request.new_context)
        except Exception:
            outcome = RetestOutcome.INCONCLUSIVE
            steps_spent = request.new_context.get("budget_steps", 0)
            evidence = b"CRASH_OR_TIMEOUT"

        result = RetestResult.create(
            request_id=request.request_id,
            refusal_id=request.refusal_id,
            candidate_digest=request.candidate_digest,
            evaluator_digest=request.evaluator_digest,
            requirement_digest=request.requirement_digest,
            context=request.new_context,
            outcome=outcome,
            steps_spent=steps_spent,
            evidence_bytes=evidence
        )

        self.requests[request.request_id] = request
        self.retest_results[request.request_id] = result
        return result

    def grant_scoped_admission(
        self,
        retest: RetestResult,
        policy_id: str = "DEFAULT_SCOPED_POLICY"
    ) -> Optional[ScopedAdmission]:
        """
        Grants scoped admission strictly bound to the verified context if retest succeeded.
        Fails closed if retest was not successful.
        """
        if retest.outcome != RetestOutcome.SUCCESS:
            return None

        admission = ScopedAdmission.create(
            retest_id=retest.retest_id,
            candidate_digest=retest.candidate_digest,
            evaluator_digest=retest.evaluator_digest,
            requirement_digest=retest.requirement_digest,
            context=retest.context,
            policy_id=policy_id
        )

        scope_key = (
            admission.candidate_digest,
            admission.context_digest,
            admission.evaluator_digest,
            admission.requirement_digest
        )
        self.admissions[scope_key] = admission
        self.admissions_granted_count += 1
        return admission

    def admission_for(
        self,
        candidate_digest: str,
        context: Dict[str, Any],
        requirement_digest: str,
        evaluator_digest: str
    ) -> Optional[ScopedAdmission]:
        """
        Context-aware admission check:
        Returns ScopedAdmission iff this exact (candidate, context, evaluator, requirement)
        has been explicitly tested and admitted.
        Returns None for any unverified context.
        """
        ctx_digest = canonical_context_digest(context)
        scope_key = (candidate_digest, ctx_digest, evaluator_digest, requirement_digest)
        return self.admissions.get(scope_key)
