#!/usr/bin/env python3
# coding: utf-8
"""
test_scoped_admission_import_monotonic.py — import_state cannot roll counters back.

At 7396cd1 import_state() assigned executed_runs_count and admissions_granted_count and
update()d attempts_spent from the snapshot, so an older export passed to a live registry
restored spent retest quota: five executor calls under a quota of 3, an admission on the
fifth, and a recorded executed_runs_count of 3 (reproducer: stargate
examples/semantic-seal/reproducer_3893fad.py, finding D).

Contract (D1): counters already present in the registry never decrease on import; a
snapshot that contradicts itself is refused whole, leaving the registry unchanged. Crash
durability beyond the last persisted state is NOT provided by this in-memory registry
(SA4 as narrowed); that is a separate, future persistence profile.
"""

from __future__ import annotations
import copy
import unittest

from scoped_admission import (
    RefusalReason, RetestOutcome, RefusalRecord, ReevaluationRequest,
    ScopedAdmissionRegistry, sha256_hex,
)

CODE = b"CANDIDATE_THAT_NEEDS_MORE_BUDGET"
CANDIDATE = sha256_hex(CODE)
EVALUATOR = sha256_hex("EVALUATOR_v1")
REQUIREMENT = sha256_hex("REQUIREMENT_v1")
MAX = ScopedAdmissionRegistry.MAX_ATTEMPTS_PER_REFUSAL_FAMILY


def refusal(evidence=b"RESOURCE_LIMIT: steps_exhausted"):
    return RefusalRecord.create(
        candidate_digest=CANDIDATE, evaluator_digest=EVALUATOR, requirement_digest=REQUIREMENT,
        inputs_digest="i" * 64, evidence_bytes=evidence, context={"budget_steps": 100},
        outcome_type=RefusalReason.RESOURCE_LIMIT, steps_executed=100)


def request(ref, budget):
    return ReevaluationRequest.create(
        refusal_id=ref.record_id, candidate_digest=CANDIDATE, evaluator_digest=EVALUATOR,
        requirement_digest=REQUIREMENT, new_context={"budget_steps": budget}, claimed_basis="budget")


class ImportMonotonic(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.ref = refusal()
        self.registry = ScopedAdmissionRegistry()
        self.registry.register_refusal(self.ref)

    def executor(self, outcome):
        def run(code, context):
            self.calls.append(context["budget_steps"])
            return outcome, 10, b"evidence"
        return run

    def spend(self, *budgets, registry=None):
        registry = registry or self.registry
        for budget in budgets:
            registry.execute_retest(request(self.ref, budget), CODE, self.executor(RetestOutcome.FAILURE))

    def counters(self, registry=None):
        registry = registry or self.registry
        return (dict(registry.attempts_spent), registry.executed_runs_count, registry.admissions_granted_count)

    def test_1_an_older_snapshot_cannot_restore_spent_quota(self):
        self.spend(200)
        older = self.registry.export_state()
        self.spend(300, 400)
        self.registry.import_state(older)
        self.assertEqual(self.registry.attempts_spent[self.ref.record_id], MAX)
        with self.assertRaises(PermissionError):
            self.spend(500)
        self.assertEqual(self.calls, [200, 300, 400])

    def test_2_no_counter_decreases(self):
        self.spend(200)
        older = self.registry.export_state()
        self.spend(300)
        before = self.counters()
        self.registry.import_state(older)
        self.assertEqual(self.counters(), before)

    def test_3_a_contradictory_snapshot_is_refused_whole(self):
        self.spend(200)
        good = self.registry.export_state()
        broken = []
        over = copy.deepcopy(good); over["attempts_spent"][self.ref.record_id] = MAX + 1; broken.append(over)
        negative = copy.deepcopy(good); negative["attempts_spent"][self.ref.record_id] = -1; broken.append(negative)
        runs = copy.deepcopy(good); runs["executed_runs_count"] = 0; broken.append(runs)       # < spent attempts
        text = copy.deepcopy(good); text["executed_runs_count"] = "9"; broken.append(text)
        granted = copy.deepcopy(good); granted["admissions_granted_count"] = -1; broken.append(granted)
        fresh = ScopedAdmissionRegistry()
        for snapshot in broken:
            before = (self.counters(fresh), dict(fresh.refusals))
            with self.assertRaises(ValueError):
                fresh.import_state(snapshot)
            self.assertEqual((self.counters(fresh), dict(fresh.refusals)), before)

    def test_4_restart_from_the_latest_export_keeps_everything(self):
        # Green before and after: the supported persistence boundary.
        self.spend(200, 300)
        restarted = ScopedAdmissionRegistry()
        restarted.import_state(self.registry.export_state())
        self.assertEqual(self.counters(restarted), self.counters())

    def test_5_merging_disjoint_histories_keeps_runs_at_least_the_spent_attempts(self):
        other_ref = refusal(b"RESOURCE_LIMIT: another run")
        other = ScopedAdmissionRegistry()
        other.register_refusal(other_ref)
        other.execute_retest(request(other_ref, 200), CODE, self.executor(RetestOutcome.FAILURE))
        other.execute_retest(request(other_ref, 300), CODE, self.executor(RetestOutcome.FAILURE))
        self.spend(200)
        self.registry.import_state(other.export_state())
        self.assertGreaterEqual(self.registry.executed_runs_count, sum(self.registry.attempts_spent.values()))


if __name__ == "__main__":
    unittest.main()
