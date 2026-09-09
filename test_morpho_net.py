#!/usr/bin/env python3
"""
test_morpho_net.py — Unit Tests for Morphogenetic Proof-Nets & Ontogenetic Quine Polyglots.
Part of Project Black-Heart (%🖤).

Verifies:
  1. Extraction of topological singularities (peaks, saddles, sinks) from reaction-diffusion PDEs.
  2. Construction of valid Lafont Interaction Proof-Nets on T^2.
  3. Reduction of spatial interaction graphs under ATP budgets into canonical Weisfeiler-Lehman digests.
  4. Ontogenetic cryptographic receipts with Ed25519 digital signatures and Merkle history chains.
  5. Single-file self-executing ISO 32000 PDF polyglot compilation.
  6. In-place incremental ontogenetic growth ('python3 quine.pdf --grow') page-by-page.
  7. Subprocess execution of the generated polyglot PDF for --status and --audit.
"""

import os
import sys
import json
import tempfile
import unittest
import subprocess

from crypto import generate_keypair
from morphogenesis import MorphogeneticField, TuringArchetype
from interaction import AGENT_CONSTRUCT, AGENT_DUPLICATE, AGENT_ERASE
from morpho_net import (
    OntogeneticProofReceipt,
    compile_morphogenetic_proof_net,
    OntogeneticPolyglotCompiler,
    grow_ontogenetic_quine_in_pdf,
    ONTOGENY_MANIFEST_PREFIX
)

