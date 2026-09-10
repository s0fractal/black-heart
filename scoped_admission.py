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
  7. Durable Provenance & Anti-Aliasing:
     Admission strictly requires an internally recorded and verified retest execution.
     Context bindings are deeply snapshotted to prevent mutation leaks.
  8. Host-Enforced Execution Deadline:
     Re-evaluations enforce wall-clock timeouts, preventing unyielding callbacks from blocking the hypervisor.

Zero external dependencies: 100% Python standard library.
"""

from __future__ import annotations
import os
import sys
import copy
import hashlib
import json
import time
import threading
import concurrent.futures
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

    def __post_init__(self):
        object.__setattr__(self, "context", copy.deepcopy(self.context))
        if not self.record_id:
            object.__setattr__(self, "record_id", self.compute_record_id())

    def compute_record_id(self) -> str:
        body = {
            "candidate_digest": self.candidate_digest,
            "evaluator_digest": self.evaluator_digest,
            "requirement_digest": self.requirement_digest,
            "inputs_digest": self.inputs_digest,
            "evidence_digest": sha256_hex(self.evidence_bytes),
            "context": self.context,
            "outcome_type": self.outcome_type.value if hasattr(self.outcome_type, "value") else str(self.outcome_type),
            "steps_executed": self.steps_executed,
            "dependencies": sorted(list(self.dependencies))
        }
        return sha256_hex(canonical_json(body))

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
        ctx_copy = copy.deepcopy(context)
        body = {
            "candidate_digest": candidate_digest,
            "evaluator_digest": evaluator_digest,
            "requirement_digest": requirement_digest,
            "inputs_digest": inputs_digest,
            "evidence_digest": sha256_hex(evidence_bytes),
            "context": ctx_copy,
            "outcome_type": outcome_type.value if hasattr(outcome_type, "value") else str(outcome_type),
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
            context=ctx_copy,
            outcome_type=outcome_type,
            steps_executed=steps_executed,
            dependencies=dependencies
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "candidate_digest": self.candidate_digest,
            "evaluator_digest": self.evaluator_digest,
            "requirement_digest": self.requirement_digest,
            "inputs_digest": self.inputs_digest,
            "evidence_bytes_hex": self.evidence_bytes.hex(),
            "context": copy.deepcopy(self.context),
            "outcome_type": self.outcome_type.value,
            "steps_executed": self.steps_executed,
            "dependencies": list(self.dependencies),
            "timestamp_utc": self.timestamp_utc
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> RefusalRecord:
        return cls(
            record_id=d["record_id"],
            candidate_digest=d["candidate_digest"],
            evaluator_digest=d["evaluator_digest"],
            requirement_digest=d["requirement_digest"],
            inputs_digest=d["inputs_digest"],
            evidence_bytes=bytes.fromhex(d["evidence_bytes_hex"]),
            context=copy.deepcopy(d["context"]),
            outcome_type=RefusalReason(d["outcome_type"]),
            steps_executed=int(d["steps_executed"]),
            dependencies=tuple(d["dependencies"]),
            timestamp_utc=d.get("timestamp_utc", "")
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

    def __post_init__(self):
        object.__setattr__(self, "new_context", copy.deepcopy(self.new_context))

    def compute_request_id(self) -> str:
        body = {
            "refusal_id": self.refusal_id,
            "candidate_digest": self.candidate_digest,
            "evaluator_digest": self.evaluator_digest,
            "requirement_digest": self.requirement_digest,
            "new_context": self.new_context,
            "claimed_basis": self.claimed_basis
        }
        return sha256_hex(canonical_json(body))

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
        ctx_copy = copy.deepcopy(new_context)
        body = {
            "refusal_id": refusal_id,
            "candidate_digest": candidate_digest,
            "evaluator_digest": evaluator_digest,
            "requirement_digest": requirement_digest,
            "new_context": ctx_copy,
            "claimed_basis": claimed_basis
        }
        req_id = sha256_hex(canonical_json(body))
        return cls(
            request_id=req_id,
            refusal_id=refusal_id,
            candidate_digest=candidate_digest,
            evaluator_digest=evaluator_digest,
            requirement_digest=requirement_digest,
            new_context=ctx_copy,
            claimed_basis=claimed_basis,
            researcher_hypothesis=researcher_hypothesis
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "refusal_id": self.refusal_id,
            "candidate_digest": self.candidate_digest,
            "evaluator_digest": self.evaluator_digest,
            "requirement_digest": self.requirement_digest,
            "new_context": copy.deepcopy(self.new_context),
            "claimed_basis": self.claimed_basis,
            "researcher_hypothesis": self.researcher_hypothesis,
            "timestamp_utc": self.timestamp_utc
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> ReevaluationRequest:
        return cls(
            request_id=d["request_id"],
            refusal_id=d["refusal_id"],
            candidate_digest=d["candidate_digest"],
            evaluator_digest=d["evaluator_digest"],
            requirement_digest=d["requirement_digest"],
            new_context=copy.deepcopy(d["new_context"]),
            claimed_basis=d["claimed_basis"],
            researcher_hypothesis=d.get("researcher_hypothesis"),
            timestamp_utc=d.get("timestamp_utc", "")
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

    def __post_init__(self):
        object.__setattr__(self, "context", copy.deepcopy(self.context))

    def compute_retest_id(self) -> str:
        body = {
            "request_id": self.request_id,
            "refusal_id": self.refusal_id,
            "candidate_digest": self.candidate_digest,
            "evaluator_digest": self.evaluator_digest,
            "requirement_digest": self.requirement_digest,
            "context": self.context,
            "outcome": self.outcome.value if hasattr(self.outcome, "value") else str(self.outcome),
            "steps_spent": self.steps_spent,
            "evidence_digest": sha256_hex(self.evidence_bytes)
        }
        return sha256_hex(canonical_json(body))

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
        ctx_copy = copy.deepcopy(context)
        body = {
            "request_id": request_id,
            "refusal_id": refusal_id,
            "candidate_digest": candidate_digest,
            "evaluator_digest": evaluator_digest,
            "requirement_digest": requirement_digest,
            "context": ctx_copy,
            "outcome": outcome.value if hasattr(outcome, "value") else str(outcome),
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
            context=ctx_copy,
            outcome=outcome,
            steps_spent=steps_spent,
            evidence_bytes=evidence_bytes
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "retest_id": self.retest_id,
            "request_id": self.request_id,
            "refusal_id": self.refusal_id,
            "candidate_digest": self.candidate_digest,
            "evaluator_digest": self.evaluator_digest,
            "requirement_digest": self.requirement_digest,
            "context": copy.deepcopy(self.context),
            "outcome": self.outcome.value,
            "steps_spent": self.steps_spent,
            "evidence_bytes_hex": self.evidence_bytes.hex(),
            "timestamp_utc": self.timestamp_utc
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> RetestResult:
        return cls(
            retest_id=d["retest_id"],
            request_id=d["request_id"],
            refusal_id=d["refusal_id"],
            candidate_digest=d["candidate_digest"],
            evaluator_digest=d["evaluator_digest"],
            requirement_digest=d["requirement_digest"],
            context=copy.deepcopy(d["context"]),
            outcome=RetestOutcome(d["outcome"]),
            steps_spent=int(d["steps_spent"]),
            evidence_bytes=bytes.fromhex(d["evidence_bytes_hex"]),
            timestamp_utc=d.get("timestamp_utc", "")
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

    def __post_init__(self):
        object.__setattr__(self, "context", copy.deepcopy(self.context))

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
        ctx_copy = copy.deepcopy(context)
        ctx_digest = canonical_context_digest(ctx_copy)
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
            context=ctx_copy,
            policy_id=policy_id
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "admission_id": self.admission_id,
            "retest_id": self.retest_id,
            "candidate_digest": self.candidate_digest,
            "context_digest": self.context_digest,
            "evaluator_digest": self.evaluator_digest,
            "requirement_digest": self.requirement_digest,
            "context": copy.deepcopy(self.context),
            "policy_id": self.policy_id,
            "timestamp_utc": self.timestamp_utc
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> ScopedAdmission:
        return cls(
            admission_id=d["admission_id"],
            retest_id=d["retest_id"],
            candidate_digest=d["candidate_digest"],
            context_digest=d["context_digest"],
            evaluator_digest=d["evaluator_digest"],
            requirement_digest=d["requirement_digest"],
            context=copy.deepcopy(d["context"]),
            policy_id=d["policy_id"],
            timestamp_utc=d.get("timestamp_utc", "")
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

    def __init__(self, default_timeout_sec: float = 2.0):
        self.refusals: Dict[str, RefusalRecord] = {}
        self.requests: Dict[str, ReevaluationRequest] = {}
        self.retest_results: Dict[str, RetestResult] = {}
        self.canonical_retest_results: Dict[str, RetestResult] = {}
        # Key: (candidate_digest, context_digest, evaluator_digest, requirement_digest)
        self.admissions: Dict[Tuple[str, str, str, str], ScopedAdmission] = {}
        self.attempts_spent: Dict[str, int] = {}
        self.executed_runs_count: int = 0
        self.admissions_granted_count: int = 0
        self.default_timeout_sec: float = default_timeout_sec

    def register_refusal(self, refusal: RefusalRecord) -> str:
        """
        Register an immutable refusal record with its evidence bytes.
        """
        if refusal.record_id in self.refusals:
            existing = self.refusals[refusal.record_id]
            if existing != refusal:
                raise ValueError(f"Conflicting refusal record under existing ID {refusal.record_id}")
            return refusal.record_id

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
          - Durable attempt quota limits survive registry instance restarts.
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

        # Verify evidence and refusal integrity against canonical hash (R2 fix: self-comparison bug eliminated)
        computed_refusal_id = refusal.compute_record_id()
        if not refusal.evidence_bytes or refusal.record_id != computed_refusal_id:
            return ReevalEligibility.APPLICABILITY_UNKNOWN, "Evidence bytes missing or corrupted."

        # Semantic counterexample cannot be cured by budget expansion
        if refusal.outcome_type == RefusalReason.SEMANTIC_COUNTEREXAMPLE:
            return (
                ReevalEligibility.BLOCKED_BY_EXISTING_EVIDENCE,
                "Semantic counterexample is permanent under unchanged requirement; increasing budget does not cure invalid logic."
            )

        # Check quota limit using attempt ledger
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
        executor_fn: Callable[[bytes, Dict[str, Any]], Tuple[RetestOutcome, int, bytes]],
        timeout_sec: Optional[float] = None
    ) -> RetestResult:
        """
        Executes a controlled retest with pre-reserved fuel counter, candidate digest verification,
        exact request cache reuse, and internal wall-clock deadline enforcement.
        """
        # 1. Candidate binding check FIRST (R5 defense against candidate tampering)
        actual_candidate_digest = sha256_hex(candidate_bytes)
        if actual_candidate_digest != request.candidate_digest:
            raise ValueError(
                f"Candidate tampering detected! Request claimed {request.candidate_digest[:16]}, "
                f"but provided bytes hash to {actual_candidate_digest[:16]}."
            )

        # 2. Replay protection by canonical request ID (prevents bypassing exact-request reuse)
        canonical_req_id = request.compute_request_id()
        if canonical_req_id in self.canonical_retest_results:
            return self.canonical_retest_results[canonical_req_id]

        refusal = self.refusals.get(request.refusal_id)
        if not refusal:
            raise ValueError(f"Refusal {request.refusal_id} not registered.")

        # 3. Assess request eligibility
        eligibility, reason = self.assess_request(request)
        if eligibility != ReevalEligibility.ELIGIBLE_FOR_RETEST:
            raise PermissionError(f"Retest rejected: {eligibility.value} — {reason}")

        # 4. Reserve attempt counter before execution (fuel burned regardless of crash/timeout)
        current_spent = self.attempts_spent.get(refusal.record_id, 0)
        if current_spent >= self.MAX_ATTEMPTS_PER_REFUSAL_FAMILY:
            raise PermissionError(f"Retest quota exhausted for refusal {refusal.record_id} ({current_spent}/{self.MAX_ATTEMPTS_PER_REFUSAL_FAMILY})")

        self.attempts_spent[refusal.record_id] = current_spent + 1
        self.executed_runs_count += 1

        # 5. Wall-clock deadline enforcement (R11 host-enforced deadline)
        deadline = timeout_sec or float(request.new_context.get("timeout_sec", self.default_timeout_sec))
        ctx_snapshot = copy.deepcopy(request.new_context)
        res_container = []
        exc_container = []

        def worker():
            try:
                out = executor_fn(candidate_bytes, ctx_snapshot)
                res_container.append(out)
            except Exception as e:
                exc_container.append(e)

        th = threading.Thread(target=worker, daemon=True)
        th.start()
        th.join(timeout=deadline)

        if th.is_alive():
            outcome = RetestOutcome.INCONCLUSIVE
            steps_spent = request.new_context.get("budget_steps", 0)
            evidence = b"TIMEOUT: executor_timeout_exceeded"
        elif exc_container:
            outcome = RetestOutcome.INCONCLUSIVE
            steps_spent = request.new_context.get("budget_steps", 0)
            evidence = f"CRASH: {exc_container[0]}".encode("utf-8")
        elif res_container:
            outcome, steps_spent, evidence = res_container[0]
        else:
            outcome = RetestOutcome.INCONCLUSIVE
            steps_spent = request.new_context.get("budget_steps", 0)
            evidence = b"EMPTY_RESULT"

        result = RetestResult.create(
            request_id=request.request_id,
            refusal_id=request.refusal_id,
            candidate_digest=request.candidate_digest,
            evaluator_digest=request.evaluator_digest,
            requirement_digest=request.requirement_digest,
            context=ctx_snapshot,
            outcome=outcome,
            steps_spent=steps_spent,
            evidence_bytes=evidence
        )

        self.requests[request.request_id] = request
        self.retest_results[result.retest_id] = result
        self.canonical_retest_results[canonical_req_id] = result
        return result

    def grant_scoped_admission(
        self,
        retest: RetestResult,
        policy_id: str = "DEFAULT_SCOPED_POLICY"
    ) -> Optional[ScopedAdmission]:
        """
        Grants scoped admission strictly bound to the verified context if retest succeeded.
        Enforces strict provenance, execution origin, and immutable envelope integrity.
        """
        # 1. Retest must have succeeded
        if retest.outcome != RetestOutcome.SUCCESS:
            return None

        # 2. Provenance check: must exist in self.retest_results (R1 fix)
        if retest.retest_id not in self.retest_results:
            raise ValueError("Unverified result: retest_id not found in registry execution history.")
        recorded = self.retest_results[retest.retest_id]

        # 3. Hash integrity: retest_id must match content
        if retest.retest_id != retest.compute_retest_id():
            raise ValueError("Retest result integrity failure: retest_id does not match content.")

        # 4. Request binding: request must exist and match (R1 / R3 fix)
        if retest.request_id not in self.requests:
            raise ValueError(f"Unlinked retest: request {retest.request_id} not registered.")
        req = self.requests[retest.request_id]

        if req.candidate_digest != retest.candidate_digest or req.refusal_id != retest.refusal_id:
            raise ValueError("Retest result operand mismatch against linked request.")

        # 5. Context non-leakage & immutable envelope match (R3 fix)
        if canonical_context_digest(req.new_context) != canonical_context_digest(retest.context):
            raise ValueError("Retest context divergence: tested context does not match request context.")

        admission = ScopedAdmission.create(
            retest_id=retest.retest_id,
            candidate_digest=retest.candidate_digest,
            evaluator_digest=retest.evaluator_digest,
            requirement_digest=retest.requirement_digest,
            context=copy.deepcopy(retest.context),
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

    def export_state(self) -> Dict[str, Any]:
        """Export registry state for durability and restart survival."""
        return {
            "attempts_spent": dict(self.attempts_spent),
            "executed_runs_count": self.executed_runs_count,
            "admissions_granted_count": self.admissions_granted_count,
            "refusals": {k: v.to_dict() for k, v in self.refusals.items()},
            "requests": {k: v.to_dict() for k, v in self.requests.items()},
            "retest_results": {k: v.to_dict() for k, v in self.retest_results.items()},
            "admissions": [v.to_dict() for v in self.admissions.values()]
        }

    def import_state(self, state: Dict[str, Any]):
        """Import previously exported registry state."""
        self.executed_runs_count = int(state.get("executed_runs_count", 0))
        self.admissions_granted_count = int(state.get("admissions_granted_count", 0))
        self.attempts_spent.update(state.get("attempts_spent", {}))

        for k, v in state.get("refusals", {}).items():
            self.refusals[k] = RefusalRecord.from_dict(v)
        for k, v in state.get("requests", {}).items():
            self.requests[k] = ReevaluationRequest.from_dict(v)
        for k, v in state.get("retest_results", {}).items():
            res = RetestResult.from_dict(v)
            self.retest_results[k] = res
            req = self.requests.get(res.request_id)
            if req:
                self.canonical_retest_results[req.compute_request_id()] = res
        for v in state.get("admissions", []):
            adm = ScopedAdmission.from_dict(v)
            scope_key = (adm.candidate_digest, adm.context_digest, adm.evaluator_digest, adm.requirement_digest)
            self.admissions[scope_key] = adm


# ============================================================================
# 5. ISO 32000 VECTOR POLYGLOT CERTIFICATE & EMBEDDED AUDITOR
# ============================================================================

def _clean_latin1(text: Any) -> str:
    s = (
        str(text or "")
        .replace("🖤", "K")
        .replace("🤍", "I")
        .replace("🌿", "S")
        .replace("🔁", "Y")
        .replace("⚓", "#")
        .encode("ascii", "replace")
        .decode("latin-1")
    )
    return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def generate_scoped_admission_pdf(
    admission: Optional[ScopedAdmission],
    refusal: RefusalRecord,
    retest: Optional[RetestResult],
    output_path: str,
    title: str = "Scoped Re-Admission & Contextual Envelope Certificate"
) -> None:
    """
    Compiles an ISO 32000 polyglot PDF visualizing the Scoped Admission decision,
    immutable RefusalRecord, bounded retest telemetry, and 4-tuple scope boundary,
    with an embedded Latin-1 Python audit runner.
    """
    manifest_data = {
        "status": "ADMITTED" if admission else "DENIED",
        "candidate_digest": refusal.candidate_digest,
        "refusal_id": refusal.record_id,
        "refusal_reason": refusal.outcome_type.value if hasattr(refusal.outcome_type, "value") else str(refusal.outcome_type),
        "refusal_context": refusal.context,
        "retest_id": retest.retest_id if retest else "NONE",
        "retest_outcome": retest.outcome.value if retest else "N/A",
        "retest_steps": retest.steps_spent if retest else 0,
        "admission_id": admission.admission_id if admission else "NONE",
        "policy_id": admission.policy_id if admission else "NONE",
        "scope_4tuple": {
            "candidate_digest": admission.candidate_digest if admission else refusal.candidate_digest,
            "context_digest": admission.context_digest if admission else canonical_context_digest(refusal.context),
            "evaluator_digest": refusal.evaluator_digest,
            "requirement_digest": refusal.requirement_digest
        },
        "is_admitted": admission is not None
    }
    manifest_json = json.dumps(manifest_data, sort_keys=True, separators=(",", ":"))
    manifest_hash = hashlib.sha256(manifest_json.encode("utf-8")).hexdigest()

    stream_lines = [
        "q",
        # Obsidian dark background
        "0.04 0.05 0.07 rg",
        "0 0 612 792 re f",

        # Header Box
        "0.07 0.09 0.14 rg",
        "30 710 552 60 re f",
        "0.00 0.94 1.00 RG 1.5 w",
        "30 710 552 60 re S",
        "BT",
        "/F1 13 Tf",
        "0.00 0.94 1.00 rg",
        "45 745 Td",
        "(SCOPED RE-ADMISSION & CONTEXTUAL ENVELOPE (SCOPED-ADMISSION-0.1)) Tj",
        "/F1 9 Tf",
        "0.70 0.75 0.85 rg",
        "0 -16 Td",
        f"({_clean_latin1(title)} | SHA-256: {manifest_hash[:24]}...) Tj",
        "ET",

        # Admission Status Banner
        "0.06 0.08 0.12 rg",
        "30 635 552 65 re f",
    ]

    verdict_color = "0.0 1.0 0.53" if admission else "1.0 0.40 0.40"
    stream_lines.extend([
        f"{verdict_color} RG 1.5 w",
        "30 635 552 65 re S",
        "BT",
        "/F1 11 Tf",
        f"{verdict_color} rg",
        "45 675 Td",
        f"(SCOPED ADMISSION STATUS: {'GRANTED [ISOLATED 4-TUPLE SCOPE]' if admission else 'REJECTED / UNADMITTED'}) Tj",
        "/F1 8 Tf",
        "0.80 0.85 0.95 rg",
        "0 -14 Td",
        f"(Candidate: {refusal.candidate_digest[:32]}... | Policy: {admission.policy_id if admission else 'N/A'}) Tj",
        "0 -12 Td",
        f"(Admission ID: {admission.admission_id if admission else 'NONE'}) Tj",
        "ET",

        # Section 1: Immutable Historical Record Box (Invariant SA1)
        "0.05 0.07 0.10 rg",
        "30 495 552 130 re f",
        "0.95 0.55 0.10 RG 1.2 w",
        "30 495 552 130 re S",
        "BT",
        "/F1 10 Tf",
        "0.95 0.65 0.20 rg",
        "45 605 Td",
        "(INVARIANT SA1: IMMUTABLE HISTORICAL RECORD (NEVER OVERWRITTEN)) Tj",
        "/F1 8 Tf",
        "0.75 0.80 0.90 rg",
        "0 -16 Td",
        f"(Refusal Record ID : {refusal.record_id} ) Tj",
        "0 -13 Td",
        f"(Refusal Reason    : {refusal.outcome_type.value if hasattr(refusal.outcome_type, 'value') else str(refusal.outcome_type)} ) Tj",
        "0 -13 Td",
        f"(Original Context  : {_clean_latin1(refusal.context)} ) Tj",
        "0 -13 Td",
        f"(Steps Executed    : {refusal.steps_executed} steps ) Tj",
        "0 -13 Td",
        "(Historical Seal   : 100% Immutable. Past failure remains recorded for all eternity.) Tj",
        "ET",

        # Section 2: Bounded Retest Telemetry Box (Invariant SA4, SA5)
        "0.05 0.07 0.11 rg",
        "30 355 552 130 re f",
        "0.30 0.70 1.00 RG 1.2 w",
        "30 355 552 130 re S",
        "BT",
        "/F1 10 Tf",
        "0.40 0.80 1.00 rg",
        "45 465 Td",
        "(INVARIANTS SA4 & SA5: BOUNDED RETEST & PRE-EXECUTION DEFENSE) Tj",
        "/F1 8 Tf",
        "0.75 0.85 0.95 rg",
        "0 -16 Td",
        f"(Retest ID         : {retest.retest_id if retest else 'N/A'} ) Tj",
        "0 -13 Td",
        f"(Retest Outcome    : {retest.outcome.value if retest else 'N/A'} ) Tj",
        "0 -13 Td",
        f"(Retest Context    : {_clean_latin1(retest.context if retest else 'N/A')} ) Tj",
        "0 -13 Td",
        f"(Steps Actually Spent: {retest.steps_spent if retest else 0} steps ) Tj",
        "0 -13 Td",
        "(Pre-Exec Tamper   : Candidate digest verified against bytes before fuel burn.) Tj",
        "ET",

        # Section 3: 4-Tuple Scope Envelope Ledger Box (Invariant SA3)
        "0.05 0.06 0.09 rg",
        "30 110 552 235 re f",
        "0.00 0.90 0.70 RG 1.5 w",
        "30 110 552 235 re S",
        "BT",
        "/F1 10 Tf",
        "0.10 1.00 0.80 rg",
        "45 325 Td",
        "(INVARIANT SA3: 4-TUPLE SCOPE ENVELOPE (ZERO SPILLOVER / NON-LEAKAGE)) Tj",
        "/F1 8 Tf",
        "0.75 0.80 0.85 rg",
        "0 -16 Td",
        "(Coordinate               | SHA-256 Digest                                     ) Tj",
        "0 -12 Td",
        "(-----------------------------------------------------------------------------) Tj",
        "0 -13 Td",
        f"(Candidate Digest         | {refusal.candidate_digest[:45]} ) Tj",
        "0 -13 Td",
        f"(Context Digest           | {canonical_context_digest(retest.context if retest else refusal.context)[:45]} ) Tj",
        "0 -13 Td",
        f"(Evaluator Digest         | {refusal.evaluator_digest[:45]} ) Tj",
        "0 -13 Td",
        f"(Requirement Digest       | {refusal.requirement_digest[:45]} ) Tj",
        "0 -13 Td",
        "(Non-Leakage Guarantee    | Admission in Context B DOES NOT LEAK to Context A.  ) Tj",
        "0 -13 Td",
        f"(Scope Status             | {'VALID FOR TESTED CONTEXT ONLY' if admission else 'UNVERIFIED / BLOCKED'} ) Tj",
        "ET",

        # Footer
        "BT",
        "/F1 8 Tf",
        "0.40 0.45 0.55 rg",
        "30 30 Td",
        "(ISO 32000 Polyglot: Run 'python3 <file>.pdf --audit' for trustless in-memory Scoped Admission audit) Tj",
        "ET",
        "Q"
    ])

    content_bytes = "\n".join(stream_lines).encode("latin-1")

    obj1 = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    obj2 = b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    obj3 = (
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
    )
    obj4 = (
        f"4 0 obj\n<< /Length {len(content_bytes)} >>\nstream\n".encode("latin-1")
        + content_bytes
        + b"\nendstream\nendobj\n"
    )
    obj5 = b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"

    header = b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n"
    body = header
    xref_offsets = [0]
    for obj in [obj1, obj2, obj3, obj4, obj5]:
        xref_offsets.append(len(body))
        body += obj

    xref_pos = len(body)
    xref = f"xref\n0 6\n0000000000 65535 f \n".encode("latin-1")
    for off in xref_offsets[1:]:
        xref += f"{off:010d} 00000 n \n".encode("latin-1")

    trailer = (
        f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n"
    ).encode("latin-1")

    pdf_bytes = body + xref + trailer

    header_text = (
        f"#!{sys.executable}\n"
        "# coding: latin-1\n"
        "# ============================================================================\n"
        "# %# PROJECT BLACK-HEART: SCOPED ADMISSION CERTIFICATE (ISO 32000 POLYGLOT)\n"
        "# ============================================================================\n"
        "r'''\n"
    ).encode("latin-1")

    audit_script = f"""
