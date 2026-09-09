#!/usr/bin/env python3
"""
test_colony.py — Comprehensive Test Suite for Living Colony Ecosystem & Neuro-Symbolic Oracle.
Part of Project Black-Heart (%🖤).

Tests:
  1. Colony genesis initialization, initial roster vitality, and ledger genesis.
  2. Basal metabolism, energy depletion, and dormant spore transition.
  3. Mycelial warrant audition & peer adoption within the colony.
  4. Neuro-symbolic oracle hypothesis verification & ATP bounty award.
  5. Dialectical sexual recombination between wealthy colony members.
  6. Multi-epoch simulation, Merkle link continuity, and living ledger settlement.
  7. Standalone ColonyPolyglotCompiler: PDF compilation and runner execution.
"""

import unittest
import os
import sys
import tempfile
import json
import io
import contextlib

from crypto import generate_keypair
from organism import Organism, Chromosome, create_genesis_organism
from metamorphosis import FrozenEvaluator, MetamorphicTransitionReceipt
from mycelium import export_warrant_from_receipt
from colony import (
    Colony,
    OrganismState,
    OrganismStatus,
    EpochRecord,
    NeuroSymbolicOracle,
    ColonyPolyglotCompiler
)

class TestColonyEcosystem(unittest.TestCase):

    def setUp(self):
        self.sk, self.pk = generate_keypair()

    # ========================================================================
    # 1. Genesis Initialization
    # ========================================================================
    def test_genesis_colony_initialization_and_vitality(self):
        """Colony must initialize with viable population, substrate bank, and ledger genesis."""
        colony = Colony.create_genesis_colony("Test Biome", initial_organisms=3, initial_substrate_atp=5000)

        self.assertEqual(len(colony.population), 3)
        self.assertEqual(len(colony.active_organisms()), 3)
        self.assertEqual(len(colony.dormant_spores()), 0)
        self.assertEqual(colony.substrate_atp, 5000)
        self.assertGreaterEqual(len(colony.ledger.blocks), 1)

        # All initial active organisms must pass verification
        for st in colony.active_organisms():
            self.assertTrue(st.organism.verify())

    # ========================================================================
    # 2. Basal Metabolism & Spore Dormancy
    # ========================================================================
    def test_basal_metabolism_and_spore_dormancy(self):
        """Exhausted organisms must transition to dormant spores without loss of state."""
        colony = Colony.create_genesis_colony("Starvation Biome", initial_organisms=1, initial_substrate_atp=0)
        org_state = colony.population[0]
        org_state.energy_atp = 2  # Low ATP, will be exhausted by basal burn

        # Step epoch with zero solar influx
        rec = colony.step_epoch(solar_influx_atp=0)

        self.assertEqual(rec.active_count, 0)
        self.assertEqual(rec.spore_count, 1)
        self.assertEqual(org_state.status, OrganismStatus.DORMANT_SPORE)
        self.assertIsNotNone(org_state.spore_checkpoint)
        self.assertIn("checkpoint_hash", org_state.spore_checkpoint)

    # ========================================================================
    # 3. Mycelial Warrant Audition within Colony
    # ========================================================================
    def test_mycelial_warrant_audition_within_colony(self):
        """Colony members must audition new Warrants in the registry and adopt optimizations."""
        colony = Colony("Audition Biome", substrate_atp=1000)

        # Organism has optimizable Signal Compressor gene
        org = create_genesis_organism(generation=0)
        org.chromosomes = [
            Chromosome('OPT', 'Signal Compressor', '(🌿 (🖤 (🌿 🤍)) 🤍) Signal', '(🌿 🤍) Signal', 100)
        ]
        org.organism_hash = org.compute_hash()
        self.assertTrue(org.verify())
        st = OrganismState(organism=org, energy_atp=500)
        colony.population.append(st)

        # Pre-seed registry with warrant from an external author
        receipt = MetamorphicTransitionReceipt(
            parent_hash="0"*64,
            successor_hash="1"*64,
            gene_id="OPT",
            site_address=('L',),
            rule_name="S(K x)I -> x",
            pre_term="🌿 (🖤 (🌿 🤍)) 🤍",
            post_term="🌿 🤍",
            atp_saved=-2,
            size_saved=-2,
            fixtures_fingerprint=FrozenEvaluator().fixtures_fingerprint,
            experiment_id="exp_w"
        )
        sk_ext, _ = generate_keypair()
        warrant = export_warrant_from_receipt(receipt, sk_ext)
        colony.registry.add_warrant(warrant)

        # Step epoch: organism should audition and adopt warrant
        rec = colony.step_epoch(solar_influx_atp=100)
        self.assertGreaterEqual(rec.warrants_adopted, 1)
        self.assertEqual(st.warrants_adopted, 1)
        self.assertEqual(st.organism.generation, 1)
        self.assertTrue(st.organism.verify())

    # ========================================================================
    # 4. Neuro-Symbolic Oracle & Bounty
    # ========================================================================
    def test_neuro_symbolic_oracle_and_bounty(self):
        """Oracle hypothesis must be validated, minted as warrant, and earn an ATP bounty."""
        colony = Colony("Oracle Biome", substrate_atp=5000)

        # Organism has an unoptimized Signal Compressor gene
        org = create_genesis_organism(generation=0)
        org.chromosomes = [
            Chromosome('OPT', 'Signal Compressor', '(🌿 (🖤 (🌿 🤍)) 🤍) Signal', '(🌿 🤍) Signal', 100)
        ]
        org.organism_hash = org.compute_hash()
        st = OrganismState(organism=org, energy_atp=200)
        colony.population.append(st)

        initial_energy = st.energy_atp
        initial_substrate = colony.substrate_atp

        # Step epoch: Oracle will formulate the S(K x)I -> x hypothesis
        rec = colony.step_epoch(solar_influx_atp=0)

        self.assertGreaterEqual(rec.warrants_minted, 1)
        self.assertEqual(st.warrants_minted, 1)
        # Check that colony mycelium now contains the newly minted warrant
        self.assertGreaterEqual(len(colony.registry.warrants), 1)
        # Check that organism received ATP bounty from substrate bank
        self.assertGreater(st.energy_atp, initial_energy - st.compute_basal_consumption())
        self.assertLess(colony.substrate_atp, initial_substrate)

    # ========================================================================
    # 5. Dialectical Sexual Recombination
    # ========================================================================
    def test_dialectical_symbiosis_in_colony(self):
        """Wealthy organisms must reproduce sexually, yielding offspring with B_n knot lineages."""
        colony = Colony("Symbiosis Biome", substrate_atp=2000)

        org_a = create_genesis_organism(generation=0)
        org_b = create_genesis_organism(generation=0)

        st_a = OrganismState(organism=org_a, energy_atp=400)
        st_b = OrganismState(organism=org_b, energy_atp=400)

        colony.population = [st_a, st_b]

        rec = colony.step_epoch(solar_influx_atp=50)

        self.assertEqual(rec.matings_count, 1)
        self.assertEqual(len(colony.population), 3)

        child_st = colony.population[-1]
        self.assertEqual(child_st.organism.generation, 1)
        self.assertTrue(child_st.organism.verify())
        self.assertEqual(st_a.matings_count, 1)
        self.assertEqual(st_b.matings_count, 1)

    # ========================================================================
    # 6. Multi-Epoch Simulation & Ledger Merkle Chain
    # ========================================================================
    def test_multi_epoch_simulation_and_ledger_settlement(self):
        """Multiple epochs must form an unbroken Merkle hash chain in the Living Ledger."""
        colony = Colony.create_genesis_colony("Ledger Biome", initial_organisms=2, initial_substrate_atp=3000)

        records = colony.simulate(epochs_count=3, solar_influx_atp=100)

        self.assertEqual(len(records), 3)
        self.assertEqual(len(colony.epochs), 3)
        # Genesis block + 3 epoch settlement blocks
        self.assertEqual(len(colony.ledger.blocks), 4)

        # Verify Merkle link continuity across epochs
        for i in range(1, len(records)):
            self.assertEqual(records[i].prev_epoch_hash, records[i-1].epoch_hash)
            self.assertEqual(records[i].epoch_hash, records[i].compute_hash())

        # Test persistence
        with tempfile.NamedTemporaryFile("w", delete=False) as f:
            tmp_name = f.name

        try:
            colony.save_to_file(tmp_name)
            loaded = Colony.load_from_file(tmp_name)
            self.assertEqual(loaded.summary(), colony.summary())
        finally:
            if os.path.exists(tmp_name):
                os.remove(tmp_name)

    # ========================================================================
    # 7. Polyglot Compiler & Runner
    # ========================================================================
    def test_colony_polyglot_compiler_and_runner(self):
        """Colony must compile to executable PDF with embedded manifest and status command."""
        colony = Colony.create_genesis_colony("Polyglot Biome", initial_organisms=2, initial_substrate_atp=4000)
        colony.step_epoch(solar_influx_atp=50)

        compiler = ColonyPolyglotCompiler(colony)
        pdf_bytes = compiler.compile_pdf()

        self.assertTrue(pdf_bytes.startswith(b"#!"))
        self.assertIn(b"%PDF-1.4", pdf_bytes)
        self.assertIn(b"# %COLONY_MANIFEST:", pdf_bytes)

        # Run standalone runner script against generated blob
        with tempfile.TemporaryDirectory() as td:
            pdf_path = os.path.join(td, "colony_test.pdf")
            with open(pdf_path, "wb") as f:
                f.write(pdf_bytes)

            runner_ns = {"__file__": pdf_path, "sys": sys, "os": os, "json": json}
            exec(compile(compiler._build_runner_script(), "<runner>", "exec"), runner_ns)

            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                runner_ns["cmd_status"]()

            out = buf.getvalue()
            self.assertIn("[BLACK-HEART] COLONY: Polyglot Biome", out)
            self.assertIn("Epochs Elapsed:", out)

if __name__ == "__main__":
    unittest.main()
