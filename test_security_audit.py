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
import stat
import builtins
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

    # ========================================================================
    # H1: Full Chain Computational Provenance (Invalid Ancestor Rejected)
    # ========================================================================
    def test_h1_invalid_ancestor_rejected_despite_valid_tip(self):
        """A valid tip must not mask a computationally invalid ancestor in chain audit or resume."""
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            bad = T.ThunkCheckpoint(
                0, "2026-09-08", "I x", "Different", 0, 0, 3, "SUSPENDED", "0" * 64,
                public_key_hex=self.pk
            )
            bad.sign(self.sk)

            good = T.ThunkCheckpoint(
                1, "2026-09-08", "I x", "x", 1, 1, 3, "SETTLED", bad.checkpoint_hash,
                public_key_hex=self.pk
            )
            good.sign(self.sk)

            pdf_path = t / "chain.pdf"
            pdf_path.write_bytes(
                T.CONTINUUM_MANIFEST_PREFIX.encode()
                + json.dumps([bad.to_dict(), good.to_dict()]).encode()
                + b"\n"
            )

            # audit_self must reject because ancestor #0 is computationally invalid
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

            self.assertIn("failed computational authenticity verification", out.getvalue())
            self.assertNotIn("Q.E.D.", out.getvalue())

            # resume_computation_in_pdf must also reject
            with self.assertRaises(ValueError) as ctx:
                T.resume_computation_in_pdf(str(pdf_path), 10, self.sk)
            self.assertIn("computational authenticity failure", str(ctx.exception))

    # ========================================================================
    # H2: Vault Rollback Restores File Permissions (Mode) and Timestamps
    # ========================================================================
    def test_h2_vault_rollback_restores_file_permissions(self):
        """Vault commit failure rollback must restore original file permissions (mode)."""
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            dest = t / "metadata"
            dest.mkdir()
            for n in ["a", "b"]:
                (dest / n).write_text("old")
                (dest / n).chmod(0o600)

            def make_archive():
                buf = io.BytesIO()
                with tarfile.open(fileobj=buf, mode="w:gz") as tar:
                    for name in ["a", "b"]:
                        m = tarfile.TarInfo(name)
                        m.size = 3
                        m.mode = 0o644
                        m.mtime = 0
                        tar.addfile(m, io.BytesIO(b"new"))
                return buf.getvalue()

            orig_copy = V.shutil.copy2
            calls = []

            def fail_second(src, dst, *args, **kw):
                calls.append(str(dst))
                if len(calls) == 2:
                    raise OSError("INJECTED_COMMIT_FAILURE")
                return orig_copy(src, dst, *args, **kw)

            with patch.object(V.shutil, "copy2", side_effect=fail_second):
                with self.assertRaises(OSError):
                    V.unpack_vault_bytes(make_archive(), str(dest))

            first = Path(calls[0])
            self.assertEqual(first.read_text(), "old")
            mode = stat.S_IMODE(first.stat().st_mode)
            self.assertEqual(mode, 0o600)

    # ========================================================================
    # H3: Rollback Failure Raises RollbackIncompleteError
    # ========================================================================
    def test_h3_vault_rollback_failure_raises_rollback_incomplete_error(self):
        """When rollback itself encounters errors, RollbackIncompleteError must be raised with details."""
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            dest = t / "rollback_io"
            dest.mkdir()
            for n in ["a", "b"]:
                (dest / n).write_text("old")

            def make_archive():
                buf = io.BytesIO()
                with tarfile.open(fileobj=buf, mode="w:gz") as tar:
                    for name in ["a", "b"]:
                        m = tarfile.TarInfo(name)
                        m.size = 3
                        m.mtime = 0
                        tar.addfile(m, io.BytesIO(b"new"))
                return buf.getvalue()

            orig_copy = V.shutil.copy2
            calls = []
            failed = [False]
            orig_open = builtins.open

            def copy(src, dst, *args, **kw):
                calls.append(str(dst))
                if len(calls) == 2:
                    failed[0] = True
                    raise OSError("INJECTED_COMMIT_FAILURE")
                return orig_copy(src, dst, *args, **kw)

            def controlled_open(file, mode="r", *args, **kw):
                if failed[0] and mode == "wb" and str(file) == calls[0]:
                    raise OSError("INJECTED_ROLLBACK_FAILURE")
                return orig_open(file, mode, *args, **kw)

            with patch.object(V.shutil, "copy2", side_effect=copy), patch("builtins.open", side_effect=controlled_open):
                with self.assertRaises(V.RollbackIncompleteError) as ctx:
                    V.unpack_vault_bytes(make_archive(), str(dest))

            err_msg = str(ctx.exception)
            self.assertIn("ROLLBACK_INCOMPLETE", err_msg)
            self.assertIn("INJECTED_COMMIT_FAILURE", err_msg)
            self.assertIn("INJECTED_ROLLBACK_FAILURE", err_msg)

    # ========================================================================
    # H4: Zero-ATP Irreducibility Check for SUSPENDED Status
    # ========================================================================
    def test_h4_zero_atp_normal_form_rejected_as_suspended(self):
        """Zero-ATP checkpoint cannot claim SUSPENDED if expression is already in normal form."""
        z = T.ThunkCheckpoint(0, "2026-09-08", "x", "x", 0, 0, 1, "SUSPENDED", "0" * 64, public_key_hex=self.pk)
        z.sign(self.sk)

        ok, err = T.verify_checkpoint_computation(z)
        self.assertFalse(ok)
        self.assertIn("already in normal form", err)

    # ========================================================================
    # J1: B4 / Unsupported Braid Profile Strictly Rejected
    # ========================================================================
    def test_j1_unsupported_b4_braid_rejected(self):
        """Fibonacci 1-qubit system must strictly reject B4 or generator index > 2."""
        from quantum import FibonacciQuantumSystem, UnsupportedBraidProfileError
        from symbiosis import BraidWord

        sys_q = FibonacciQuantumSystem()
        # B3 relation holds within numerical tolerance: sigma_1 sigma_2 sigma_1 == sigma_2 sigma_1 sigma_2
        u_b3_a = sys_q.compile_braid_to_unitary(BraidWord.from_generators(3, [1, 2, 1]))
        u_b3_b = sys_q.compile_braid_to_unitary(BraidWord.from_generators(3, [2, 1, 2]))
        diff = max(abs(getattr(u_b3_a, k) - getattr(u_b3_b, k)) for k in ("m00", "m01", "m10", "m11"))
        self.assertLess(diff, 1e-12)

        # B4 braid on 4 strands must be rejected
        with self.assertRaises(UnsupportedBraidProfileError) as ctx:
            sys_q.compile_braid_to_unitary(BraidWord.from_generators(4, [2, 3, 2]))
        self.assertIn("only supports up to 3 strands", str(ctx.exception))

        # Generator sigma_3 on any braid must be rejected
        with self.assertRaises(UnsupportedBraidProfileError) as ctx2:
            sys_q.generator_matrix(3, 1)
        self.assertIn("only supports generators sigma_1 and sigma_2", str(ctx2.exception))

    # ========================================================================
    # J2: Strict Quantum Audit from Frozen Operands (Rejects Zero Matrix & Bad Probabilities)
    # ========================================================================
    def test_j2_quantum_audit_rejects_zero_matrix_and_invalid_probabilities(self):
        """Standalone quantum runner cmd_audit must recompute invariants from operands and reject tampered state."""
        from quantum import QuantumPolyglotCompiler, ComplexMatrix2x2, QUANTUM_MANIFEST_PREFIX
        from symbiosis import BraidWord

        q = QuantumPolyglotCompiler(BraidWord.from_generators(3, [1, 2, 1]))
        qb = q.compile_pdf()

        def execute_audit(blob, mutate_fn):
            p = QUANTUM_MANIFEST_PREFIX.encode("latin1")
            start = blob.rfind(p)
            end = blob.find(b"\n", start)
            data = json.loads(blob[start + len(p):end].decode("utf-8"))
            mutate_fn(data)
            with tempfile.TemporaryDirectory() as td:
                path = Path(td) / "test_audit.pdf"
                path.write_bytes(blob[:start] + QUANTUM_MANIFEST_PREFIX.encode("latin1") + json.dumps(data).encode("utf-8") + blob[end:])
                ns = {"__name__": "audit_runner", "__file__": str(path)}
                exec(compile(q._build_runner_script(), "<runner>", "exec"), ns)
                out = io.StringIO()
                try:
                    with contextlib.redirect_stdout(out):
                        ns["cmd_audit"]()
                    code = 0
                except SystemExit as se:
                    code = se.code
                return code, out.getvalue()

        # Legitimate circuit must pass
        code_ok, out_ok = execute_audit(qb, lambda d: None)
        self.assertEqual(code_ok, 0)
        self.assertIn("AUDIT PASSED", out_ok)

        # Zero matrix must fail unitarity
        code_zero, out_zero = execute_audit(qb, lambda d: d.update(unitary=ComplexMatrix2x2.zero().to_list()))
        self.assertEqual(code_zero, 1)
        self.assertIn("AUDIT FAILED", out_zero)
        self.assertIn("Unitarity violation", out_zero)

        # Negative probability must fail bounds
        code_neg, out_neg = execute_audit(qb, lambda d: d.update(prob_0=-1, prob_1=2))
        self.assertEqual(code_neg, 1)
        self.assertIn("AUDIT FAILED", out_neg)
        self.assertIn("Probability bounds violated", out_neg)

    # ========================================================================
    # J3: Organism Verification is Pure and Idempotent
    # ========================================================================
    def test_j3_organism_verification_is_pure_and_idempotent(self):
        """Organism verify() must not mutate genomic hash or invalidate subsequent verification."""
        from organism import create_genesis_organism

        org = create_genesis_organism()
        original_hash = org.organism_hash

        first_verify = org.verify()
        self.assertTrue(first_verify)
        self.assertEqual(org.organism_hash, original_hash)
        self.assertEqual(org.compute_hash(), original_hash)

        # Repeated verify() calls must remain completely sound and idempotent
        for _ in range(5):
            self.assertTrue(org.verify())
            self.assertEqual(org.organism_hash, original_hash)
            self.assertEqual(org.compute_hash(), original_hash)

    # ========================================================================
    # J4: Organism Rejects Non-Hex or Off-Curve Public Key
    # ========================================================================
    def test_j4_organism_rejects_non_hex_or_off_curve_public_key(self):
        """Organism verify() must fail if public_key_hex is not valid hex on the Ed25519 curve."""
        from organism import Organism, Chromosome
        from crypto import is_valid_public_key

        # 'z'*64 is not valid hex
        self.assertFalse(is_valid_public_key("z" * 64))
        bogus_hex = Organism(0, "00" * 32, "z" * 64, "", [Chromosome("x", "x", "x", "x")])
        self.assertFalse(bogus_hex.verify())

        # '00'*32 is not in the prime-order subgroup
        self.assertFalse(is_valid_public_key("00" * 32))
        bogus_zero = Organism(0, "00" * 32, "00" * 32, "", [Chromosome("x", "x", "x", "x")])
        self.assertFalse(bogus_zero.verify())

    # ========================================================================
    # J5: Dual-Vault Amalgamation Preserves Preexisting Namespaced Files
    # ========================================================================
    def test_j5_dual_vault_amalgamation_preserves_preexisting_namespaced_files(self):
        """Vault amalgamation must never overwrite or destroy preexisting files from either parent."""
        from symbiosis import amalgamate_dual_vaults

        def make_vault(td, dirname, files_dict):
            root = Path(td) / dirname
            root.mkdir()
            for name, val in files_dict.items():
                p = root / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(val)
            return V.pack_files_to_vault(list(files_dict), str(root))[0]

        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            vault_a = make_vault(td, "a", {"x": b"A", "lineage_b/x": b"preexisting-A"})
            vault_b = make_vault(td, "b", {"x": b"B"})

            merged, _ = amalgamate_dual_vaults(vault_a, vault_b)
            dest = t / "out"
            dest.mkdir()
            V.unpack_vault_bytes(merged, str(dest))

            unpacked = {str(p.relative_to(dest)): p.read_bytes() for p in dest.rglob("*") if p.is_file()}

            # Both original A files must be preserved exactly!
            self.assertIn("x", unpacked)
            self.assertEqual(unpacked["x"], b"A")
            self.assertIn("lineage_b/x", unpacked)
            self.assertEqual(unpacked["lineage_b/x"], b"preexisting-A")

            # B's conflicting file must be disambiguated to lineage_b_2/x without loss!
            self.assertIn("lineage_b_2/x", unpacked)
            self.assertEqual(unpacked["lineage_b_2/x"], b"B")

    # ========================================================================
    # J6: Lineage Audit Rejects Forged Child or Parent Hashes
    # ========================================================================
    def test_j6_lineage_audit_rejects_forged_child_or_parent_hashes(self):
        """Symbiotic polyglot audit_lineage must reject tampered child_hash or parent_hash."""
        from symbiosis import SymbiosisPolyglotCompiler, SYMBIOSIS_MANIFEST_PREFIX, dialectical_crossover
        from organism import create_genesis_organism

        a = create_genesis_organism(0)
        b = create_genesis_organism(1)
        c, braid = dialectical_crossover(a, b)

        sc = SymbiosisPolyglotCompiler(c, a, b, braid)
        sb = sc.compile_pdf()

        def execute_symb_audit(blob, mutate_fn):
            p = SYMBIOSIS_MANIFEST_PREFIX.encode("latin1")
            start = blob.rfind(p)
            end = blob.find(b"\n", start)
            data = json.loads(blob[start + len(p):end].decode("utf-8"))
            mutate_fn(data)
            with tempfile.TemporaryDirectory() as td:
                path = Path(td) / "test_symb_audit.pdf"
                path.write_bytes(blob[:start] + SYMBIOSIS_MANIFEST_PREFIX.encode("latin1") + json.dumps(data).encode("utf-8") + blob[end:])
                ns = {"__name__": "audit_runner", "__file__": str(path)}
                exec(compile(sc._build_runner_script(), "<runner>", "exec"), ns)
                out = io.StringIO()
                try:
                    with contextlib.redirect_stdout(out):
                        ns["audit_lineage"]()
                    code = 0
                except SystemExit as se:
                    code = se.code
                return code, out.getvalue()

        # Legitimate symbiotic document must pass
        code_ok, out_ok = execute_symb_audit(sb, lambda d: None)
        self.assertEqual(code_ok, 0)
        self.assertIn("METABOLIC REPLAY & GENOMIC INTEGRITY VERIFIED", out_ok)

        # Forged child hash must fail
        code_child, out_child = execute_symb_audit(sb, lambda d: d.update(child_hash="f" * 64))
        self.assertEqual(code_child, 1)
        self.assertIn("LINEAGE AUDIT FAILED", out_child)
        self.assertIn("Child genomic hash mismatch", out_child)

        # Forged parent hash must fail
        code_parent, out_parent = execute_symb_audit(sb, lambda d: d.update(parent_a_hash="a" * 64))
        self.assertEqual(code_parent, 1)
        self.assertIn("LINEAGE AUDIT FAILED", out_parent)
        self.assertIn("Parent derivation hash mismatch", out_parent)

    # ========================================================================
    # J7: Morphogenesis Full-Entropy Hash Dependence
    # ========================================================================
    def test_j7_morphogenesis_full_entropy_hash_dependence(self):
        """Morphogenesis seed and parameters must fold full 256 bits of SHA-256 entropy."""
        from morphogenesis import PhenotypeGenesis, _fold_hash_entropy

        h1 = "123456789abcdef0" + "0" * 48
        h2 = "123456789abcdef0" + "f" * 48

        # Hashes sharing the first 16 hex chars have different 256-bit entropy folds
        v1 = _fold_hash_entropy(h1)
        v2 = _fold_hash_entropy(h2)
        self.assertNotEqual(v1, v2)

        p1, f1 = PhenotypeGenesis.from_hash(h1, steps=5, grid_size=16)
        p2, f2 = PhenotypeGenesis.from_hash(h2, steps=5, grid_size=16)

        # Parameters and field must not be identically frozen
        self.assertTrue(p1.F != p2.F or p1.k != p2.k or f1.v != f2.v)

    # ========================================================================
    # K1: Transition Audit Rejects Unauthorized Chromosome Mutations
    # ========================================================================
    def test_k1_transition_audit_rejects_unauthorized_chromosome_mutation(self):
        """Metamorphic transition audit must verify whole-genome invariance and reject off-target chromosome tampering."""
        from organism import create_genesis_organism, Chromosome
        from metamorphosis import contemplate_and_evolve, audit_metamorphic_transition, MetamorphicProvenanceError
        import copy

        p = create_genesis_organism()
        p.chromosomes.append(Chromosome('OPT', 'Optimizer', '🌿 (🖤 (🌿 🤍)) 🤍', '🌿 🤍', 100))
        p.chromosomes.append(Chromosome('LATE', 'Smaller gain', '🤍 x', 'x', 100))
        p.organism_hash = p.compute_hash()

        succ, log, receipt = contemplate_and_evolve(p)
        self.assertIsNotNone(succ)
        self.assertIsNotNone(receipt)

        # Untampered transition passes
        ok, msg = audit_metamorphic_transition(p, succ, receipt)
        self.assertTrue(ok)
        self.assertIn("TRANSITION VERIFIED", msg)

        # Off-target chromosome corrupted in successor
        tampered_succ = copy.deepcopy(succ)
        tampered_receipt = copy.deepcopy(receipt)
        off_target = next(c for c in tampered_succ.chromosomes if c.gene_id != receipt.gene_id)
        off_target.expression = "corrupted"
        off_target.expected_normal_form = "different"
        tampered_succ.organism_hash = tampered_succ.compute_hash()
        tampered_receipt.successor_hash = tampered_succ.organism_hash

        with self.assertRaises(MetamorphicProvenanceError) as cm:
            audit_metamorphic_transition(p, tampered_succ, tampered_receipt)
        self.assertIn("altered in successor organism without authorization", str(cm.exception))

    # ========================================================================
    # K2: Transition Audit Rejects Unknown Rules and Forged Claims
    # ========================================================================
    def test_k2_transition_audit_rejects_unknown_rules_and_forged_receipt_claims(self):
        """Metamorphic transition audit must reject unknown rules, false pre_terms, and fabricated size/ID claims."""
        from organism import create_genesis_organism, Chromosome
        from metamorphosis import contemplate_and_evolve, audit_metamorphic_transition, MetamorphicProvenanceError
        import copy

        p = create_genesis_organism()
        p.chromosomes.append(Chromosome('OPT', 'Optimizer', '🌿 (🖤 (🌿 🤍)) 🤍', '🌿 🤍', 100))
        p.organism_hash = p.compute_hash()

        succ, log, receipt = contemplate_and_evolve(p)

        # Unknown rule rejected
        bad_rule = copy.deepcopy(receipt)
        bad_rule.rule_name = "RULE_THAT_DOES_NOT_EXIST"
        with self.assertRaises(MetamorphicProvenanceError) as cm:
            audit_metamorphic_transition(p, succ, bad_rule)
        self.assertIn("Unrecognized or unauthorized mutation rule", str(cm.exception))

        # False pre-term claim rejected
        bad_pre = copy.deepcopy(receipt)
        bad_pre.pre_term = "false-history"
        with self.assertRaises(MetamorphicProvenanceError) as cm:
            audit_metamorphic_transition(p, succ, bad_pre)
        self.assertIn("Claimed pre_term", str(cm.exception))

        # Inflated size saved claim rejected
        bad_size = copy.deepcopy(receipt)
        bad_size.size_saved = 999999
        with self.assertRaises(MetamorphicProvenanceError) as cm:
            audit_metamorphic_transition(p, succ, bad_size)
        self.assertIn("Claimed size_saved", str(cm.exception))

        # Fabricated experiment ID rejected
        bad_eid = copy.deepcopy(receipt)
        bad_eid.experiment_id = "no-such-experiment"
        with self.assertRaises(MetamorphicProvenanceError) as cm:
            audit_metamorphic_transition(p, succ, bad_eid)
        self.assertIn("Experiment ID derivation mismatch", str(cm.exception))

    # ========================================================================
    # K3: Frozen Evaluator Rejects Suspended Computations as Unsettled
    # ========================================================================
    def test_k3_frozen_evaluator_rejects_suspended_computations_as_unsettled(self):
        """Computations running out of ATP budget must not receive semantic invariance or efficiency credit."""
        from glyph import App, I, Y, Var, evaluate
        from metamorphosis import FrozenEvaluator, MutationVerdict

        y = App(Y, I)
        orig = App(I, App(I, y))
        ev = FrozenEvaluator([Var('x')], atp_budget_per_test=10)

        res_a = evaluate(App(orig, Var('x')), max_atp=10)
        res_b = evaluate(App(y, Var('x')), max_atp=10)
        self.assertTrue(res_a.is_suspended())
        self.assertTrue(res_b.is_suspended())

        eval_receipt = ev.evaluate_transformation(orig, y)
        self.assertFalse(eval_receipt.semantic_preserved)
        self.assertEqual(eval_receipt.verdict, MutationVerdict.REJECTED_BUDGET_EXCEEDED)

    # ========================================================================
    # K4: Producer Binds Exact Winning Experiment Record
    # ========================================================================
    def test_k4_producer_binds_exact_winning_experiment_record(self):
        """contemplate_and_evolve must link the exact winning candidate's experiment ID rather than last record."""
        from organism import create_genesis_organism, Chromosome
        from metamorphosis import contemplate_and_evolve

        p = create_genesis_organism()
        # Gene 1 has large ATP gain (15 ATP)
        p.chromosomes.append(Chromosome('OPT', 'High gain optimizer', '🌿 (🖤 (🌿 🤍)) 🤍', '🌿 🤍', 100))
        # Gene 2 has smaller ATP gain (1 ATP)
        p.chromosomes.append(Chromosome('LATE', 'Low gain optimizer', '🤍 x', 'x', 100))
        p.organism_hash = p.compute_hash()

        succ, log, receipt = contemplate_and_evolve(p)
        self.assertIsNotNone(receipt)

        linked = next(x for x in log.records if x.experiment_id == receipt.experiment_id)
        self.assertEqual(receipt.gene_id, "OPT")
        self.assertEqual(linked.gene_id, "OPT")
        self.assertEqual(linked.candidate_term, receipt.post_term)
        self.assertEqual(linked.site_address, receipt.site_address)
        self.assertEqual(linked.rule_name, receipt.rule_name)

    # ========================================================================
    # K5: Frozen Evaluator Rejects Empty Fixtures
    # ========================================================================
    def test_k5_frozen_evaluator_rejects_empty_fixtures(self):
        """FrozenEvaluator with empty fixtures must not grant vacuous semantic credit."""
        from glyph import App, I, Var
        from metamorphosis import FrozenEvaluator, MutationVerdict

        ev = FrozenEvaluator([])
        z = ev.evaluate_transformation(App(I, I), Var('unrelated'))
        self.assertFalse(z.semantic_preserved)
        self.assertEqual(z.verdict, MutationVerdict.REJECTED_UNTESTED)
        self.assertEqual(z.test_inputs_count, 0)

    # ========================================================================
    # K6: Quantum Audit Rejects NaN and Non-Finite Claims
    # ========================================================================
    def test_k6_quantum_audit_rejects_nan_and_nonfinite_claims(self):
        """Topological quantum audit runner must reject NaN and non-finite probability/Bloch values."""
        from quantum import QuantumPolyglotCompiler
        from symbiosis import BraidWord
        import copy, json, tempfile, io, contextlib
        from pathlib import Path

        q = QuantumPolyglotCompiler(BraidWord.from_generators(3, [1, 2, 1]))
        blob = q.compile_pdf()
        ns = {'__name__': 'trusted'}
        exec(compile(q._build_runner_script(), "<runner>", "exec"), ns)
        prefix = ns['MANIFEST_PREFIX'].encode('latin1')
        start = blob.rfind(prefix)
        end = blob.find(b'\n', start)
        d = json.loads(blob[start + len(prefix):end].decode('utf-8'))

        def run_qa(mutate_fn):
            data = copy.deepcopy(d)
            mutate_fn(data)
            with tempfile.TemporaryDirectory() as td:
                f = Path(td) / "subject.pdf"
                f.write_bytes(blob[:start] + prefix + json.dumps(data).encode("utf-8") + blob[end:])
                runner_ns = {'__name__': 'trusted', '__file__': str(f)}
                exec(compile(q._build_runner_script(), "<runner>", "exec"), runner_ns)
                buf = io.StringIO()
                code = 0
                with contextlib.redirect_stdout(buf):
                    try:
                        runner_ns['cmd_audit']()
                    except SystemExit as se:
                        code = se.code
                return code, buf.getvalue()

        # Legitimate passes
        ok_code, ok_out = run_qa(lambda data: None)
        self.assertEqual(ok_code, 0)
        self.assertIn("AUDIT PASSED", ok_out)

        # NaN probabilities fail
        nan_code, nan_out = run_qa(lambda data: data.update(prob_0=float('nan'), prob_1=float('nan'), bloch={'x': float('nan'), 'y': float('nan'), 'z': float('nan')}))
        self.assertEqual(nan_code, 1)
        self.assertIn("AUDIT FAILED: Invalid or non-finite probability values", nan_out)

if __name__ == "__main__":
    unittest.main()

