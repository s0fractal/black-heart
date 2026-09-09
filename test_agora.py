#!/usr/bin/env python3
# coding: utf-8
"""
test_agora.py — Test Suite for Mycelial Social Democracy & Consensus Agora.
Part of Project Black-Heart (%🖤).
"""

import os
import sys
import tempfile
import unittest
import subprocess

from crypto import generate_keypair
from cid import compute_cidv1_raw, is_valid_cidv1
from agora import (
    ProposalType,
    VoteDirection,
    ProposalStatus,
    AgoraProposal,
    AgoraBallot,
    SlashingReceipt,
    ConsensusSettlementReceipt,
    calculate_gini_coefficient,
    calculate_herfindahl_index,
    audit_combinator_theorem,
    AgoraConsensusEngine,
    AgoraPolyglotCompiler,
    initialize_agora_assembly,
    grow_agora_page,
    AGORA_MANIFEST_PREFIX
)

class TestQuadraticVotingAndMetrics(unittest.TestCase):
    """Verifies quadratic voting mathematics and socio-economic inequality metrics."""

    def setUp(self):
        self.sk1, self.pk1 = generate_keypair()
        self.sk2, self.pk2 = generate_keypair()

    def test_quadratic_weight_formula_and_tampering(self):
        # 100 ATP -> weight 10
        ballot = AgoraBallot(
            proposal_id="PROP_01",
            voter_public_key=self.pk1,
            direction=VoteDirection.AYE.value,
            atp_burned=100,
            quadratic_weight=10,
            reason="Sound theorem"
        )
        ballot.sign(self.sk1)
        self.assertTrue(ballot.verify_signature())

        # Tampering with weight (trying to claim weight 50 instead of 10)
        ballot_cheat = AgoraBallot.from_dict(ballot.to_dict())
        ballot_cheat.quadratic_weight = 50
        self.assertFalse(ballot_cheat.verify_signature())

        # 99 ATP -> weight 9 (floor of sqrt(99))
        ballot2 = AgoraBallot(
            proposal_id="PROP_01",
            voter_public_key=self.pk2,
            direction=VoteDirection.NAY.value,
            atp_burned=99,
            quadratic_weight=9
        )
        ballot2.sign(self.sk2)
        self.assertTrue(ballot2.verify_signature())

    def test_gini_coefficient(self):
        # Perfect equality
        self.assertEqual(calculate_gini_coefficient([100, 100, 100, 100]), 0.0)
        # Empty
        self.assertEqual(calculate_gini_coefficient([]), 0.0)
        # High inequality
        gini_skewed = calculate_gini_coefficient([10, 10, 10, 10000])
        self.assertGreater(gini_skewed, 0.70)
        self.assertLessEqual(gini_skewed, 1.0)

    def test_herfindahl_index(self):
        # 4 equal voters -> 4 * (0.25^2) = 0.25
        self.assertAlmostEqual(calculate_herfindahl_index([10, 10, 10, 10]), 0.25, places=2)
        # 1 monopoly voter -> 1.0
        self.assertAlmostEqual(calculate_herfindahl_index([100]), 1.0, places=2)


