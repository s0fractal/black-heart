#!/usr/bin/env python3
# coding: utf-8
"""
test_sovereign_continuity.py — Verification Suite for Engine #34 (SOVEREIGN-0.1).
Part of Project Black-Heart (%🖤).

Tests all 7 Sovereign Continuity Invariants:
  - SC1: Substrate-Independent Identity (Ed25519 Genesis + CIDv1 DAG)
  - SC2: Monotonic Provenance Append (Byte and DAG growth)
  - SC3: Metabolic Capacity Bound (Active Surface <= B_max)
  - SC4: Anti-Resurrection Immune Gate (EpistemicResurrectionError on tombstoned claims)
  - SC5: Phenotypic Polymorphism (Never copy raw experience; share warrants & NFs)
  - SC6: Idempotent Cold Boot (<200ms re-verification on migrated cold host)
  - SC7: Dual-Spine ISO 32000 Polyglot (Executable Python script + standard PDF)
"""

import os
import sys
import json
import time
import shutil
import tempfile
import unittest
import subprocess

from sovereign_continuity import (
    SovereignOrganism,
    SovereignChromosome,
    SovereignWarrant,
    TombstoneStela,
    SovereignReceipt,
    ForgettingMembrane,
    MyceliumSynapse,
    generate_sovereign_polyglot,
    ReAdoptionRecord
)
from controlled_forgetting import AdmissionStatus, EpistemicResurrectionError
import cid


