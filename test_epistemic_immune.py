#!/usr/bin/env python3
# coding: utf-8
"""
test_epistemic_immune.py — Unit & Integration Test Suite for Engine #26.
Part of Project Black-Heart (%🖤).

Tests the normative implementation of EPISTEMIC-IMMUNE-0.1:
  1. ResurrectionDefense: Blocks tombstoned mutations prior to trial execution.
  2. CounterexampleMetabolism: Mints Grade C claims, calculates mu(C), credits gas bounty.
  3. HypothesisElevationCycle: Elevates surviving empirical hypotheses to axiomatic identities.
  4. HorizontalInoculation: Transfers and verifies peer tombstone registries across the swarm.
  5. StarvationAutophagy: Prunes non-vital chromosomes under ATP deficiency to restore homeostasis.
  6. ISO 32000 Append-Only Growth: Preserves document byte prefix on immune updates.
  7. Standalone Polyglot Execution: Direct subprocess audit of compiled immune polyglot.
"""

import os
import sys
import json
import tempfile
import unittest
import subprocess
import hashlib

import crypto
import glyph
from organism import Chromosome
import warrant_kernel
from warrant_kernel import (
    EvidenceGrade, Polarity, EdgeClaim, EmpiricalWitness, AxiomaticWitness,
    WarrantVerifier, TrustConfig, VerificationStatus
)
import controlled_forgetting
from controlled_forgetting import (
    RetirementMode, AdmissionStatus, NegativeSpaceMeter,
    RetirementRecord, EpistemicTombstoneRegistry
)
import epistemic_immune
from epistemic_immune import (
    ImmuneHealthStatus, EpistemicOrganism, ResurrectionDefense,
    CounterexampleMetabolism, HypothesisElevationCycle,
    HorizontalInoculation, StarvationAutophagy, observe_divergence,
    generate_immune_organism_pdf, append_immune_hud_to_pdf
)


