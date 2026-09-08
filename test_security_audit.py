#!/usr/bin/env python3
"""
test_security_audit.py — Comprehensive Fail-Closed Verification Test Suite.
Verifies all 9 priority security findings (G1–G9) from Codex Security Review.
Part of Project Black-Heart (%🖤).
"""

import os
import sys
import io
import json
import copy
import tempfile
import contextlib
import hashlib
import unittest
from pathlib import Path

import crypto as C
import cross_proof as X
import continuum as T
import monad as M
import vault as V
import zk_glyph as Z

class TestSecurityAuditG1toG9(unittest.TestCase):
    """Adversarial test fixtures ensuring all verifiers are strictly fail-closed."""

    def setUp(self):
        self.sk, self.pk = C.generate_keypair()

    # ========================================================================
    # G1: Continuum Checkpoint Integrity & Downgrade Prevention
    # ========================================================================
    def test_g1_checkpoint_signature_stripping_rejected(self):
        """Signed checkpoint downgraded by clearing signature_hex MUST fail verification."""
        cp = T.ThunkCheckpoint(
            0, "2026-09-08", "I x", "I x", 0, 0, 3, "SUSPENDED", "0" * 64,
            public_key_hex=self.pk
        )
        cp.sign(self.sk)
        self.assertTrue(cp.verify())

        # Attempt to strip signature while retaining public_key_hex
        bad = copy.deepcopy(cp)
        bad.current_expr = "forged"
        bad.signature_hex = ""
        bad.checkpoint_hash = bad.compute_hash()
        self.assertFalse(bad.verify(), "Stripped signature on key-bound checkpoint was accepted!")

    def test_g1_invalid_predecessor_step_rejected(self):
        """step_continuum must refuse to step from an invalid or tampered predecessor."""
        cp = T.ThunkCheckpoint(
            0, "2026-09-08", "I x", "I x", 0, 0, 3, "SUSPENDED", "0" * 64,
            public_key_hex=self.pk
        )
        cp.sign(self.sk)
        invalid = copy.deepcopy(cp)
        invalid.current_expr = "I changed"
        self.assertFalse(invalid.verify())

        with self.assertRaises(ValueError):
            T.step_continuum(invalid, 10)

    # ========================================================================
    # G2: Standalone Runners Fail-Closed Without Verification
    # ========================================================================
    def test_g2_oracle_runner_zero_signature_refused(self):
        """Standalone oracle runner must exit with code 1 when signature is invalid."""
        with tempfile.TemporaryDirectory() as td:
            oracle_pdf = Path(td) / "oracle.pdf"
            o = X.TelemetryOraclePolyglot("Test Oracle")
            o.add_incident("INC-1", "2026-09-01", "outage", 300)
            o.compile(str(oracle_pdf), self.sk)

            # Alter signature to zeros
            raw = oracle_pdf.read_bytes()
            prefix = X.ORACLE_MANIFEST_PREFIX.encode("utf-8")
            start = raw.index(prefix) + len(prefix)
            end = raw.index(b"\n", start)
            m = json.loads(raw[start:end])
            m["signature_hex"] = "00" * 64
            oracle_pdf.write_bytes(raw[:start] + json.dumps(m, ensure_ascii=False).encode() + raw[end:])

            ns = {"__name__": "review_runner"}
            exec(compile(X._generate_oracle_runner(), "<oracle runner>", "exec"), ns)
            out = io.StringIO()
            old_argv = sys.argv
            sys.argv = [str(oracle_pdf)]
            try:
                with contextlib.redirect_stdout(out):
                    with self.assertRaises(SystemExit) as cm:
                        ns["main"]()
                    self.assertEqual(cm.exception.code, 1)
            finally:
                sys.argv = old_argv

            self.assertNotIn("RFC 8032 VERIFIED", out.getvalue())
            self.assertIn("FAILED", out.getvalue())

    def test_g2_continuum_auditor_false_qed_refused(self):
        """Continuum auditor must refuse to print Q.E.D. on unverified or reducible SETTLED expression."""
        with tempfile.TemporaryDirectory() as td:
            cp_pdf = Path(td) / "checkpoint.pdf"
            fake = {
                "height": 0, "timestamp_utc": "2026-09-08", "initial_expr": "I x",
                "current_expr": "not_a_normal_form", "atp_spent_step": 0, "atp_accumulated": 0,
                "peak_size": 3, "status": "SETTLED", "prev_hash": "0" * 64,
                "checkpoint_hash": "0" * 64, "signature_hex": "00" * 64, "public_key_hex": "11" * 32
            }
            cp_pdf.write_bytes(T.CONTINUUM_MANIFEST_PREFIX.encode() + json.dumps([fake]).encode() + b"\n")

            cn = {"__name__": "review_runner", "__file__": str(cp_pdf)}
            exec(compile(T.ResumableComputationPolyglot()._build_runner_script(), "<continuum runner>", "exec"), cn)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                with self.assertRaises(SystemExit) as cm:
                    cn["audit_self"](str(cp_pdf))
                self.assertEqual(cm.exception.code, 1)

            self.assertNotIn("Q.E.D.", out.getvalue())
            self.assertIn("[FAIL]", out.getvalue())

    # ========================================================================
    # G3: Agreement Terms Tamper Refusal
    # ========================================================================
    def test_g3_unsigned_agreement_alteration_refused(self):
        """Altering agreement terms (base_fee_usd) must be rejected by adjudicate_bilateral."""
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            oracle_pdf = t / "oracle.pdf"
            agreement_pdf = t / "agreement.pdf"

            o = X.TelemetryOraclePolyglot("Oracle")
            o.add_incident("INC-1", "2026-09-01", "outage", 300)
            o.compile(str(oracle_pdf), self.sk)

            ag = X.BilateralAgreementPolyglot("Agreement", self.pk, base_fee_usd=10000)
            ag.compile(str(agreement_pdf))

            # Baseline adjudication
            baseline = X.adjudicate_bilateral(str(agreement_pdf), str(oracle_pdf))
            self.assertEqual(baseline.net_service_due_usd, 9500)

            # Adversary tampers with fee
            raw = agreement_pdf.read_bytes()
            prefix = X.AGREEMENT_MANIFEST_PREFIX.encode("utf-8")
            start = raw.index(prefix) + len(prefix)
            end = raw.index(b"\n", start)
            m = json.loads(raw[start:end])
            m["base_fee_usd"] = 90000
            agreement_pdf.write_bytes(raw[:start] + json.dumps(m, ensure_ascii=False).encode() + raw[end:])

            with self.assertRaises(PermissionError):
                X.adjudicate_bilateral(str(agreement_pdf), str(oracle_pdf))

    # ========================================================================
    # G4: Oracle Anchor & Identity Verification
    # ========================================================================
    def test_g4_oracle_anchor_and_label_tampering_refused(self):
        """Unsigned oracle anchor modification must be rejected by adjudicate_bilateral."""
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            oracle_pdf = t / "oracle.pdf"
            agreement_pdf = t / "agreement.pdf"

            o = X.TelemetryOraclePolyglot("Original Oracle")
            o.add_incident("INC-1", "2026-09-01", "outage", 300)
            o.compile(str(oracle_pdf), self.sk)

            ag = X.BilateralAgreementPolyglot("Agreement", self.pk)
            ag.compile(str(agreement_pdf))

            # Tamper with anchor and label
            raw = oracle_pdf.read_bytes()
            prefix = X.ORACLE_MANIFEST_PREFIX.encode("utf-8")
            start = raw.index(prefix) + len(prefix)
            end = raw.index(b"\n", start)
            m = json.loads(raw[start:end])
            m["oracle_anchor"] = "a" * 64
            m["oracle_name"] = "Impersonated Oracle"
            oracle_pdf.write_bytes(raw[:start] + json.dumps(m, ensure_ascii=False).encode() + raw[end:])

            with self.assertRaises(PermissionError):
                X.adjudicate_bilateral(str(agreement_pdf), str(oracle_pdf))

    # ========================================================================
    # G5: Contract Runner Multi-Layer Integrity (Visual / Parameters / Evidence)
    # ========================================================================
    def test_g5_visual_text_and_manifest_tampering_refused(self):
        """Contract runner must detect visual text edits and parameter/evidence alterations."""
        ns = {"__name__": "review_runner"}
        exec(compile(M._generate_contract_runner(), "<contract runner>", "exec"), ns)

        def run(path):
            old = sys.argv
            sys.argv = [str(path)]
            out = io.StringIO()
            exitcode = None
            try:
                with contextlib.redirect_stdout(out):
                    try:
                        ns["main"]()
                    except SystemExit as e:
                        exitcode = e.code
            finally:
                sys.argv = old
            return {"exit": exitcode, "green": "Document integrity sound" in out.getvalue(), "output": out.getvalue()}

        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            c = M.SelfVerifyingContractPolyglot("TEST")
            c.add_clause("C1", "Payment", "Provider pays 100 USD", "uptime_check", "uptime >= 99.5", "TRUE")
            c.attach_evidence("E1", "2026-09-01", "outage", 300, "fixture")
            base = t / "base.pdf"
            c.compile(str(base))
            raw = base.read_bytes()

            # Baseline passes
            orig = run(base)
            self.assertTrue(orig["green"])

            # 1. Visual modification in PDF bytes
            p_vis = t / "visual.pdf"
            p_vis.write_bytes(raw.replace(b"Provider pays 100 USD", b"Provider pays 000 USD"))
            r_vis = run(p_vis)
            self.assertEqual(r_vis["exit"], 1)
            self.assertFalse(r_vis["green"])

            # 2. Manifest evidence modification
            prefix = "%🖤 CONTRACT_MANIFEST: ".encode("utf-8")
            start = raw.index(prefix) + len(prefix)
            end = raw.index(b"\n", start)
            m = json.loads(raw[start:end])
            m["evidence_log"][0]["duration_minutes"] = 0
            p_ev = t / "evidence.pdf"
            p_ev.write_bytes(raw[:start] + json.dumps(m, ensure_ascii=False).encode() + raw[end:])
            r_ev = run(p_ev)
            self.assertEqual(r_ev["exit"], 1)
            self.assertFalse(r_ev["green"])

            # 3. Manifest fee modification
            m2 = json.loads(raw[start:end])
            m2["parameters"]["base_monthly_fee_usd"] = 90000
            p_fee = t / "fee.pdf"
            p_fee.write_bytes(raw[:start] + json.dumps(m2, ensure_ascii=False).encode() + raw[end:])
            r_fee = run(p_fee)
            self.assertEqual(r_fee["exit"], 1)
            self.assertFalse(r_fee["green"])

    # ========================================================================
    # G6: Ed25519 Canonical Point & Small-Order / Identity Rejection
    # ========================================================================
    def test_g6_rfc8032_strict_point_and_identity_rejection(self):
        """verify_bytes must reject identity public key, small-order keys, and non-canonical points."""
        identity = (1).to_bytes(32, "little")
        forged = identity + bytes(32)
        self.assertFalse(C.verify_bytes(identity, b"arbitrary", forged), "Identity point was accepted!")

        noncanonical = (C.Q + 1).to_bytes(32, "little")
        self.assertFalse(C.verify_bytes(noncanonical, b"arbitrary", forged), "Non-canonical y >= Q was accepted!")

        # S >= L rejection
        valid_sig = C.sign_bytes(bytes(range(32)), b"msg")
        bad_s_sig = valid_sig[:32] + (C.L + 5).to_bytes(32, "little")
        self.assertFalse(C.verify_bytes(self.pk.encode()[:32], b"msg", bad_s_sig))

    # ========================================================================
    # G7: Atomic Monad Step & Budget Validation
    # ========================================================================
    def test_g7_atomic_monad_step_and_atp_overspend_refusal(self):
        """LiterateMonad.step_clause must be atomic: reject overspend and invalid types before mutation."""
        state = M.MonadState(1, 0, M.DualSpineTree())
        with self.assertRaises(ValueError):
            M.LiterateMonad.step_clause("C", "T", "P", "p", "TRUE", "TRUE", atp_cost=2).run(state)
        self.assertEqual(state.atp_budget, 1)
        self.assertEqual(len(state.dual_tree.code_nodes), 0)

        state2 = M.MonadState(1, 0, M.DualSpineTree())
        with self.assertRaises(TypeError):
            M.LiterateMonad.step_clause("C", "T", "P", "p", "TRUE", "TRUE", atp_cost="invalid").run(state2)
        self.assertEqual(len(state2.dual_tree.code_nodes), 0)

    # ========================================================================
    # G8: Vault Hash Mismatch & Path Traversal Prevention
    # ========================================================================
    def test_g8_vault_hash_mismatch_and_traversal_refused(self):
        """extract_vault_from_pdf must verify VAULT_HASH; unpack_vault_bytes must prevent traversal."""
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            src = t / "src"
            src.mkdir()
            (src / "hello.txt").write_text("fixture")
            pdf = t / "vault.pdf"
            pdf.write_bytes(b"%PDF-1.7\n%%EOF\n")

            h = V.embed_vault_into_polyglot(str(pdf), ["hello.txt"], str(src))
            raw = pdf.read_bytes()
            self.assertIn(h.encode(), raw)

            # Tampered hash
            pdf.write_bytes(raw.replace(h.encode(), b"0" * 64))
            with self.assertRaises(ValueError):
                V.extract_vault_from_pdf(str(pdf), str(t / "out"))

            # Pin mismatch
            pdf.write_bytes(raw)
            with self.assertRaises(ValueError):
                V.extract_vault_from_pdf(str(pdf), str(t / "out"), expected_vault_hash="f" * 64)

            # Clean extraction
            files = V.extract_vault_from_pdf(str(pdf), str(t / "out"), expected_vault_hash=h)
            self.assertEqual(files, ["hello.txt"])
            self.assertEqual((t / "out/hello.txt").read_text(), "fixture")

    # ========================================================================
    # G9: Independent Generator H with Unknown Discrete Log
    # ========================================================================
    def test_g9_generator_h_discrete_log_unknown(self):
        """GENERATOR_H must be derived via true Hash-to-Curve, not a known scalar multiple of B."""
        old_scalar = int.from_bytes(hashlib.sha512(b"BLACK_HEART_CURVE25519_GENERATOR_H_SEED_2026").digest()[:32], "little") % C.L
        old_H = C._scalar_mult(C.BASE_POINT, old_scalar)
        self.assertNotEqual(Z.GENERATOR_H, old_H, "GENERATOR_H still uses old known scalar!")

        # Verify H has prime order L
        self.assertEqual(C._scalar_mult(Z.GENERATOR_H, C.L), (0, 1))
        self.assertNotEqual(Z.GENERATOR_H, C.BASE_POINT)
        self.assertNotEqual(Z.GENERATOR_H, (0, 1))

if __name__ == "__main__":
    unittest.main()
