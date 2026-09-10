#!/usr/bin/env python3
"""
Regression: quarantine means the candidate PROVES a retired statement.

`smt_refute_tombstone` asserted the candidate's formula together with
`(= (comb_<target>) (comb_poison))` and quarantined on SAT. Three things were
wrong with that at once:

  * SAT is consistency, not derivation. A theory being consistent with a claim
    says nothing about whether it makes the claim; almost every theory is
    consistent with almost every fresh equality.
  * both symbols were minted by the checker from the tombstone's id, so the
    equality was about names neither the candidate nor the retirement record
    ever mentioned.
  * the id was truncated to sixteen characters with non-alphanumerics mapped to
    `_`, so distinct subjects could collide onto one symbol.

Measured on the base commit, with one retirement registered:

    tautology q=q          -> QUARANTINED_EPISTEMIC_VIOLATION
    unrelated candidate    -> QUARANTINED_EPISTEMIC_VIOLATION
    empty candidate        -> QUARANTINED_EPISTEMIC_VIOLATION
    empty registry         -> CERTIFIED_SOUND_ORGANISM (smt_status=UNSAT)

Saying nothing was a violation, and checking nothing was a certification.

What the sections pin:

  A  the four controls: a tautology, an unrelated candidate, a candidate that
     genuinely entails the retired statement, and a solver that cannot decide.
  B  a tombstone with no supplied statement is unchecked, never passed, and no
     verdict means the organism is sound.
  C  the statement comes from the caller, because a retirement record carries a
     subject and a loss declaration but no formula.

The predicate, in full: for a retired statement P, the candidate entails P
exactly when `candidate ∧ ¬P` is unsatisfiable. Nothing here says the CNF is a
faithful rendering of what was retired; that stays the caller's assertion, as
in S3a and S3b.
"""
from __future__ import annotations

import os
import sys
import unittest

# Same import guard, and same reason, as test_retirement_binding.py.
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path[:1]:
    sys.path.insert(0, _HERE)
for _name, _mod in list(sys.modules.items()):
    _file = getattr(_mod, "__file__", None)
    if not _file:
        continue
    if os.path.dirname(os.path.abspath(_file)) != _HERE and \
            os.path.exists(os.path.join(_HERE, os.path.basename(_file))):
        del sys.modules[_name]

import crypto
import smt_kernel as sm
from smt_kernel import (
    smt_refute_tombstone, QuarantineVerdict, TombstoneCheckStatus, SMTStatus, SMTResult,
)
from controlled_forgetting import EpistemicTombstoneRegistry, RetirementMode

if os.path.dirname(os.path.abspath(sm.__file__)) != _HERE:
    raise ImportError(f"smt_kernel resolved to {sm.__file__}, outside {_HERE}")

# The retired statement, in the candidate's own vocabulary.
RETIRED = "(= a b)"
DECLS = "(declare-fun a () U)\n(declare-fun b () U)\n"

TAUTOLOGY = "(declare-fun q () U)\n(assert (= q q))"
UNRELATED = "(declare-fun c () U)\n(declare-fun d () U)\n(assert (not (= c d)))"
ENTAILING = DECLS + "(assert (= a b))"
CONTRADICTING = DECLS + "(assert (not (= a b)))"
EMPTY = ""


class UndecidedSolver:
    """A solver that never decides, for the fourth control."""

    def __init__(self):
        self.calls = 0

    def solve_smt2(self, *a, **k):
        self.calls += 1
        return SMTResult(status=SMTStatus.UNKNOWN)


class ForbiddenSolver:
    def solve_smt2(self, *a, **k):
        raise AssertionError("the solver was consulted when nothing was checkable")


