#!/usr/bin/env python3
# coding: utf-8
"""
test_sheaf_agora.py — Comprehensive Unit & Integration Test Suite for Engine #35:
Federated Sheaf Agora & Cohomological Constitutionalism (AGORA-0.2).

Covers Invariants FSA1–FSA6:
  - Quadratic ballot tallying and anti-plutocratic power distribution
  - Mathematical Gini coefficient and Plutocracy Ceiling enforcement
  - Grassroots coalition defeating single oligarch
  - Harmonious Čech descent and global ratification (dim H^1 == 0)
  - Topological Čech fracture veto fail-closed (dim H^1 > 0)
  - Stake slashing on false equivalence proposals (SLASHED_AUDIT_FAILED)
  - Sovereign quine citizen voting using autopoietic metabolic ATP
  - ISO 32000 PDF polyglot compilation and standalone CLI execution
"""

import os
import sys
import tempfile
import unittest
import subprocess
from typing import List

import crypto
from crypto import generate_keypair
import glyph
from glyph import parse, evaluate
import cid
from cid import is_valid_cidv1

import sheaf_kernel
from sheaf_kernel import EpistemicContext

import agora
from agora import ProposalType, VoteDirection

import sovereign_continuity
from sovereign_continuity import SovereignOrganism

import sheaf_agora
from sheaf_agora import (
    RatificationStatus,
    FederatedBallot,
    calculate_gini,
    FederatedChamber,
    FederatedProposal,
    FederatedSettlementReceipt,
    FederatedAgoraParliament,
    generate_sheaf_agora_pdf
)