class TestImmuneAuditingAndSlashing(unittest.TestCase):
    """Verifies that false theorems are detected and the author's stake is slashed."""

    def test_theorem_audit(self):
        # Sound: 🌿 🖤 🤍 -> 🤍
        ok, msg = audit_combinator_theorem("🌿 🖤 🤍", "🤍")
        self.assertTrue(ok)
        self.assertIn("Sound", msg)

        # Contradiction: 🖤 Truth False reduces to Truth, not False
        ok_bad, msg_bad = audit_combinator_theorem("🖤 Truth False", "False")
        self.assertFalse(ok_bad)
        self.assertIn("Contradiction", msg_bad)

    def test_slashing_execution_in_engine(self):
        engine = AgoraConsensusEngine()
        sk_auth, pk_auth = generate_keypair()
        sk_voter, pk_voter = generate_keypair()

        engine.register_citizen(pk_auth, initial_atp=500)
        engine.register_citizen(pk_voter, initial_atp=500)

        # Author tables FALSE claim
        false_prop = AgoraProposal(
            proposal_id="PROP_FALSE_01",
            proposal_type=ProposalType.THEOREM_CONGRUENCE.value,
            title="Bogus Equivalence",
            statement="Asserting K x y == y",
            pre_term="🖤 Truth False",
            post_term="False",
            author_public_key="",
            stake_atp=200,
            timestamp_utc="2026-09-09T12:00:00Z"
        )
        false_prop.sign(sk_auth)
        engine.table_proposal(false_prop)

        # Balance locked: 500 - 200 = 300
        self.assertEqual(engine.citizen_balances[pk_auth], 300)

        # Citizen votes NAY with 25 ATP (weight 5)
        ballot = AgoraBallot(
            proposal_id="PROP_FALSE_01",
            voter_public_key=pk_voter,
            direction=VoteDirection.NAY.value,
            atp_burned=25,
            quadratic_weight=5,
            reason="Refuted by Church-Rosser reduction"
        )
        ballot.sign(sk_voter)
        engine.cast_ballot(ballot)

        # Evaluate and settle
        settlement = engine.evaluate_and_settle("PROP_FALSE_01")
        self.assertEqual(settlement.status, ProposalStatus.SLASHED.value)
        self.assertIsNotNone(settlement.slashing_receipt)
        self.assertEqual(settlement.slashing_receipt.slashed_atp, 200)

        # Voter received bounty (200 // 2 = 100)
        # Voter initial: 500 - 25 + 100 = 575
        self.assertEqual(engine.citizen_balances[pk_voter], 575)
        # Author lost stake: remaining 300
        self.assertEqual(engine.citizen_balances[pk_auth], 300)


class TestConsensusQuorumAndSettlement(unittest.TestCase):
    """Verifies that sound proposals achieve supermajority and are ratified."""

    def test_ratification_flow(self):
        engine = AgoraConsensusEngine(supermajority_ratio=0.667, quorum_ratio=0.50)
        sk_author, pk_author = generate_keypair()
        citizens = [generate_keypair() for _ in range(3)]

        engine.register_citizen(pk_author, initial_atp=500)
        for _, pk in citizens:
            engine.register_citizen(pk, initial_atp=500)

        # Table sound theorem: S K I == I
        prop = AgoraProposal(
            proposal_id="PROP_SOUND_01",
            proposal_type=ProposalType.THEOREM_CONGRUENCE.value,
            title="S K I is Identity",
            statement="🌿 🖤 🤍 == 🤍",
            pre_term="🌿 🖤 🤍",
            post_term="🤍",
            stake_atp=100,
            timestamp_utc="2026-09-09T12:00:00Z"
        )
        prop.sign(sk_author)
        engine.table_proposal(prop)

        # 3 citizens vote AYE with 400 ATP each (weight 20 each, total 60 Aye weight)
        # Total voted: 1200 / 2000 = 60% > 50% quorum
        for sk, pk in citizens:
            b = AgoraBallot(
                proposal_id="PROP_SOUND_01",
                voter_public_key=pk,
                direction=VoteDirection.AYE.value,
                atp_burned=400,
                quadratic_weight=20
            )
            b.sign(sk)
            engine.cast_ballot(b)

        settlement = engine.evaluate_and_settle("PROP_SOUND_01", prev_cid="bafkreihdwdcefgh4dqkjv67uzcmw7ojee6xedzdetojuzjevtenxquvyku")
        self.assertEqual(settlement.status, ProposalStatus.RATIFIED.value)
        self.assertTrue(settlement.quorum_reached)
        self.assertTrue(settlement.supermajority_reached)
        self.assertEqual(settlement.aye_weight, 60)
        self.assertEqual(settlement.nay_weight, 0)
        self.assertEqual(settlement.total_atp_voted, 1200)
        self.assertEqual(len(settlement.multi_signatures), 3)


