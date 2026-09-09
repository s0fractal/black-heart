#!/usr/bin/env python3
"""
test_mycelium.py — Test Suite for Epistemic Mycelium Swarm, Warrants & Immune Defense.
Part of Project Black-Heart (%🖤).

Tests:
  1. Church-Rosser NormalFormEntry creation, cryptographic signing, and replay verification.
  2. Warrant creation from MetamorphicTransitionReceipt, peer endorsements, and tamper detection.
  3. DivergenceRecord negative knowledge creation, counterexample replay, and immunity.
  4. EpistemicRegistry persistence, Merkle root calculation, and lookup.
  5. LocalImmuneEvaluator: Audition and successful adoption of beneficial warrant.
  6. LocalImmuneEvaluator: Rejection of invalid/divergent warrant with counterexample minting.
  7. P2P Epistemic Mesh Gossip: HTTP daemon gossip synchronization between two autonomous nodes.
"""

import unittest
import os
import sys
import tempfile
import json
import time

from crypto import generate_keypair, public_key_from_secret
from glyph import parse, evaluate, S, K, I, App
from organism import Organism, Chromosome, create_genesis_organism
from metamorphosis import (
    contemplate_and_evolve,
    FrozenEvaluator,
    ExperimentLog,
    MetamorphicTransitionReceipt,
    MutationVerdict
)
from mycelium import (
    NormalFormEntry,
    Warrant,
    WarrantEndorsement,
    WarrantEpistemicGrade,
    DivergenceRecord,
    EpistemicRegistry,
    LocalImmuneEvaluator,
    export_warrant_from_receipt,
    export_divergences_from_log
)
from mesh import (
    start_epistemic_daemon,
    sync_epistemic_from_remote_peer
)