class QuarantineTest(unittest.TestCase):

    def setUp(self):
        self.sk, self.pk = crypto.generate_keypair()
        self.reg = EpistemicTombstoneRegistry()
        self.reg.retire("RETIRED-RULE", "d" * 64, RetirementMode.REFUTED,
                        "Refuted by a counterexample.", self.sk, self.pk)
        self.statements = {"RETIRED-RULE": RETIRED}

    def report(self, formula, statements=None, solver=None):
        return smt_refute_tombstone(
            formula, self.reg,
            self.statements if statements is None else statements, solver)

    # ---------------------------------------------------------------- A ---

    def test_A1_a_tautology_entails_nothing(self):
        r = self.report(TAUTOLOGY)
        self.assertEqual(r.verdict, QuarantineVerdict.NO_ENTAILMENT_FOUND)
        self.assertEqual(r.quarantined_tombstones, [])
        self.assertEqual(r.checked_count, 1)

    def test_A2_an_unrelated_candidate_entails_nothing(self):
        r = self.report(UNRELATED)
        self.assertEqual(r.verdict, QuarantineVerdict.NO_ENTAILMENT_FOUND)
        self.assertEqual(r.quarantined_tombstones, [])

    def test_A3_a_candidate_that_proves_the_retired_statement_is_quarantined(self):
        r = self.report(ENTAILING)
        self.assertEqual(r.verdict, QuarantineVerdict.ENTAILS_RETIRED_STATEMENT)
        self.assertEqual(r.quarantined_tombstones, ["RETIRED-RULE"])
        self.assertIs(r.checks[0].status, TombstoneCheckStatus.ENTAILED)

    def test_A4_an_undecided_solver_is_inconclusive_not_safe_and_not_guilty(self):
        solver = UndecidedSolver()
        r = self.report(ENTAILING, solver=solver)
        self.assertEqual(r.verdict, QuarantineVerdict.INCONCLUSIVE)
        self.assertEqual(r.quarantined_tombstones, [])
        self.assertEqual(r.checked_count, 0)
        self.assertEqual(r.unchecked_count, 1)
        self.assertEqual(solver.calls, 1)

    def test_A5_denying_the_retired_statement_is_not_entailing_it(self):
        """The opposite of the retired claim must not be quarantined either."""
        r = self.report(CONTRADICTING)
        self.assertEqual(r.verdict, QuarantineVerdict.NO_ENTAILMENT_FOUND)
        self.assertIs(r.checks[0].status, TombstoneCheckStatus.NOT_ENTAILED)

    def test_A6_an_empty_candidate_says_nothing_and_is_charged_with_nothing(self):
        r = self.report(EMPTY)
        self.assertEqual(r.verdict, QuarantineVerdict.NO_ENTAILMENT_FOUND)
        self.assertEqual(r.quarantined_tombstones, [])

    def test_A7_a_solver_error_is_unknown_not_a_verdict(self):
        class Raising:
            def solve_smt2(self, *a, **k):
                raise RuntimeError("boom")
        r = self.report(ENTAILING, solver=Raising())
        self.assertEqual(r.verdict, QuarantineVerdict.INCONCLUSIVE)
        self.assertIs(r.checks[0].status, TombstoneCheckStatus.UNKNOWN)

    # ---------------------------------------------------------------- B ---

    def test_B1_a_tombstone_without_a_statement_is_unchecked(self):
        r = self.report(ENTAILING, statements={})
        self.assertEqual(r.verdict, QuarantineVerdict.NOTHING_CHECKED)
        self.assertEqual(r.checked_count, 0)
        self.assertEqual(r.unchecked_count, 1)
        self.assertIs(r.checks[0].status, TombstoneCheckStatus.NO_STATEMENT_SUPPLIED)

    def test_B2_an_empty_registry_certifies_nothing(self):
        r = smt_refute_tombstone(ENTAILING, EpistemicTombstoneRegistry(), {},
                                 solver=ForbiddenSolver())
        self.assertEqual(r.verdict, QuarantineVerdict.NOTHING_CHECKED)
        self.assertEqual(r.checks, [])

    def test_B3_no_verdict_asserts_soundness(self):
        """There is no value in the vocabulary that means the organism is sound."""
        self.assertNotIn("CERTIFIED_SOUND_ORGANISM", [v.value for v in QuarantineVerdict])
        for v in QuarantineVerdict:
            self.assertNotIn("SOUND", v.value)
            self.assertNotIn("SAFE", v.value)
        self.assertFalse(hasattr(self.report(TAUTOLOGY), "is_safe"))

    def test_B4_one_unchecked_tombstone_does_not_hide_behind_a_checked_one(self):
        self.reg.retire("SECOND-RULE", "e" * 64, RetirementMode.WITHDRAWN,
                        "Withdrawn by its author.", self.sk, self.pk)
        r = self.report(UNRELATED)          # a statement only for the first
        self.assertEqual(r.verdict, QuarantineVerdict.NO_ENTAILMENT_FOUND)
        self.assertEqual(r.checked_count, 1)
        self.assertEqual(r.unchecked_count, 1)
        statuses = {c.tombstone_id: c.status for c in r.checks}
        self.assertIs(statuses["SECOND-RULE"], TombstoneCheckStatus.NO_STATEMENT_SUPPLIED)

    def test_B5_a_quarantine_outranks_an_unknown(self):
        self.reg.retire("SECOND-RULE", "e" * 64, RetirementMode.WITHDRAWN,
                        "Withdrawn by its author.", self.sk, self.pk)
        r = self.report(ENTAILING, statements={"RETIRED-RULE": RETIRED})
        self.assertEqual(r.verdict, QuarantineVerdict.ENTAILS_RETIRED_STATEMENT)

    # ---------------------------------------------------------------- C ---

    def test_C1_each_tombstone_is_checked_against_its_own_statement(self):
        """Ids are used as keys, not minted into symbols and truncated."""
        long_a = "GENE-" + "A" * 40
        long_b = "GENE-" + "A" * 39 + "B"
        reg = EpistemicTombstoneRegistry()
        for tid in (long_a, long_b):
            reg.retire(tid, "d" * 64, RetirementMode.REFUTED, "Refuted.", self.sk, self.pk)
        r = smt_refute_tombstone(ENTAILING, reg, {long_a: RETIRED})
        self.assertEqual(r.quarantined_tombstones, [long_a])
        statuses = {c.tombstone_id: c.status for c in r.checks}
        self.assertIs(statuses[long_b], TombstoneCheckStatus.NO_STATEMENT_SUPPLIED)

    def test_C2_the_statement_is_not_derived_from_the_registry(self):
        """A record carries a subject and a loss declaration, not a formula."""
        record = self.reg.tombstones["RETIRED-RULE"]
        for field in ("target_id", "target_digest", "mode", "loss_declaration"):
            self.assertTrue(hasattr(record, field))
        self.assertFalse(any("smt" in f.lower() or "formula" in f.lower()
                             for f in record.__dataclass_fields__))
        self.assertEqual(self.report(ENTAILING, statements={}).verdict,
                         QuarantineVerdict.NOTHING_CHECKED)

    def test_C3_every_check_names_its_tombstone_and_its_reason(self):
        r = self.report(ENTAILING)
        self.assertEqual(len(r.checks), 1)
        self.assertEqual(r.checks[0].tombstone_id, "RETIRED-RULE")
        self.assertIn("prove", r.checks[0].reason)


if __name__ == "__main__":
    unittest.main(verbosity=2)
