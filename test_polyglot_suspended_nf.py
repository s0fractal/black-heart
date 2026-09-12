#!/usr/bin/env python3
"""
Regression: a budget-suspended reduction is not a verified normal form, in
either consumer that compares reductions.

Security scan of e549de3, `improper-verification.suspended-normal-form`.
`glyph.evaluate(t, max_atp=b)` returns `.term`/`.normal_form` with status
SUSPENDED when the budget is exhausted. Two consumers compared those terms
without checking `is_settled()`:

  1. `polyglot.audit_polyglot_claims` (reached by `cli.py verify`): a claim
     whose expression does not terminate, with expected == expression, audits
     as verified -- reproduced at the maximum allowed budget (100000), where
     both sides suspend to the same string.
  2. `epistemic_swarm` `SwarmAgoraCommons.vote_and_settle` (the reward/canon
     path): the same non-terminating proposal is voted sound, RATIFIED, its
     author rewarded (stake + 30 ATP), and the expression appended to the
     Swarm Canon -- reproduced end to end.

Fix: both sites require the reduction (and the expected side) to SETTLE
within budget before any equality is trusted.

Sections:
  A  the host auditor rejects a suspended claim; accepts a settled one
  B  the swarm neither ratifies, rewards, nor canonizes a suspended proposal;
     still ratifies a genuine identity
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest

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

import glyph
import polyglot as PG
from polyglot import PolyglotDocument, audit_polyglot_claims
from epistemic_swarm import (SwarmMembrane, SwarmAgoraCommons, EpistemicOrganism,
                             SwarmOrganismState)
from organism import Chromosome
from crypto import generate_keypair

if os.path.dirname(os.path.abspath(PG.__file__)) != _HERE:
    raise ImportError(f"polyglot resolved to {PG.__file__}, outside {_HERE}")

NONTERMINATING = "🌿 🤍 🤍 (🌿 🤍 🤍)"     # (S I I)(S I I): never settles
MAX_BUDGET = 100000


class HostAuditorTest(unittest.TestCase):
    """Section A: polyglot.audit_polyglot_claims."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

    def audit(self, expr, expected, max_atp):
        doc = PolyglotDocument(title="probe")
        doc.add_claim("c1", "d", expr, expected, max_atp=max_atp)
        path = os.path.join(self._tmp.name, "doc.pdf")
        doc.compile(path)
        return audit_polyglot_claims(path)

    def test_A1_a_suspended_claim_is_not_verified_even_at_max_budget(self):
        # both sides suspend to the same string at the max budget
        self.assertEqual(glyph.evaluate(glyph.parse(NONTERMINATING), max_atp=MAX_BUDGET).status.value,
                         "SUSPENDED")
        self.assertFalse(self.audit(NONTERMINATING, NONTERMINATING, MAX_BUDGET),
                         "a non-terminating claim audited as verified")

    def test_A2_a_settled_claim_still_verifies(self):
        self.assertTrue(self.audit("🌿 🖤 🖤 x", "x", 10000),
                        "S K K x -> x should verify")

    def test_A3_a_settled_mismatch_still_fails(self):
        self.assertFalse(self.audit("🖤 x y", "y", 10000),
                         "K x y -> x, so expected y must fail")


class SwarmRewardTest(unittest.TestCase):
    """Section B: epistemic_swarm vote_and_settle -> reward + canon."""

    def make_org(self, oid, x, atp=300):
        sk, pk = generate_keypair()
        org = EpistemicOrganism(
            organism_id=oid, generation=0,
            chromosomes=[Chromosome(gene_id="G_I", gene_name="I", expression="I x",
                                    expected_normal_form="x", vital=True)],
            public_key_hex=pk, atp_reserve=atp, active_axioms=["I x"])
        st = SwarmOrganismState(organism_id=oid, x=x, y=1, heading=(1, 0), is_alive=True)
        return org, st, pk, sk

    def swarm_of(self, n=3):
        swarm = SwarmMembrane(grid_width=16, grid_height=16)
        for i in range(n):
            swarm.add_organism(*self.make_org(f"org-{i}", i + 1))
        return swarm

    def test_B1_a_suspended_proposal_is_not_ratified_rewarded_or_canonized(self):
        swarm = self.swarm_of()
        before = swarm.organisms["org-0"].atp_reserve
        prop = SwarmAgoraCommons.table_proposal(
            swarm=swarm, author_id="org-0", expression=NONTERMINATING,
            expected_normal_form=NONTERMINATING, evidence_grade="A", stake_atp=50)
        ratified, _ = SwarmAgoraCommons.vote_and_settle(swarm, prop)
        self.assertFalse(ratified, "a non-terminating theorem was ratified")
        self.assertEqual(prop.status, "REJECTED")
        self.assertFalse(any(a.expression == NONTERMINATING for a in swarm.canon),
                         "a non-terminating theorem entered the canon")
        # not rewarded: never rose above the pre-stake balance
        self.assertLess(swarm.organisms["org-0"].atp_reserve, before + 30)

    def test_B2_a_genuine_identity_still_ratifies_and_rewards(self):
        swarm = self.swarm_of()
        before = swarm.organisms["org-0"].atp_reserve            # 300
        prop = SwarmAgoraCommons.table_proposal(
            swarm=swarm, author_id="org-0", expression="🌿 🖤 🖤 x",
            expected_normal_form="x", evidence_grade="A", stake_atp=50)
        ratified, _ = SwarmAgoraCommons.vote_and_settle(swarm, prop)
        self.assertTrue(ratified, "S K K x -> x should ratify")
        self.assertEqual(prop.status, "RATIFIED")
        self.assertTrue(any(a.expression == "🌿 🖤 🖤 x" for a in swarm.canon))
        self.assertEqual(swarm.organisms["org-0"].atp_reserve, before + 30)  # stake back +30


if __name__ == "__main__":
    unittest.main()
