#!/usr/bin/env python3
# coding: utf-8
"""
test_sovereign_remediation.py — Verification Suite for Findings F01–F12 Remediation.
Part of Project Black-Heart (%🖤).

Validates that all defect scenarios fail closed with rigorous mathematical & cryptographic guards:
  - F01 (P1): Skeletons compute non-zero hashes; behavioral traces bind to drift analysis.
  - F02 (P2 & D3): Manifest audit detects tampered skeleton hash or matrices fail-closed.
  - F03 (S1): Sheaf descent rejects obstructed or unverified local sections fail-closed.
  - F04 (S2 & S3): Sheaf descent enforces domain coverage and restriction consistency across components.
  - F05 (S4): Sheaf descent records 1-cocycle disagreement count.
  - F06 (C1, C2, C3): Cold reconstitution requires valid migration sig, genesis link, and unbroken DAG.
  - F07 (D1 & D2): PDF embedded auditor rejects tampered state; --migrate preserves receipt history.
  - F08 (A1 & A2): Agora rejects zero-vote empty sessions and sub-threshold/unanimous Nay votes.
  - F09 (A3): Čech cohomology fracture (H^1 > 0) cannot be overridden by unanimous political votes.
  - F10 (A4): Slashed false equivalence proposals halt fail-closed with stake forfeiture.
  - F11 (C4): Anti-resurrection immune gate strictly requires signed ReAdoptionRecord.
  - F12 (C5): Metabolic capacity ceiling (B_max) strictly enforced in evolution & reconstitution.
"""

import base64
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# Engine #32: Epistemic Palimpsest Kernel
import palimpsest_kernel as pal

# Engine #33: Epistemic Sheaf Kernel
import sheaf_kernel as sh

# Engine #34: Sovereign Continuity Quine
import sovereign_continuity as sc

# Engine #35: Federated Sheaf Agora
import sheaf_agora as ag


