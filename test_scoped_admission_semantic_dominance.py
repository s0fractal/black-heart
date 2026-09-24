#!/usr/bin/env python3
# coding: utf-8
"""
test_scoped_admission_semantic_dominance.py — a semantic counterexample dominates the
resource path of the same (candidate, evaluator, requirement).

At 3893fad a SEMANTIC_COUNTEREXAMPLE was blocked only on its own record: registering a
RESOURCE_LIMIT refusal for the same triple opened a retest and an admission (SA2). Both
records stay registered (SA1); the semantic fact is stronger when deciding whether the
candidate may be executed again. Reproducer: stargate examples/semantic-seal.

Only an authenticated semantic record (record_id recomputes, evidence non-empty) may block:
unverified evidence is neither a permission nor a prohibition. A semantic-shaped record
that does not authenticate makes the decision APPLICABILITY_UNKNOWN, unless a valid one
of the same triple blocks anyway.
"""

from __future__ import annotations
import dataclasses
import unittest

from scoped_admission import (
    RefusalReason, ReevalEligibility, RetestOutcome, RefusalRecord,
    ReevaluationRequest, ScopedAdmissionRegistry, sha256_hex,
)

CODE = b"CANDIDATE_WITH_A_SEMANTIC_COUNTEREXAMPLE"
CANDIDATE = sha256_hex(CODE)
EVALUATOR = sha256_hex("EVALUATOR_v1")
REQUIREMENT = sha256_hex("REQUIREMENT_v1")


def refusal(kind, *, candidate=CANDIDATE, evaluator=EVALUATOR, requirement=REQUIREMENT,
            inputs="i" * 64, evidence=None, budget=100):
    return RefusalRecord.create(
        candidate_digest=candidate, evaluator_digest=evaluator, requirement_digest=requirement,
        inputs_digest=inputs, evidence_bytes=kind.value.encode("utf-8") if evidence is None else evidence,
        context={"budget_steps": budget}, outcome_type=kind, steps_executed=budget)


def request(ref, budget=200):
    return ReevaluationRequest.create(
        refusal_id=ref.record_id, candidate_digest=ref.candidate_digest,
        evaluator_digest=ref.evaluator_digest, requirement_digest=ref.requirement_digest,
        new_context={"budget_steps": budget}, claimed_basis="budget expansion")


class SemanticDominance(unittest.TestCase):
    def setUp(self):
        self.registry = ScopedAdmissionRegistry()
        self.calls = []

    def executor(self, code, context):
        self.calls.append(context["budget_steps"])
        return RetestOutcome.SUCCESS, 10, b"SUCCESS"

    def both(self, first, second):
        for ref in (first, second):
            self.registry.register_refusal(ref)

    def test_1_semantic_then_resource_blocks_the_resource_request(self):
        semantic = refusal(RefusalReason.SEMANTIC_COUNTEREXAMPLE, budget=100)
        resource = refusal(RefusalReason.RESOURCE_LIMIT, budget=10)
        self.both(semantic, resource)
        self.assertEqual(self.registry.assess_request(request(resource))[0],
                         ReevalEligibility.BLOCKED_BY_EXISTING_EVIDENCE)

    def test_2_registration_order_does_not_matter(self):
        semantic = refusal(RefusalReason.SEMANTIC_COUNTEREXAMPLE, budget=100)
        resource = refusal(RefusalReason.RESOURCE_LIMIT, budget=10)
        self.both(resource, semantic)
        self.assertEqual(self.registry.assess_request(request(resource))[0],
                         ReevalEligibility.BLOCKED_BY_EXISTING_EVIDENCE)

    def test_3_no_executor_call_no_attempt_no_admission_and_both_records_kept(self):
        semantic = refusal(RefusalReason.SEMANTIC_COUNTEREXAMPLE, budget=100)
        resource = refusal(RefusalReason.RESOURCE_LIMIT, budget=10)
        self.both(semantic, resource)
        with self.assertRaises(PermissionError):
            self.registry.execute_retest(request(resource), CODE, self.executor)
        self.assertEqual(self.calls, [])
        self.assertEqual(self.registry.attempts_spent[resource.record_id], 0)
        self.assertEqual(self.registry.executed_runs_count, 0)
        self.assertIsNone(self.registry.admission_for(CANDIDATE, {"budget_steps": 200},
                                                      REQUIREMENT, EVALUATOR))
        self.assertEqual(set(self.registry.refusals), {semantic.record_id, resource.record_id})

    def test_4_other_inputs_digest_still_blocks(self):
        # inputs_digest is the witness's provenance, not the scope of the authority.
        semantic = refusal(RefusalReason.SEMANTIC_COUNTEREXAMPLE, inputs="w" * 64)
        resource = refusal(RefusalReason.RESOURCE_LIMIT, inputs="i" * 64, budget=10)
        self.both(semantic, resource)
        self.assertEqual(self.registry.assess_request(request(resource))[0],
                         ReevalEligibility.BLOCKED_BY_EXISTING_EVIDENCE)

    def test_5_another_triple_does_not_cross_block(self):
        # Green before and after the fix: the guard must not over-block.
        resource = refusal(RefusalReason.RESOURCE_LIMIT, budget=10)
        self.registry.register_refusal(resource)
        for other in (dict(candidate=sha256_hex(b"OTHER")), dict(evaluator=sha256_hex("E2")),
                      dict(requirement=sha256_hex("R2"))):
            self.registry.register_refusal(refusal(RefusalReason.SEMANTIC_COUNTEREXAMPLE, **other))
        self.assertEqual(self.registry.assess_request(request(resource))[0],
                         ReevalEligibility.ELIGIBLE_FOR_RETEST)

    def test_6_imported_history_blocks_too(self):
        semantic = refusal(RefusalReason.SEMANTIC_COUNTEREXAMPLE, budget=100)
        resource = refusal(RefusalReason.RESOURCE_LIMIT, budget=10)
        self.both(semantic, resource)
        restarted = ScopedAdmissionRegistry()
        restarted.import_state(self.registry.export_state())
        self.assertEqual(restarted.assess_request(request(resource))[0],
                         ReevalEligibility.BLOCKED_BY_EXISTING_EVIDENCE)


