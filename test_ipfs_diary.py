#!/usr/bin/env python3
# coding: utf-8
"""
test_ipfs_diary.py — Test Suite for Self-Preserving Ontogenetic Diary & IPFS Engine.
Part of Project Black-Heart (%🖤).
"""

import os
import sys
import tempfile
import unittest
import subprocess
from unittest.mock import patch, MagicMock

from cid import (
    compute_cidv1_raw,
    compute_cidv1_for_file,
    is_valid_cidv1,
    verify_data_cid,
    verify_file_cid
)
from mycelium import WarrantEpistemicGrade
from crypto import generate_keypair
from ipfs_diary import (
    OntogeneticDiaryReceipt,
    DiarySettlement,
    DiaryPolyglotCompiler,
    initialize_ontogenetic_diary,
    grow_diary_page,
    pin_to_kubo_daemon,
    DIARY_MANIFEST_PREFIX
)

class TestCidV1Raw(unittest.TestCase):
    """Verifies pure-Python standard library CIDv1 calculation."""

    def test_canonical_test_vectors(self):
        # Empty string test vector for CIDv1 raw sha256 base32
        empty_cid = compute_cidv1_raw(b"")
        self.assertEqual(empty_cid, "bafkreihdwdcefgh4dqkjv67uzcmw7ojee6xedzdetojuzjevtenxquvyku")
        self.assertTrue(is_valid_cidv1(empty_cid))
        self.assertTrue(verify_data_cid(b"", empty_cid))

        # "hello world\n" standard test vector
        hello_cid = compute_cidv1_raw(b"hello world\n")
        self.assertEqual(hello_cid, "bafkreifjjcie6lypi6ny7amxnfftagclbuxndqonfipmb64f2km2devei4")
        self.assertTrue(is_valid_cidv1(hello_cid))
        self.assertTrue(verify_data_cid(b"hello world\n", hello_cid))

    def test_cid_validation(self):
        self.assertFalse(is_valid_cidv1(""))
        self.assertFalse(is_valid_cidv1("QmXoypizjW3WknFiJnKLwHCnL72vedxjQkDDP1mXWo6uco"))  # CIDv0
        self.assertFalse(is_valid_cidv1("bafkreihdwdcefgh4dqkjv67uzcmw7ojee6xedzdetojuzjevtenxquvyk!"))  # invalid char
        self.assertFalse(is_valid_cidv1("bafkrei" + "a" * 50))  # wrong length
        self.assertFalse(is_valid_cidv1(12345))  # type error safe

    def test_file_cid_streaming(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            test_content = b"The universe is an open quine evolving across spacetime.\n" * 100
            f.write(test_content)
            temp_path = f.name
        try:
            expected_cid = compute_cidv1_raw(test_content)
            file_cid = compute_cidv1_for_file(temp_path)
            self.assertEqual(file_cid, expected_cid)
            self.assertTrue(verify_file_cid(temp_path, expected_cid))
            self.assertFalse(verify_file_cid(temp_path, "bafkreihdwdcefgh4dqkjv67uzcmw7ojee6xedzdetojuzjevtenxquvyku"))
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


class TestOntogeneticReceipt(unittest.TestCase):
    """Verifies cryptographic receipts and tamper-resistance."""

    def setUp(self):
        self.sk_hex, self.pk_hex = generate_keypair()

    def test_receipt_signing_and_verification(self):
        rec = OntogeneticDiaryReceipt(
            generation=0,
            timestamp_utc="2026-09-09T12:00:00Z",
            thought_prompt="Who are you?",
            thought_content="I am a self-referential polyglot ledger.",
            thought_hash="abcd" * 16,
            epistemic_grade=WarrantEpistemicGrade.LOCALLY_TESTED.value,
            atp_burned=42,
            prev_cid="",
            public_key_hex="",
            signature_hex="",
            receipt_hash=""
        )
        rec.sign(self.sk_hex)
        self.assertTrue(rec.is_attested())
        self.assertEqual(rec.public_key_hex, self.pk_hex)
        self.assertTrue(rec.verify())

    def test_receipt_tamper_detection(self):
        rec = OntogeneticDiaryReceipt(
            generation=1,
            timestamp_utc="2026-09-09T12:00:00Z",
            thought_prompt="Question",
            thought_content="Answer",
            thought_hash="1234" * 16,
            epistemic_grade=WarrantEpistemicGrade.RULE_DERIVED.value,
            atp_burned=10,
            prev_cid="bafkreihdwdcefgh4dqkjv67uzcmw7ojee6xedzdetojuzjevtenxquvyku",
            public_key_hex="",
            signature_hex="",
            receipt_hash=""
        )
        rec.sign(self.sk_hex)
        self.assertTrue(rec.verify())

        # Tampering with thought content
        rec_tampered = OntogeneticDiaryReceipt.from_dict(rec.to_dict())
        rec_tampered.thought_content = "Subverted Answer"
        self.assertFalse(rec_tampered.verify())

        # Tampering with epistemic grade
        rec_tampered2 = OntogeneticDiaryReceipt.from_dict(rec.to_dict())
        rec_tampered2.epistemic_grade = WarrantEpistemicGrade.REFUTED.value
        self.assertFalse(rec_tampered2.verify())

        # Tampering with generation
        rec_tampered3 = OntogeneticDiaryReceipt.from_dict(rec.to_dict())
        rec_tampered3.generation = 2
        self.assertFalse(rec_tampered3.verify())

        # Tampering with prev_cid
        rec_tampered4 = OntogeneticDiaryReceipt.from_dict(rec.to_dict())
        rec_tampered4.prev_cid = "bafkreifjjcie6lypi6ny7amxnfftagclbuxndqonfipmb64f2km2devei4"
        self.assertFalse(rec_tampered4.verify())

        # Tampering with atp_burned
        rec_tampered5 = OntogeneticDiaryReceipt.from_dict(rec.to_dict())
        rec_tampered5.atp_burned = 999
        self.assertFalse(rec_tampered5.verify())

        # Tampering with timestamp
        rec_tampered6 = OntogeneticDiaryReceipt.from_dict(rec.to_dict())
        rec_tampered6.timestamp_utc = "2099-01-01T00:00:00Z"
        self.assertFalse(rec_tampered6.verify())

        # Tampering with public key
        rec_tampered7 = OntogeneticDiaryReceipt.from_dict(rec.to_dict())
        _, other_pk = generate_keypair()
        rec_tampered7.public_key_hex = other_pk
        self.assertFalse(rec_tampered7.verify())


class TestDiaryGrowthAndAppendOnly(unittest.TestCase):
    """Verifies ISO 32000 §7.5.6 append-only growth and CID provenance."""

    def test_growth_and_prefix_immutability(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            diary_path = os.path.join(tmpdir, "diary.pdf")

            # 1. Initialize Genesis (Gen 0)
            genesis_rec, gen0_cid = initialize_ontogenetic_diary(
                diary_path,
                genesis_thought="Genesis seed of autonomous memory.",
                genesis_prompt="Initialize system",
                epistemic_grade=WarrantEpistemicGrade.PROPOSED.value
            )
            self.assertTrue(os.path.exists(diary_path))
            self.assertTrue(is_valid_cidv1(gen0_cid))

            with open(diary_path, "rb") as f:
                gen0_bytes = f.read()

            self.assertEqual(compute_cidv1_raw(gen0_bytes), gen0_cid)
            self.assertTrue(gen0_bytes.startswith(b"# coding: utf-8\nr\"\"\"%PDF-1.7\n"))

            # 2. Append Generation 1 (Gen 1)
            settlement_1 = grow_diary_page(
                diary_path,
                thought_prompt="What is the nature of time?",
                thought_content="Time is the unidirectional monotonic growth of the ledger.",
                epistemic_grade=WarrantEpistemicGrade.LOCALLY_TESTED.value,
                atp_burned=25
            )
            self.assertEqual(settlement_1.generation, 1)
            self.assertEqual(settlement_1.prev_cid, gen0_cid)
            self.assertTrue(is_valid_cidv1(settlement_1.current_cid))

            with open(diary_path, "rb") as f:
                gen1_bytes = f.read()

            # STRICT APPEND-ONLY PROPERTY: after.startswith(before)
            self.assertTrue(
                gen1_bytes.startswith(gen0_bytes),
                "Append-only failure: gen1 bytes must start with exact gen0 bytes!"
            )
            self.assertEqual(compute_cidv1_raw(gen1_bytes), settlement_1.current_cid)

            # 3. Append Generation 2 (Gen 2) with signature
            sk, pk = generate_keypair()
            settlement_2 = grow_diary_page(
                diary_path,
                thought_prompt="Can rewrites be soundly verified?",
                thought_content="Theorem proven: Interaction combinator confluence preserves Church-Rosser normal forms.",
                epistemic_grade=WarrantEpistemicGrade.RULE_DERIVED.value,
                atp_burned=50,
                secret_key_hex=sk
            )
            self.assertEqual(settlement_2.generation, 2)
            self.assertEqual(settlement_2.prev_cid, settlement_1.current_cid)
            self.assertTrue(is_valid_cidv1(settlement_2.current_cid))

            with open(diary_path, "rb") as f:
                gen2_bytes = f.read()

            # STRICT APPEND-ONLY PROPERTY FOR GEN 2
            self.assertTrue(
                gen2_bytes.startswith(gen1_bytes),
                "Append-only failure: gen2 bytes must start with exact gen1 bytes!"
            )
            self.assertEqual(compute_cidv1_raw(gen2_bytes), settlement_2.current_cid)

    def test_corrupt_manifest_and_sequence_break_detection(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            diary_path = os.path.join(tmpdir, "broken_diary.pdf")
            initialize_ontogenetic_diary(diary_path, genesis_thought="Genesis")

            # Corrupt the manifest by modifying the file bytes
            with open(diary_path, "rb") as f:
                content = f.read()

            # Corrupt the receipt hash in the manifest
            corrupted = content.replace(b'"receipt_hash": "', b'"receipt_hash": "corrupted_hash_')
            with open(diary_path, "wb") as f:
                f.write(corrupted)

            with self.assertRaises(ValueError) as ctx:
                grow_diary_page(diary_path, thought_content="Should fail due to corrupt manifest")
            self.assertIn("hash mismatch", str(ctx.exception).lower())


class TestSubprocessQuineCli(unittest.TestCase):
    """Verifies that the compiled PDF is a dual-spine polyglot executing via Python CLI."""

    def test_subprocess_cli_commands(self):
        project_root = os.path.abspath(os.path.dirname(__file__))
        sub_env = {**os.environ, "PYTHONPATH": project_root}

        with tempfile.TemporaryDirectory() as tmpdir:
            diary_path = os.path.join(tmpdir, "quine_diary.pdf")

            # Initialize diary
            initialize_ontogenetic_diary(
                diary_path,
                genesis_thought="Autonomous quine awakens in subprocess sandbox.",
                genesis_prompt="Awaken",
                epistemic_grade=WarrantEpistemicGrade.PROPOSED.value
            )

            # 1. Test python3 <diary>.pdf --status
            proc_status = subprocess.run(
                [sys.executable, diary_path, "--status"],
                capture_output=True,
                text=True,
                env=sub_env
            )
            self.assertEqual(proc_status.returncode, 0, proc_status.stderr)
            self.assertIn("PROJECT BLACK-HEART // ONTOGENTIC IPFS DIARY HUD", proc_status.stdout)
            self.assertIn("Current Generation: #0", proc_status.stdout)
            self.assertIn("Current CIDv1:      bafkrei", proc_status.stdout)

            # 2. Test python3 <diary>.pdf --append ...
            proc_append = subprocess.run(
                [
                    sys.executable,
                    diary_path,
                    "--append", "Reflecting on self-reproduction through incremental PDF streams.",
                    "--prompt", "Reflect on morphogenesis",
                    "--grade", "LOCALLY_TESTED"
                ],
                capture_output=True,
                text=True,
                env=sub_env
            )
            self.assertEqual(proc_append.returncode, 0, proc_append.stderr)
            self.assertIn("DIARY SETTLEMENT ACCOMPLISHED", proc_append.stdout)
            self.assertIn("Generation:      #1", proc_append.stdout)

            # 3. Test python3 <diary>.pdf --lineage
            proc_lineage = subprocess.run(
                [sys.executable, diary_path, "--lineage"],
                capture_output=True,
                text=True,
                env=sub_env
            )
            self.assertEqual(proc_lineage.returncode, 0, proc_lineage.stderr)
            self.assertIn("DIARY ONTOGENTIC LINEAGE ACROSS 2 GENERATIONS", proc_lineage.stdout)
            self.assertIn("#00", proc_lineage.stdout)
            self.assertIn("#01", proc_lineage.stdout)

            # 4. Test python3 <diary>.pdf --audit
            proc_audit = subprocess.run(
                [sys.executable, diary_path, "--audit"],
                capture_output=True,
                text=True,
                env=sub_env
            )
            self.assertEqual(proc_audit.returncode, 0, proc_audit.stderr)
            self.assertIn("ALL 2 DIARY PAGES CRYPTOGRAPHICALLY VERIFIED & AUDITED", proc_audit.stdout)


class TestKuboDaemonBridge(unittest.TestCase):
    """Verifies fail-closed resilience when IPFS Kubo node is offline or online."""

    def test_offline_daemon_resilience(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"%PDF-1.7 mock content for IPFS testing\n")
            temp_path = f.name
        try:
            # Point to a dead/unbound local port
            ok, msg, cid = pin_to_kubo_daemon(temp_path, daemon_url="http://127.0.0.1:59998")
            self.assertFalse(ok)
            self.assertIsNone(cid)
            self.assertIn("IPFS Kubo daemon unavailable", msg)
            self.assertIn("Local CIDv1 preserved: bafkrei", msg)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    @patch("urllib.request.urlopen")
    def test_mocked_kubo_daemon_success(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"Name":"mock.pdf","Hash":"bafkreihdwdcefgh4dqkjv67uzcmw7ojee6xedzdetojuzjevtenxquvyku","Size":"123"}\n'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"%PDF-1.7 mock content\n")
            temp_path = f.name
        try:
            ok, msg, cid = pin_to_kubo_daemon(temp_path, daemon_url="http://127.0.0.1:5001")
            self.assertTrue(ok)
            self.assertEqual(cid, "bafkreihdwdcefgh4dqkjv67uzcmw7ojee6xedzdetojuzjevtenxquvyku")
            self.assertIn("Successfully published", msg)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

if __name__ == "__main__":
    unittest.main()