class TestSovereignRemediation(unittest.TestCase):
    """Rigorous positive and negative controls for all findings F01 through F12."""

    # ========================================================================
    # F01: Skeleton Tree Hashing & Trace Generation (P1)
    # ========================================================================
    def test_f01_skeleton_and_trace_integrity(self):
        """F01: Skeletons must have non-zero tree hashes and behavioral matrices must bind to drift."""
        s0 = pal.ReasoningSkeleton.create(0, [])
        s1 = pal.ReasoningSkeleton.create(1, [])
        self.assertNotEqual(s0.tree_hash, "0" * 64)
        self.assertNotEqual(s1.tree_hash, "0" * 64)
        self.assertNotEqual(s0.tree_hash, s1.tree_hash)

        m0 = pal.BehavioralTraceMatrix(0)
        m1 = pal.BehavioralTraceMatrix(1)
        self.assertEqual(m0.generation, 0)
        self.assertEqual(m1.generation, 1)

        analyzer = pal.PalimpsestDriftAnalyzer()
        drift = analyzer.analyze_drift(s0, s1, m0, m1)
        self.assertEqual(drift.gen_old, 0)
        self.assertEqual(drift.gen_new, 1)
        self.assertIsNotNone(drift.verdict)

    # ========================================================================
    # F02: Palimpsest PDF Manifest & CLI Audit (P2 & D3)
    # ========================================================================
    def test_f02_palimpsest_tamper_detection(self):
        """F02: Tampered skeleton or manifest in Palimpsest PDF must fail audit fail-closed."""
        with tempfile.TemporaryDirectory() as td:
            pdf_path = Path(td) / "palimpsest.pdf"
            s0 = pal.ReasoningSkeleton.create(0, [])
            s1 = pal.ReasoningSkeleton.create(1, [])
            m0 = pal.BehavioralTraceMatrix(0)
            m1 = pal.BehavioralTraceMatrix(1)
            t = pal.PalimpsestDriftAnalyzer().analyze_drift(s0, s1, m0, m1)
            pal.generate_palimpsest_pdf(t, s0, s1, str(pdf_path))

            # Tamper with the manifest
            raw = pdf_path.read_bytes()
            tag = pal.PALIMPSEST_MANIFEST_PREFIX.encode("latin-1")
            idx = raw.index(tag) + len(tag)
            end = raw.index(b"\n", idx)
            manifest = json.loads(raw[idx:end])
            manifest["skeleton_new"]["tree_hash"] = "deadbeef" * 8
            tampered_bytes = raw[:idx] + json.dumps(manifest).encode("latin-1") + raw[end:]
            pdf_path.write_bytes(tampered_bytes)

            # Standalone execution of tampered polyglot PDF: python3 palimpsest.pdf --audit
            res = subprocess.run(
                [sys.executable, "-B", str(pdf_path), "--audit"],
                capture_output=True,
                text=True
            )
            self.assertEqual(res.returncode, 1)
            self.assertIn("INTEGRITY FAILURE", res.stdout)

    # ========================================================================
    # F03: Sheaf Descent Local Theorem Verification (S1)
    # ========================================================================
    def test_f03_sheaf_descent_rejects_obstructed_or_unverified(self):
        """F03: verify_descent must fail closed on obstructed or diverging local claims."""
        kernel = sh.EpistemicSheafKernel()
        c1 = sh.EpistemicContext.create("ctx1", ["ski"], 100)
        c2 = sh.EpistemicContext.create("ctx2", ["ski"], 100)
        kernel.register_context(c1)
        kernel.register_context(c2)

        # Register obstructed section
        kernel.register_section(sh.LocalSection.create(
            context=c1, claim_name="claim1", term_expression="I", normal_form="K",
            verified_steps=0, status=sh.SectionStatus.OBSTRUCTED
        ))
        kernel.register_section(sh.LocalSection.create(
            context=c2, claim_name="claim1", term_expression="I", normal_form="K",
            verified_steps=0, status=sh.SectionStatus.OBSTRUCTED
        ))

        report = kernel.verify_descent("claim1", [c1, c2])
        self.assertFalse(report.is_gluing_admissible)
        self.assertIn("obstructed", report.rejection_reason.lower())

    # ========================================================================
    # F04: Sheaf Descent Domain Coverage & Restriction Consistency (S2 & S3)
    # ========================================================================
    def test_f04_sheaf_descent_domain_coverage_and_restriction(self):
        """F04: verify_descent must fail on uncovered domains or disjoint conflicting sections."""
        kernel = sh.EpistemicSheafKernel()
        c1 = sh.EpistemicContext.create("ctx1", ["ski"], 100)
        kernel.register_context(c1)
        kernel.register_section(sh.LocalSection.create(c1, "claim", "I", "I", 0))

        # Uncovered target context
        uncovered = sh.EpistemicContext.create("uncovered", ["uncovered_domain"], 100)
        report_uncovered = kernel.verify_descent("claim", [c1], target_union_context=uncovered)
        self.assertFalse(report_uncovered.is_gluing_admissible)
        self.assertIn("uncovered domains", report_uncovered.rejection_reason)

        # Disjoint contexts with conflicting normal forms
        ca = sh.EpistemicContext.create("ca", ["domain_A"], 100)
        cb = sh.EpistemicContext.create("cb", ["domain_B"], 100)
        kernel2 = sh.EpistemicSheafKernel()
        kernel2.register_context(ca)
        kernel2.register_context(cb)
        kernel2.register_section(sh.LocalSection.create(ca, "claim_ab", "I", "I", 0))
        kernel2.register_section(sh.LocalSection.create(cb, "claim_ab", "K", "K", 0))

        report_conflict = kernel2.verify_descent("claim_ab", [ca, cb])
        self.assertFalse(report_conflict.is_gluing_admissible)
        self.assertIn("conflicting local normal forms", report_conflict.rejection_reason)

    # ========================================================================
    # F05: Sheaf Descent 1-Cocycle Overlap Tracking (S4)
    # ========================================================================
    def test_f05_sheaf_descent_cocycle_metric(self):
        """F05: Positive control confirming 1-cocycle disagreement metric is accurate."""
        kernel = sh.EpistemicSheafKernel()
        c1 = sh.EpistemicContext.create("u1", ["ski"], 100)
        c2 = sh.EpistemicContext.create("u2", ["ski"], 100)
        kernel.register_context(c1)
        kernel.register_context(c2)

        # Agreement on overlap
        kernel.register_section(sh.LocalSection.create(c1, "claim", "I", "I", 0))
        kernel.register_section(sh.LocalSection.create(c2, "claim", "I", "I", 0))
        report_ok = kernel.verify_descent("claim", [c1, c2])
        self.assertTrue(report_ok.is_gluing_admissible)
        self.assertEqual(report_ok.h1_dimension, 0)

        # Disagreement on overlap: u2 changed to 'K'
        kernel.register_section(sh.LocalSection.create(c2, "claim", "K", "K", 0))
        report_fail = kernel.verify_descent("claim", [c1, c2])
        self.assertFalse(report_fail.is_gluing_admissible)
        self.assertEqual(report_fail.h1_dimension, 1)

    # ========================================================================
    # F06: Sovereign Organism Cold Reconstitution (C1, C2, C3)
    # ========================================================================
    def test_f06_sovereign_reconstitution_invariants(self):
        """F06: Reconstitution enforces verified migration signature, unbroken identity, and DAG."""
        org = sc.SovereignOrganism.create_genesis()
        org.evolve_step("Gen 1")
        seed_bundle = json.loads(org.export_migration_seed())

        # C1: Reject empty / missing migration signature
        bad_sig = json.loads(json.dumps(seed_bundle))
        bad_sig["migration_signature_hex"] = ""
        with self.assertRaises(ValueError):
            sc.SovereignOrganism.reconstitute_from_seed(json.dumps(bad_sig))

        # C2: Reject mismatched genesis author identity
        other_org = sc.SovereignOrganism.create_genesis()
        bad_author = json.loads(json.dumps(seed_bundle))
        bad_author["payload"]["author_pk_hex"] = other_org.author_pk_hex
        sig_other = sc.sign_bytes(
            bytes.fromhex(other_org.secret_key_hex),
            b"sovereign-migration-v1:" + hashlib.sha256(sc.canonical_jcs(bad_author["payload"])).digest()
        ).hex()
        bad_author["migration_signature_hex"] = sig_other
        with self.assertRaises(ValueError):
            sc.SovereignOrganism.reconstitute_from_seed(json.dumps(bad_author))

        # C3: Reject disordered / broken receipt lineage DAG
        bad_dag = json.loads(json.dumps(seed_bundle))
        receipts = bad_dag["payload"]["history_receipts"]
        bad_dag["payload"]["history_receipts"] = [receipts[1], receipts[0]]
        sig_dag = sc.sign_bytes(
            bytes.fromhex(org.secret_key_hex),
            b"sovereign-migration-v1:" + hashlib.sha256(sc.canonical_jcs(bad_dag["payload"])).digest()
        ).hex()
        bad_dag["migration_signature_hex"] = sig_dag
        with self.assertRaises(ValueError):
            sc.SovereignOrganism.reconstitute_from_seed(json.dumps(bad_dag))

    # ========================================================================
    # F07: PDF Embedded Quine Audit & Migration Continuity (D1 & D2)
    # ========================================================================
    def test_f07_polyglot_audit_and_migration_preservation(self):
        """F07: PDF embedded auditor rejects tampered state and --migrate preserves lineage."""
        with tempfile.TemporaryDirectory() as td:
            pdf_path = Path(td) / "sovereign_quine.pdf"
            org = sc.SovereignOrganism.create_genesis()
            org.evolve_step("Gen 1")
            sc.generate_sovereign_polyglot(org, str(pdf_path))

            # D1: Tampered manifest fails embedded audit
            raw = pdf_path.read_bytes()
            tag = b"# %BLACK_HEART_SOVEREIGN_MANIFEST: "
            idx = raw.index(tag) + len(tag)
            end = raw.index(b"\n", idx)
            bundle = json.loads(base64.b64decode(raw[idx:end]))
            manifest = bundle.get("payload", bundle)
            manifest["genesis_pk_hex"] = "forged"
            manifest["active_cost"] = 999999
            bundle["payload"] = manifest
            tampered_bytes = raw[:idx] + base64.b64encode(json.dumps(bundle).encode()) + raw[end:]
            pdf_path.write_bytes(tampered_bytes)

            audit_res = subprocess.run(
                [sys.executable, "-B", str(pdf_path), "--audit"],
                capture_output=True,
                text=True
            )
            self.assertEqual(audit_res.returncode, 1)
            self.assertIn("[FAIL]", audit_res.stdout)

            # D2: Clean polyglot --migrate preserves full receipt lineage
            clean_pdf = Path(td) / "clean_quine.pdf"
            sc.generate_sovereign_polyglot(org, str(clean_pdf))
            mig_res = subprocess.run(
                [sys.executable, "-B", str(clean_pdf), "--migrate"],
                capture_output=True,
                text=True
            )
            self.assertEqual(mig_res.returncode, 0)
            restored = sc.SovereignOrganism.reconstitute_from_seed(mig_res.stdout)
            self.assertEqual(len(restored.history_receipts), len(org.history_receipts))
            self.assertEqual(restored.cid_chain, org.cid_chain)

    # ========================================================================
    # F08: Federated Agora Quorum & Democratic Thresholds (A1 & A2)
    # ========================================================================
    def test_f08_agora_quorum_and_negative_vote_rejection(self):
        """F08: Agora rejects empty vote sessions and unanimous/sub-threshold Nay votes."""
        parliament = ag.FederatedAgoraParliament()
        c1 = ag.FederatedChamber("c1", "Chamber 1", sh.EpistemicContext.create("c1", ["ski"], 100))
        parliament.register_chamber(c1)

        prop = ag.FederatedProposal(
            proposal_id="prop_quorum",
            title="Quorum Test",
            proposal_type=ag.ProposalType.CONSTITUTIONAL_AMENDMENT,
            claim_name="claim",
            stake_atp=100,
            chamber_terms={"c1": "I"},
            target_nf="I"
        )
        parliament.proposals["prop_quorum"] = prop

        # A1: Settle with 0 votes -> Must reject quorum
        r1 = parliament.settle_proposal("prop_quorum")
        self.assertEqual(r1.status, ag.RatificationStatus.REJECTED_POLITICAL_VOTE)
        self.assertFalse(r1.is_ratified)
        self.assertIn("quorum not met", r1.rejection_reason)

        # A2: Unanimous Nay votes -> Must reject political threshold
        prop_nay = ag.FederatedProposal(
            proposal_id="prop_nay",
            title="Nay Test",
            proposal_type=ag.ProposalType.CONSTITUTIONAL_AMENDMENT,
            claim_name="claim",
            stake_atp=100,
            chamber_terms={"c1": "I"},
            target_nf="I"
        )
        parliament.proposals["prop_nay"] = prop_nay
        ballot_nay = ag.FederatedBallot.cast("c1", "aa" * 32, "prop_nay", False, 100)
        c1.ballots[ballot_nay.voter_pk_hex] = ballot_nay

        r2 = parliament.settle_proposal("prop_nay")
        self.assertEqual(r2.status, ag.RatificationStatus.REJECTED_POLITICAL_VOTE)
        self.assertFalse(r2.is_ratified)
        self.assertIn("Failed quadratic supermajority threshold", r2.rejection_reason)

    # ========================================================================
    # F09: Čech Cohomology Fracture Vetoes Affirmative Votes (A3)
    # ========================================================================
    def test_f09_cohomology_fracture_vetoes_unanimous_aye(self):
        """F09: Non-trivial Čech cohomology obstruction blocks 100% affirmative political votes."""
        parliament = ag.FederatedAgoraParliament()
        c1 = ag.FederatedChamber("c1", "Chamber 1", sh.EpistemicContext.create("c1", ["ski"], 100))
        c2 = ag.FederatedChamber("c2", "Chamber 2", sh.EpistemicContext.create("c2", ["ski"], 100))
        parliament.register_chamber(c1)
        parliament.register_chamber(c2)

        # Divergent terms across overlapping domain ['ski']
        prop_fracture = ag.FederatedProposal(
            proposal_id="prop_fracture",
            title="Fracture Proposal",
            proposal_type=ag.ProposalType.CONSTITUTIONAL_AMENDMENT,
            claim_name="claim",
            stake_atp=100,
            chamber_terms={"c1": "I", "c2": "K"},
            target_nf="I"
        )
        parliament.proposals["prop_fracture"] = prop_fracture

        # 100% Yeas cast across both chambers
        b1 = ag.FederatedBallot.cast("c1", "11" * 32, "prop_fracture", True, 100)
        b2 = ag.FederatedBallot.cast("c2", "22" * 32, "prop_fracture", True, 100)
        c1.ballots[b1.voter_pk_hex] = b1
        c2.ballots[b2.voter_pk_hex] = b2

        receipt = parliament.settle_proposal("prop_fracture")
        self.assertEqual(receipt.status, ag.RatificationStatus.REJECTED_COHOMOLOGICAL_FRACTURE)
        self.assertFalse(receipt.is_ratified)
        self.assertGreater(receipt.h1_dimension, 0)
        self.assertIn("Čech Cohomology Obstruction", receipt.rejection_reason)

    # ========================================================================
    # F10: Slashed False Equivalence Proposals (A4)
    # ========================================================================
    def test_f10_slashed_falsehood_proposal(self):
        """F10: False algebraic equivalence proposal is slashed fail-closed with stake forfeiture."""
        parliament = ag.FederatedAgoraParliament()
        c1 = ag.FederatedChamber("c1", "Chamber 1", sh.EpistemicContext.create("c1", ["ski"], 100))
        parliament.register_chamber(c1)

        # Claim says target is 'I', but expression 'K' reduces to 'K' (not 'I')
        prop_false = ag.FederatedProposal(
            proposal_id="prop_false",
            title="Falsehood Theorem",
            proposal_type=ag.ProposalType.THEOREM_CONGRUENCE,
            claim_name="false_claim",
            stake_atp=250,
            chamber_terms={"c1": "K"},
            target_nf="I"
        )
        parliament.proposals["prop_false"] = prop_false

        b = ag.FederatedBallot.cast("c1", "33" * 32, "prop_false", True, 100)
        c1.ballots[b.voter_pk_hex] = b

        receipt = parliament.settle_proposal("prop_false")
        self.assertEqual(receipt.status, ag.RatificationStatus.SLASHED_AUDIT_FAILED)
        self.assertFalse(receipt.is_ratified)
        self.assertEqual(receipt.slashed_stake, 250)
        self.assertIn("Theorem reduction divergence", receipt.rejection_reason)

    # ========================================================================
    # F11: Anti-Resurrection ReAdoptionRecord Guard (C4)
    # ========================================================================
    def test_f11_readoption_record_enforcement(self):
        """F11: Readopting a tombstoned warrant strictly requires a verified ReAdoptionRecord."""
        org = sc.SovereignOrganism.create_genesis(metabolic_capacity=50)
        mem = org.membrane
        w = sc.SovereignWarrant("w_retire", "rule", "I I", "I", atp_saved=1, hits=1, gen_admitted=0, maintenance_cost=10)
        mem.admit_warrant(w)
        mem.prune_metabolism(current_gen=1, author_pk_hex=org.author_pk_hex, secret_key_hex=org.secret_key_hex, base_cost=50)

        # Must raise EpistemicResurrectionError
        with self.assertRaises(sc.EpistemicResurrectionError):
            mem.execute_warrant_guard("w_retire")

        # Attempt readoption without ReAdoptionRecord -> Must fail closed
        new_w = sc.SovereignWarrant("w_retire", "rule", "I I", "I", atp_saved=1, hits=5, gen_admitted=1, maintenance_cost=10)
        with self.assertRaises(ValueError):
            mem.readopt_warrant("w_retire", new_w)

        # Legitimate readoption with valid signed ReAdoptionRecord
        stela = mem.tombstones["w_retire"]
        record = sc.ReAdoptionRecord(
            record_id="readopt_01",
            target_stela_id="w_retire",
            target_stela_hash=stela.tombstone_id,
            new_warrant_digest=new_w.compute_cid(),
            author_pk_hex=org.author_pk_hex,
            justification_proof="Verified fresh algebraic normal form convergence."
        )
        record.sign(org.secret_key_hex)
        mem.readopt_warrant("w_retire", new_w, record)

        # Guard now passes without raising
        mem.execute_warrant_guard("w_retire")
        self.assertIn("w_retire", mem.active_warrants)

    # ========================================================================
    # F12: Metabolic Capacity Bound B_max (C5)
    # ========================================================================
    def test_f12_metabolic_capacity_bound_enforced(self):
        """F12: Organism cannot emit valid receipts when active cost exceeds metabolic capacity."""
        tiny_org = sc.SovereignOrganism.create_genesis(metabolic_capacity=1)
        # Genesis active cost is 115 ATP (chromosomes), which exceeds capacity 1 ATP
        with self.assertRaises(ValueError):
            tiny_org.evolve_step("Over capacity step")


if __name__ == "__main__":
    unittest.main()
