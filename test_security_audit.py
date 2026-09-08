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
import tarfile
import unittest
from unittest.mock import patch
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

        # S >= L rejection: valid public key and valid R point, but S scalar >= L
        valid_sk = bytes(range(32))
        valid_pk = C.public_key_from_secret(valid_sk)
        valid_sig = C.sign_bytes(valid_sk, b"msg")
        bad_s_sig = valid_sig[:32] + (C.L + 5).to_bytes(32, "little")
        self.assertFalse(C.verify_bytes(valid_pk, b"msg", bad_s_sig))

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
        import tarfile
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

            # Traversal rejection and destination integrity:
            # An archive containing valid file followed by traversal '../forbidden' must be refused
            # without overwriting or modifying files in dest directory!
            buf = io.BytesIO()
            with tarfile.open(fileobj=buf, mode="w:gz") as tar:
                a = tarfile.TarInfo("existing.txt")
                a.size = 3
                tar.addfile(a, io.BytesIO(b"new"))
                b = tarfile.TarInfo("../forbidden")
                b.size = 0
                tar.addfile(b, io.BytesIO())

            dest = t / "dest_traversal"
            dest.mkdir()
            (dest / "existing.txt").write_text("old")
            with self.assertRaises(ValueError):
                V.unpack_vault_bytes(buf.getvalue(), str(dest))
            self.assertEqual((dest / "existing.txt").read_text(), "old", "Destination was modified despite traversal refusal!")

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

    # ========================================================================
    # R1: Continuum Signer Stripping & Chain Continuity Enforcement
    # ========================================================================
    def test_r1_continuum_signer_stripping_and_continuity_refusal(self):
        """Continuum chain audit must refuse checkpoints where key and signature were stripped."""
        with tempfile.TemporaryDirectory() as td:
            pdf_path = Path(td) / "continuum.pdf"
            poly = T.ResumableComputationPolyglot("TEST CONTINUUM")
            poly.initialize("I x", 100, self.sk, self.pk)
            poly.compile(str(pdf_path))

            # Modify checkpoint 0 by erasing public key and signature
            raw = pdf_path.read_bytes()
            prefix = T.CONTINUUM_MANIFEST_PREFIX.encode("utf-8")
            start = raw.index(prefix) + len(prefix)
            end = raw.index(b"\n", start)
            cps = json.loads(raw[start:end])
            cps[0]["current_expr"] = "altered"
            cps[0]["public_key_hex"] = ""
            cps[0]["signature_hex"] = ""
            fake_cp = T.ThunkCheckpoint.from_dict(cps[0])
            cps[0]["checkpoint_hash"] = fake_cp.compute_hash()

            pdf_path.write_bytes(raw[:start] + json.dumps(cps).encode() + raw[end:])

            # Verify with expected signer pk
            self.assertFalse(fake_cp.verify(expected_public_key_hex=self.pk))

            # Auditor must reject
            cn = {"__name__": "review_runner", "__file__": str(pdf_path)}
            exec(compile(T.ResumableComputationPolyglot()._build_runner_script(), "<continuum runner>", "exec"), cn)
            with self.assertRaises(SystemExit) as cm:
                cn["audit_self"](str(pdf_path), expected_signer_pk=self.pk)
            self.assertEqual(cm.exception.code, 1)

    # ========================================================================
    # R2: Settled Checkpoint Reduction Transition Verification
    # ========================================================================
    def test_r2_settled_checkpoint_false_reduction_transition_refused(self):
        """Settled checkpoint with normal form 'Different' but initial 'I x' must fail transition replay."""
        with tempfile.TemporaryDirectory() as td:
            pdf_path = Path(td) / "false_transition.pdf"
            forged = T.ThunkCheckpoint(
                0, "2026-09-08", "I x", "Different", 0, 0, 3, "SETTLED", "0" * 64,
                public_key_hex=self.pk
            )
            forged.sign(self.sk)
            self.assertTrue(forged.verify())

            pdf_path.write_bytes(T.CONTINUUM_MANIFEST_PREFIX.encode() + json.dumps([forged.to_dict()]).encode() + b"\n")

            cn = {"__name__": "review_runner", "__file__": str(pdf_path)}
            exec(compile(T.ResumableComputationPolyglot()._build_runner_script(), "<continuum runner>", "exec"), cn)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                with self.assertRaises(SystemExit) as cm:
                    cn["audit_self"](str(pdf_path))
                self.assertEqual(cm.exception.code, 1)

            self.assertNotIn("Q.E.D.", out.getvalue())
            self.assertIn("Computational transition mismatch", out.getvalue())

    # ========================================================================
    # R3: Closed Security Schema Enforcement in Monad Polyglots
    # ========================================================================
    def test_r3_monad_missing_security_fields_aborts(self):
        """Contract runner must abort with code 1 if required security hashes are deleted (closed schema)."""
        with tempfile.TemporaryDirectory() as td:
            pdf_path = Path(td) / "contract.pdf"
            c = M.SelfVerifyingContractPolyglot("TEST")
            c.add_clause("C", "Pay", "Provider pays 100 USD", "p", "TRUE", "TRUE")
            c.attach_evidence("E", "2026-09-01", "outage", 300, "fixture")
            c.compile(str(pdf_path))

            # Alter contract by stripping stream_hash and evidence_hash
            raw = pdf_path.read_bytes()
            prefix = "%🖤 CONTRACT_MANIFEST: ".encode("utf-8")
            start = raw.index(prefix) + len(prefix)
            end = raw.index(b"\n", start)
            man = json.loads(raw[start:end])
            del man["stream_hash"]
            del man["evidence_hash"]
            pdf_path.write_bytes(raw[:start] + json.dumps(man).encode() + raw[end:])

            ns = {"__name__": "review_runner", "__file__": str(pdf_path)}
            exec(compile(M._generate_contract_runner(), "<contract runner>", "exec"), ns)
            old_argv = sys.argv
            sys.argv = [str(pdf_path)]
            out = io.StringIO()
            try:
                with contextlib.redirect_stdout(out):
                    with self.assertRaises(SystemExit) as cm:
                        ns["main"]()
                    self.assertEqual(cm.exception.code, 1)
            finally:
                sys.argv = old_argv

            self.assertIn("Missing required security field", out.getvalue())

    # ========================================================================
    # R4 & R5: Bilateral Agreement Roster & Author Binding Enforcement
    # ========================================================================
    def test_r4_and_r5_agreement_roster_and_author_binding(self):
        """Bilateral adjudication must require registered party signatures and author pin."""
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            oracle_pdf = t / "oracle.pdf"
            agreement_pdf = t / "agreement.pdf"

            o = X.TelemetryOraclePolyglot("Oracle")
            o.add_incident("I", "2026-09-01", "outage", 300)
            o.compile(str(oracle_pdf), self.sk)

            client_sk, client_pk = C.generate_keypair()
            ag = X.BilateralAgreementPolyglot("Agreement", self.pk, agreement_secret_key_hex=self.sk)
            ag.add_party("CLIENT", "Client", client_pk, secret_key_hex=client_sk)
            ag.compile(str(agreement_pdf))

            # Baseline adjudication with pin
            pin = hashlib.sha256(agreement_pdf.read_bytes()).hexdigest()
            rcpt = X.adjudicate_bilateral(str(agreement_pdf), str(oracle_pdf), expected_agreement_hash=pin)
            self.assertEqual(rcpt.net_service_due_usd, 9500)
            self.assertEqual(rcpt.trust_status, "AUTHENTICATED_PINNED")

            # R5: Popping party signature must be rejected
            raw = agreement_pdf.read_bytes()
            prefix = X.AGREEMENT_MANIFEST_PREFIX.encode("utf-8")
            start = raw.index(prefix) + len(prefix)
            end = raw.index(b"\n", start)
            m = json.loads(raw[start:end])
            del m["parties"][0]["signature_hex"]
            agreement_pdf.write_bytes(raw[:start] + json.dumps(m).encode() + raw[end:])
            with self.assertRaises(PermissionError):
                X.adjudicate_bilateral(str(agreement_pdf), str(oracle_pdf))

            # R4: Author replacement with attacker key must be rejected when expected author is pinned
            attacker_sk, attacker_pk = C.generate_keypair()
            m["base_fee_usd"] = 90000
            m["agreement_author_pk_hex"] = attacker_pk
            terms_dict = {
                "base_fee_usd": 90000,
                "parties": [{"name": p["name"], "public_key_hex": p["public_key_hex"], "role": p["role"]} for p in m["parties"]],
                "penalty_rate_usd": m["penalty_rate_usd"],
                "target_uptime_percent": m["target_uptime_percent"],
                "title": m["title"],
                "trusted_oracle_pk_hex": m["trusted_oracle_pk_hex"],
            }
            raw_terms = json.dumps(terms_dict, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
            m["agreement_signature_hex"] = C.sign_bytes(bytes.fromhex(attacker_sk), raw_terms).hex()
            # Even if party signs new terms:
            m["parties"][0]["signature_hex"] = C.sign_bytes(bytes.fromhex(client_sk), raw_terms).hex()
            agreement_pdf.write_bytes(raw[:start] + json.dumps(m).encode() + raw[end:])

            # Adjudication with expected author pin MUST raise PermissionError
            with self.assertRaises(PermissionError):
                X.adjudicate_bilateral(str(agreement_pdf), str(oracle_pdf), expected_author_pk_hex=self.pk)

    # ========================================================================
    # R6: Missing VAULT_HASH Marker Rejection
    # ========================================================================
    def test_r6_missing_vault_hash_marker_refused(self):
        """extract_vault_from_pdf must refuse extraction if %🖤 VAULT_HASH: is missing without explicit pin."""
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            src = t / "src"
            src.mkdir()
            (src / "x.txt").write_text("data")
            pdf = t / "vault.pdf"
            pdf.write_bytes(b"%PDF-1.7\n%%EOF\n")

            V.embed_vault_into_polyglot(str(pdf), ["x.txt"], str(src))

            # Strip %🖤 VAULT_HASH: line
            raw = pdf.read_bytes()
            vh_prefix = "%🖤 VAULT_HASH:".encode("utf-8")
            lines = [l for l in raw.split(b"\n") if not l.startswith(vh_prefix)]
            pdf.write_bytes(b"\n".join(lines))

            # Without pin, must refuse
            with self.assertRaises(ValueError):
                V.extract_vault_from_pdf(str(pdf), str(t / "out"))

    # ========================================================================
    # R7: Atomic Vault Extraction Preserves Destination on Failure
    # ========================================================================
    def test_r7_atomic_vault_extraction_preserves_destination_on_failure(self):
        """Failed vault extraction must not modify existing files in destination directory."""
        import tarfile
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            buf = io.BytesIO()
            with tarfile.open(fileobj=buf, mode="w:gz") as tar:
                a = tarfile.TarInfo("existing.txt")
                a.size = 3
                tar.addfile(a, io.BytesIO(b"new"))
                b = tarfile.TarInfo("../forbidden")
                b.size = 0
                tar.addfile(b, io.BytesIO())

            dest = t / "dest"
            dest.mkdir()
            (dest / "existing.txt").write_text("original_content")

            with self.assertRaises(ValueError):
                V.unpack_vault_bytes(buf.getvalue(), str(dest))

            self.assertEqual((dest / "existing.txt").read_text(), "original_content")

    # ========================================================================
    # R8: Continuum Step Checkpoint Validity
    # ========================================================================
    def test_r8_continuum_step_validity(self):
        """step_continuum on a signed checkpoint must produce a successor that passes its own verify()."""
        cp = T.ThunkCheckpoint(
            0, "2026-09-08", "I x", "I x", 0, 0, 3, "SUSPENDED", "0" * 64,
            public_key_hex=self.pk
        )
        cp.sign(self.sk)
        self.assertTrue(cp.verify())

        # 1. Step with secret key produces valid signed checkpoint
        signed_next = T.step_continuum(cp, 10, secret_key_hex=self.sk)
        self.assertTrue(signed_next.verify())
        self.assertEqual(signed_next.public_key_hex, self.pk)
        self.assertTrue(bool(signed_next.signature_hex))

        # 2. Step without secret key produces valid unsigned checkpoint (no claimed predecessor key)
        unsigned_next = T.step_continuum(cp, 10)
        self.assertTrue(unsigned_next.verify(), "Unsigned successor failed its own verify()!")
        self.assertEqual(unsigned_next.public_key_hex, "")
        self.assertEqual(unsigned_next.signature_hex, "")

    # ========================================================================
    # N1: Vault Destination Symlink Breakout Prevention
    # ========================================================================
    def test_n1_destination_symlink_traversal_refused(self):
        """Unpacking a vault into a destination containing symlinks pointing outside must fail and leave outside intact."""
        import tarfile
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            dst = t / "symlink_dest"
            dst.mkdir()
            outside = t / "outside.txt"
            outside.write_text("original_outside_content")

            # Create symlink inside destination pointing outside
            (dst / "target_link").symlink_to(outside)

            # Archive contains a regular file matching the symlink name
            buf = io.BytesIO()
            with tarfile.open(fileobj=buf, mode="w:gz") as tar:
                m = tarfile.TarInfo("target_link")
                m.size = 7
                tar.addfile(m, io.BytesIO(b"malicious"))

            with self.assertRaises(ValueError):
                V.unpack_vault_bytes(buf.getvalue(), str(dst))

            self.assertEqual(outside.read_text(), "original_outside_content", "Outside file was overwritten through symlink!")

    # ========================================================================
    # N2: Vault Commit Collision Leaves Destination Intact (Transactional)
    # ========================================================================
    def test_n2_commit_collision_leaves_destination_intact(self):
        """A type collision on a later member must abort during preflight before modifying earlier files."""
        import tarfile
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            dst = t / "commit_collision"
            dst.mkdir()
            (dst / "first").write_text("initial_first")
            (dst / "blocked").write_text("existing_regular_file")

            buf = io.BytesIO()
            with tarfile.open(fileobj=buf, mode="w:gz") as tar:
                m1 = tarfile.TarInfo("first")
                m1.size = 3
                tar.addfile(m1, io.BytesIO(b"new"))
                m2 = tarfile.TarInfo("blocked/child")
                m2.size = 4
                tar.addfile(m2, io.BytesIO(b"data"))

            with self.assertRaises(FileExistsError):
                V.unpack_vault_bytes(buf.getvalue(), str(dst))

            self.assertEqual((dst / "first").read_text(), "initial_first", "Earlier file was overwritten despite later collision!")

    # ========================================================================
    # N3: Deterministic Vault Packing Independent of Wall-Clock Time
    # ========================================================================
    def test_n3_deterministic_vault_gzip_packing(self):
        """pack_files_to_vault must produce byte-identical archives regardless of system clock."""
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            src = t / "src"
            src.mkdir()
            (src / "sample.py").write_text("print('hello deterministic world')")

            with patch("time.time", return_value=1700000000):
                archive_a, hash_a, _ = V.pack_files_to_vault(["sample.py"], str(src))

            with patch("time.time", return_value=1700000001):
                archive_b, hash_b, _ = V.pack_files_to_vault(["sample.py"], str(src))

            self.assertEqual(archive_a, archive_b, "Gzip archives differ across different timestamps!")
            self.assertEqual(hash_a, hash_b, "Vault hashes differ across different timestamps!")
            self.assertEqual(archive_a[4:8], b"\x00\x00\x00\x00", "Gzip header does not have mtime=0!")

    # ========================================================================
    # N4: Replay Verifies Actual ATP Fuel Accounting
    # ========================================================================
    def test_n4_atp_accounting_mismatch_refused(self):
        """audit_self must refuse checkpoints where claimed ATP does not match actual fuel spent."""
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            # 'I x' requires 1 ATP reduction step to reach 'x', but checkpoint claims atp_accumulated=0
            cp = T.ThunkCheckpoint(
                0, "2026-09-08", "I x", "x", 0, 0, 3, "SETTLED", "0" * 64,
                public_key_hex=self.pk
            )
            cp.sign(self.sk)

            pdf_path = t / "cp.pdf"
            pdf_path.write_bytes(T.CONTINUUM_MANIFEST_PREFIX.encode() + json.dumps([cp.to_dict()]).encode() + b"\n")

            ns = {"__name__": "review_runner", "__file__": str(pdf_path)}
            exec(compile(T.ResumableComputationPolyglot()._build_runner_script(), "<pinned runner>", "exec"), ns)

            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                with self.assertRaises(SystemExit) as cm:
                    ns["audit_self"](str(pdf_path), expected_signer_pk=self.pk)
                self.assertEqual(cm.exception.code, 1)

            self.assertIn("Computational ATP accounting mismatch", out.getvalue())
            self.assertNotIn("Q.E.D.", out.getvalue())

    # ========================================================================
    # N5: Shared Computational Gate Refuses False SETTLED in Resume
    # ========================================================================
    def test_n5_resume_computation_rejects_false_settled(self):
        """resume_computation_in_pdf must reject false settled checkpoint through shared computational verifier."""
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            forged = T.ThunkCheckpoint(
                0, "2026-09-08", "I x", "Different", 0, 0, 3, "SETTLED", "0" * 64,
                public_key_hex=self.pk
            )
            forged.sign(self.sk)

            pdf_path = t / "forged_settled.pdf"
            pdf_path.write_bytes(T.CONTINUUM_MANIFEST_PREFIX.encode() + json.dumps([forged.to_dict()]).encode() + b"\n")

            with self.assertRaises(ValueError) as ctx:
                T.resume_computation_in_pdf(str(pdf_path), 10, self.sk)

            self.assertIn("Computational transition mismatch", str(ctx.exception))

    # ========================================================================
    # F1: Closed Checkpoint Status Set & Typed Refusal for Unknown Status
    # ========================================================================
    def test_f1_unknown_status_fails_closed(self):
        """Unknown checkpoint status must be rejected across helper, audit, and resume."""
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            u = T.ThunkCheckpoint(
                0, "2026-09-08", "I x", "Different", 0, 0, 3, "TYPO", "0" * 64,
                public_key_hex=self.pk
            )
            u.sign(self.sk)

            ok, err = T.verify_checkpoint_computation(u)
            self.assertFalse(ok)
            self.assertIn("Invalid or unrecognized checkpoint status", err)

            pdf_path = t / "unknown_status.pdf"
            pdf_path.write_bytes(T.CONTINUUM_MANIFEST_PREFIX.encode() + json.dumps([u.to_dict()]).encode() + b"\n")

            # Public auditor must reject with exit code 1
            ns = {"__name__": "review_runner", "__file__": str(pdf_path)}
            oldpath = list(sys.path)
            try:
                exec(compile(T.ResumableComputationPolyglot()._build_runner_script(), "<runner>", "exec"), ns)
            finally:
                sys.path[:] = oldpath

            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                with self.assertRaises(SystemExit) as cm:
                    ns["audit_self"](str(pdf_path), expected_signer_pk=self.pk)
                self.assertEqual(cm.exception.code, 1)

            self.assertIn("invalid status", out.getvalue().lower())
            self.assertNotIn("COMPUTATION SUSPENDED", out.getvalue())
            self.assertNotIn("Q.E.D.", out.getvalue())

            # Resume must also reject
            with self.assertRaises(ValueError) as ctx:
                T.resume_computation_in_pdf(str(pdf_path), 10, self.sk)
            self.assertIn("invalid status", str(ctx.exception).lower())

    # ========================================================================
    # F2: step_continuum Refuses Computationally Invalid SUSPENDED Checkpoints
    # ========================================================================
    def test_f2_step_continuum_refuses_invalid_suspended_predecessor(self):
        """step_continuum must verify predecessor computational validity even when SUSPENDED."""
        s = T.ThunkCheckpoint(
            0, "2026-09-08", "I x", "I Different", 0, 0, 3, "SUSPENDED", "0" * 64,
            public_key_hex=self.pk
        )
        s.sign(self.sk)

        ok, err = T.verify_checkpoint_computation(s)
        self.assertFalse(ok)

        with self.assertRaises(ValueError) as ctx:
            T.step_continuum(s, 10, self.sk)

        self.assertIn("input checkpoint failed computational verification", str(ctx.exception))

    # ========================================================================
    # F3: Strict Integer Typing, Budget Invariants, and Chain Delta Accounting
    # ========================================================================
    def test_f3_atp_spent_step_invariants_and_chain_delta(self):
        """ATP step and accumulated fields must be strictly typed, bounded, and chain-consistent."""
        # Step exceeds total
        cp_exceed = T.ThunkCheckpoint(
            1, "2026-09-08", "I x", "x", 999, 1, 3, "SETTLED", "0" * 64,
            public_key_hex=self.pk
        )
        cp_exceed.sign(self.sk)
        ok, err = T.verify_checkpoint_computation(cp_exceed)
        self.assertFalse(ok)
        self.assertIn("exceeds accumulated total", err)

        # Genesis step != accumulated
        cp_genesis = T.ThunkCheckpoint(
            0, "2026-09-08", "I x", "x", 0, 1, 3, "SETTLED", "0" * 64,
            public_key_hex=self.pk
        )
        cp_genesis.sign(self.sk)
        ok, err = T.verify_checkpoint_computation(cp_genesis)
        self.assertFalse(ok)
        self.assertIn("Genesis checkpoint (height 0) step ATP", err)

        # Non-integer boolean type rejected
        cp_bool = T.ThunkCheckpoint(
            0, "2026-09-08", "I x", "x", True, True, 3, "SETTLED", "0" * 64,  # type: ignore
            public_key_hex=self.pk
        )
        ok, err = T.verify_checkpoint_computation(cp_bool)
        self.assertFalse(ok)
        self.assertIn("strict integers", err)

    # ========================================================================
    # F4: Vault Commit Engine Rollback on Mid-Extraction I/O Failure
    # ========================================================================
    def test_f4_vault_commit_failure_rolls_back_cleanly(self):
        """Vault commit failure must cleanly roll back all modified and created files."""
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            dst = t / "io-failure"
            dst.mkdir()
            (dst / "a").write_text("old")
            (dst / "b").write_text("old")

            def make_archive(entries):
                buf = io.BytesIO()
                with tarfile.open(fileobj=buf, mode="w:gz") as tar:
                    for name, data in entries:
                        m = tarfile.TarInfo(name)
                        m.size = len(data)
                        tar.addfile(m, io.BytesIO(data))
                return buf.getvalue()

            original_copy = V.shutil.copy2
            calls = []

            def fail_second(src, dest, *args, **kw):
                calls.append(str(dest))
                if len(calls) == 2:
                    raise OSError("REVIEW_INJECTED_SECOND_COPY_FAILURE")
                return original_copy(src, dest, *args, **kw)

            with patch.object(V.shutil, "copy2", side_effect=fail_second):
                with self.assertRaises(OSError) as ctx:
                    V.unpack_vault_bytes(make_archive([("a", b"new"), ("b", b"new")]), str(dst))
                self.assertEqual(str(ctx.exception), "REVIEW_INJECTED_SECOND_COPY_FAILURE")

            self.assertEqual(len(calls), 2)
            self.assertEqual((dst / "a").read_text(), "old")
            self.assertEqual((dst / "b").read_text(), "old")

if __name__ == "__main__":
    unittest.main()