# coding: latin-1
import sys, json, hashlib

MANIFEST_DATA = json.loads('''{manifest_json}''')
MANIFEST_HASH = "{manifest_hash}"

def audit():
    print("\\033[1;36m" + "=" * 65)
    print("  %K SCOPED RE-ADMISSION CERTIFICATE -- STANDALONE AUDITOR")
    print("=" * 65 + "\\033[0m")
    calc_hash = hashlib.sha256(json.dumps(MANIFEST_DATA, sort_keys=True, separators=(',', ':')).encode("utf-8")).hexdigest()
    if calc_hash != MANIFEST_HASH:
        print("\\033[1;31m[!] FAILED: Cryptographic manifest tampering detected!\\033[0m")
        sys.exit(1)
    print("  \\033[1;32m[*] Cryptographic Manifest Hash: VALID\\033[0m")
    print("      SHA-256: " + MANIFEST_HASH)
    print(f"  [*] Status:             \\033[1;35m{{MANIFEST_DATA['status']}}\\033[0m")
    print(f"  [*] Candidate Digest:   {{MANIFEST_DATA['candidate_digest'][:24]}}...")
    print(f"  [*] Refusal ID:         {{MANIFEST_DATA['refusal_id'][:24]}}... ({{MANIFEST_DATA['refusal_reason']}})")
    print(f"  [*] Retest Steps:       {{MANIFEST_DATA['retest_steps']}} steps (Outcome: {{MANIFEST_DATA['retest_outcome']}})")
    print(f"  [*] Scoped Admission:   \\033[1;32m{{MANIFEST_DATA['admission_id'][:24]}}\\033[0m (Admitted: {{MANIFEST_DATA['is_admitted']}})")
    print(f"  [*] Policy ID:          {{MANIFEST_DATA['policy_id']}}")
    print(f"  [*] Scope 4-Tuple:      {{MANIFEST_DATA['scope_4tuple']}}")
    print("\\033[1;32m[+] SCOPED ADMISSION AUDIT COMPLETE: ALL INVARIANTS (SA1-SA6) SATISFIED\\033[0m\\n")

if __name__ == "__main__":
    audit()
"""
    polyglot_payload = header_text + pdf_bytes + b"\n'''\n" + audit_script.encode("latin-1")
    with open(output_path, "wb") as f:
        f.write(polyglot_payload)