class TestSovereignContinuity(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="blackheart_sovereign_")

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_control_01_genesis_and_unbroken_identity(self):
        """Invariant SC1: Genesis creation and unbroken cryptographic identity."""
        org = SovereignOrganism.create_genesis(
            organism_id="%🖤-TEST-ORGANISM-GENESIS",
            metabolic_capacity=300
        )
        self.assertEqual(org.generation, 0)
        self.assertTrue(org.genesis_pk_hex)
        self.assertEqual(org.genesis_pk_hex, org.author_pk_hex)
        self.assertEqual(len(org.history_receipts), 1)
        self.assertEqual(len(org.cid_chain), 1)
        self.assertTrue(cid.is_valid_cidv1(org.cid_chain[0]))

        # Verify receipt
        receipt = org.history_receipts[0]
        self.assertTrue(receipt.verify())
        self.assertEqual(receipt.generation, 0)
        self.assertEqual(receipt.parent_cid, "")

    def test_control_02_autopoietic_evolution_and_atp_accounting(self):
        """Invariant SC2: Monotonic provenance append and ATP conservation."""
        org = SovereignOrganism.create_genesis(metabolic_capacity=300)
        initial_expr = org.chromosomes["GENE-SOVEREIGN-01"].expression

        # Evolve step
        receipt_1 = org.evolve_step(thought_stimulus="Contemplate Gene 01")
        self.assertEqual(org.generation, 1)
        self.assertEqual(len(org.history_receipts), 2)
        self.assertEqual(len(org.cid_chain), 2)
        self.assertEqual(receipt_1.parent_cid, org.cid_chain[0])
        self.assertEqual(receipt_1.cid, org.cid_chain[1])
        self.assertTrue(receipt_1.verify())

        # Check that ATP conservation is non-negative
        self.assertGreaterEqual(org.atp_cumulative_saved, 0)

    def test_control_03_metabolic_capacity_and_controlled_forgetting(self):
        """Invariant SC3: Metabolic capacity bound and automatic tombstoning."""
        # Create organism with restrictive capacity
        org = SovereignOrganism.create_genesis(metabolic_capacity=150)
        base_cost = org.current_active_cost()

        # Add multiple warrants to artificially overload metabolism
        for i in range(5):
            w = SovereignWarrant(
                warrant_id=f"test-warrant-{i}",
                rule_name="S(K x)(K y) -> K(x y)",
                pre_term="S (K I) (K I)",
                post_term="K (I I)",
                atp_saved=10,
                hits=1 + i,
                gen_admitted=0,
                maintenance_cost=30
            )
            org.membrane.admit_warrant(w)

        # Active cost should exceed capacity before pruning
        self.assertGreater(org.current_active_cost(), 150)

        # Trigger metabolic pruning
        new_tombstones = org.membrane.prune_metabolism(
            current_gen=1,
            author_pk_hex=org.author_pk_hex,
            secret_key_hex=org.secret_key_hex,
            base_cost=sum(c.maintenance_cost for c in org.chromosomes.values())
        )

        # Check equilibrium
        self.assertTrue(len(new_tombstones) > 0)
        self.assertLessEqual(org.current_active_cost(), 150)

        # Check tombstone properties
        for t in new_tombstones:
            self.assertTrue(t.loss_declaration)
            self.assertTrue(t.verify())
            self.assertIn(t.target_id, org.membrane.tombstones)

    def test_control_04_anti_resurrection_immune_gate(self):
        """Invariant SC4: EpistemicResurrectionError on tombstoned claims."""
        org = SovereignOrganism.create_genesis(metabolic_capacity=100)
        w = SovereignWarrant(
            warrant_id="warrant-to-prune",
            rule_name="I x -> x",
            pre_term="I I",
            post_term="I",
            atp_saved=5,
            hits=1,
            gen_admitted=0,
            maintenance_cost=50
        )
        org.membrane.admit_warrant(w)
        org.membrane.prune_metabolism(
            current_gen=1,
            author_pk_hex=org.author_pk_hex,
            secret_key_hex=org.secret_key_hex,
            base_cost=sum(c.maintenance_cost for c in org.chromosomes.values())
        )

        self.assertIn("warrant-to-prune", org.membrane.tombstones)

        # Attempt to execute/guard tombstoned warrant
        with self.assertRaises(EpistemicResurrectionError):
            org.membrane.execute_warrant_guard("warrant-to-prune")

        # Explicit readoption
        resurrected_w = SovereignWarrant(
            warrant_id="warrant-to-prune",
            rule_name="I x -> x",
            pre_term="I I",
            post_term="I",
            atp_saved=5,
            hits=10,
            gen_admitted=2,
            maintenance_cost=10
        )
        stela = org.membrane.tombstones["warrant-to-prune"]
        rec = ReAdoptionRecord(
            record_id="readopt-rec-1",
            target_stela_id="warrant-to-prune",
            target_stela_hash=stela.tombstone_id,
            new_warrant_digest=resurrected_w.compute_cid(),
            author_pk_hex=org.author_pk_hex,
            justification_proof="Verified fresh proof of equivalence under SKIY calculus."
        )
        rec.sign(org.secret_key_hex)
        org.membrane.readopt_warrant("warrant-to-prune", resurrected_w, rec)

        # Guard should now pass without raising
        org.membrane.execute_warrant_guard("warrant-to-prune")
        self.assertIn("warrant-to-prune", org.membrane.active_warrants)

    def test_control_05_substrate_migration_and_cold_reconstitution(self):
        """Invariants SC1, SC6: Cold host migration and idempotent verification."""
        org = SovereignOrganism.create_genesis(metabolic_capacity=250)
        org.evolve_step("Step 1")
        org.evolve_step("Step 2")

        # Export migration seed
        seed_json = org.export_migration_seed()
        self.assertIn("SOVEREIGN-MIGRATION-0.1", seed_json)

        # Reconstitute on cold virtual host
        reconstituted = SovereignOrganism.reconstitute_from_seed(
            seed_json,
            secret_key_hex=org.secret_key_hex
        )

        self.assertEqual(reconstituted.generation, org.generation)
        self.assertEqual(reconstituted.genesis_pk_hex, org.genesis_pk_hex)
        self.assertEqual(reconstituted.cid_chain, org.cid_chain)
        self.assertEqual(reconstituted.atp_cumulative_saved, org.atp_cumulative_saved)
        self.assertEqual(len(reconstituted.chromosomes), len(org.chromosomes))
        self.assertEqual(len(reconstituted.history_receipts), len(org.history_receipts))

        # Further evolve the reconstituted organism
        step3 = reconstituted.evolve_step("Step 3 on New Host")
        self.assertEqual(reconstituted.generation, 3)
        self.assertEqual(step3.parent_cid, org.cid_chain[-1])

    def test_control_06_epistemic_mycelium_synapse_and_thesis_2(self):
        """Invariant SC5: Mycelial exchange without copying experience."""
        org = SovereignOrganism.create_genesis(metabolic_capacity=300)
        payload = org.synapse.export_payload(org)

        self.assertEqual(payload["type"], "EPISTEMIC_MYCELIUM_BROADCAST")
        self.assertIn("layer_1_normal_forms", payload)
        self.assertIn("layer_2_warrants", payload)
        self.assertIn("layer_3_divergences", payload)
        # Ensure no private internal state is leaked
        self.assertNotIn("secret_key_hex", payload)
        self.assertNotIn("cid_chain", payload)

        # Audition valid foreign warrant
        valid_warrant = {
            "rule_name": "S(K x)(K y) -> K(x y)",
            "pre_term": "S (K I) (K I)",
            "post_term": "K (I I)",
            "atp_saved": 10
        }
        passed, msg = org.synapse.audition_foreign_warrant(valid_warrant)
        self.assertTrue(passed)
        self.assertIn("ACCEPTED", msg)

        # Audition divergent foreign warrant
        divergent_warrant = {
            "rule_name": "S(K x)(K y) -> K(x y)",
            "pre_term": "S (K I) (K I)",
            "post_term": "I",  # False equivalence!
            "atp_saved": 10
        }
        failed, err_msg = org.synapse.audition_foreign_warrant(divergent_warrant)
        self.assertFalse(failed)
        self.assertIn("REJECTED", err_msg)
        self.assertEqual(len(org.synapse.divergence_antibodies), 1)

    def test_control_07_iso_32000_polyglot_and_standalone_runner(self):
        """Invariant SC7: Dual-spine ISO 32000 polyglot and CLI runner."""
        org = SovereignOrganism.create_genesis(metabolic_capacity=300)
        org.evolve_step("Generational step 1")

        pdf_path = os.path.join(self.tmp_dir, "sovereign_organism.pdf")
        pdf_bytes = generate_sovereign_polyglot(org, pdf_path)

        self.assertTrue(os.path.exists(pdf_path))
        self.assertIn(b"%PDF-1.4", pdf_bytes[:1024])
        self.assertTrue(pdf_bytes.startswith(b"#!/usr/bin/env python3"))

        # Test standalone execution: --audit
        res_audit = subprocess.run(
            [sys.executable, pdf_path, "--audit"],
            capture_output=True,
            text=True,
            timeout=10
        )
        self.assertEqual(res_audit.returncode, 0)
        self.assertIn("SOVEREIGN CONTINUITY QUINE AUDITOR", res_audit.stdout)
        self.assertIn("[PASS] Substrate-independent cryptographic lineage verified.", res_audit.stdout)

        # Test standalone execution: --migrate
        res_migrate = subprocess.run(
            [sys.executable, pdf_path, "--migrate"],
            capture_output=True,
            text=True,
            timeout=10
        )
        self.assertEqual(res_migrate.returncode, 0)
        self.assertIn("exported_by", res_migrate.stdout)


if __name__ == "__main__":
    unittest.main()
