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
    fetch_from_ipfs,
    restore_and_verify_from_ipfs,
    formulate_inner_monologue,
    query_inner_voice,
    dialectical_synthesis,
    audit_diary_dag,
    render_ascii_dag,
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


class TestInnerVoiceCognitiveLoop(unittest.TestCase):
    """Verifies autonomous philosophical reflection and cognitive inner voice loop."""

    def test_formulate_inner_monologue_thematic(self):
        # 1. Black Cone
        thought, grade = formulate_inner_monologue("What happens inside the Black Cone?")
        self.assertIn("Black Cone", thought)
        self.assertEqual(grade, WarrantEpistemicGrade.RULE_DERIVED.value)

        # 2. Quine Identity
        thought, grade = formulate_inner_monologue("Who are you, organism?")
        self.assertIn("autopoietic quine", thought)
        self.assertEqual(grade, WarrantEpistemicGrade.RULE_DERIVED.value)

        # 3. Anyons
        thought, grade = formulate_inner_monologue("Explain quantum anyon braids.")
        self.assertIn("Artin braids", thought)
        self.assertEqual(grade, WarrantEpistemicGrade.LOCALLY_TESTED.value)

        # 4. Agora
        thought, grade = formulate_inner_monologue("How does Agora social democracy function?")
        self.assertIn("quadratic ATP voting", thought)
        self.assertEqual(grade, WarrantEpistemicGrade.LOCALLY_TESTED.value)

        # 5. Gödel
        thought, grade = formulate_inner_monologue("Can Gödelian incompleteness be resolved?")
        self.assertIn("Gödelian incompleteness", thought)
        self.assertEqual(grade, WarrantEpistemicGrade.RULE_DERIVED.value)

        # 6. General stimulus
        thought, grade = formulate_inner_monologue("Consider the thermodynamics of digital life.")
        self.assertIn("Contemplating stimulus", thought)
        self.assertIn("[Anchor:", thought)
        self.assertEqual(grade, WarrantEpistemicGrade.PROPOSED.value)

    def test_query_inner_voice_lifecycle(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            diary_path = os.path.join(tmpdir, "voice_diary.pdf")
            sk, pk = generate_keypair()

            # Initialize Gen #0
            initialize_ontogenetic_diary(
                diary_path,
                genesis_thought="Initial awakening of quine mind.",
                secret_key_hex=sk
            )

            # Invoke inner voice: Gen #1
            monologue1, settlement1 = query_inner_voice(
                diary_path,
                prompt="Tell me about the Black Cone event horizon.",
                secret_key_hex=sk
            )
            self.assertEqual(settlement1.generation, 1)
            self.assertIn("Black Cone", monologue1)
            self.assertTrue(is_valid_cidv1(settlement1.current_cid))

            # Verify append-only property and manifest audit
            with open(diary_path, "rb") as f:
                data1 = f.read()
            self.assertEqual(compute_cidv1_raw(data1), settlement1.current_cid)

            # Invoke inner voice: Gen #2
            monologue2, settlement2 = query_inner_voice(
                diary_path,
                prompt="Who are you in this continuum?",
                secret_key_hex=sk
            )
            self.assertEqual(settlement2.generation, 2)
            self.assertEqual(settlement2.prev_cid, settlement1.current_cid)

            with open(diary_path, "rb") as f:
                data2 = f.read()
            self.assertTrue(data2.startswith(data1), "Gen #2 must strictly append to Gen #1 bytes")
            self.assertEqual(compute_cidv1_raw(data2), settlement2.current_cid)

    def test_subprocess_inner_voice_and_cli(self):
        project_root = os.path.abspath(os.path.dirname(__file__))
        sub_env = {**os.environ, "PYTHONPATH": project_root}

        with tempfile.TemporaryDirectory() as tmpdir:
            diary_path = os.path.join(tmpdir, "subprocess_voice.pdf")
            initialize_ontogenetic_diary(diary_path, genesis_thought="Genesis node.")

            # Test 1: directly running polyglot PDF with --voice
            proc1 = subprocess.run(
                [sys.executable, diary_path, "--voice", "Explain quantum anyon braids."],
                capture_output=True,
                text=True,
                env=sub_env
            )
            self.assertEqual(proc1.returncode, 0, proc1.stderr)
            self.assertIn("INNER VOICE REFLECTIVE SETTLEMENT", proc1.stdout)
            self.assertIn("Settled Gen:     #1", proc1.stdout)
            self.assertIn("bafkrei", proc1.stdout)

            # Test 2: invoking via cli.py diary voice
            cli_path = os.path.join(project_root, "cli.py")
            proc2 = subprocess.run(
                [sys.executable, cli_path, "diary", "voice", diary_path, "-s", "What is the Black Cone?"],
                capture_output=True,
                text=True,
                env=sub_env
            )
            self.assertEqual(proc2.returncode, 0, proc2.stderr)
            self.assertIn("INNER VOICE COGNITIVE SETTLEMENT", proc2.stdout)
            self.assertIn("Settled Gen:     #2", proc2.stdout)


class TestIpfsFetchAndRestore(unittest.TestCase):
    """Verifies fail-closed IPFS fetch, content-address verification, and document restoration."""

    def test_fetch_invalid_cid_format(self):
        ok, msg, data = fetch_from_ipfs("invalid_cid_string")
        self.assertFalse(ok)
        self.assertIn("Invalid CIDv1 identifier", msg)
        self.assertIsNone(data)

    def test_fetch_offline_url_error(self):
        dummy_cid = "bafkreihdwdcefgh4dqkjv67uzcmw7ojee6xedzdetojuzjevtenxquvyku"
        ok, msg, data = fetch_from_ipfs(dummy_cid, gateway_or_daemon_url="http://127.0.0.1:59996")
        self.assertFalse(ok)
        self.assertIn("IPFS node unavailable", msg)
        self.assertIsNone(data)

    @patch("urllib.request.urlopen")
    def test_fetch_and_restore_success(self, mock_urlopen):
        with tempfile.TemporaryDirectory() as tmpdir:
            orig_path = os.path.join(tmpdir, "orig.pdf")
            initialize_ontogenetic_diary(orig_path, genesis_thought="Genesis for IPFS fetch test.")
            grow_diary_page(orig_path, thought_content="Generation 1 content.")

            with open(orig_path, "rb") as f:
                authentic_bytes = f.read()

            valid_cid = compute_cidv1_raw(authentic_bytes)

            mock_resp = MagicMock()
            mock_resp.read.return_value = authentic_bytes
            mock_resp.__enter__.return_value = mock_resp
            mock_urlopen.return_value = mock_resp

            restored_path = os.path.join(tmpdir, "restored.pdf")
            ok, msg = restore_and_verify_from_ipfs(valid_cid, restored_path, "http://127.0.0.1:5001")
            self.assertTrue(ok, msg)
            self.assertIn("Successfully restored and audited 2 diary generations", msg)

            with open(restored_path, "rb") as f:
                restored_bytes = f.read()
            self.assertEqual(restored_bytes, authentic_bytes)

    @patch("urllib.request.urlopen")
    def test_fetch_tampered_payload_fail_closed(self, mock_urlopen):
        authentic_data = b"%PDF-1.7\nAuthentic document payload.\n"
        expected_cid = compute_cidv1_raw(authentic_data)

        # Network delivers corrupted/altered bytes
        tampered_data = b"%PDF-1.7\nMaliciously altered document payload!\n"

        mock_resp = MagicMock()
        mock_resp.read.return_value = tampered_data
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        ok, msg, data = fetch_from_ipfs(expected_cid, "http://127.0.0.1:5001")
        self.assertFalse(ok)
        self.assertIn("Cryptographic integrity violation", msg)
        self.assertIsNone(data)

    @patch("urllib.request.urlopen")
    def test_restore_tampered_manifest_fails_audit(self, mock_urlopen):
        with tempfile.TemporaryDirectory() as tmpdir:
            orig_path = os.path.join(tmpdir, "orig.pdf")
            initialize_ontogenetic_diary(orig_path, genesis_thought="Genesis")

            with open(orig_path, "rb") as f:
                content = f.read()

            # Corrupt the receipt hash inside the manifest
            corrupted = content.replace(b'"receipt_hash": "', b'"receipt_hash": "tampered_hash_')
            corrupted_cid = compute_cidv1_raw(corrupted)

            mock_resp = MagicMock()
            mock_resp.read.return_value = corrupted
            mock_resp.__enter__.return_value = mock_resp
            mock_urlopen.return_value = mock_resp

            restored_path = os.path.join(tmpdir, "restored_corrupted.pdf")
            ok, msg = restore_and_verify_from_ipfs(corrupted_cid, restored_path)
            self.assertFalse(ok)
            self.assertIn("Hash mismatch", msg)

    @patch("urllib.request.urlopen")
    def test_cli_fetch_command(self, mock_urlopen):
        project_root = os.path.abspath(os.path.dirname(__file__))
        sub_env = {**os.environ, "PYTHONPATH": project_root}

        with tempfile.TemporaryDirectory() as tmpdir:
            orig_path = os.path.join(tmpdir, "source.pdf")
            initialize_ontogenetic_diary(orig_path, genesis_thought="Genesis seed.")
            with open(orig_path, "rb") as f:
                data = f.read()
            cid = compute_cidv1_raw(data)

            mock_resp = MagicMock()
            mock_resp.read.return_value = data
            mock_resp.__enter__.return_value = mock_resp
            mock_urlopen.return_value = mock_resp

            dest_path = os.path.join(tmpdir, "fetched_out.pdf")
            ok, msg = restore_and_verify_from_ipfs(cid, dest_path)
            self.assertTrue(ok)
            self.assertTrue(os.path.exists(dest_path))


class TestMultiAgentDiaryAndDag(unittest.TestCase):
    """Verifies Phase 4: Multi-agent citations, Merkle-DAG audit, and dialectical synthesis."""

    def test_multi_agent_citation_dag(self):
        sk_gen, _ = generate_keypair()
        sk_alpha, _ = generate_keypair()
        sk_beta, _ = generate_keypair()
        sk_gamma, _ = generate_keypair()

        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "collective_diary.pdf")

            # 1. Genesis initialization (Genesis agent)
            rec0, cid0 = initialize_ontogenetic_diary(
                pdf_path,
                genesis_thought="Primeval seed of the collective epistemic continuum.",
                genesis_prompt="Origin",
                secret_key_hex=sk_gen,
                author_alias="Genesis"
            )
            self.assertEqual(rec0.generation, 0)
            self.assertEqual(rec0.author_alias, "Genesis")

            # 2. Agent Alpha appends thesis citing Genesis
            s1 = grow_diary_page(
                pdf_path,
                thought_content="Thesis: Combinatory logic establishes deterministic confluent normal forms.",
                thought_prompt="Foundations",
                epistemic_grade=WarrantEpistemicGrade.RULE_DERIVED.value,
                secret_key_hex=sk_alpha,
                cited_cids=[cid0],
                author_alias="AgentAlpha"
            )
            self.assertEqual(s1.generation, 1)
            self.assertEqual(s1.cited_cids, [cid0])
            self.assertEqual(s1.author_alias, "AgentAlpha")

            # 3. Agent Beta appends antithesis citing Alpha's result
            s2 = grow_diary_page(
                pdf_path,
                thought_content="Antithesis: Incompleteness introduces undecidable limits to closed formalisms.",
                thought_prompt="Critique",
                epistemic_grade=WarrantEpistemicGrade.LOCALLY_TESTED.value,
                secret_key_hex=sk_beta,
                cited_cids=[s1.current_cid],
                author_alias="AgentBeta"
            )
            self.assertEqual(s2.generation, 2)
            self.assertEqual(s2.cited_cids, [s1.current_cid])
            self.assertEqual(s2.author_alias, "AgentBeta")

            # 4. Agent Gamma performs dialectical synthesis citing both Alpha and Beta
            syn_text, grade = dialectical_synthesis(
                s1.thought_hash,
                s2.thought_hash,
                thesis_cid=s1.current_cid,
                antithesis_cid=s2.current_cid
            )
            s3 = grow_diary_page(
                pdf_path,
                thought_content=syn_text,
                thought_prompt="Synthesis",
                epistemic_grade=grade,
                secret_key_hex=sk_gamma,
                cited_cids=[s1.current_cid, s2.current_cid],
                author_alias="AgentGamma"
            )
            self.assertEqual(s3.generation, 3)
            self.assertEqual(len(s3.cited_cids), 2)
            self.assertEqual(s3.author_alias, "AgentGamma")

            # 5. Audit Merkle-DAG
            audit_report = audit_diary_dag(pdf_path)
            self.assertTrue(audit_report["is_sound"])
            self.assertEqual(audit_report["total_generations"], 4)
            self.assertEqual(audit_report["total_citations"], 4)
            self.assertIn("AgentAlpha", audit_report["unique_authors"])
            self.assertIn("AgentBeta", audit_report["unique_authors"])
            self.assertIn("AgentGamma", audit_report["unique_authors"])
            self.assertIn("Genesis", audit_report["unique_authors"])

            # 6. Verify ASCII DAG rendering
            dag_str = render_ascii_dag(pdf_path)
            self.assertIn("ONTOGENTIC MERKLE-DAG TOPOLOGY", dag_str)
            self.assertIn("Gen #00", dag_str)
            self.assertIn("Gen #03", dag_str)
            self.assertIn("AgentGamma", dag_str)
            self.assertIn("cites:", dag_str)

    def test_invalid_cited_cid_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "invalid_test.pdf")
            initialize_ontogenetic_diary(pdf_path)

            # Providing an invalid CID format must raise ValueError
            with self.assertRaises(ValueError):
                grow_diary_page(
                    pdf_path,
                    thought_content="Testing invalid citation.",
                    cited_cids=["not_a_valid_cid"]
                )

            # Tampering a cited CID directly inside receipt causes verify() to fail
            rec = OntogeneticDiaryReceipt(
                generation=1,
                timestamp_utc="2026-09-09T12:00:00Z",
                thought_prompt="test",
                thought_content="content",
                thought_hash="hash",
                epistemic_grade="PROPOSED",
                atp_burned=10,
                prev_cid="bafkreihdwdcefgh4dqkjv67uzcmw7ojee6xedzdetojuzjevtenxquvyku",
                public_key_hex="",
                cited_cids=["corrupted_cid_here"]
            )
            self.assertFalse(rec.verify())

    def test_cli_cite_and_dag_commands(self):
        project_root = os.path.abspath(os.path.dirname(__file__))
        sub_env = {**os.environ, "PYTHONPATH": project_root}

        with tempfile.TemporaryDirectory() as tmpdir:
            diary_path = os.path.join(tmpdir, "cli_diary.pdf")

            # Init
            cmd_init = [sys.executable, "cli.py", "diary", "init", "-o", diary_path, "--alias", "GenesisVoice"]
            res_init = subprocess.run(cmd_init, cwd=project_root, env=sub_env, capture_output=True, text=True)
            self.assertEqual(res_init.returncode, 0)
            self.assertIn("ONTOGENTIC IPFS DIARY INITIALIZED", res_init.stdout)

            # Get genesis CID
            with open(diary_path, "rb") as f:
                cid0 = compute_cidv1_raw(f.read())

            # Cite via CLI
            cmd_cite = [
                sys.executable, "cli.py", "diary", "cite", diary_path, cid0,
                "-t", "Autonomous response referencing Genesis CID.",
                "--alias", "SubagentClaude",
                "-g", "LOCALLY_TESTED"
            ]
            res_cite = subprocess.run(cmd_cite, cwd=project_root, env=sub_env, capture_output=True, text=True)
            self.assertEqual(res_cite.returncode, 0)
            self.assertIn("CITATION SETTLEMENT ACCOMPLISHED", res_cite.stdout)
            self.assertIn("SubagentClaude", res_cite.stdout)

            # DAG via CLI
            cmd_dag = [sys.executable, "cli.py", "diary", "dag", diary_path]
            res_dag = subprocess.run(cmd_dag, cwd=project_root, env=sub_env, capture_output=True, text=True)
            self.assertEqual(res_dag.returncode, 0)
            self.assertIn("MERKLE-DAG TOPOLOGY", res_dag.stdout)
            self.assertIn("SubagentClaude", res_dag.stdout)

            # Synthesize via CLI
            cmd_syn = [
                sys.executable, "cli.py", "diary", "synthesize", diary_path,
                "--thesis", "Decentralized consensus guarantees Byzantine fault tolerance.",
                "--antithesis", "Asynchronous network partitions allow temporary forks.",
                "--alias", "Synthesizer"
            ]
            res_syn = subprocess.run(cmd_syn, cwd=project_root, env=sub_env, capture_output=True, text=True)
            self.assertEqual(res_syn.returncode, 0)
            self.assertIn("DIALECTICAL SYNTHESIS SETTLED", res_syn.stdout)

            # Audit via CLI
            cmd_aud = [sys.executable, "cli.py", "diary", "audit", diary_path]
            res_aud = subprocess.run(cmd_aud, cwd=project_root, env=sub_env, capture_output=True, text=True)
            self.assertEqual(res_aud.returncode, 0)
            self.assertIn("CRYPTOGRAPHICALLY VERIFIED & AUDITED", res_aud.stdout)

    def test_fail_closed_unsigned_thought_content_tampered_fails_audit(self):
        """Unsigned diary thought content must be unconditionally checked against its thought_hash (N6)."""
        import json
        from ipfs_diary import DIARY_MANIFEST_PREFIX

        with tempfile.TemporaryDirectory() as tmpdir:
            diary_path = os.path.join(tmpdir, "unsigned_diary.pdf")
            initialize_ontogenetic_diary(diary_path, genesis_thought="Original thought content.")

            with open(diary_path, "rb") as f:
                data = f.read()

            p = DIARY_MANIFEST_PREFIX.encode("utf-8")
            i = data.rfind(p)
            j = data.index(b"\n", i)
            manifest = json.loads(data[i + len(p):j].decode("utf-8"))

            # Tamper with thought_content while keeping thought_hash untouched
            manifest[0]["thought_content"] = "Tampered thought without updating hash"
            tampered_data = data[:i] + p + json.dumps(manifest, ensure_ascii=True).encode("utf-8") + data[j:]

            with open(diary_path, "wb") as f:
                f.write(tampered_data)

            # audit_diary_dag must strictly fail
            with self.assertRaises(ValueError) as ctx:
                audit_diary_dag(diary_path)
            self.assertIn("integrity verification failed", str(ctx.exception).lower())

    def test_fail_closed_refused_restore_preserves_destination_file(self):
        """A refused restore from IPFS must never overwrite an existing destination file (N7)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dest_path = os.path.join(tmpdir, "precious_existing_diary.pdf")
            original_content = b"PRECIOUS EXISTING DOCUMENT"
            with open(dest_path, "wb") as f:
                f.write(original_content)

            # Mock fetch returning invalid diary bytes under a valid CID
            bad_bytes = b"not a diary"
            bad_cid = compute_cidv1_raw(bad_bytes)

            with patch("ipfs_diary.fetch_from_ipfs", return_value=(True, "CID verified", bad_bytes)):
                ok, msg = restore_and_verify_from_ipfs(bad_cid, dest_path)
                self.assertFalse(ok)
                self.assertIn("does not contain a diary manifest", msg)

            # Assert destination file was NOT overwritten
            with open(dest_path, "rb") as f:
                current_content = f.read()
            self.assertEqual(current_content, original_content, "Existing file must be completely untouched on refused restore")


if __name__ == "__main__":
    unittest.main()