class TestAppendOnlyAgoraGrowth(unittest.TestCase):
    """Verifies ISO 32000 §7.5.6 append-only growth and CIDv1 chain continuity."""

    def test_monotonic_append_invariance(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "agora.pdf")

            # 1. Initialize Genesis Agora Document (Gen 0)
            genesis_rec, gen0_cid = initialize_agora_assembly(pdf_path)
            self.assertTrue(os.path.exists(pdf_path))
            self.assertTrue(is_valid_cidv1(gen0_cid))

            with open(pdf_path, "rb") as f:
                gen0_bytes = f.read()

            self.assertEqual(compute_cidv1_raw(gen0_bytes), gen0_cid)
            self.assertTrue(gen0_bytes.startswith(b"# coding: utf-8\nr\"\"\"%PDF-1.7\n"))

            # 2. Append Ratified Session (Gen 1)
            sk, pk = generate_keypair()
            prop1 = AgoraProposal(
                proposal_id="PROP_01",
                proposal_type=ProposalType.METABOLIC_TAX_RATE.value,
                title="Establish 5% Solar Pool Tax",
                statement="Redistribute ATP to subsidize dormant spores.",
                target_value=0.05,
                stake_atp=50,
                timestamp_utc="2026-09-09T13:00:00Z"
            )
            prop1.sign(sk)
            rec1 = ConsensusSettlementReceipt(
                generation=1,
                timestamp_utc="2026-09-09T13:00:00Z",
                proposal=prop1,
                status=ProposalStatus.RATIFIED.value,
                aye_weight=80,
                nay_weight=10,
                abstain_weight=5,
                total_atp_voted=6500,
                quorum_reached=True,
                supermajority_reached=True,
                gini_coefficient=0.22,
                hhi_index=0.18,
                multi_signatures=[prop1.signature_hex],
                prev_cid=gen0_cid
            )
            gen1_cid = grow_agora_page(pdf_path, rec1)
            self.assertTrue(is_valid_cidv1(gen1_cid))

            with open(pdf_path, "rb") as f:
                gen1_bytes = f.read()

            # STRICT APPEND-ONLY INVARIANT: after.startswith(before)
            self.assertTrue(
                gen1_bytes.startswith(gen0_bytes),
                "Append-only failure: gen1 bytes must start with exact gen0 bytes!"
            )
            self.assertEqual(compute_cidv1_raw(gen1_bytes), gen1_cid)

            # 3. Append Slashed Session (Gen 2)
            prop2 = AgoraProposal(
                proposal_id="PROP_02",
                proposal_type=ProposalType.THEOREM_CONGRUENCE.value,
                title="Subversive Theorem",
                statement="Claiming identity is paradox",
                pre_term="🤍",
                post_term="🖤",
                stake_atp=100,
                timestamp_utc="2026-09-09T14:00:00Z"
            )
            prop2.sign(sk)
            slash = SlashingReceipt(
                proposal_id="PROP_02",
                slashed_author_pk=pk,
                slashed_atp=100,
                bounty_paid_atp=50,
                proof_of_refutation="Contradiction: '🤍' -> '🤍', but '🖤' -> '🖤'",
                timestamp_utc="2026-09-09T14:00:00Z"
            )
            rec2 = ConsensusSettlementReceipt(
                generation=2,
                timestamp_utc="2026-09-09T14:00:00Z",
                proposal=prop2,
                status=ProposalStatus.SLASHED.value,
                aye_weight=0,
                nay_weight=40,
                abstain_weight=0,
                total_atp_voted=1600,
                quorum_reached=True,
                supermajority_reached=False,
                gini_coefficient=0.25,
                hhi_index=0.25,
                slashing_receipt=slash,
                multi_signatures=[prop2.signature_hex],
                prev_cid=gen1_cid
            )
            gen2_cid = grow_agora_page(pdf_path, rec2)
            self.assertTrue(is_valid_cidv1(gen2_cid))

            with open(pdf_path, "rb") as f:
                gen2_bytes = f.read()

            # STRICT APPEND-ONLY INVARIANT FOR GEN 2
            self.assertTrue(
                gen2_bytes.startswith(gen1_bytes),
                "Append-only failure: gen2 bytes must start with exact gen1 bytes!"
            )
            self.assertEqual(compute_cidv1_raw(gen2_bytes), gen2_cid)


