#!/usr/bin/env python3
# coding: utf-8
"""
test_controlled_forgetting.py — Unit & Integration Test Suite for Engine #25.
Part of Project Black-Heart (%🖤).

Tests the normative implementation of CONTROLLED-FORGETTING-0.1 and WARRANT.md §9:
  1. Invariants I1 & I4: Exact subject identity and mandatory non-empty loss declarations.
  2. Invariant I2: Default exclusion of retired artifacts from active cognitive surface.
  3. Invariant I3: ResurrectionGuard immune gate preventing implicit resurrection.
  4. Re-adoption protocol: Authorized unretirement via signed ReAdoptionRecord.
  5. Invariant I5: Retirement is not refutation (separation of truth-value from admission).
  6. Negative Space Coverage Metric (mu(C)) and metabolic gas reclamation bounties.
  7. Domain-separated RFC 8032 Ed25519 signatures.
  8. ISO 32000 append-only incremental document updates and standalone subprocess audit.
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
import warrant_kernel
import controlled_forgetting
from controlled_forgetting import (
    RetirementMode,
    AdmissionStatus,
    EpistemicResurrectionError,
    NegativeSpaceMeter,
    RetirementRecord,
    ReAdoptionRecord,
    EpistemicTombstoneRegistry,
    append_retirement_tombstone_to_pdf
)


class TestControlledForgetting(unittest.TestCase):

    def setUp(self):
        self.sk_author, self.pk_author = crypto.generate_keypair()
        self.sk_peer, self.pk_peer = crypto.generate_keypair()

    def test_01_invariants_i1_and_i4_exact_subject_and_loss_mandatory(self):
        """Invariant I1 (Exact Subject) and I4 (Loss is First-Class)."""
        target_id = "ALLELE_EXP_SWAP_01"
        target_digest = hashlib.sha256(b"S K I -> K I").hexdigest()

        # Invariant I4: Empty loss string MUST raise ValueError
        with self.assertRaises(ValueError) as ctx:
            RetirementRecord(
                record_id="",
                target_id=target_id,
                target_digest=target_digest,
                mode=RetirementMode.ARCHIVED,
                loss_declaration="",  # Empty loss
                negative_space_coverage=0.3,
                atp_gas_recovered=100,
                author_pk_hex=self.pk_author,
                signature_hex=""
            )
        self.assertIn("Invariant I4 violation", str(ctx.exception))

        # Whitespace-only loss MUST also raise ValueError
        with self.assertRaises(ValueError) as ctx:
            RetirementRecord(
                record_id="",
                target_id=target_id,
                target_digest=target_digest,
                mode=RetirementMode.ARCHIVED,
                loss_declaration="   \t\n  ",
                negative_space_coverage=0.3,
                atp_gas_recovered=100,
                author_pk_hex=self.pk_author,
                signature_hex=""
            )
        self.assertIn("Invariant I4 violation", str(ctx.exception))

        # Valid non-empty loss succeeds
        rec = RetirementRecord(
            record_id="",
            target_id=target_id,
            target_digest=target_digest,
            mode=RetirementMode.ARCHIVED,
            loss_declaration="Pruned trial swap candidate; lost experimental exploration history.",
            negative_space_coverage=0.35,
            atp_gas_recovered=120,
            author_pk_hex=self.pk_author,
            signature_hex=""
        )
        self.assertTrue(len(rec.record_id) == 64)
        self.assertEqual(rec.target_id, target_id)
        self.assertEqual(rec.target_digest, target_digest)

    def test_02_mode_superseded_requires_replacement(self):
        """Retirement mode SUPERSEDED requires a replacement_id."""
        target_id = "HYPOTHESIS_E01"
        target_digest = hashlib.sha256(b"empirical_fixture_rule").hexdigest()

        # SUPERSEDED with replacement_id=None raises ValueError
        with self.assertRaises(ValueError) as ctx:
            RetirementRecord(
                record_id="",
                target_id=target_id,
                target_digest=target_digest,
                mode=RetirementMode.SUPERSEDED,
                replacement_id=None,
                loss_declaration="Elevated to Axiomatic rule.",
                negative_space_coverage=0.5,
                atp_gas_recovered=150,
                author_pk_hex=self.pk_author,
                signature_hex=""
            )
        self.assertIn("SUPERSEDED requires a valid non-empty replacement_id", str(ctx.exception))

        # Valid SUPERSEDED succeeds
        rec = RetirementRecord(
            record_id="",
            target_id=target_id,
            target_digest=target_digest,
            mode=RetirementMode.SUPERSEDED,
            replacement_id="AXIOMATIC_RULE_A01",
            loss_declaration="Empirical hypothesis superseded by proven axiomatic theorem.",
            negative_space_coverage=0.5,
            atp_gas_recovered=150,
            author_pk_hex=self.pk_author,
            signature_hex=""
        )
        self.assertEqual(rec.replacement_id, "AXIOMATIC_RULE_A01")

    def test_03_invariant_i2_default_exclusion(self):
        """Invariant I2: Retired artifacts are excluded from default active evaluation."""
        registry = EpistemicTombstoneRegistry()
        active_gene = "GENE_METABOLISM_CORE"
        retired_gene = "GENE_TRIAL_MUTANT_42"

        self.assertTrue(registry.is_admitted(active_gene))
        self.assertEqual(registry.get_admission_status(active_gene), AdmissionStatus.ACTIVE)

        # Retire the trial mutant
        rec = registry.retire(
            target_id=retired_gene,
            target_digest=hashlib.sha256(b"mutant_42").hexdigest(),
            mode=RetirementMode.REFUTED,
            loss_declaration="Mutant allele regressed fitness by 14 ATP; refuted by counterexample.",
            author_sk_hex=self.sk_author,
            author_pk_hex=self.pk_author,
            rule_or_pattern="x y -> y x"
        )
        self.assertTrue(rec.verify_signature())

        # Now retired_gene must be excluded
        self.assertFalse(registry.is_admitted(retired_gene))
        self.assertEqual(registry.get_admission_status(retired_gene), AdmissionStatus.RETIRED)

        # Filter active surface
        genes = [active_gene, retired_gene, "GENE_FLOW_01"]
        active_surface, historical_substrate = registry.filter_active_surface(genes, lambda g: g)
        self.assertIn(active_gene, active_surface)
        self.assertIn("GENE_FLOW_01", active_surface)
        self.assertNotIn(retired_gene, active_surface)
        self.assertIn(retired_gene, historical_substrate)

    def test_04_invariant_i3_resurrection_guard(self):
        """Invariant I3: No implicit resurrection without signed ReAdoptionRecord."""
        registry = EpistemicTombstoneRegistry()
        retired_gene = "GENE_QUARANTINED_99"

        registry.retire(
            target_id=retired_gene,
            target_digest="dummy_digest",
            mode=RetirementMode.QUARANTINED,
            loss_declaration="Suspended pending multi-agent audit.",
            author_sk_hex=self.sk_author,
            author_pk_hex=self.pk_author
        )

        # Attempting to execute or admit the retired gene triggers Resurrection Guard
        with self.assertRaises(EpistemicResurrectionError) as ctx:
            registry.assert_viable_for_admission(retired_gene)
        self.assertIn("Resurrection Guard Refusal", str(ctx.exception))
        self.assertIn("Invariant I3 prohibits implicit resurrection", str(ctx.exception))

    def test_05_readoption_protocol(self):
        """Authorized unretirement via signed ReAdoptionRecord."""
        registry = EpistemicTombstoneRegistry()
        target_id = "GENE_BENCHMARK_PROT"

        ret_rec = registry.retire(
            target_id=target_id,
            target_digest="prot_digest",
            mode=RetirementMode.ARCHIVED,
            loss_declaration="Archived during metabolic rest period.",
            author_sk_hex=self.sk_author,
            author_pk_hex=self.pk_author
        )

        self.assertFalse(registry.is_admitted(target_id))

        # Re-adopt with fresh evidence
        readopt_rec = registry.readopt(
            target_id=target_id,
            justification="New environmental stress requires re-activation of benchmark protein.",
            new_evidence_claim_id="CLAIM_EVIDENCE_2026",
            author_sk_hex=self.sk_author,
            author_pk_hex=self.pk_author
        )
        self.assertTrue(readopt_rec.verify_signature())

        # Now re-admitted
        self.assertTrue(registry.is_admitted(target_id))
        self.assertEqual(registry.get_admission_status(target_id), AdmissionStatus.READOPTED)
        # Immune gate assertion passes without error
        registry.assert_viable_for_admission(target_id)

    def test_06_negative_space_metric_and_gas_reclamation(self):
        """Verify Negative Space Coverage Metric mu(C) and ATP fuel reclamation."""
        # Refuting commutative swap in non-commutative logic eliminates 75% of arbitrary rewrites
        cov_swap = NegativeSpaceMeter.calculate_coverage("x y -> y x")
        self.assertEqual(cov_swap, 0.75)
        gas_swap = NegativeSpaceMeter.compute_gas_reclamation(cov_swap)
        self.assertEqual(gas_swap, 50 + int(200 * 0.75))  # 50 + 150 = 200 ATP

        # Deep expression pruning
        cov_deep = NegativeSpaceMeter.calculate_coverage("🌿 (🖤 🤍) (🌿 🖤 🤍)")
        self.assertGreater(cov_deep, 0.0)
        self.assertLessEqual(cov_deep, 1.0)

    def test_07_domain_separated_signatures(self):
        """Verify domain separation in Ed25519 signatures (retirement-sig-v1:)."""
        rec = RetirementRecord(
            record_id="",
            target_id="T1",
            target_digest="D1",
            mode=RetirementMode.WITHDRAWN,
            loss_declaration="Voluntary withdrawal.",
            negative_space_coverage=0.2,
            atp_gas_recovered=90,
            author_pk_hex=self.pk_author,
            signature_hex=""
        )
        rec.sign(self.sk_author)
        self.assertTrue(rec.verify_signature())

        # Signing without domain separation fails
        bad_sig = crypto.sign_hex(self.sk_author, bytes.fromhex(rec.record_id))
        rec_bad = RetirementRecord.from_dict(rec.to_dict())
        rec_bad.signature_hex = bad_sig
        self.assertFalse(rec_bad.verify_signature())

        # Mismatched key fails
        rec_bad_key = RetirementRecord.from_dict(rec.to_dict())
        rec_bad_key.author_pk_hex = self.pk_peer
        self.assertFalse(rec_bad_key.verify_signature())

    def test_08_iso_32000_append_only_polyglot_and_audit(self):
        """Verify ISO 32000 append-only growth and standalone subprocess execution."""
        # 1. Create a base PDF using warrant_kernel
        t_str = "🤍 🖤"
        h = glyph.evaluate(glyph.parse(t_str)).hash
        c_ground = warrant_kernel.EdgeClaim.create_and_sign(
            "p_root", "eval", "term", h, warrant_kernel.Polarity.AFFIRM,
            warrant_kernel.GroundedWitness(t_str, h), self.sk_author, self.pk_author
        )

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tf_base:
            base_path = tf_base.name
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tf_inc:
            inc_path = tf_inc.name

        try:
            warrant_kernel.generate_warrant_ledger_pdf([c_ground], base_path)
            with open(base_path, "rb") as f:
                base_bytes = f.read()

            # 2. Append retirement tombstone
            registry = EpistemicTombstoneRegistry()
            rec = registry.retire(
                target_id="TRIAL_MUTATION_007",
                target_digest=hashlib.sha256(b"trial_007").hexdigest(),
                mode=RetirementMode.REFUTED,
                loss_declaration="Pruned trial mutation; failed immune check.",
                author_sk_hex=self.sk_author,
                author_pk_hex=self.pk_author,
                rule_or_pattern="x y -> y x"
            )

            inc_bytes = append_retirement_tombstone_to_pdf(base_bytes, inc_path, rec, registry)

            # 3. Unbroken ISO 32000 Append-Only Invariant: after.startswith(before)
            # Find base up to %%EOF
            prev_eof = base_bytes.rfind(b"%%EOF")
            expected_prefix = base_bytes[:prev_eof + 5]
            self.assertTrue(
                inc_bytes.startswith(expected_prefix),
                "ISO 32000 append-only invariant broken: incremental file does not start with previous bytes."
            )

            # 4. Standalone Subprocess Audit: python3 inc_path
            repo_dir = os.path.dirname(os.path.abspath(__file__))
            cmd = [sys.executable, inc_path]
            proc = subprocess.run(cmd, cwd=repo_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            self.assertEqual(proc.returncode, 0, f"Polyglot subprocess audit failed:\n{proc.stderr}")
            self.assertIn("CONTROLLED FORGETTING AUDITOR", proc.stdout)
            self.assertIn("All retirement tombstones cryptographically verified", proc.stdout)
            self.assertIn("[TOMBSTONE] 'TRIAL_MUTATION_007'", proc.stdout)
        finally:
            if os.path.exists(base_path):
                os.remove(base_path)
            if os.path.exists(inc_path):
                os.remove(inc_path)

    def test_09_generate_tombstone_stele_pdf_standalone(self):
        """Verify generating a fresh standalone Tombstone Stele polyglot PDF with multiple modes."""
        registry = EpistemicTombstoneRegistry()
        rec_dep = registry.retire(
            target_id="LEGACY_HEURISTIC_V1",
            target_digest=hashlib.sha256(b"legacy_heur_1").hexdigest(),
            mode=RetirementMode.DEPRECATED,
            loss_declaration="Deprecated in favor of confluent algebraic normal forms.",
            author_sk_hex=self.sk_author,
            author_pk_hex=self.pk_author,
            rule_or_pattern="I (K x) -> K"
        )
        rec_ref = registry.retire(
            target_id="FLAWED_AXIOM_C99",
            target_digest=hashlib.sha256(b"flawed_ax_99").hexdigest(),
            mode=RetirementMode.REFUTED,
            loss_declaration="Counterexample demonstrates non-termination.",
            author_sk_hex=self.sk_author,
            author_pk_hex=self.pk_author,
            rule_or_pattern="x y -> y x"
        )

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tf:
            pdf_path = tf.name

        try:
            pdf_bytes = controlled_forgetting.generate_tombstone_stele_pdf(
                [rec_dep, rec_ref], pdf_path, registry
            )
            self.assertIn(b"%PDF-1.7", pdf_bytes)
            self.assertIn(b"RETIREMENT_MANIFEST", pdf_bytes)

            repo_dir = os.path.dirname(os.path.abspath(__file__))
            proc = subprocess.run([sys.executable, pdf_path], cwd=repo_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            self.assertEqual(proc.returncode, 0, f"Polyglot subprocess audit failed:\n{proc.stderr}")
            self.assertIn("Audited 2 tombstones", proc.stdout)
            self.assertIn("LEGACY_HEURISTIC_V1", proc.stdout)
            self.assertIn("DEPRECATED", proc.stdout)
            self.assertIn("FLAWED_AXIOM_C99", proc.stdout)
            self.assertIn("REFUTED", proc.stdout)
            self.assertIn("All retirement tombstones cryptographically verified", proc.stdout)
        finally:
            if os.path.exists(pdf_path):
                os.remove(pdf_path)


if __name__ == "__main__":
    unittest.main()