class TestEpistemicImmune(unittest.TestCase):

    def setUp(self):
        self.sk_author, self.pk_author = crypto.generate_keypair()
        self.sk_peer, self.pk_peer = crypto.generate_keypair()

        # Build sample chromosomes
        self.core_chromosome = Chromosome(
            gene_id="GENE-SOVEREIGN-CORE",
            gene_name="Sovereign Core",
            expression="S K K",
            expected_normal_form="I",
            vital=True
        )
        self.experimental_chromosome = Chromosome(
            gene_id="GENE-EXP-REWRITE-01",
            gene_name="Trial Rewrite Exp",
            expression="S (K (S I)) (K I)",
            expected_normal_form="I",
            vital=False
        )

        self.organism = EpistemicOrganism(
            organism_id="ORG-ALPHA-001",
            generation=0,
            chromosomes=[self.core_chromosome, self.experimental_chromosome],
            public_key_hex=self.pk_author,
            atp_reserve=500
        )

    def test_01_resurrection_defense_blocks_tombstoned_mutations(self):
        """Invariant I3 pre-flight gate prevents testing tombstoned rules, saving ATP."""
        registry = self.organism.tombstone_registry
        rule = "x y -> y x"
        digest = hashlib.sha256(rule.encode("utf-8")).hexdigest()

        # Initially permitted
        ok, reason = ResurrectionDefense.preflight_check(registry, rule, digest)
        self.assertTrue(ok)
        self.assertEqual(reason, "")

        # Tombstone the rule
        rec = registry.retire(
            target_id=rule,
            target_digest=digest,
            mode=RetirementMode.REFUTED,
            loss_declaration="Refuted non-confluent swap rule by counterexample.",
            author_sk_hex=self.sk_author,
            author_pk_hex=self.pk_author,
            rule_or_pattern=rule
        )
        self.assertTrue(rec.verify_signature())

        # Now preflight MUST refuse the candidate rule
        ok_after, reason_after = ResurrectionDefense.preflight_check(registry, rule, digest)
        self.assertFalse(ok_after)
        self.assertIn("Resurrection Defense Refusal", reason_after)
        self.assertIn("REFUTED", reason_after)

    def test_02_divergence_counterexample_gas_bounty(self):
        """Failed candidate mutation generates Grade C claim and credits gas bounty based on mu(C)."""
        initial_atp = self.organism.atp_reserve
        rule_name = "x y -> y x"
        # `rule_name` is the retirement subject, not code. The refutation runs
        # between two terms the caller names, measured rather than asserted:
        #   K   (I (K I)) -> K (K I)   in 1 ATP
        #   K I (I (K I)) -> I         in 1 ATP
        parent_term = "🖤"
        candidate_term = "🖤 🤍"
        input_fix = "🤍 (🖤 🤍)"
        obs = observe_divergence(parent_term, candidate_term, input_fix)
        self.assertTrue(obs.diverges(), obs.detail)

        outcome = CounterexampleMetabolism.metabolize_counterexample(
            organism=self.organism,
            gene_id="GENE-EXP-REWRITE-01",
            rule_name=rule_name,
            parent_term=parent_term,
            candidate_term=candidate_term,
            input_fixture=input_fix,
            expected_norm=obs.parent_output,
            actual_norm=obs.candidate_output,
            atp_cost=obs.atp_required,
            secret_key_hex=self.sk_author,
            public_key_hex=self.pk_author
        )
        self.assertTrue(outcome.granted(), outcome.verdict.reason)
        claim, tomb, bounty = outcome.claim, outcome.retirement, outcome.gas_bounty

        # Claim verification
        self.assertEqual(claim.grade, EvidenceGrade.COUNTEREXAMPLE)
        self.assertEqual(claim.polarity, Polarity.REFUTE)
        self.assertTrue(claim.verify_signature())

        # The credited claim passes an audit performed by someone else
        self.assertEqual(
            WarrantVerifier(TrustConfig()).audit_claim(claim).status,
            VerificationStatus.PASS)

        # Tombstone verification
        self.assertEqual(tomb.mode, RetirementMode.REFUTED)
        self.assertTrue(len(tomb.loss_declaration) > 0)
        self.assertTrue(tomb.verify_signature())

        # Negative space & Gas bounty verification
        self.assertGreaterEqual(tomb.negative_space_coverage, 0.5)
        self.assertGreater(bounty, 100)
        self.assertEqual(self.organism.atp_reserve, initial_atp + bounty)
        self.assertEqual(self.organism.total_bounties_reclaimed, bounty)

        # Confirm target is excluded from active surface
        self.assertFalse(self.organism.tombstone_registry.is_admitted(rule_name))

    def test_03_hypothesis_elevation_e_to_a(self):
        """Surviving empirical hypothesis is promoted to Grade A and supersedes old claim."""
        rule = "I x -> x"
        emp_witness = EmpiricalWitness(
            fixtures=["🤍", "🖤", "🌿"],
            fixtures_fingerprint="fp123",
            delta_atp=1,
            delta_size=0
        )
        emp_witness.fixtures_fingerprint = emp_witness.compute_fixtures_fingerprint()

        c_emp = EdgeClaim.create_and_sign(
            parent_hash=self.organism.compute_genome_hash(),
            tau=rule,
            omega="GENE-EXP-01",
            successor_hash="succ_hash",
            polarity=Polarity.AFFIRM,
            witness=emp_witness,
            secret_key_hex=self.sk_author,
            public_key_hex=self.pk_author
        )
        self.organism.claims.append(c_emp)
        self.assertEqual(c_emp.grade, EvidenceGrade.EMPIRICAL)

        # Trigger elevation cycle
        res = HypothesisElevationCycle.evaluate_and_elevate(
            self.organism, self.sk_author, self.pk_author
        )
        self.assertIsNotNone(res)
        promoted, ret_rec = res

        # Promoted claim is Axiomatic
        self.assertEqual(promoted.grade, EvidenceGrade.AXIOMATIC)
        self.assertEqual(promoted.tau, rule)
        self.assertIn(rule, self.organism.active_axioms)

        # Old claim is superseded
        self.assertEqual(ret_rec.mode, RetirementMode.SUPERSEDED)
        self.assertEqual(ret_rec.target_id, c_emp.claim_id)
        self.assertEqual(ret_rec.replacement_id, promoted.claim_id)
        self.assertFalse(self.organism.tombstone_registry.is_admitted(c_emp.claim_id))

    def test_04_horizontal_cross_inoculation(self):
        """Organism A absorbs Organism B's tombstones, gaining immunity against B's failures."""
        peer_registry = EpistemicTombstoneRegistry()
        failed_rule = "S K -> K"
        rec = peer_registry.retire(
            target_id=failed_rule,
            target_digest=hashlib.sha256(failed_rule.encode("utf-8")).hexdigest(),
            mode=RetirementMode.REFUTED,
            loss_declaration="Peer trial showed non-confluence under substitution.",
            author_sk_hex=self.sk_peer,
            author_pk_hex=self.pk_peer,
            rule_or_pattern=failed_rule
        )
        self.assertTrue(rec.verify_signature())

        # Inoculate organism
        self.assertTrue(self.organism.tombstone_registry.is_admitted(failed_rule))
        report = HorizontalInoculation.inoculate(self.organism, peer_registry)

        self.assertEqual(report.absorbed_tombstones_count, 1)
        self.assertEqual(report.rejected_signatures_count, 0)
        self.assertEqual(self.organism.inoculated_tombstones_count, 1)

        # Organism A now rejects the peer's failed rule
        self.assertFalse(self.organism.tombstone_registry.is_admitted(failed_rule))
        ok, reason = ResurrectionDefense.preflight_check(self.organism.tombstone_registry, failed_rule)
        self.assertFalse(ok)

    def test_05_starvation_autophagy_restores_homeostasis(self):
        """Starvation triggers autophagy, archiving non-vital chromosomes and recovering fuel."""
        # Drain ATP to critical starvation level
        self.organism.atp_reserve = 40
        self.assertEqual(self.organism.get_health_status(), ImmuneHealthStatus.STARVATION)

        report = StarvationAutophagy.trigger_autophagy(
            self.organism, self.sk_author, self.pk_author,
            starvation_threshold=80, recovery_target_atp=150
        )

        self.assertTrue(report.triggered)
        self.assertIn("GENE-EXP-REWRITE-01", report.pruned_chromosomes)
        self.assertGreater(report.reclaimed_fuel, 0)
        self.assertGreaterEqual(self.organism.atp_reserve, 80)
        self.assertEqual(self.organism.autophagy_events_count, 1)

        # Non-vital chromosome is removed from active genome and archived
        remaining_gene_ids = [c.gene_id for c in self.organism.chromosomes]
        self.assertNotIn("GENE-EXP-REWRITE-01", remaining_gene_ids)
        self.assertIn("GENE-SOVEREIGN-CORE", remaining_gene_ids)
        self.assertFalse(self.organism.tombstone_registry.is_admitted("GENE-EXP-REWRITE-01"))
        self.assertEqual(
            self.organism.tombstone_registry.tombstones["GENE-EXP-REWRITE-01"].mode,
            RetirementMode.ARCHIVED
        )

    def test_06_iso_32000_append_only_immune_stele(self):
        """Incremental update with Immune HUD preserves byte prefix (after.startswith(before))."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tf_base:
            base_path = tf_base.name
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tf_inc:
            inc_path = tf_inc.name

        try:
            # Generate base immune organism
            generate_immune_organism_pdf(self.organism, base_path)
            with open(base_path, "rb") as f:
                base_bytes = f.read()

            self.assertIn(b"%PDF-1.7", base_bytes)
            self.assertIn(b"IMMUNE_METABOLISM_MANIFEST", base_bytes)

            # Evolve: add a tombstone and credit fuel
            self.organism.generation += 1
            self.organism.atp_reserve += 150
            self.organism.tombstone_registry.retire(
                target_id="MUTANT_Z99",
                target_digest=hashlib.sha256(b"z99").hexdigest(),
                mode=RetirementMode.DEPRECATED,
                loss_declaration="Deprecated legacy mutant.",
                author_sk_hex=self.sk_author,
                author_pk_hex=self.pk_author
            )

            # Append incremental revision
            inc_bytes = append_immune_hud_to_pdf(base_bytes, inc_path, self.organism)

            # Check ISO 32000 append-only invariant
            prev_eof = base_bytes.rfind(b"%%EOF")
            expected_prefix = base_bytes[:prev_eof + 5]
            self.assertTrue(
                inc_bytes.startswith(expected_prefix),
                "ISO 32000 append-only invariant violated."
            )
        finally:
            if os.path.exists(base_path):
                os.remove(base_path)
            if os.path.exists(inc_path):
                os.remove(inc_path)

    def test_07_standalone_polyglot_immune_audit(self):
        """Direct execution of compiled immune organism PDF via python3 subprocess."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tf:
            pdf_path = tf.name

        try:
            generate_immune_organism_pdf(self.organism, pdf_path)

            repo_dir = os.path.dirname(os.path.abspath(__file__))
            proc = subprocess.run(
                [sys.executable, pdf_path],
                cwd=repo_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            self.assertEqual(proc.returncode, 0, f"Subprocess failed:\n{proc.stderr}")
            self.assertIn("EPISTEMIC IMMUNE METABOLISM AUDITOR", proc.stdout)
            self.assertIn("Organism ID: ORG-ALPHA-001", proc.stdout)
            self.assertIn("Immune metabolism and tombstone defenses fully verified", proc.stdout)
        finally:
            if os.path.exists(pdf_path):
                os.remove(pdf_path)


if __name__ == "__main__":
    unittest.main()
