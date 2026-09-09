#!/usr/bin/env python3
# coding: utf-8
"""
test_epistemic_swarm.py — Test Suite for Engine #27: Epistemic Swarm Membrane & Symbiotic Quine Evolution.
Part of Project Black-Heart (%🖤).

Tests:
  1. test_spatial_grid_and_harvesting: Morphogen field kinetics and ATP harvesting.
  2. test_tombstone_gossip_cascade: Falsification broadcast, hop-count decay, and herd immunity.
  3. test_symbiotic_mating_compatibility_pass: Compatible quine crossover, genome inheritance, fuel endowment.
  4. test_symbiotic_mating_incompatibility_fail: Invariant S1 fail-closed rejection when parent carries tombstoned gene.
  5. test_swarm_agora_consensus: Quadratic voting, supermajority quorum, and canon ratification.
  6. test_starvation_and_extinction: Autophagy under environmental stress and fuel recycling.
  7. test_swarm_membrane_pdf_polyglot: ISO 32000 append-only update, vector HUD rendering, and Latin-1 Python script execution.
"""

from __future__ import annotations
import os
import sys
import json
import unittest
import tempfile
import subprocess
from typing import Tuple, List, Dict, Optional, Any

import crypto
from crypto import generate_keypair, public_key_from_secret
import glyph
from organism import Chromosome
import warrant_kernel
from warrant_kernel import EvidenceGrade, EdgeClaim, CounterexampleWitness
import controlled_forgetting
from controlled_forgetting import RetirementMode, EpistemicTombstoneRegistry
import epistemic_immune
from epistemic_immune import EpistemicOrganism, CounterexampleMetabolism
import epistemic_swarm
from epistemic_swarm import (
    SwarmMorphogenGrid, TombstoneSignal, CascadeReport,
    SwarmOrganismState, SwarmInoculationCascade,
    BilateralQuineSymbiosis, EpistemicIncompatibilityError,
    SwarmProposal, SwarmAxiom, SwarmAgoraCommons,
    SwarmMembrane, generate_swarm_membrane_pdf, append_swarm_membrane_hud
)


def _make_dummy_organism(oid: str, x: int, y: int, atp: int = 500) -> Tuple[EpistemicOrganism, SwarmOrganismState, str, str]:
    sk_hex, pk_hex = generate_keypair()

    c1 = Chromosome(gene_id="GENESIS_I", gene_name="Identity Gene", expression="I x", expected_normal_form="x", vital=True)
    c2 = Chromosome(gene_id="GENESIS_K", gene_name="Constant Gene", expression="K x y", expected_normal_form="x", vital=True)

    org = EpistemicOrganism(
        organism_id=oid,
        generation=0,
        chromosomes=[c1, c2],
        public_key_hex=pk_hex,
        atp_reserve=atp,
        active_axioms=["I x"]
    )
    st = SwarmOrganismState(
        organism_id=oid,
        x=x,
        y=y,
        heading=(1, 0),
        is_alive=True
    )
    return org, st, pk_hex, sk_hex