class TestSubprocessAgoraQuine(unittest.TestCase):
    """Verifies that the compiled Agora PDF runs as a standalone Python CLI."""

    def test_subprocess_cli_execution(self):
        project_root = os.path.abspath(os.path.dirname(__file__))
        sub_env = {**os.environ, "PYTHONPATH": project_root}

        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "parliament.pdf")
            initialize_agora_assembly(pdf_path)

            # 1. python3 parliament.pdf --status
            p_status = subprocess.run(
                [sys.executable, pdf_path, "--status"],
                capture_output=True,
                text=True,
                env=sub_env
            )
            self.assertEqual(p_status.returncode, 0, p_status.stderr)
            self.assertIn("MYCELIAL CONSENSUS AGORA HUD", p_status.stdout)
            self.assertIn("Gini Inequality:", p_status.stdout)
            self.assertIn("Current CIDv1:      bafkrei", p_status.stdout)

            # 2. python3 parliament.pdf --lineage
            p_lineage = subprocess.run(
                [sys.executable, pdf_path, "--lineage"],
                capture_output=True,
                text=True,
                env=sub_env
            )
            self.assertEqual(p_lineage.returncode, 0, p_lineage.stderr)
            self.assertIn("CONSTITUTIONAL LINEAGE ACROSS 1 RATIFIED SESSIONS", p_lineage.stdout)

            # 3. python3 parliament.pdf --audit
            p_audit = subprocess.run(
                [sys.executable, pdf_path, "--audit"],
                capture_output=True,
                text=True,
                env=sub_env
            )
            self.assertEqual(p_audit.returncode, 0, p_audit.stderr)
            self.assertIn("ALL 1 AGORA SESSIONS CRYPTOGRAPHICALLY AUDITED & SOUND", p_audit.stdout)

    def test_insufficient_funds_rejected(self):
        engine = AgoraConsensusEngine()
        sk, pk = generate_keypair()
        engine.register_citizen(pk, initial_atp=50)

        # Tabling proposal needing 100 ATP should fail
        prop = AgoraProposal(
            proposal_id="PROP_TOO_EXPENSIVE",
            proposal_type=ProposalType.METABOLIC_TAX_RATE.value,
            title="Costly Proposal",
            statement="Should fail",
            stake_atp=100
        )
        prop.sign(sk)
        with self.assertRaises(ValueError) as ctx:
            engine.table_proposal(prop)
        self.assertIn("insufficient ATP", str(ctx.exception))

    def test_corrupt_manifest_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "corrupt_agora.pdf")
            initialize_agora_assembly(pdf_path)

            with open(pdf_path, "rb") as f:
                data = f.read()

            # Corrupt the receipt hash
            corrupt = data.replace(b'"receipt_hash": "', b'"receipt_hash": "corrupt_')
            with open(pdf_path, "wb") as f:
                f.write(corrupt)

            sk, _ = generate_keypair()
            prop = AgoraProposal(
                proposal_id="PROP_FAIL",
                proposal_type=ProposalType.METABOLIC_TAX_RATE.value,
                title="Fail",
                statement="Fail"
            )
            prop.sign(sk)
            rec = ConsensusSettlementReceipt(
                generation=1,
                timestamp_utc="2026-09-09T12:00:00Z",
                proposal=prop,
                status=ProposalStatus.RATIFIED.value,
                aye_weight=10,
                nay_weight=0,
                abstain_weight=0,
                total_atp_voted=100,
                quorum_reached=True,
                supermajority_reached=True,
                gini_coefficient=0.0,
                hhi_index=0.1
            )
            with self.assertRaises(ValueError) as ctx:
                grow_agora_page(pdf_path, rec)
            self.assertIn("mismatch", str(ctx.exception).lower())

if __name__ == "__main__":
    unittest.main()