class TestMorphogeneticProofNet(unittest.TestCase):
    """Tests compilation, reduction, receipts, and quine polyglot execution."""

    def setUp(self):
        self.sk_hex, self.pk_hex = generate_keypair()

    def test_pde_singularity_extraction(self):
        """Reaction-diffusion field must yield critical points and a valid InteractionNet."""
        field = MorphogeneticField(width=32, height=32, F=0.038, k=0.061)
        field.seed_from_hash("55" * 32)
        for _ in range(60):
            field.step(dt=1.0)

        net, crit_pts = compile_morphogenetic_proof_net(field, min_v=0.10)
        self.assertGreater(len(net.nodes), 0)
        self.assertGreater(len(crit_pts), 0)
        types_present = {pt.point_type for pt in crit_pts}
        self.assertTrue(types_present.issubset({"PEAK", "SADDLE", "SINK"}))

        # Check node types
        types = {node.agent_type for node in net.nodes.values()}
        self.assertTrue(types.issubset({AGENT_CONSTRUCT, AGENT_DUPLICATE, AGENT_ERASE}))

    def test_net_reduction_and_deterministic_wl_digest(self):
        """Interaction net reduction must burn ATP and produce deterministic WL digests."""
        def run_sim():
            f = MorphogeneticField(width=28, height=28, F=0.038, k=0.061)
            f.seed_from_hash("77" * 32)
            for _ in range(50):
                f.step(dt=1.0)
            n, _ = compile_morphogenetic_proof_net(f, min_v=0.10)
            initial_digest = n.canonical_digest()
            steps, _, settled = n.reduce(max_atp=300)
            settled_digest = n.canonical_digest()
            return initial_digest, steps, settled, settled_digest

        d1, s1, st1, sd1 = run_sim()
        d2, s2, st2, sd2 = run_sim()

        self.assertEqual(d1, d2, "Initial WL digest must be deterministic")
        self.assertEqual(s1, s2, "Reduction steps must be deterministic")
        self.assertEqual(st1, st2, "Settled state must be deterministic")
        self.assertEqual(sd1, sd2, "Settled WL digest must be deterministic")
        self.assertEqual(len(sd1), 64, "WL digest must be 64-char SHA256 hex string")

    def test_ontogenetic_proof_receipt_cryptography(self):
        """Ontogenetic proof receipts must sign and verify correctly and detect tampering."""
        receipt = OntogeneticProofReceipt(
            generation=0,
            timestamp_utc="2026-09-09T12:00:00Z",
            archetype="turing_spots",
            pde_steps=80,
            initial_nodes=42,
            active_pairs=15,
            reduced_steps=24,
            atp_burned=24,
            settled=True,
            weisfeiler_lehman_digest="a" * 64,
            prev_receipt_hash="0" * 64,
            public_key_hex=self.pk_hex
        )
        receipt.sign(self.sk_hex)

        self.assertTrue(receipt.verify(), "Valid signed receipt must verify")
        self.assertEqual(len(receipt.signature_hex), 128)
        self.assertEqual(len(receipt.receipt_hash), 64)

        # Serialization round-trip
        d = receipt.to_dict()
        restored = OntogeneticProofReceipt.from_dict(d)
        self.assertTrue(restored.verify())
        self.assertEqual(restored.receipt_hash, receipt.receipt_hash)

        # Tampering detection
        restored.atp_burned += 1
        self.assertFalse(restored.verify(), "Tampered receipt must fail verification")

    def test_polyglot_compiler_structure(self):
        """Compiled ontogenetic polyglot must satisfy ISO 32000 and contain Python runner."""
        arch = TuringArchetype.SPOTS
        compiler = OntogeneticPolyglotCompiler(archetype=arch)

        receipt = OntogeneticProofReceipt(
            generation=0,
            timestamp_utc="2026-09-09T12:00:00Z",
            archetype=arch.key,
            pde_steps=40,
            initial_nodes=20,
            active_pairs=8,
            reduced_steps=12,
            atp_burned=12,
            settled=True,
            weisfeiler_lehman_digest="b" * 64,
            prev_receipt_hash="0" * 64,
            public_key_hex=self.pk_hex
        )
        receipt.sign(self.sk_hex)

        field = MorphogeneticField(width=32, height=32, F=arch.F, k=arch.k, Du=arch.Du, Dv=arch.Dv)
        field.seed_from_hash("42" * 32)
        compiler.receipts = [receipt]
        pdf_bytes = compiler.compile_bytes(field)

        # Must start with %PDF-1.7
        self.assertTrue(pdf_bytes.startswith(b"# coding: utf-8\nr\"\"\"%PDF-1.7"))
        # Must contain PDF EOF marker
        self.assertIn(b"%%EOF", pdf_bytes)
        # Must contain manifest
        self.assertIn(ONTOGENY_MANIFEST_PREFIX.encode("utf-8"), pdf_bytes)
        # Must contain python preamble
        self.assertIn(b"# coding: utf-8", pdf_bytes)
        self.assertIn(b"def cmd_status(", pdf_bytes)

    def test_incremental_growth_and_subprocess_execution(self):
        """PDF polyglot must grow generation-by-generation in-place and run under python3."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "ontogenetic_organism.pdf")

            # 1. Initialize Genesis Polyglot (Generation #0)
            arch = TuringArchetype.LABYRINTH
            field = MorphogeneticField(width=36, height=36, F=arch.F, k=arch.k, Du=arch.Du, Dv=arch.Dv)
            field.seed_from_hash("99" * 32)
            for _ in range(40):
                field.step(dt=1.0)

            net, _ = compile_morphogenetic_proof_net(field)
            init_n = len(net.nodes)
            act_p = len(net.active_pairs())
            steps_r, _, settled = net.reduce(max_atp=200)
            wl_dig = net.canonical_digest()

            rec0 = OntogeneticProofReceipt(
                generation=0,
                timestamp_utc="2026-09-09T12:00:00Z",
                archetype=arch.key,
                pde_steps=40,
                initial_nodes=init_n,
                active_pairs=act_p,
                reduced_steps=steps_r,
                atp_burned=steps_r,
                settled=settled,
                weisfeiler_lehman_digest=wl_dig,
                prev_receipt_hash="0" * 64,
                public_key_hex=self.pk_hex
            )
            rec0.sign(self.sk_hex)

            compiler = OntogeneticPolyglotCompiler(archetype=arch)
            compiler.receipts = [rec0]
            compiler.compile(pdf_path, field)

            size_gen0 = os.path.getsize(pdf_path)
            with open(pdf_path, "rb") as f:
                bytes_gen0 = f.read()

            # 2. Run 'python3 organism.pdf --status'
            res_status = subprocess.run(
                [sys.executable, pdf_path, "--status"],
                capture_output=True,
                text=True,
                timeout=15
            )
            self.assertEqual(res_status.returncode, 0, f"Status run failed: {res_status.stderr}")
            self.assertIn("Current Generation:    #0", res_status.stdout)

            # 3. Grow to Generation #1 via grow_ontogenetic_quine_in_pdf
            rec1 = grow_ontogenetic_quine_in_pdf(pdf_path, pde_steps=20, atp_budget=200, secret_key_hex=self.sk_hex)
            self.assertEqual(rec1.generation, 1)
            self.assertEqual(rec1.prev_receipt_hash, rec0.receipt_hash)
            size_gen1 = os.path.getsize(pdf_path)
            self.assertGreater(size_gen1, size_gen0, "PDF must grow incrementally in size")

            with open(pdf_path, "rb") as f:
                bytes_gen1 = f.read()
            self.assertTrue(bytes_gen1.startswith(bytes_gen0), "R5 remediation: gen1 must preserve gen0 prefix byte-for-byte")

            # 4. Grow to Generation #2 via subprocess 'python3 organism.pdf --grow' with secret key
            res_grow = subprocess.run(
                [sys.executable, pdf_path, "--grow", "--secret-key", self.sk_hex],
                capture_output=True,
                text=True,
                timeout=25
            )
            self.assertEqual(res_grow.returncode, 0, f"Grow subprocess failed: {res_grow.stderr}")
            self.assertIn("Generation #2", res_grow.stdout)
            size_gen2 = os.path.getsize(pdf_path)
            self.assertGreater(size_gen2, size_gen1)

            with open(pdf_path, "rb") as f:
                bytes_gen2 = f.read()
            self.assertTrue(bytes_gen2.startswith(bytes_gen1), "R5 remediation: gen2 must preserve gen1 prefix byte-for-byte")

            # 5. Run 'python3 organism.pdf --audit' to cryptographically audit entire lineage
            res_audit = subprocess.run(
                [sys.executable, pdf_path, "--audit"],
                capture_output=True,
                text=True,
                timeout=15
            )
            self.assertEqual(res_audit.returncode, 0, f"Audit run failed: {res_audit.stderr}")
            self.assertIn("ONTOGENETIC GENERATIONS & PROOF-NETS CRYPTOGRAPHICALLY VERIFIED", res_audit.stdout)

    def test_audit_fails_on_tampered_receipt(self):
        """Auditing a tampered or mutated receipt in the PDF manifest must fail-closed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "tampered_organism.pdf")

            arch = TuringArchetype.PULSARS
            field = MorphogeneticField(width=24, height=24, F=arch.F, k=arch.k, Du=arch.Du, Dv=arch.Dv)
            field.seed_from_hash("11" * 32)
            for _ in range(20):
                field.step(dt=1.0)

            compiler = OntogeneticPolyglotCompiler(archetype=arch)
            rec, _ = compiler.initialize_genesis(seed_hash="11" * 32, secret_key_hex=self.sk_hex, initial_pde_steps=20)
            compiler.compile(pdf_path, field)

            with open(pdf_path, "rb") as f:
                content = f.read()

            # Tamper with the proof-net digest in the manifest JSON
            tampered_content = content.replace(
                rec.weisfeiler_lehman_digest.encode("utf-8"),
                b"f" * 64
            )
            self.assertNotEqual(content, tampered_content)

            with open(pdf_path, "wb") as f:
                f.write(tampered_content)

            # Audit must detect invalid signature/hash and return non-zero exit code
            res = subprocess.run(
                [sys.executable, pdf_path, "--audit"],
                capture_output=True,
                text=True,
                timeout=15
            )
            self.assertNotEqual(res.returncode, 0)
            self.assertTrue("[FAIL]" in res.stdout or "[FAIL]" in res.stderr)

    def test_r5_and_r6_security_remediation(self):
        """Remediates R5 (strictly append-only bytes) and R6 (no derived secret keys without authorization)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = os.path.join(tmpdir, "r5_r6.pdf")
            arch = TuringArchetype.SPOTS
            field = MorphogeneticField(width=36, height=36, F=arch.F, k=arch.k, Du=arch.Du, Dv=arch.Dv)
            field.seed_from_hash("42" * 32)

            genesis = OntogeneticProofReceipt(
                generation=0,
                timestamp_utc="2026-09-09T00:00:00Z",
                archetype=arch.key,
                pde_steps=0,
                initial_nodes=0,
                active_pairs=0,
                reduced_steps=0,
                atp_burned=0,
                settled=True,
                weisfeiler_lehman_digest="b" * 64,
                prev_receipt_hash="0" * 64,
                public_key_hex=self.pk_hex
            )
            genesis.sign(self.sk_hex)
            compiler = OntogeneticPolyglotCompiler(archetype=arch)
            compiler.receipts = [genesis]
            compiler.compile(root, field)

            with open(root, "rb") as f:
                before = f.read()

            # Growth without secret key
            child = grow_ontogenetic_quine_in_pdf(root, pde_steps=1, atp_budget=10)
            with open(root, "rb") as f:
                after = f.read()

            # R5: Original prefix must be strictly preserved
            self.assertTrue(after.startswith(before), "R5: after.startswith(before) must be strictly True")

            # R6: No secret key synthesized from public receipt hash
            self.assertEqual(child.public_key_hex, "", "R6: Public key must be empty when unsigned")
            self.assertEqual(child.signature_hex, "", "R6: Signature must be empty when unsigned")
            self.assertFalse(child.is_attested(), "R6: Child must be unattested")
            self.assertFalse(child.verify(), "R6: verify() must return False for unattested child")

    def test_n10_unsigned_step_does_not_dead_end_subsequent_growth(self):
        """N10 remediation: An unsigned growth step must not dead-end subsequent growth."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = os.path.join(tmpdir, "n10_organism.pdf")
            arch = TuringArchetype.SPOTS
            field = MorphogeneticField(width=24, height=24, F=arch.F, k=arch.k, Du=arch.Du, Dv=arch.Dv)
            field.seed_from_hash("33" * 32)

            genesis = OntogeneticProofReceipt(
                generation=0,
                timestamp_utc="2026-09-09T00:00:00Z",
                archetype=arch.key,
                pde_steps=0,
                initial_nodes=0,
                active_pairs=0,
                reduced_steps=0,
                atp_burned=0,
                settled=True,
                weisfeiler_lehman_digest="c" * 64,
                prev_receipt_hash="0" * 64,
                public_key_hex=self.pk_hex
            )
            genesis.sign(self.sk_hex)
            compiler = OntogeneticPolyglotCompiler(archetype=arch)
            compiler.receipts = [genesis]
            compiler.compile(root, field)

            # Gen 1: Unsigned growth step
            gen1 = grow_ontogenetic_quine_in_pdf(root, pde_steps=1, atp_budget=10)
            self.assertFalse(gen1.is_attested())

            # Gen 2: Subsequent growth step with key must succeed cleanly without ValueError
            gen2 = grow_ontogenetic_quine_in_pdf(root, pde_steps=1, atp_budget=10, secret_key_hex=self.sk_hex)
            self.assertEqual(gen2.generation, 2)
            self.assertTrue(gen2.is_attested())
            self.assertTrue(gen2.verify())


if __name__ == "__main__":
    unittest.main()
