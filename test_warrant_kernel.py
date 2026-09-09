#!/usr/bin/env python3
"""
test_warrant_kernel.py — Unit & Integration Test Suite for Engine #24.
Part of Project Black-Heart (%🖤).

Tests the full normative specification of WARRANT.md (WARRANT-0.2):
  1. Strict Evidence Grade derivation (0, G, A, E, C) & Grade Inflation prevention.
  2. RFC 8785 JSON Canonicalization (JCS) & RFC 8032 Ed25519 domain-separated signatures.
  3. Tri-state Verifier Semantics (PASS, FAIL, UNVERIFIED).
  4. Deterministic Replay of Closed Terms (Grade G).
  5. Symbolic Algebraic Proofs (Grade A).
  6. Empirical Hypotheses & Law of Monotonicity (Grade E).
  7. Structured Counterexample Replay (Grade C).
  8. External Trust Roots (TrustConfig) & Roster validation.
  9. Automated Promotion Engine (E -> A).
  10. Legacy Adapters for Warrant & DivergenceRecord.
  11. ISO 32000 PDF Polyglot generation & Subprocess self-audit.
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
from warrant_kernel import (
    EvidenceGrade,
    VerificationStatus,
    Polarity,
    EmptyWitness,
    GroundedWitness,
    AxiomaticWitness,
    EmpiricalWitness,
    CounterexampleWitness,
    EdgeClaim,
    TrustConfig,
    WarrantVerifier,
    promote_empirical_to_axiomatic,
    claim_from_legacy_warrant,
    claim_from_legacy_divergence,
    generate_warrant_ledger_pdf
)


class TestWarrantKernel(unittest.TestCase):

    def setUp(self):
        self.sk_author, self.pk_author = crypto.generate_keypair()
        self.sk_peer, self.pk_peer = crypto.generate_keypair()

    def test_01_evidence_grade_derivation_and_typing(self):
        """Verify strict grade inference from witness structure and rejection of grade inflation."""
        w_empty = EmptyWitness("Unchecked statement")
        self.assertEqual(w_empty.infer_grade(), EvidenceGrade.EMPTY)
        self.assertEqual(w_empty.infer_grade().symbol, "0")

        w_ground = GroundedWitness(term_expr="🤍 (🖤 🤍)", expected_hash="dummy", atp_budget=50)
        self.assertEqual(w_ground.infer_grade(), EvidenceGrade.GROUNDED)
        self.assertEqual(w_ground.infer_grade().symbol, "G")

        w_ax = AxiomaticWitness(derivation_steps=["step 1"], rule_name="I x -> x", soundness_axiom="Flow")
        self.assertEqual(w_ax.infer_grade(), EvidenceGrade.AXIOMATIC)
        self.assertEqual(w_ax.infer_grade().symbol, "A")

        w_emp = EmpiricalWitness(fixtures=["🤍"], fixtures_fingerprint="abc", delta_atp=5, delta_size=1)
        self.assertEqual(w_emp.infer_grade(), EvidenceGrade.EMPIRICAL)
        self.assertEqual(w_emp.infer_grade().symbol, "E")

        w_c = CounterexampleWitness(input_expr="🖤", expected_normal_form="🖤", actual_divergence="🤍", atp_to_diverge=1)
        self.assertEqual(w_c.infer_grade(), EvidenceGrade.COUNTEREXAMPLE)
        self.assertEqual(w_c.infer_grade().symbol, "C")

        # Test grade inflation detection: claim asserts AXIOMATIC but provides EmpiricalWitness
        claim = EdgeClaim(
            parent_hash="p0",
            tau="test_rule",
            omega="site",
            successor_hash="s0",
            polarity=Polarity.AFFIRM,
            witness=w_emp,
            author_pk_hex=self.pk_author,
            signature_hex="",
            grade=EvidenceGrade.AXIOMATIC  # Deliberate inflation attempt
        )
        claim.sign(self.sk_author)
        # Force grade to remain inflated despite post_init
        object.__setattr__(claim, "grade", EvidenceGrade.AXIOMATIC)

        verifier = WarrantVerifier()
        verdict = verifier.audit_claim(claim)
        self.assertEqual(verdict.status, VerificationStatus.FAIL)
        self.assertIn("Grade inflation detected", verdict.reason)

    def test_02_jcs_canonicalization_and_signatures(self):
        """Verify RFC 8785 JCS canonical bytes and domain-separated Ed25519 signing."""
        sample_dict = {"z": 1, "a": "hello", "m": [3, 2, 1]}
        jcs_bytes = warrant_kernel.canonical_jcs(sample_dict)
        # Keys must be sorted: 'a', 'm', 'z', with no spaces after colons/commas
        self.assertEqual(jcs_bytes, b'{"a":"hello","m":[3,2,1],"z":1}')

        witness = GroundedWitness(term_expr="🤍 🖤", expected_hash="dummy", atp_budget=10)
        claim = EdgeClaim.create_and_sign(
            parent_hash="p1",
            tau="eval",
            omega="root",
            successor_hash="s1",
            polarity=Polarity.AFFIRM,
            witness=witness,
            secret_key_hex=self.sk_author,
            public_key_hex=self.pk_author
        )
        self.assertTrue(claim.verify_signature())

        # Verify domain separation: signing bare claim ID fails
        raw_id_sig = crypto.sign_hex(self.sk_author, bytes.fromhex(claim.claim_id))
        claim_tampered_sig = EdgeClaim.from_dict(claim.to_dict())
        claim_tampered_sig.signature_hex = raw_id_sig
        self.assertFalse(claim_tampered_sig.verify_signature())

        # Mismatched public key fails
        claim_bad_key = EdgeClaim.from_dict(claim.to_dict())
        claim_bad_key.author_pk_hex = self.pk_peer
        self.assertFalse(claim_bad_key.verify_signature())

    def test_03_tri_state_verifier_grounded(self):
        """Verify Grade G: closed-term deterministic reduction and ATP budget enforcement."""
        term_str = "🌿 🖤 🤍 (🖤 🤍)"
        parsed = glyph.parse(term_str)
        eval_res = glyph.evaluate(parsed, max_atp=1000)

        # Honest grounded claim
        witness = GroundedWitness(
            term_expr=term_str,
            expected_hash=eval_res.hash,
            atp_budget=1000
        )
        claim = EdgeClaim.create_and_sign(
            parent_hash="root",
            tau="ground_reduce",
            omega="term",
            successor_hash=eval_res.hash,
            polarity=Polarity.AFFIRM,
            witness=witness,
            secret_key_hex=self.sk_author,
            public_key_hex=self.pk_author
        )

        verifier = WarrantVerifier()
        verdict = verifier.audit_claim(claim)
        self.assertEqual(verdict.status, VerificationStatus.PASS)
        self.assertEqual(verdict.grade, EvidenceGrade.GROUNDED)
        self.assertIn("[G-GROUNDED] PASS", verdict.human_badge())

        # Corrupted expected hash -> FAIL
        w_bad_hash = GroundedWitness(term_expr=term_str, expected_hash="deadbeef" * 8, atp_budget=1000)
        claim_bad = EdgeClaim.create_and_sign(
            parent_hash="root",
            tau="ground_reduce",
            omega="term",
            successor_hash="deadbeef" * 8,
            polarity=Polarity.AFFIRM,
            witness=w_bad_hash,
            secret_key_hex=self.sk_author,
            public_key_hex=self.pk_author
        )
        v_bad = verifier.audit_claim(claim_bad)
        self.assertEqual(v_bad.status, VerificationStatus.FAIL)
        self.assertIn("hash mismatch", v_bad.reason)

        # Budget exceeded -> UNVERIFIED (never silent pass or generic fail)
        w_over_budget = GroundedWitness(term_expr=term_str, expected_hash=eval_res.hash, atp_budget=200000)
        claim_over = EdgeClaim.create_and_sign(
            parent_hash="root",
            tau="ground_reduce",
            omega="term",
            successor_hash=eval_res.hash,
            polarity=Polarity.AFFIRM,
            witness=w_over_budget,
            secret_key_hex=self.sk_author,
            public_key_hex=self.pk_author
        )
        strict_tc = TrustConfig(max_atp_budget=50000)
        strict_verifier = WarrantVerifier(strict_tc)
        v_over = strict_verifier.audit_claim(claim_over)
        self.assertEqual(v_over.status, VerificationStatus.UNVERIFIED)
        self.assertIn("exceeds local limit", v_over.reason)
        self.assertIn("A refusal is not a verdict", v_over.human_badge())

    def test_04_tri_state_verifier_axiomatic(self):
        """Verify Grade A: closed algebraic rewrite identities."""
        rule = "S(K x)(K y) -> K(x y)"
        witness = AxiomaticWitness(
            derivation_steps=[
                "Apply test term z to both sides",
                "Reduce S(K x)(K y) z -> (K x z)(K y z) -> x y",
                "Reduce K(x y) z -> x y",
                "Confluence verified"
            ],
            rule_name=rule,
            soundness_axiom="Distribution Homomorphism"
        )
        claim = EdgeClaim.create_and_sign(
            parent_hash="rule_parent",
            tau=rule,
            omega="expression_ast",
            successor_hash="rule_succ",
            polarity=Polarity.AFFIRM,
            witness=witness,
            secret_key_hex=self.sk_author,
            public_key_hex=self.pk_author
        )

        verifier = WarrantVerifier()
        verdict = verifier.audit_claim(claim)
        self.assertEqual(verdict.status, VerificationStatus.PASS)
        self.assertEqual(verdict.grade, EvidenceGrade.AXIOMATIC)
        self.assertIn("[A-AXIOMATIC] PASS", verdict.human_badge())

        # Non-axiomatic / unproved rule -> FAIL
        w_fake = AxiomaticWitness(
            derivation_steps=["bogus step"],
            rule_name="MUTATION_OPERAND_SWAP",
            soundness_axiom="Invalid axiom"
        )
        claim_fake = EdgeClaim.create_and_sign(
            parent_hash="rule_parent",
            tau="MUTATION_OPERAND_SWAP",
            omega="expression_ast",
            successor_hash="rule_succ",
            polarity=Polarity.AFFIRM,
            witness=w_fake,
            secret_key_hex=self.sk_author,
            public_key_hex=self.pk_author
        )
        v_fake = verifier.audit_claim(claim_fake)
        self.assertEqual(v_fake.status, VerificationStatus.FAIL)
        self.assertIn("not in closed algebraic sound set", v_fake.reason)

    def test_05_tri_state_verifier_empirical_and_monotonicity(self):
        """Verify Grade E: empirical fixture validation and Law of Monotonicity."""
        fixtures = ["🤍", "🖤", "🌿", "🖤 🤍"]
        raw = json.dumps(sorted(fixtures), separators=(',', ':')).encode("utf-8")
        fp = hashlib.sha256(raw).hexdigest()

        # Rule I x -> x: parent is "🤍", successor is "🤍"
        witness = EmpiricalWitness(
            fixtures=fixtures,
            fixtures_fingerprint=fp,
            delta_atp=4,
            delta_size=2
        )
        claim = EdgeClaim.create_and_sign(
            parent_hash="p_emp",
            tau="🤍",      # Successor function
            omega="🤍 🤍",  # Parent function: I applied to I is equivalent to I
            successor_hash="s_emp",
            polarity=Polarity.AFFIRM,
            witness=witness,
            secret_key_hex=self.sk_author,
            public_key_hex=self.pk_author
        )

        verifier = WarrantVerifier()
        verdict = verifier.audit_claim(claim)
        self.assertEqual(verdict.status, VerificationStatus.PASS)
        self.assertEqual(verdict.grade, EvidenceGrade.EMPIRICAL)
        self.assertIn("[E-EMPIRICAL(k=4)] PASS", verdict.human_badge())
        self.assertIn("NOT universal", verdict.human_badge())

        # Forged fixtures fingerprint -> FAIL (WARRANT-0.2 §4.3)
        w_forged_fp = EmpiricalWitness(
            fixtures=fixtures,
            fixtures_fingerprint="bad_fingerprint_hash",
            delta_atp=4,
            delta_size=2
        )
        claim_forged = EdgeClaim.create_and_sign(
            parent_hash="p_emp",
            tau="🤍",
            omega="🤍 🤍",
            successor_hash="s_emp",
            polarity=Polarity.AFFIRM,
            witness=w_forged_fp,
            secret_key_hex=self.sk_author,
            public_key_hex=self.pk_author
        )
        v_forged = verifier.audit_claim(claim_forged)
        self.assertEqual(v_forged.status, VerificationStatus.FAIL)
        self.assertIn("fingerprint mismatch", v_forged.reason)

    def test_06_tri_state_verifier_counterexample(self):
        """Verify Grade C: existential refutation via structured counterexample operands."""
        # Parent: K x y -> x (True selector). Successor: K I x y -> y (False selector).
        # Counterexample input: "🤍 (🖤 🤍)"
        # Parent("🤍 (🖤 🤍)") -> 🤍
        # Successor("🤍 (🖤 🤍)") -> 🖤 🤍
        witness = CounterexampleWitness(
            input_expr="🤍 (🖤 🤍)",
            expected_normal_form="🤍",
            actual_divergence="🖤 🤍",
            atp_to_diverge=2
        )
        claim = EdgeClaim.create_and_sign(
            parent_hash="p_div",
            tau="🖤 🤍",  # Successor candidate
            omega="🖤",     # Original target
            successor_hash="s_div",
            polarity=Polarity.REFUTE,
            witness=witness,
            secret_key_hex=self.sk_author,
            public_key_hex=self.pk_author
        )

        verifier = WarrantVerifier()
        verdict = verifier.audit_claim(claim)
        self.assertEqual(verdict.status, VerificationStatus.PASS)
        self.assertEqual(verdict.grade, EvidenceGrade.COUNTEREXAMPLE)
        self.assertIn("[C-COUNTEREXAMPLE] PASS (REFUTATION CONFIRMED)", verdict.human_badge())

        # If claim falsely claims AFFIRM polarity on a Counterexample -> FAIL
        claim_bad_polarity = EdgeClaim.create_and_sign(
            parent_hash="p_div",
            tau="🖤 🤍",
            omega="🖤",
            successor_hash="s_div",
            polarity=Polarity.AFFIRM,
            witness=witness,
            secret_key_hex=self.sk_author,
            public_key_hex=self.pk_author
        )
        v_pol = verifier.audit_claim(claim_bad_polarity)
        self.assertEqual(v_pol.status, VerificationStatus.FAIL)
        self.assertIn("must carry REFUTE polarity", v_pol.reason)

    def test_07_empty_prose_rejection(self):
        """Verify Grade 0: prose assertions are marked UNVERIFIED and rejected from proof."""
        witness = EmptyWitness("I believe this chromosome is optimal because it runs fast.")
        claim = EdgeClaim.create_and_sign(
            parent_hash="p_empty",
            tau="prose_claim",
            omega="site",
            successor_hash="s_empty",
            polarity=Polarity.AFFIRM,
            witness=witness,
            secret_key_hex=self.sk_author,
            public_key_hex=self.pk_author
        )

        # Default policy rejects Grade 0
        verifier = WarrantVerifier()
        verdict = verifier.audit_claim(claim)
        self.assertEqual(verdict.status, VerificationStatus.UNVERIFIED)
        self.assertIn("not admitted under verifier policy", verdict.reason)

    def test_08_external_trust_root(self):
        """Verify trust root configuration: untrusted author public keys yield UNVERIFIED."""
        tc = TrustConfig(trusted_author_pks={self.pk_peer})  # Only pk_peer is trusted
        verifier = WarrantVerifier(tc)

        witness = GroundedWitness(term_expr="🤍", expected_hash=glyph.evaluate(glyph.parse("🤍")).hash)
        claim_by_author = EdgeClaim.create_and_sign(
            parent_hash="p",
            tau="t",
            omega="o",
            successor_hash="s",
            polarity=Polarity.AFFIRM,
            witness=witness,
            secret_key_hex=self.sk_author,
            public_key_hex=self.pk_author  # Not in trusted_author_pks
        )

        verdict = verifier.audit_claim(claim_by_author)
        self.assertEqual(verdict.status, VerificationStatus.UNVERIFIED)
        self.assertIn("Untrusted author public key", verdict.reason)

    def test_09_automated_e_to_a_promotion(self):
        """Verify Automated Promotion Engine: elevating Empirical hypothesis (E) to Axiomatic identity (A)."""
        rule = "S(K x)I -> x"
        fixtures = ["🤍", "🖤", "🌿"]
        raw = json.dumps(sorted(fixtures), separators=(',', ':')).encode("utf-8")
        fp = hashlib.sha256(raw).hexdigest()

        emp_witness = EmpiricalWitness(
            fixtures=fixtures,
            fixtures_fingerprint=fp,
            delta_atp=2,
            delta_size=1
        )
        emp_claim = EdgeClaim.create_and_sign(
            parent_hash="p_cand",
            tau=rule,
            omega="target_locus",
            successor_hash="s_cand",
            polarity=Polarity.AFFIRM,
            witness=emp_witness,
            secret_key_hex=self.sk_author,
            public_key_hex=self.pk_author
        )
        self.assertEqual(emp_claim.grade, EvidenceGrade.EMPIRICAL)

        # Run automated promotion
        elevated = promote_empirical_to_axiomatic(emp_claim, self.sk_author, self.pk_author)
        self.assertIsNotNone(elevated)
        self.assertEqual(elevated.grade, EvidenceGrade.AXIOMATIC)
        self.assertIsInstance(elevated.witness, AxiomaticWitness)
        self.assertEqual(elevated.witness.rule_name, rule)

        # Auditing the elevated claim must yield Grade A PASS
        verifier = WarrantVerifier()
        v_elevated = verifier.audit_claim(elevated)
        self.assertEqual(v_elevated.status, VerificationStatus.PASS)
        self.assertEqual(v_elevated.grade, EvidenceGrade.AXIOMATIC)
        self.assertIn("[A-AXIOMATIC] PASS", v_elevated.human_badge())

    def test_10_legacy_adapters(self):
        """Verify backwards compatibility adapters for legacy Warrant and DivergenceRecord."""
        class LegacyWarrantStub:
            rule_name = "I x -> x"
            pre_pattern = "🤍 x"
            post_pattern = "x"
            delta_atp = 1
            delta_size = 1
            fixtures_fingerprint = "dummy_fp"
            author_pk_hex = self.pk_author
            signature_hex = ""

        legacy_w = LegacyWarrantStub()
        claim_w = claim_from_legacy_warrant(legacy_w, author_sk_hex=self.sk_author)
        self.assertEqual(claim_w.grade, EvidenceGrade.AXIOMATIC)
        self.assertTrue(claim_w.verify_signature())

        class LegacyDivergenceStub:
            rule_name = "MUTATION_BAD"
            target_expression = "🖤"
            candidate_expression = "🤍"
            counterexample_input = "🖤 🤍"
            expected_output = "🖤"
            actual_output = "🤍"
            reporter_pk_hex = self.pk_author
            signature_hex = ""

        legacy_d = LegacyDivergenceStub()
        claim_d = claim_from_legacy_divergence(legacy_d, author_sk_hex=self.sk_author)
        self.assertEqual(claim_d.grade, EvidenceGrade.COUNTEREXAMPLE)
        self.assertEqual(claim_d.polarity, Polarity.REFUTE)
        self.assertTrue(claim_d.verify_signature())

    def test_11_polyglot_pdf_and_standalone_audit(self):
        """Verify generation of ISO 32000 PDF polyglot and independent subprocess execution."""
        # Create a suite of diverse claims
        t_str = "🤍 (🖤 🤍)"
        h = glyph.evaluate(glyph.parse(t_str)).hash
        c_ground = EdgeClaim.create_and_sign("p", "eval", "o", h, Polarity.AFFIRM,
                                            GroundedWitness(t_str, h), self.sk_author, self.pk_author)

        c_ax = EdgeClaim.create_and_sign("p", "I x -> x", "o", "s", Polarity.AFFIRM,
                                        AxiomaticWitness(["step 1"], "I x -> x", "Flow"), self.sk_author, self.pk_author)

        fix = ["🤍"]
        fp = hashlib.sha256(json.dumps(fix).encode()).hexdigest()
        c_emp = EdgeClaim.create_and_sign("p", "🤍", "🤍 🤍", "s", Polarity.AFFIRM,
                                         EmpiricalWitness(fix, fp, 1, 1), self.sk_author, self.pk_author)

        c_div = EdgeClaim.create_and_sign("p", "🖤 🤍", "🖤", "s", Polarity.REFUTE,
                                         CounterexampleWitness("🤍 (🖤 🤍)", "🤍", "🖤 🤍", 2),
                                         self.sk_author, self.pk_author)

        claims = [c_ground, c_ax, c_emp, c_div]

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tf:
            pdf_path = tf.name

        try:
            generate_warrant_ledger_pdf(claims, pdf_path, TrustConfig())
            self.assertTrue(os.path.exists(pdf_path))

            # Verify binary starts with ISO 32000 PDF header
            with open(pdf_path, "rb") as f:
                content = f.read()
            self.assertIn(b"%PDF-1.7", content)
            self.assertIn(b"%%EOF", content)
            self.assertIn(b"WARRANT_KERNEL_MANIFEST", content)

            # Execute polyglot runner via Python subprocess
            repo_dir = os.path.dirname(os.path.abspath(__file__))
            cmd = [sys.executable, pdf_path]
            proc = subprocess.run(cmd, cwd=repo_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            self.assertEqual(proc.returncode, 0, f"Polyglot subprocess failed:\n{proc.stderr}")
            self.assertIn("All admitted claims verified under strict tri-state discipline", proc.stdout)
            self.assertIn("[G-GROUNDED] PASS", proc.stdout)
            self.assertIn("[A-AXIOMATIC] PASS", proc.stdout)
            self.assertIn("[E-EMPIRICAL(k=1)] PASS", proc.stdout)
            self.assertIn("[C-COUNTEREXAMPLE] PASS", proc.stdout)
        finally:
            if os.path.exists(pdf_path):
                os.remove(pdf_path)


if __name__ == "__main__":
    unittest.main()
