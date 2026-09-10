#!/usr/bin/env python3
# coding: utf-8
"""
examples/scoped_admission_demo.py — Live Scoped Re-Admission Polyglot Demonstration.
Part of Project Black-Heart (%🖤).
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scoped_admission import (
    ScopedAdmissionRegistry, RefusalRecord, ReevaluationRequest,
    RefusalReason, RetestOutcome, generate_scoped_admission_pdf, sha256_hex
)



def run_demo():
    print("\033[1;36m" + "=" * 65)
    print("  %🖤 BLACK-HEART: SCOPED RE-ADMISSION (SCOPED_ADMISSION-0.1)")
    print("=" * 65 + "\033[0m\n")

    registry = ScopedAdmissionRegistry()
    candidate_code = b"S K K (K Truth Mirage) S K K"
    candidate_digest = sha256_hex(candidate_code)
    evaluator_digest = sha256_hex("HERMETIC_COMBINATOR_EVALUATOR_v1")
    requirement_digest = sha256_hex("TERMINATION_WITHIN_STEP_BUDGET")

    # 1. Historical Failure: Candidate terminated due to RESOURCE_LIMIT at 100 steps
    refusal = RefusalRecord.create(
        candidate_digest=candidate_digest,
        evaluator_digest=evaluator_digest,
        requirement_digest=requirement_digest,
        inputs_digest=sha256_hex("standard_truth_probe"),
        evidence_bytes=b"GAS_EXHAUSTED_STEP_100_STACK_DEPTH_14",
        context={"budget_steps": 100, "domain": "pure_ski"},
        outcome_type=RefusalReason.RESOURCE_LIMIT,
        steps_executed=100
    )
    registry.register_refusal(refusal)
    print(f"[+] Historical Refusal Registered:")
    print(f"    Record ID:     {refusal.record_id[:24]}...")
    print(f"    Outcome:       {refusal.outcome_type.value}")
    print(f"    Prior Context: {refusal.context}\n")

    # 2. Targeted Re-evaluation Request under Expanded Context (budget_steps: 200)
    req = ReevaluationRequest.create(
        refusal_id=refusal.record_id,
        candidate_digest=candidate_digest,
        evaluator_digest=evaluator_digest,
        requirement_digest=requirement_digest,
        new_context={"budget_steps": 200, "domain": "pure_ski"},
        claimed_basis="Increased budget steps from 100 to 200 after metabolic gas harvest",
        researcher_hypothesis="Term settles at 142 steps when unconstrained"
    )
    print(f"[+] Reevaluation Request Created:")
    print(f"    Request ID:    {req.request_id[:24]}...")
    print(f"    New Context:   {req.new_context}\n")

    # 3. Controlled Bounded Retest Execution
    def mock_evaluator(code_bytes, ctx):
        budget = ctx.get("budget_steps", 0)
        needed = 142
        if budget >= needed:
            return RetestOutcome.SUCCESS, needed, b"SETTLED_AT_142_STEPS_RESULT_Truth"
        return RetestOutcome.FAILURE, budget, b"GAS_EXHAUSTED"


    retest = registry.execute_retest(req, candidate_code, mock_evaluator)
    print(f"[+] Bounded Retest Executed:")
    print(f"    Retest ID:     {retest.retest_id[:24]}...")
    print(f"    Outcome:       {retest.outcome.value}")
    print(f"    Steps Spent:   {retest.steps_spent} steps (quota: 1 attempt burned)\n")

    # 4. Grant Scoped Admission
    admission = registry.grant_scoped_admission(retest, policy_id="METABOLIC_HARVEST_ADMISSION_v1")
    print(f"[+] Scoped Admission Granted:")
    print(f"    Admission ID:  {admission.admission_id[:24]}...")
    print(f"    Context Hash:  {admission.context_digest[:24]}...")
    print(f"    Non-Leakage:   Valid ONLY for context B. Context A remains BLOCKED.\n")

    # 5. Compile ISO 32000 Polyglot PDF Certificate
    out_pdf = "examples/scoped_admission.pdf"
    os.makedirs("examples", exist_ok=True)
    generate_scoped_admission_pdf(admission, refusal, retest, out_pdf)
    print(f"[✓] Polyglot Certificate compiled to: {out_pdf}")

if __name__ == "__main__":
    run_demo()