class TestMycelium(unittest.TestCase):

    def setUp(self):
        self.sk_a, self.pk_a = generate_keypair()
        self.sk_b, self.pk_b = generate_keypair()

    # ========================================================================
    # 1. Normal Form Entry Tests
    # ========================================================================
    def test_normal_form_entry_creation_and_verification(self):
        """Church-Rosser normal forms must be signed, verifiable, and reject tampering."""
        expr = "🌿 🖤 🖤 🤍" # S K K I -> (K I) (K I) -> I
        entry = NormalFormEntry.create_and_sign(expr, self.sk_a, atp_budget=100)

        self.assertEqual(entry.nf_expr, "🤍")
        self.assertTrue(entry.verify(replay_if_untrusted=True))

        # Tampered normal form string fails verification
        tampered_nf = NormalFormEntry.from_dict(entry.to_dict())
        tampered_nf.nf_expr = "🖤"
        self.assertFalse(tampered_nf.verify())

        # Tampered signature fails verification
        tampered_sig = NormalFormEntry.from_dict(entry.to_dict())
        tampered_sig.signature_hex = "aa" * 64
        self.assertFalse(tampered_sig.verify())

    # ========================================================================
    # 2. Warrant Creation & Peer Endorsements
    # ========================================================================
    def test_warrant_creation_and_peer_endorsements(self):
        """Warrants must wrap metamorphic receipts, support peer endorsements, and verify fail-closed."""
        p = create_genesis_organism()
        p.chromosomes.append(Chromosome('OPT', 'Optimizer', '🌿 (🖤 (🌿 🤍)) 🤍', '🌿 🤍', 100))
        p.organism_hash = p.compute_hash()

        succ, log, receipt = contemplate_and_evolve(p)
        self.assertIsNotNone(receipt)

        warrant = export_warrant_from_receipt(receipt, self.sk_a)
        self.assertTrue(warrant.verify())
        self.assertEqual(warrant.author_pk_hex, self.pk_a)
        self.assertEqual(warrant.rule_name, receipt.rule_name)

        # Peer Node B endorses warrant
        end = warrant.add_endorsement(self.sk_b, local_delta_atp=receipt.atp_saved)
        self.assertEqual(end.endorser_pk_hex, self.pk_b)
        self.assertTrue(warrant.verify())

        # Tampered rule name breaks warrant ID derivation
        w_tamp = Warrant.from_dict(warrant.to_dict())
        w_tamp.rule_name = "RULE_CONSTANT_DISTRIBUTION_ELIM"
        self.assertFalse(w_tamp.verify())

    # ========================================================================
    # 3. Divergence Record & Negative Knowledge
    # ========================================================================
    def test_divergence_record_creation_and_counterexample_replay(self):
        """Divergence records must capture exact counterexamples and verify under replay."""
        # Testing swapping operands: target K vs candidate I on input K
        # K K -> K, I K -> K. If we use K vs I on input I: K I -> K, I I -> I
        target = "🖤"
        cand = "🤍"
        div = DivergenceRecord.create_and_sign(
            rule_name="MUTATION_OPERAND_SWAP",
            target_expr=target,
            cand_expr=cand,
            counterexample_input="🤍",
            expected_out="🖤 🤍",
            actual_out="🤍",
            reporter_sk=self.sk_a
        )
        self.assertTrue(div.verify(replay_counterexample=True))

        # Tampering with counterexample input fails verification
        div_tamp = DivergenceRecord.from_dict(div.to_dict())
        div_tamp.counterexample_input = "🖤"
        self.assertFalse(div_tamp.verify())

    # ========================================================================
    # 4. Epistemic Registry Persistence & Merkle Root
    # ========================================================================
    def test_epistemic_registry_persistence_and_merkle_root(self):
        """EpistemicRegistry stores, computes Merkle roots, and round-trips via JSON."""
        reg = EpistemicRegistry()
        nf = NormalFormEntry.create_and_sign("🤍 🤍", self.sk_a)
        reg.add_normal_form(nf)

        # Create a warrant
        receipt = MetamorphicTransitionReceipt(
            parent_hash="0"*64,
            successor_hash="1"*64,
            gene_id="GENE-01",
            site_address=("L",),
            rule_name="S(K I) -> I",
            pre_term="🌿 (🖤 🤍)",
            post_term="🤍",
            atp_saved=-2,
            size_saved=-2,
            fixtures_fingerprint="fp"*16,
            experiment_id="exp01"
        )
        w = export_warrant_from_receipt(receipt, self.sk_a)
        reg.add_warrant(w)

        summary = reg.summary()
        self.assertEqual(summary["normal_forms_count"], 1)
        self.assertEqual(summary["warrants_count"], 1)
        self.assertNotEqual(summary["warrant_merkle_root"], "0" * 64)

        with tempfile.NamedTemporaryFile("w", delete=False) as f:
            tmp_name = f.name

        try:
            reg.save_to_file(tmp_name)
            loaded = EpistemicRegistry.load_from_file(tmp_name)
            self.assertEqual(loaded.summary(), summary)
            self.assertIn(w.warrant_id, loaded.warrants)
        finally:
            if os.path.exists(tmp_name):
                os.remove(tmp_name)

    # ========================================================================
    # 5. Local Immune Evaluator: Successful Adoption
    # ========================================================================
    def test_local_immune_evaluator_audition_and_adoption(self):
        """Organism auditions external warrant, proves semantic invariance locally, and adopts."""
        p = create_genesis_organism()
        p.chromosomes = [
            Chromosome('OPT', 'Signal Compressor', '(🌿 (🖤 (🌿 🤍)) 🤍) Signal', '(🌿 🤍) Signal', 100)
        ]
        p.organism_hash = p.compute_hash()
        self.assertTrue(p.verify())

        # External node produced a valid warrant for S(K (S I)) I -> S I
        receipt = MetamorphicTransitionReceipt(
            parent_hash="0"*64,
            successor_hash="1"*64,
            gene_id="OPT",
            site_address=(),
            rule_name="S(K x)I -> x",
            pre_term="🌿 (🖤 (🌿 🤍)) 🤍",
            post_term="🌿 🤍",
            atp_saved=-2,
            size_saved=-2,
            fixtures_fingerprint=FrozenEvaluator().fixtures_fingerprint,
            experiment_id="exp_w"
        )
        warrant = export_warrant_from_receipt(receipt, self.sk_b)

        immune = LocalImmuneEvaluator()
        verdict = immune.audition_warrant(p, warrant, self.sk_a)

        self.assertTrue(verdict.adopted)
        self.assertEqual(verdict.reason, "SUCCESSFULLY_ADOPTED")
        self.assertIsNotNone(verdict.successor_organism)
        self.assertEqual(verdict.successor_organism.generation, p.generation + 1)
        self.assertTrue(verdict.successor_organism.verify())
        self.assertIsNotNone(verdict.endorsement)
        self.assertEqual(len(warrant.endorsements), 1)

    # ========================================================================
    # 6. Local Immune Evaluator: Rejection & Divergence Minting
    # ========================================================================
    def test_local_immune_evaluator_rejection_and_counterexample(self):
        """Warrant that breaks local semantics or metabolic reduction is rejected with counterexample."""
        p = create_genesis_organism()
        p.chromosomes = [
            Chromosome('SWAP', 'Swap test', '🌿 (🌿 🖤) 🌿', '🌿 (🌿 🖤) 🌿', 100)
        ]
        p.organism_hash = p.compute_hash()
        self.assertTrue(p.verify())

        # Forged/exploratory warrant claiming operand swap is valid
        receipt = MetamorphicTransitionReceipt(
            parent_hash="0"*64,
            successor_hash="1"*64,
            gene_id="SWAP",
            site_address=(),
            rule_name="MUTATION_OPERAND_SWAP",
            pre_term="🌿 (🌿 🖤) 🌿",
            post_term="🌿 (🌿 (🌿 🖤))",
            atp_saved=-1,
            size_saved=0,
            fixtures_fingerprint=FrozenEvaluator().fixtures_fingerprint,
            experiment_id="exp_swap"
        )
        warrant = export_warrant_from_receipt(receipt, self.sk_b)

        immune = LocalImmuneEvaluator()
        verdict = immune.audition_warrant(p, warrant, self.sk_a)

        self.assertFalse(verdict.adopted)
        self.assertIn("REJECTED", verdict.reason)
        self.assertIsNotNone(verdict.divergence_record)
        self.assertTrue(verdict.divergence_record.verify())

    # ========================================================================
    # 7. P2P Epistemic Mesh Gossip Sync
    # ========================================================================
    def test_p2p_epistemic_mesh_gossip(self):
        """Two nodes sync warrants, normal forms, and divergences over HTTP gossip."""
        reg_a = EpistemicRegistry()
        reg_b = EpistemicRegistry()

        nf = NormalFormEntry.create_and_sign("🌿 🖤 🖤 🤍", self.sk_a)
        reg_a.add_normal_form(nf)

        receipt = MetamorphicTransitionReceipt(
            parent_hash="0"*64,
            successor_hash="1"*64,
            gene_id="GENE-01",
            site_address=(),
            rule_name="S(K I) -> I",
            pre_term="🌿 (🖤 🤍)",
            post_term="🤍",
            atp_saved=-2,
            size_saved=-2,
            fixtures_fingerprint=FrozenEvaluator().fixtures_fingerprint,
            experiment_id="exp01"
        )
        w = export_warrant_from_receipt(receipt, self.sk_a)
        reg_a.add_warrant(w)

        # Start Node A daemon on port 8931
        srv = start_epistemic_daemon(reg_a, port=8931)
        try:
            # Sync Node B from Node A
            counts = sync_epistemic_from_remote_peer(reg_b, "http://127.0.0.1:8931")
            self.assertEqual(counts["warrants"], 1)
            self.assertEqual(counts["normal_forms"], 1)

            # Node B now possesses the warrant and normal form
            self.assertIn(w.warrant_id, reg_b.warrants)
            self.assertIn(nf.term_hash, reg_b.normal_forms)
            self.assertEqual(reg_b.summary()["warrant_merkle_root"], reg_a.summary()["warrant_merkle_root"])
        finally:
            srv.shutdown()
            srv.server_close()

    # ========================================================================
    # 8. Epistemic Grade Taxonomy (Review 10 Fix)
    # ========================================================================
    def test_warrant_epistemic_grade_separation(self):
        """Warrants must distinguish RULE_DERIVED, LOCALLY_TESTED, and PROPOSED."""
        # Algebraic rule -> RULE_DERIVED
        rec_alg = MetamorphicTransitionReceipt(
            parent_hash="0"*64,
            successor_hash="1"*64,
            gene_id="G1",
            site_address=(),
            rule_name="I x -> x",
            pre_term="🤍 y",
            post_term="y",
            atp_saved=-1,
            size_saved=-1,
            fixtures_fingerprint="fp1",
            experiment_id="e1"
        )
        w_alg = export_warrant_from_receipt(rec_alg, self.sk_a)
        self.assertEqual(w_alg.epistemic_grade, WarrantEpistemicGrade.RULE_DERIVED.value)
        self.assertTrue(w_alg.verify())

        # Speculative trial mutation without measured savings -> PROPOSED
        rec_trial = MetamorphicTransitionReceipt(
            parent_hash="0"*64,
            successor_hash="1"*64,
            gene_id="G2",
            site_address=(),
            rule_name="MUTATION_OPERAND_SWAP",
            pre_term="🌿 a b",
            post_term="a",
            atp_saved=-2,  # nominal trial value <= 0
            size_saved=-1,
            fixtures_fingerprint="fp2",
            experiment_id="e2"
        )
        w_trial = export_warrant_from_receipt(rec_trial, self.sk_a)
        self.assertEqual(w_trial.epistemic_grade, WarrantEpistemicGrade.PROPOSED.value)
        self.assertTrue(w_trial.verify())

if __name__ == "__main__":
    unittest.main()