class TestEpistemicSwarm(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_spatial_grid_and_harvesting(self):
        """Verify Gray-Scott spatial kinetics and ATP energetic harvesting."""
        grid = SwarmMorphogenGrid(width=16, height=16)
        u0, v0 = grid.get_concentrations(4, 4)
        self.assertGreater(u0, 0.0)
        self.assertGreaterEqual(v0, 0.0)

        # Harvest ATP
        harvested = grid.harvest_atp(4, 4)
        self.assertGreaterEqual(harvested, 5)
        self.assertLessEqual(harvested, 40)

        # Step grid
        grid.step(dt=1.0)
        u1, v1 = grid.get_concentrations(4, 4)
        self.assertTrue(0.0 <= u1 <= 1.0)
        self.assertTrue(0.0 <= v1 <= 1.0)

        # Deposit biomass
        grid.deposit_biomass(4, 4, atp_amount=50)
        u2, v2 = grid.get_concentrations(4, 4)
        self.assertGreaterEqual(v2, v1)

    def test_tombstone_gossip_cascade(self):
        """Verify epidemic gossip propagation of tombstone defenses across spatial neighborhood."""
        swarm = SwarmMembrane(grid_width=16, grid_height=16)

        # Create 3 organisms close to each other
        org0, st0, pk0, sk0 = _make_dummy_organism("org-0", 2, 2, atp=300)
        org1, st1, pk1, sk1 = _make_dummy_organism("org-1", 3, 2, atp=300)
        org2, st2, pk2, sk2 = _make_dummy_organism("org-2", 4, 3, atp=300)

        swarm.add_organism(org0, st0, pk0, sk0)
        swarm.add_organism(org1, st1, pk1, sk1)
        swarm.add_organism(org2, st2, pk2, sk2)

        # Organism 0 metabolizes a counterexample for a flawed candidate
        claim, tombstone, gas_bounty = CounterexampleMetabolism.metabolize_counterexample(
            organism=org0,
            gene_id="GENESIS_K",
            rule_name="K I (S K)",
            input_fixture="x",
            expected_norm="x",
            actual_norm="y",
            atp_cost=20,
            secret_key_hex=sk0,
            public_key_hex=pk0
        )
        self.assertTrue(tombstone.verify_signature())

        # Broadcast tombstone through swarm membrane
        cascade = SwarmInoculationCascade.broadcast_tombstone(
            swarm=swarm,
            origin_id="org-0",
            tombstone=tombstone,
            max_hops=3,
            comm_radius=3
        )

        self.assertIn("org-1", cascade.organisms_inoculated)
        self.assertIn("org-2", cascade.organisms_inoculated)
        self.assertGreaterEqual(cascade.hops_reached, 1)
        self.assertGreater(cascade.reproduction_number_r0, 0.0)
        self.assertGreater(cascade.total_negative_space_pruned, 0.0)

        # Verify recipients ingested the defense and got bonus ATP
        self.assertIn(tombstone.target_id, org1.tombstone_registry.tombstones)
        self.assertIn(tombstone.target_id, org2.tombstone_registry.tombstones)
        self.assertEqual(org1.atp_reserve, 325)  # 300 + 25
        self.assertEqual(org2.atp_reserve, 325)

    def test_symbiotic_mating_compatibility_pass(self):
        """Verify successful bilateral quine mating between compatible parents."""
        swarm = SwarmMembrane(grid_width=16, grid_height=16)

        org_a, st_a, pk_a, sk_a = _make_dummy_organism("parent-A", 5, 5, atp=200)
        org_b, st_b, pk_b, sk_b = _make_dummy_organism("parent-B", 6, 5, atp=200)

        # Give Parent B an extra gene
        c_extra = Chromosome(gene_id="EXTRA_S", gene_name="Combinator S Gene", expression="S x y z", expected_normal_form="x z (y z)", vital=True)
        org_b.chromosomes.append(c_extra)
        org_b.active_axioms.append("S x y z")

        swarm.add_organism(org_a, st_a, pk_a, sk_a)
        swarm.add_organism(org_b, st_b, pk_b, sk_b)

        # Check compatibility
        compat, reason = BilateralQuineSymbiosis.check_mating_compatibility(org_a, org_b)
        self.assertTrue(compat)
        self.assertEqual(reason, "COMPATIBLE")

        # Execute mating
        child_org, child_st = BilateralQuineSymbiosis.recombine_and_mate(
            swarm=swarm,
            parent_a_id="parent-A",
            parent_b_id="parent-B",
            mating_cost_atp=60
        )

        self.assertTrue(child_org.organism_id.startswith("quine-child-"))
        self.assertEqual(child_org.generation, 1)
        self.assertEqual(org_a.atp_reserve, 140)  # 200 - 60
        self.assertEqual(org_b.atp_reserve, 140)
        self.assertGreater(child_org.atp_reserve, 80)
        self.assertEqual(st_a.children_count, 1)
        self.assertEqual(st_b.children_count, 1)

        # Child inherits vital genes and active axioms from both parents
        gene_ids = [c.gene_id for c in child_org.chromosomes]
        self.assertIn("GENESIS_I", gene_ids)
        self.assertIn("GENESIS_K", gene_ids)
        self.assertIn("EXTRA_S", gene_ids)
        self.assertIn("S x y z", child_org.active_axioms)

    def test_symbiotic_mating_incompatibility_fail(self):
        """Verify Invariant S1: fail-closed rejection when parent contains a refuted/tombstoned gene."""
        swarm = SwarmMembrane(grid_width=16, grid_height=16)

        org_a, st_a, pk_a, sk_a = _make_dummy_organism("parent-A", 5, 5, atp=200)
        org_b, st_b, pk_b, sk_b = _make_dummy_organism("parent-B", 6, 5, atp=200)

        # Parent A actively uses "I x"
        # Parent B has tombstoned "I x"
        claim_b, tomb_b, gas_b = CounterexampleMetabolism.metabolize_counterexample(
            organism=org_b,
            gene_id="GENESIS_I",
            rule_name="I x",
            input_fixture="x",
            expected_norm="x",
            actual_norm="divergence",
            atp_cost=10,
            secret_key_hex=sk_b,
            public_key_hex=pk_b
        )

        swarm.add_organism(org_a, st_a, pk_a, sk_a)
        swarm.add_organism(org_b, st_b, pk_b, sk_b)

        # Compatibility check must fail
        compat, reason = BilateralQuineSymbiosis.check_mating_compatibility(org_a, org_b)
        self.assertFalse(compat)
        self.assertIn("is tombstoned/refuted", reason)

        # Attempting to mate must raise EpistemicIncompatibilityError
        with self.assertRaises(EpistemicIncompatibilityError):
            BilateralQuineSymbiosis.recombine_and_mate(
                swarm=swarm,
                parent_a_id="parent-A",
                parent_b_id="parent-B",
                mating_cost_atp=60
            )

    def test_swarm_agora_consensus(self):
        """Verify Swarm Agora parliamentary voting, supermajority quorum, and canon ratification."""
        swarm = SwarmMembrane(grid_width=16, grid_height=16)

        org0, st0, pk0, sk0 = _make_dummy_organism("org-0", 1, 1, atp=300)
        org1, st1, pk1, sk1 = _make_dummy_organism("org-1", 2, 1, atp=300)
        org2, st2, pk2, sk2 = _make_dummy_organism("org-2", 3, 1, atp=300)

        swarm.add_organism(org0, st0, pk0, sk0)
        swarm.add_organism(org1, st1, pk1, sk1)
        swarm.add_organism(org2, st2, pk2, sk2)

        # Table a sound identity: S K K x == x
        prop = SwarmAgoraCommons.table_proposal(
            swarm=swarm,
            author_id="org-0",
            expression="S K K x",
            expected_normal_form="x",
            evidence_grade="A",
            stake_atp=50
        )
        self.assertEqual(prop.status, "PENDING")
        self.assertEqual(org0.atp_reserve, 250)

        # Vote and settle
        ratified, reason = SwarmAgoraCommons.vote_and_settle(swarm, prop)
        self.assertTrue(ratified)
        self.assertEqual(prop.status, "RATIFIED")
        self.assertEqual(len(swarm.canon), 1)
        self.assertEqual(swarm.canon[0].expression, "S K K x")

        # Author gets back stake plus bounty (+80 total, 250 + 80 = 330)
        self.assertEqual(org0.atp_reserve, 330)

        # All living organisms received the ratified axiom
        self.assertIn("S K K x", org0.active_axioms)
        self.assertIn("S K K x", org1.active_axioms)
        self.assertIn("S K K x", org2.active_axioms)

        # Table an unsound identity: S K x == x (which is false in combinatory logic)
        unsound_prop = SwarmAgoraCommons.table_proposal(
            swarm=swarm,
            author_id="org-1",
            expression="S K x",
            expected_normal_form="x",
            evidence_grade="A",
            stake_atp=50
        )
        ratified_unsound, reason_unsound = SwarmAgoraCommons.vote_and_settle(swarm, unsound_prop)
        self.assertFalse(ratified_unsound)
        self.assertEqual(unsound_prop.status, "REJECTED")

    def test_starvation_and_extinction(self):
        """Verify dynamic starvation autophagy and extinction recycling in stressed organisms."""
        swarm = SwarmMembrane(grid_width=16, grid_height=16)

        # Create organism with low ATP
        org, st, pk, sk = _make_dummy_organism("stressed-org", 0, 0, atp=70)
        # Add non-vital bloated gene for autophagy reclamation
        bloated = Chromosome(
            gene_id="BLOATED_GENE",
            gene_name="Bloated Gene",
            expression="K (K (K I)) (S S)",
            expected_normal_form="K (K I)",
            vital=False
        )
        org.chromosomes.append(bloated)
        swarm.add_organism(org, st, pk, sk)

        # Step simulation
        res = swarm.step(num_ticks=1)
        self.assertEqual(res["autophagies"], 1)

        # Drive ATP to 0 and verify extinction (living cost is 5, so 5 - 5 = 0 <= 0)
        org.atp_reserve = 5
        res2 = swarm.step(num_ticks=1)
        self.assertFalse(st.is_alive)
        self.assertGreaterEqual(res2["extinctions"], 1)

    def test_swarm_membrane_pdf_polyglot(self):
        """Verify ISO 32000 append-only polyglot generation and Python runner execution."""
        swarm = SwarmMembrane(grid_width=16, grid_height=16)
        org0, st0, pk0, sk0 = _make_dummy_organism("org-0", 2, 2, atp=400)
        org1, st1, pk1, sk1 = _make_dummy_organism("org-1", 4, 4, atp=400)
        swarm.add_organism(org0, st0, pk0, sk0)
        swarm.add_organism(org1, st1, pk1, sk1)

        pdf_path = os.path.join(self.temp_dir.name, "swarm_membrane.pdf")
        pdf_bytes = generate_swarm_membrane_pdf(swarm, pdf_path)

        self.assertTrue(os.path.exists(pdf_path))
        self.assertTrue(pdf_bytes.startswith(b"#!" + sys.executable.encode("latin-1")))
        self.assertIn(b"%PDF-1.7", pdf_bytes)
        self.assertIn(b"SWARM_MEMBRANE_MANIFEST:", pdf_bytes)

        # Test ISO 32000 incremental update
        swarm.step(num_ticks=2)
        append_path = os.path.join(self.temp_dir.name, "swarm_membrane_updated.pdf")
        append_bytes = append_swarm_membrane_hud(pdf_bytes, append_path, swarm)

        # ISO 32000 Invariant: byte prefix must be identical
        self.assertTrue(append_bytes.startswith(pdf_bytes))

        # Test direct execution of the polyglot PDF via Python
        cmd = [sys.executable, pdf_path]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, f"Polyglot execution failed: {proc.stderr}")
        self.assertIn("EPISTEMIC SWARM MEMBRANE AUDITOR", proc.stdout)
        self.assertIn("Swarm membrane state and cryptographic signatures verified", proc.stdout)


if __name__ == "__main__":
    unittest.main()