class SemanticAuthentication(unittest.TestCase):
    """Codex review of #99: the dominance scan must not trust outcome_type alone."""

    def setUp(self):
        self.registry = ScopedAdmissionRegistry()
        self.calls = []
        self.resource = refusal(RefusalReason.RESOURCE_LIMIT, budget=10)
        self.valid = refusal(RefusalReason.SEMANTIC_COUNTEREXAMPLE, budget=100)
        self.forged = dataclasses.replace(self.valid, record_id="f" * 64)
        self.empty = refusal(RefusalReason.SEMANTIC_COUNTEREXAMPLE, evidence=b"", budget=100)

    def executor(self, code, context):
        self.calls.append(context["budget_steps"])
        return RetestOutcome.SUCCESS, 10, b"SUCCESS"

    def eligibility(self, *records, registry=None):
        registry = registry or self.registry
        for ref in records:
            registry.register_refusal(ref)
        return registry.assess_request(request(self.resource))[0]

    def test_7_a_forged_semantic_id_does_not_block_it_is_unknown(self):
        self.assertEqual(self.eligibility(self.forged, self.resource), ReevalEligibility.APPLICABILITY_UNKNOWN)

    def test_8_empty_semantic_evidence_does_not_block_it_is_unknown(self):
        self.assertEqual(self.empty.record_id, self.empty.compute_record_id())
        self.assertEqual(self.eligibility(self.empty, self.resource), ReevalEligibility.APPLICABILITY_UNKNOWN)

    def test_9_order_does_not_matter_for_an_unauthenticated_record(self):
        self.assertEqual(self.eligibility(self.resource, self.forged), ReevalEligibility.APPLICABILITY_UNKNOWN)

    def test_10_a_valid_semantic_wins_over_an_invalid_one_in_either_order(self):
        # Green before and after: a valid seal blocks whatever else is registered.
        for records in ((self.forged, self.valid, self.resource), (self.resource, self.valid, self.forged)):
            self.assertEqual(self.eligibility(*records, registry=ScopedAdmissionRegistry()),
                             ReevalEligibility.BLOCKED_BY_EXISTING_EVIDENCE)

    def test_11_an_imported_forged_semantic_does_not_block(self):
        self.eligibility(self.resource)
        state = self.registry.export_state()
        forged = self.valid.to_dict()
        forged["record_id"] = "f" * 64
        state["refusals"]["f" * 64] = forged
        restarted = ScopedAdmissionRegistry()
        restarted.import_state(state)
        self.assertEqual(restarted.assess_request(request(self.resource))[0],
                         ReevalEligibility.APPLICABILITY_UNKNOWN)

    def test_12_unknown_runs_nothing_spends_nothing_admits_nothing(self):
        # Green before and after: blocked or unknown, neither may run the executor.
        self.eligibility(self.forged, self.resource)
        with self.assertRaises(PermissionError):
            self.registry.execute_retest(request(self.resource), CODE, self.executor)
        self.assertEqual((self.calls, self.registry.attempts_spent[self.resource.record_id]), ([], 0))
        self.assertIsNone(self.registry.admission_for(CANDIDATE, {"budget_steps": 200}, REQUIREMENT, EVALUATOR))


if __name__ == "__main__":
    unittest.main()