class TestFederatedSheafAgora(unittest.TestCase):
    def setUp(self):
        self.sk_sponsor, self.pk_sponsor = generate_keypair()
        self.sk_voter1, self.pk_voter1 = generate_keypair()
        self.sk_voter2, self.pk_voter2 = generate_keypair()

    def test_01_quadratic_ballot_and_gini_calculation(self):
        """FSA2 & FSA3: Quadratic voting power and Gini coefficient calculations."""
        # AYE vote: floor(sqrt(100)) = 10
        b_aye = FederatedBallot(
            voter_pk_hex=self.pk_voter1,
            chamber_id="ch_logic",
            proposal_id="p-1",
            pledged_atp=100,
            direction=VoteDirection.AYE
        )
        self.assertEqual(b_aye.effective_votes, 10)
        b_aye.sign(self.sk_voter1)
        self.assertTrue(b_aye.verify())

        # NAY vote: -floor(sqrt(49)) = -7
        b_nay = FederatedBallot(
            voter_pk_hex=self.pk_voter2,
            chamber_id="ch_logic",
            proposal_id="p-1",
            pledged_atp=49,
            direction=VoteDirection.NAY
        )
        self.assertEqual(b_nay.effective_votes, -7)
        b_nay.sign(self.sk_voter2)
        self.assertTrue(b_nay.verify())

        # Gini equality: identical stakes -> Gini = 0.0
        self.assertAlmostEqual(calculate_gini([50, 50, 50, 50]), 0.0, places=4)

        # Single stake or empty -> Gini = 0.0
        self.assertAlmostEqual(calculate_gini([100]), 0.0, places=4)
        self.assertAlmostEqual(calculate_gini([]), 0.0, places=4)

        # Unequal distribution: [10, 10, 10, 70]
        gini = calculate_gini([10, 10, 10, 70])
        self.assertGreater(gini, 0.40)
        self.assertLessEqual(gini, 1.0)

    def test_02_plutocracy_resistance_grassroots_defeat_oligarch(self):
        """FSA2: 10 grassroots voters (4 ATP each) defeat 1 oligarch (100 ATP)."""
        parliament = FederatedAgoraParliament("Grassroots Parliament")
        ctx = EpistemicContext.create("Assembly", ["civics"], 100)
        ch = FederatedChamber("ch_assembly", "Assembly", ctx)
        parliament.register_chamber(ch)

        # Oligarch with 100 ATP casts NAY -> floor(sqrt(100)) = 10 Nays
        sk_oligarch, pk_oligarch = generate_keypair()
        b_oligarch = FederatedBallot(
            voter_pk_hex=pk_oligarch,
            chamber_id="ch_assembly",
            proposal_id="prop_grassroots",
            pledged_atp=100,
            direction=VoteDirection.NAY
        )
        b_oligarch.sign(sk_oligarch)
        parliament.cast_ballot(b_oligarch)

        # 10 grassroots voters with 4 ATP each cast AYE -> 10 * floor(sqrt(4)) = 20 Yeas
        for i in range(10):
            sk_g, pk_g = generate_keypair()
            b_g = FederatedBallot(
                voter_pk_hex=pk_g,
                chamber_id="ch_assembly",
                proposal_id="prop_grassroots",
                pledged_atp=4,
                direction=VoteDirection.AYE
            )
            b_g.sign(sk_g)
            parliament.cast_ballot(b_g)

        yeas, nays = ch.local_tally()
        self.assertEqual(yeas, 20)
        self.assertEqual(nays, 10)
        # Grassroots have 40 ATP total vs 100 ATP oligarch, but grassroots WIN 20 to 10!
        self.assertGreater(yeas, nays)

    def test_03_triple_gate_ratification_success(self):
        """FSA4: Full triple ratification gate success with dim H^1 == 0."""
        parliament = FederatedAgoraParliament("Consensus Federation")
        ctx1 = EpistemicContext.create("Logic Chamber", ["logic"], 120)
        ctx2 = EpistemicContext.create("Computation Chamber", ["computation"], 150)
        ch1 = FederatedChamber("ch1", "Logic Chamber", ctx1)
        ch2 = FederatedChamber("ch2", "Computation Chamber", ctx2)
        parliament.register_chamber(ch1)
        parliament.register_chamber(ch2)

        prop = FederatedProposal(
            proposal_id="prop_identity",
            title="Axiom of Computational Identity",
            proposal_type=ProposalType.THEOREM_CONGRUENCE,
            claim_name="Computational Identity S (K I) (K I) == I",
            sponsor_pk_hex=self.pk_sponsor,
            stake_atp=50,
            chamber_terms={
                "ch1": "(K I) (K I)",
                "ch2": "I"
            },
            target_nf="I"
        )
        prop.sign(self.sk_sponsor)
        parliament.table_proposal(prop)

        # Cast affirmative ballots
        b1 = FederatedBallot(
            voter_pk_hex=self.pk_voter1,
            chamber_id="ch1",
            proposal_id="prop_identity",
            pledged_atp=36,
            direction=VoteDirection.AYE
        )
        b1.sign(self.sk_voter1)
        parliament.cast_ballot(b1)

        b2 = FederatedBallot(
            voter_pk_hex=self.pk_voter2,
            chamber_id="ch2",
            proposal_id="prop_identity",
            pledged_atp=25,
            direction=VoteDirection.AYE
        )
        b2.sign(self.sk_voter2)
        parliament.cast_ballot(b2)

        receipt = parliament.resolve_session("prop_identity")
        self.assertEqual(receipt.status, RatificationStatus.RATIFIED_GLOBAL)
        self.assertEqual(receipt.h1_dimension, 0)
        self.assertEqual(receipt.total_yeas, 6 + 5)
        self.assertEqual(receipt.total_nays, 0)
        self.assertTrue(is_valid_cidv1(receipt.cid))
        self.assertEqual(len(parliament.receipt_chain), 1)

    def test_04_cech_cohomological_fracture_veto(self):
        """FSA4: Unanimous political vote rejected fail-closed on Čech cohomology defect (dim H^1 = 1)."""
        parliament = FederatedAgoraParliament("Fractured Federation")
        # Two chambers sharing the 'consensus' domain
        ctx1 = EpistemicContext.create("Chamber Alpha", ["consensus", "alpha"], 120)
        ctx2 = EpistemicContext.create("Chamber Beta", ["consensus", "beta"], 120)
        ch1 = FederatedChamber("ch_a", "Chamber Alpha", ctx1)
        ch2 = FederatedChamber("ch_b", "Chamber Beta", ctx2)
        parliament.register_chamber(ch1)
        parliament.register_chamber(ch2)

        # Propose conflicting normal forms on the shared 'consensus' domain:
        # Chamber Alpha gets 'K' (reduces to 🖤)
        # Chamber Beta gets 'K I' (reduces to 🖤 (🤍))
        prop = FederatedProposal(
            proposal_id="prop_split",
            title="Conflicting Axiom Across Domains",
            proposal_type=ProposalType.CONSTITUTIONAL_AMENDMENT,
            claim_name="Consensus Settlement Rule",
            sponsor_pk_hex=self.pk_sponsor,
            stake_atp=20,
            chamber_terms={
                "ch_a": "K",
                "ch_b": "K I"
            },
            target_nf="N/A"
        )
        prop.sign(self.sk_sponsor)
        parliament.table_proposal(prop)

        # 100% Affirmative political vote in both chambers!
        b1 = FederatedBallot(
            voter_pk_hex=self.pk_voter1,
            chamber_id="ch_a",
            proposal_id="prop_split",
            pledged_atp=25,
            direction=VoteDirection.AYE
        )
        b1.sign(self.sk_voter1)
        parliament.cast_ballot(b1)

        b2 = FederatedBallot(
            voter_pk_hex=self.pk_voter2,
            chamber_id="ch_b",
            proposal_id="prop_split",
            pledged_atp=25,
            direction=VoteDirection.AYE
        )
        b2.sign(self.sk_voter2)
        parliament.cast_ballot(b2)

        receipt = parliament.resolve_session("prop_split")
        # Supermajority was 100%, but fail-closed Čech veto triggers!
        self.assertEqual(receipt.status, RatificationStatus.REJECTED_COHOMOLOGICAL_FRACTURE)
        self.assertGreater(receipt.h1_dimension, 0)
        self.assertIn("Čech Cohomology Obstruction", receipt.rejection_reason)

    def test_05_plutocracy_ceiling_rejection(self):
        """FSA3: Motion rejected when federation Gini index exceeds plutocracy ceiling (0.65)."""
        parliament = FederatedAgoraParliament("Unequal Parliament")
        ctx = EpistemicContext.create("General", ["economy"], 100)
        ch = FederatedChamber("ch_econ", "Economy Chamber", ctx)
        parliament.register_chamber(ch)

        # Extremely skewed stake distribution: 1 voter at 10,000 ATP, 10 voters at 1 ATP
        sk_whale, pk_whale = generate_keypair()
        b_whale = FederatedBallot(
            voter_pk_hex=pk_whale,
            chamber_id="ch_econ",
            proposal_id="prop_econ",
            pledged_atp=10000,
            direction=VoteDirection.AYE
        )
        b_whale.sign(sk_whale)
        parliament.cast_ballot(b_whale)

        for _ in range(10):
            sk_p, pk_p = generate_keypair()
            bp = FederatedBallot(
                voter_pk_hex=pk_p,
                chamber_id="ch_econ",
                proposal_id="prop_econ",
                pledged_atp=1,
                direction=VoteDirection.AYE
            )
            bp.sign(sk_p)
            parliament.cast_ballot(bp)

        prop = FederatedProposal(
            proposal_id="prop_econ",
            title="Monetary Reform",
            proposal_type=ProposalType.METABOLIC_TAX_RATE,
            claim_name="Tax Policy",
            sponsor_pk_hex=self.pk_sponsor,
            stake_atp=10,
            chamber_terms={"ch_econ": "I"},
            target_nf="I"
        )
        prop.sign(self.sk_sponsor)
        parliament.table_proposal(prop)

        receipt = parliament.resolve_session("prop_econ", gini_ceiling=0.65)
        self.assertEqual(receipt.status, RatificationStatus.REJECTED_PLUTOCRACY_CEILING)
        self.assertGreaterEqual(receipt.federation_gini, 0.65)

    def test_06b_unsettled_theorem_is_unverified_not_slashed(self):
        """FSA5 (S-verif-8): a reduction that does not settle within the chamber budget is
        UNVERIFIED_AUDIT_BUDGET — no ratification, no slash, stake untouched. Before this
        rule `omega omega` reached the cohomology gate mislabelled as a fracture, and a true
        identity `Y f` vs `f (Y f)` was SLASHED_AUDIT_FAILED."""
        parliament = FederatedAgoraParliament("Rigorous Agora")
        ctx = EpistemicContext.create("Math Chamber", ["algebra"], 100)
        ch = FederatedChamber("ch_math", "Math Chamber", ctx)
        parliament.register_chamber(ch)
        for pid, term, target in (("prop_omega", "S I I (S I I)", "I"), ("prop_yf", "Y f", "f (Y f)")):
            prop = FederatedProposal(
                proposal_id=pid, title="Unsettled Theorem",
                proposal_type=ProposalType.THEOREM_CONGRUENCE, claim_name=f"claim {pid}",
                sponsor_pk_hex=self.pk_sponsor, stake_atp=80,
                chamber_terms={"ch_math": term}, target_nf=target
            )
            prop.sign(self.sk_sponsor)
            parliament.table_proposal(prop)
            b = FederatedBallot(voter_pk_hex=self.pk_voter1, chamber_id="ch_math",
                                proposal_id=pid, pledged_atp=49, direction=VoteDirection.AYE)
            b.sign(self.sk_voter1)
            parliament.cast_ballot(b)
            receipt = parliament.resolve_session(pid)
            self.assertEqual(receipt.status, RatificationStatus.UNVERIFIED_AUDIT_BUDGET, pid)
            self.assertEqual(receipt.slashed_stake, 0, pid)
            self.assertIn("did not settle", receipt.rejection_reason)
            self.assertFalse(receipt.is_ratified)

    def test_06c_chamber_order_does_not_decide_slash(self):
        """FSA5 (S-verif-8 amendment): a settled counterexample in any chamber slashes,
        whatever the dictionary order; an unsettled or erroring chamber never hides it.
        Before the amendment `{Y I, K}` was UNVERIFIED and `{K, Y I}` was SLASHED."""
        cases = [
            ("unsettled+counterexample", [("ch_a", "Y I"), ("ch_b", "K")]),
            ("counterexample+unsettled", [("ch_b", "K"), ("ch_a", "Y I")]),
            ("error+counterexample", [("ch_a", "(("), ("ch_b", "K")]),
            ("counterexample+error", [("ch_b", "K"), ("ch_a", "((")]),
        ]
        for label, terms in cases:
            parliament = FederatedAgoraParliament("Rigorous Agora")
            for cid, name in (("ch_a", "Chamber A"), ("ch_b", "Chamber B")):
                ctx = EpistemicContext.create(name, ["algebra"], 100)
                parliament.register_chamber(FederatedChamber(cid, name, ctx))
            prop = FederatedProposal(
                proposal_id=f"prop_{label}", title="Order test",
                proposal_type=ProposalType.THEOREM_CONGRUENCE, claim_name=f"claim {label}",
                sponsor_pk_hex=self.pk_sponsor, stake_atp=80,
                chamber_terms=dict(terms), target_nf="I"
            )
            prop.sign(self.sk_sponsor)
            parliament.table_proposal(prop)
            b = FederatedBallot(voter_pk_hex=self.pk_voter1, chamber_id="ch_a",
                                proposal_id=prop.proposal_id, pledged_atp=49, direction=VoteDirection.AYE)
            b.sign(self.sk_voter1)
            parliament.cast_ballot(b)
            receipt = parliament.resolve_session(prop.proposal_id)
            self.assertEqual(receipt.status, RatificationStatus.SLASHED_AUDIT_FAILED, label)
            self.assertEqual(receipt.slashed_stake, 80, label)
            self.assertIn("Chamber B", receipt.rejection_reason, label)

        # No settled counterexample anywhere: unsettled + error is UNVERIFIED, not slashed
        parliament = FederatedAgoraParliament("Rigorous Agora")
        for cid, name in (("ch_a", "Chamber A"), ("ch_b", "Chamber B")):
            parliament.register_chamber(FederatedChamber(cid, name, EpistemicContext.create(name, ["algebra"], 100)))
        prop = FederatedProposal(
            proposal_id="prop_unsettled_error", title="Order test",
            proposal_type=ProposalType.THEOREM_CONGRUENCE, claim_name="claim ue",
            sponsor_pk_hex=self.pk_sponsor, stake_atp=80,
            chamber_terms={"ch_a": "Y I", "ch_b": "(("}, target_nf="I"
        )
        prop.sign(self.sk_sponsor)
        parliament.table_proposal(prop)
        receipt = parliament.resolve_session("prop_unsettled_error")
        self.assertEqual(receipt.status, RatificationStatus.UNVERIFIED_AUDIT_BUDGET)
        self.assertEqual(receipt.slashed_stake, 0)

    def test_06_fail_closed_theorem_slashing(self):
        """FSA5: Proposal claiming equivalence that reduces to false is slashed."""
        parliament = FederatedAgoraParliament("Rigorous Agora")
        ctx = EpistemicContext.create("Math Chamber", ["algebra"], 100)
        ch = FederatedChamber("ch_math", "Math Chamber", ctx)
        parliament.register_chamber(ch)

        # Sponsor fraudulently claims 'K I' (False) reduces to 'I'
        prop = FederatedProposal(
            proposal_id="prop_falsehood",
            title="False Theorem Equivalence",
            proposal_type=ProposalType.THEOREM_CONGRUENCE,
            claim_name="False Claim K I == I",
            sponsor_pk_hex=self.pk_sponsor,
            stake_atp=80,
            chamber_terms={"ch_math": "K I"},
            target_nf="I"
        )
        prop.sign(self.sk_sponsor)
        parliament.table_proposal(prop)

        # Cast affirmative vote
        b = FederatedBallot(
            voter_pk_hex=self.pk_voter1,
            chamber_id="ch_math",
            proposal_id="prop_falsehood",
            pledged_atp=49,
            direction=VoteDirection.AYE
        )
        b.sign(self.sk_voter1)
        parliament.cast_ballot(b)

        receipt = parliament.resolve_session("prop_falsehood")
        self.assertEqual(receipt.status, RatificationStatus.SLASHED_AUDIT_FAILED)
        self.assertEqual(receipt.slashed_stake, 80)
        self.assertIn("Theorem reduction divergence", receipt.rejection_reason)

    def test_07_sovereign_quine_citizen_voting(self):
        """Engine #34 & #35 integration: Sovereign organism votes using metabolic ATP."""
        parliament = FederatedAgoraParliament("Civic Agora")
        ctx = EpistemicContext.create("Civic Chamber", ["civics"], 100)
        ch = FederatedChamber("ch_civic", "Civic Chamber", ctx)
        parliament.register_chamber(ch)

        organism = SovereignOrganism.create_genesis(organism_id="%🖤-SOVEREIGN-VOTER-1")

        prop = FederatedProposal(
            proposal_id="prop_tax",
            title="Metabolic Tax Policy",
            proposal_type=ProposalType.METABOLIC_TAX_RATE,
            claim_name="Tax Rate 10%",
            sponsor_pk_hex=self.pk_sponsor,
            stake_atp=15,
            chamber_terms={"ch_civic": "I"},
            target_nf="I"
        )
        prop.sign(self.sk_sponsor)
        parliament.table_proposal(prop)

        # Organism pledges 36 ATP -> floor(sqrt(36)) = 6 Yeas
        ballot = parliament.vote_with_sovereign_organism(
            organism=organism,
            chamber_id="ch_civic",
            proposal_id="prop_tax",
            atp_stake=36,
            direction=VoteDirection.AYE
        )
        self.assertEqual(ballot.effective_votes, 6)
        self.assertTrue(ballot.verify())

        receipt = parliament.resolve_session("prop_tax")
        self.assertEqual(receipt.status, RatificationStatus.RATIFIED_GLOBAL)
        self.assertEqual(receipt.total_yeas, 6)

    def _session_with_two_honest_nays(self):
        """A theorem session that the cohomology and theorem gates pass, with
        two honest NAY ballots of pledge 36 (6 effective nays each)."""
        parliament = FederatedAgoraParliament("Ballot Weight Federation")
        ctx1 = EpistemicContext.create("Logic Chamber", ["logic"], 120)
        ctx2 = EpistemicContext.create("Computation Chamber", ["computation"], 150)
        parliament.register_chamber(FederatedChamber("ch1", "Logic Chamber", ctx1))
        parliament.register_chamber(FederatedChamber("ch2", "Computation Chamber", ctx2))
        prop = FederatedProposal(
            proposal_id="prop_weight", title="Identity", proposal_type=ProposalType.THEOREM_CONGRUENCE,
            claim_name="(K I) (K I) == I", sponsor_pk_hex=self.pk_sponsor, stake_atp=50,
            chamber_terms={"ch1": "(K I) (K I)", "ch2": "I"}, target_nf="I")
        prop.sign(self.sk_sponsor)
        parliament.table_proposal(prop)
        for ch, sk, pk in (("ch1", self.sk_voter1, self.pk_voter1), ("ch2", self.sk_voter2, self.pk_voter2)):
            b = FederatedBallot(voter_pk_hex=pk, chamber_id=ch, proposal_id="prop_weight",
                                pledged_atp=36, direction=VoteDirection.NAY)
            b.sign(sk)
            parliament.cast_ballot(b)
        return parliament

    def test_09_ballot_weight_is_derived_from_the_pledge_not_declared(self):
        """Scan `e549de3` finding 13: a signer must not choose `effective_votes`.

        Before the fix a ballot with `pledged_atp=1` and a signed
        `effective_votes=1_000_000` was RATIFIED_GLOBAL against twelve honest
        nays, through both the in-memory object and `from_dict`; the honest
        control with the same pledge was REJECTED_POLITICAL_VOTE."""
        sk_att, pk_att = generate_keypair()

        # Control: the honest weight for a pledge of 1 is 1 and it loses 1:12.
        parliament = self._session_with_two_honest_nays()
        honest = FederatedBallot(voter_pk_hex=pk_att, chamber_id="ch1", proposal_id="prop_weight",
                                 pledged_atp=1, direction=VoteDirection.AYE)
        honest.sign(sk_att)
        parliament.cast_ballot(honest)
        receipt = parliament.resolve_session("prop_weight")
        self.assertEqual((receipt.total_yeas, receipt.total_nays), (1, 12))
        self.assertEqual(receipt.status, RatificationStatus.REJECTED_POLITICAL_VOTE)

        # Attack 1: mutate the object after construction, then sign the mutation.
        parliament = self._session_with_two_honest_nays()
        forged = FederatedBallot(voter_pk_hex=pk_att, chamber_id="ch1", proposal_id="prop_weight",
                                 pledged_atp=1, direction=VoteDirection.AYE)
        forged.effective_votes = 10 ** 6
        forged.sign(sk_att)
        self.assertFalse(forged.verify(), "a signed but non-derived weight must not verify")
        with self.assertRaises(ValueError):
            parliament.cast_ballot(forged)
        receipt = parliament.resolve_session("prop_weight")
        self.assertEqual((receipt.total_yeas, receipt.total_nays), (0, 12))
        self.assertEqual(receipt.status, RatificationStatus.REJECTED_POLITICAL_VOTE)

        # Attack 2: the inflated weight arrives in a dict and is signed as such.
        parliament = self._session_with_two_honest_nays()
        d = dict(voter_pk_hex=pk_att, chamber_id="ch1", proposal_id="prop_weight",
                 pledged_atp=1, direction="AYE", effective_votes=10 ** 6)
        from_wire = FederatedBallot.from_dict(d)
        self.assertEqual(from_wire.effective_votes, 1, "from_dict derives the weight; it does not copy it")
        from_wire.effective_votes = 10 ** 6
        from_wire.sign(sk_att)
        received = FederatedBallot.from_dict(from_wire.to_dict())
        self.assertFalse(received.verify())
        with self.assertRaises(ValueError):
            parliament.cast_ballot(received)

        # The NAY side is covered by the same rule (the tally takes abs()).
        nay = FederatedBallot(voter_pk_hex=pk_att, chamber_id="ch1", proposal_id="prop_weight",
                              pledged_atp=1, direction=VoteDirection.NAY)
        nay.effective_votes = -(10 ** 6)
        nay.sign(sk_att)
        self.assertFalse(nay.verify())

        # An honest ballot still round-trips through to_dict/from_dict and verifies.
        honest = FederatedBallot(voter_pk_hex=pk_att, chamber_id="ch1", proposal_id="prop_weight",
                                 pledged_atp=49, direction=VoteDirection.NAY)
        honest.sign(sk_att)
        again = FederatedBallot.from_dict(honest.to_dict())
        self.assertEqual(again.effective_votes, -7)
        self.assertTrue(again.verify())

    def test_08_iso32000_pdf_polyglot_and_cli_execution(self):
        """FSA6: ISO 32000 PDF polyglot generation and standalone execution."""
        parliament = FederatedAgoraParliament("Polyglot Parliament")
        ctx1 = EpistemicContext.create("Alpha", ["physics"], 100)
        ctx2 = EpistemicContext.create("Beta", ["logic"], 100)
        parliament.register_chamber(FederatedChamber("ch1", "Alpha", ctx1))
        parliament.register_chamber(FederatedChamber("ch2", "Beta", ctx2))

        prop = FederatedProposal(
            proposal_id="prop_poly",
            title="Polyglot Motion",
            proposal_type=ProposalType.CONSTITUTIONAL_AMENDMENT,
            claim_name="Universal Polyglot Rule",
            sponsor_pk_hex=self.pk_sponsor,
            stake_atp=20,
            chamber_terms={"ch1": "I", "ch2": "I"},
            target_nf="I"
        )
        prop.sign(self.sk_sponsor)
        parliament.table_proposal(prop)

        b = FederatedBallot(
            voter_pk_hex=self.pk_voter1,
            chamber_id="ch1",
            proposal_id="prop_poly",
            pledged_atp=25,
            direction=VoteDirection.AYE
        )
        b.sign(self.sk_voter1)
        parliament.cast_ballot(b)

        receipt = parliament.resolve_session("prop_poly")

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            pdf_path = f.name

        try:
            pdf_bytes = generate_sheaf_agora_pdf(parliament, receipt, pdf_path)
            self.assertTrue(pdf_bytes.startswith(b"#!/usr/bin/env python3\n# coding: latin-1\nr'''%PDF-1.4"))
            self.assertIn(b"%%EOF\n'''\n", pdf_bytes)

            # Test standalone CLI execution
            res = subprocess.run([sys.executable, pdf_path], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, f"Polyglot script failed: {res.stderr}")
            self.assertIn("FEDERATED SHEAF AGORA PARLIAMENT AUDITOR", res.stdout)
            self.assertIn("RATIFIED_GLOBAL", res.stdout)

            # Test vector rendering with pdftoppm if available
            pdftoppm_bin = "/opt/homebrew/bin/pdftoppm"
            if os.path.exists(pdftoppm_bin):
                out_prefix = os.path.join(tempfile.gettempdir(), "sheaf_agora_render_test")
                ppm_res = subprocess.run([pdftoppm_bin, "-png", "-r", "150", pdf_path, out_prefix], capture_output=True, text=True)
                self.assertEqual(ppm_res.returncode, 0, f"pdftoppm failed: {ppm_res.stderr}")
                self.assertTrue(os.path.exists(f"{out_prefix}-1.png"))
                os.remove(f"{out_prefix}-1.png")
        finally:
            if os.path.exists(pdf_path):
                os.remove(pdf_path)


if __name__ == "__main__":
    unittest.main()
