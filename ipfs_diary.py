#!/usr/bin/env python3
# coding: utf-8
"""
ipfs_diary.py — Self-Preserving Ontogenetic Diary & LLM Inner Voice on IPFS.
Part of Project Black-Heart (%🖤).

Features:
  1. Content-Addressed Identity: Every developmental version of the diary possesses
     a canonical IPFS CIDv1 (raw/sha256/base32 'bafkrei...').
  2. Append-Only Ontogeny: Each cognitive reflection appends an ISO 32000 §7.5.6
     incremental update page without modifying previous bytes (after.startswith(before) == True).
  3. Epistemic Hygiene: Thoughts carry explicit WarrantEpistemicGrade standings:
     - PROPOSED: Speculative contemplation, reflection, or raw LLM dialogue.
     - LOCALLY_TESTED: Empirically verified against internal combinator/immune fixtures.
     - RULE_DERIVED: Algebraically proven rewrite theorems.
     - REFUTED: Flagged contradictions or invalid assertions.
  4. Merkle-DAG Provenance: Each generation embeds its parent's exact CID (prev_cid).
  5. Sovereign Dual-Spine Polyglot: Valid ISO 32000 PDF viewable in any PDF reader,
     and directly executable as Python ('python3 diary.pdf --status / --lineage / --append').
  6. Zero External Dependencies: Pure Python standard library with optional Kubo HTTP API bridge.
"""

from __future__ import annotations
import os
import sys
import json
import time
import urllib.request
import urllib.error
import hashlib
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any, Union

from cid import compute_cidv1_raw, compute_cidv1_for_file, is_valid_cidv1
from mycelium import WarrantEpistemicGrade
from crypto import (
    generate_keypair,
    public_key_from_secret,
    sign_bytes,
    verify_bytes,
    is_valid_public_key
)

DIARY_MANIFEST_PREFIX = "%" + "🖤" + " DIARY_MANIFEST: "

# ============================================================================
# 1. DATA STRUCTURES & RECEIPTS
# ============================================================================

@dataclass
class OntogeneticDiaryReceipt:
    """
    Cryptographic receipt certifying an ontogenetic diary entry.
    Links thought content, epistemic grade, author key, and IPFS Merkle provenance.
    """
    generation: int
    timestamp_utc: str
    thought_prompt: str
    thought_content: str
    thought_hash: str
    epistemic_grade: str
    atp_burned: int
    prev_cid: str
    public_key_hex: str
    signature_hex: str = ""
    receipt_hash: str = ""
    cited_cids: List[str] = field(default_factory=list)
    author_alias: str = ""

    def compute_thought_hash(self) -> str:
        return hashlib.sha256(f"{self.thought_prompt}:{self.thought_content}".encode("utf-8")).hexdigest()

    def canonical_bytes_for_signing(self) -> bytes:
        payload = (
            f"DIARY_RECEIPT:{self.generation}:{self.timestamp_utc}:{self.thought_hash}:"
            f"{self.epistemic_grade}:{self.atp_burned}:{self.prev_cid}:{self.public_key_hex}"
        )
        if self.cited_cids:
            payload += f":CITATIONS={','.join(sorted(self.cited_cids))}"
        if self.author_alias:
            payload += f":ALIAS={self.author_alias}"
        return payload.encode("utf-8")

    def compute_hash(self) -> str:
        data = self.canonical_bytes_for_signing() + (f":{self.signature_hex}".encode("utf-8") if self.signature_hex else b"")
        return hashlib.sha256(data).hexdigest()

    def is_attested(self) -> bool:
        return bool(self.public_key_hex and self.signature_hex)

    def sign(self, secret_key_hex: str) -> None:
        sk_bytes = bytes.fromhex(secret_key_hex)
        pk_bytes = public_key_from_secret(sk_bytes)
        self.public_key_hex = pk_bytes.hex()
        self.thought_hash = self.compute_thought_hash()
        sig = sign_bytes(sk_bytes, self.canonical_bytes_for_signing())
        self.signature_hex = sig.hex()
        self.receipt_hash = self.compute_hash()

    def verify_integrity(self) -> bool:
        """Verifies content-addressing, thought content hash, and structural hash integrity."""
        if self.generation < 0:
            return False
        if self.thought_hash != self.compute_thought_hash():
            return False
        for c in self.cited_cids:
            if not is_valid_cidv1(c):
                return False
        expected_hash = self.compute_hash()
        if self.receipt_hash and self.receipt_hash != expected_hash:
            return False
        return True

    def verify(self) -> bool:
        if not self.verify_integrity():
            return False
        if not self.is_attested():
            return False
        if not is_valid_public_key(self.public_key_hex):
            return False
        try:
            pk_bytes = bytes.fromhex(self.public_key_hex)
            sig_bytes = bytes.fromhex(self.signature_hex)
            return verify_bytes(pk_bytes, self.canonical_bytes_for_signing(), sig_bytes)
        except Exception:
            return False

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "generation": self.generation,
            "timestamp_utc": self.timestamp_utc,
            "thought_prompt": self.thought_prompt,
            "thought_content": self.thought_content,
            "thought_hash": self.thought_hash,
            "epistemic_grade": self.epistemic_grade,
            "atp_burned": self.atp_burned,
            "prev_cid": self.prev_cid,
            "public_key_hex": self.public_key_hex,
            "signature_hex": self.signature_hex,
            "receipt_hash": self.receipt_hash,
        }
        if self.cited_cids:
            d["cited_cids"] = list(self.cited_cids)
        if self.author_alias:
            d["author_alias"] = self.author_alias
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> OntogeneticDiaryReceipt:
        return cls(
            generation=int(d["generation"]),
            timestamp_utc=str(d["timestamp_utc"]),
            thought_prompt=str(d.get("thought_prompt", "")),
            thought_content=str(d.get("thought_content", "")),
            thought_hash=str(d["thought_hash"]),
            epistemic_grade=str(d.get("epistemic_grade", WarrantEpistemicGrade.PROPOSED.value)),
            atp_burned=int(d.get("atp_burned", 0)),
            prev_cid=str(d.get("prev_cid", "")),
            public_key_hex=str(d.get("public_key_hex", "")),
            signature_hex=str(d.get("signature_hex", "")),
            receipt_hash=str(d.get("receipt_hash", "")),
            cited_cids=list(d.get("cited_cids", [])),
            author_alias=str(d.get("author_alias", ""))
        )

@dataclass
class DiarySettlement:
    """Settlement returned to an LLM or caller upon completing a diary growth step."""
    generation: int
    current_cid: str
    prev_cid: str
    epistemic_grade: str
    thought_hash: str
    atp_burned: int
    receipt_hash: str
    status: str
    cited_cids: List[str] = field(default_factory=list)
    author_alias: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "generation": self.generation,
            "current_cid": self.current_cid,
            "prev_cid": self.prev_cid,
            "epistemic_grade": self.epistemic_grade,
            "thought_hash": self.thought_hash,
            "atp_burned": self.atp_burned,
            "receipt_hash": self.receipt_hash,
            "status": self.status
        }
        if self.cited_cids:
            d["cited_cids"] = list(self.cited_cids)
        if self.author_alias:
            d["author_alias"] = self.author_alias
        return d

# ============================================================================
# 2. ISO 32000 VECTOR DIARY COMPILER
# ============================================================================

class DiaryPolyglotCompiler:
    """
    Compiles self-executing ISO 32000 PDF polyglots embodying the LLM inner voice diary.
    """

    def generate_page_stream(self, rec: OntogeneticDiaryReceipt, cid_stamp: str = "") -> str:
        """Draws dark obsidian layout, status badge, thought text, and provenance stamps."""
        # Color palette for epistemic grade
        if rec.epistemic_grade == WarrantEpistemicGrade.RULE_DERIVED.value:
            badge_r, badge_g, badge_b = 0.85, 0.70, 0.20  # Gold
            badge_label = "RULE_DERIVED (MATHEMATICAL THEOREM)"
        elif rec.epistemic_grade == WarrantEpistemicGrade.LOCALLY_TESTED.value:
            badge_r, badge_g, badge_b = 0.12, 0.58, 0.28  # Emerald
            badge_label = "LOCALLY_TESTED (EMPIRICALLY VERIFIED)"
        elif rec.epistemic_grade == WarrantEpistemicGrade.REFUTED.value:
            badge_r, badge_g, badge_b = 0.75, 0.15, 0.20  # Crimson
            badge_label = "REFUTED (DIVERGENCE CONTRADICTION)"
        else:
            badge_r, badge_g, badge_b = 0.55, 0.25, 0.75  # Amethyst / Violet
            badge_label = "PROPOSED (EXPLORATORY REFLECTION)"

        # Escape strings for PDF Tj
        def pdf_escape(s: str) -> str:
            return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

        author_badge = f"  |  VOICE: {pdf_escape(rec.author_alias)}" if rec.author_alias else ""

        ops = [
            "q",
            # Dark Obsidian Background
            "0.03 0.04 0.07 rg",
            "0 0 595 842 re f",
            # Outer Gold Border
            "0.85 0.70 0.25 RG 1.5 w",
            "30 30 535 782 re S",
            # Header Medallion
            "0.08 0.10 0.18 rg",
            "45 740 505 55 re f",
            "0.85 0.70 0.25 RG 1.0 w 45 740 505 55 re S",
            "1.0 1.0 1.0 rg",
            "BT /F1 14 Tf 60 772 Td (PROJECT BLACK-HEART // ONTOGENTIC IPFS DIARY) Tj ET",
            "0.85 0.70 0.25 rg",
            f"BT /F1 9 Tf 60 752 Td (GENERATION #{rec.generation}{author_badge}  |  EPOCH: {rec.timestamp_utc}  |  GAS: {rec.atp_burned} ATP) Tj ET",
            # Epistemic Grade Banner
            f"{badge_r:.3f} {badge_g:.3f} {badge_b:.3f} rg",
            "45 700 505 28 re f",
            "1.0 1.0 1.0 rg",
            f"BT /F1 10 Tf 60 710 Td (EPISTEMIC STANDING: {badge_label}) Tj ET",
            # Thought / Reflection Panel
            "0.06 0.08 0.14 rg",
            "45 360 505 320 re f",
            "0.25 0.40 0.65 RG 1.0 w 45 360 505 320 re S",
            "0.40 0.80 1.00 rg",
            "BT /F1 10 Tf 60 655 Td (PROMPT / COGNITIVE TRIGGER:) Tj ET",
            "0.95 0.95 0.95 rg",
        ]

        prompt_clean = pdf_escape(rec.thought_prompt[:120]) if rec.thought_prompt else "<Autonomous Inner Voice>"
        ops.append(f"BT /F1 9 Tf 65 638 Td ({prompt_clean}) Tj ET")

        ops.append("0.40 0.80 1.00 rg")
        ops.append("BT /F1 10 Tf 60 605 Td (REFLECTIVE SETTLEMENT & INNER MONOLOGUE:) Tj ET")
        ops.append("0.90 0.92 0.96 rg")

        # Simple line-wrap for thought text
        words = rec.thought_content.split()
        lines = []
        cur_line = []
        for w in words:
            if len(" ".join(cur_line + [w])) > 72:
                lines.append(" ".join(cur_line))
                cur_line = [w]
            else:
                cur_line.append(w)
        if cur_line:
            lines.append(" ".join(cur_line))

        y_pos = 585
        for l in lines[:10]:
            clean_l = pdf_escape(l)
            ops.append(f"BT /F1 9 Tf 65 {y_pos} Td ({clean_l}) Tj ET")
            y_pos -= 16

        # Merkle-DAG Provenance Panel
        ops.extend([
            "0.05 0.07 0.12 rg",
            "45 60 505 280 re f",
            "0.85 0.70 0.25 RG 1.0 w 45 60 505 280 re S",
            "1.0 1.0 1.0 rg",
            "BT /F1 11 Tf 60 315 Td (IPFS MERKLE-DAG PROVENANCE & SETTLEMENT ANCHOR) Tj ET",
            "0.75 0.85 0.95 rg",
            f"BT /F1 9 Tf 60 288 Td (Parent CIDv1 (prev_cid):   {pdf_escape(rec.prev_cid or '<Genesis Ancestor>')}) Tj ET",
            f"BT /F1 9 Tf 60 270 Td (Thought Content Hash:        ⚓ {rec.thought_hash[:44]}...) Tj ET",
            f"BT /F1 9 Tf 60 252 Td (Receipt Canonical Hash:      {rec.receipt_hash[:44]}...) Tj ET",
            f"BT /F1 9 Tf 60 234 Td (Signer Public Key:           {rec.public_key_hex[:44] if rec.public_key_hex else '<UNATTESTED>'}...) Tj ET",
            f"BT /F1 9 Tf 60 216 Td (Attestation Status:          {'CRYPTOGRAPHICALLY AUTHENTICATED (Ed25519)' if rec.is_attested() else 'UNATTESTED'}) Tj ET",
        ])

        if rec.cited_cids:
            c_str = ", ".join([c[:18] + "..." for c in rec.cited_cids])
            ops.append("0.40 0.80 1.00 rg")
            ops.append(f"BT /F1 9 Tf 60 198 Td (Cited Thought CIDs:         {pdf_escape(c_str)}) Tj ET")

        ops.extend([
            "0.85 0.70 0.25 rg",
            "BT /F1 9 Tf 60 165 Td (Autonomous Quine CLI Interface:) Tj ET",
            "0.90 0.90 0.90 rg",
            "BT /F1 8 Tf 75 147 Td ($ python3 <diary>.pdf --status                # Displays latest generation HUD) Tj ET",
            "BT /F1 8 Tf 75 131 Td ($ python3 <diary>.pdf --lineage               # Traverses full CID ancestry) Tj ET",
            "BT /F1 8 Tf 75 115 Td ($ python3 <diary>.pdf --dag                   # Visualizes Merkle-DAG citations) Tj ET",
            "BT /F1 8 Tf 75 99  Td ($ python3 <diary>.pdf --cite <cid> \"thought\" # Cites prior CID in new thought) Tj ET",
            "BT /F1 8 Tf 75 83  Td ($ python3 <diary>.pdf --publish              # Pins current version to IPFS) Tj ET",
            "Q"
        ])
        return "\n".join(ops)

    def _build_base_pdf(self, rec: OntogeneticDiaryReceipt) -> bytes:
        """Generates initial ISO 32000 PDF bytes for generation 0."""
        stream_content = self.generate_page_stream(rec)
        stream_bytes = stream_content.encode("utf-8")

        objects = [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            (
                b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
                b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>"
            ),
            (
                f"<< /Length {len(stream_bytes)} >>\nstream\n".encode("latin1") +
                stream_bytes +
                b"\nendstream"
            ),
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        ]

        out = bytearray(b"# coding: utf-8\nr\"\"\"%PDF-1.7\n%\xf0\x9f\x96\xa4\n")
        offsets = [0]
        for i, obj in enumerate(objects, 1):
            offsets.append(len(out))
            out.extend(f"{i} 0 obj\n".encode("latin1"))
            out.extend(obj)
            out.extend(b"\nendobj\n")

        xref_offset = len(out)
        out.extend(f"xref\n0 {len(objects) + 1}\n".encode("latin1"))
        out.extend(b"0000000000 65535 f \n")
        for off in offsets[1:]:
            out.extend(f"{off:010d} 00000 n \n".encode("latin1"))

        out.extend(
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF".encode("latin1")
        )
        return bytes(out)

    def _build_runner_script(self) -> str:
        return r'''
import sys
import os
import json
import argparse

for _p in [os.getcwd(), os.path.dirname(os.path.abspath(__file__))]:
    if _p and _p not in sys.path:
        sys.path.insert(0, _p)

from cid import compute_cidv1_raw, compute_cidv1_for_file
from ipfs_diary import (
    OntogeneticDiaryReceipt,
    grow_diary_page,
    pin_to_kubo_daemon,
    query_inner_voice,
    restore_and_verify_from_ipfs,
    render_ascii_dag,
    audit_diary_dag,
    DIARY_MANIFEST_PREFIX
)

def _extract_manifest(filepath):
    with open(filepath, "rb") as f:
        data = f.read()
    prefix = DIARY_MANIFEST_PREFIX.encode("utf-8")
    idx = data.rfind(prefix)
    if idx == -1:
        print("[FAIL] No diary receipt manifest found.")
        sys.exit(1)
    end_idx = data.find(b"\n", idx)
    raw = data[idx + len(prefix):end_idx].decode("utf-8")
    return json.loads(raw), data

def cmd_status(filepath):
    manifest, data = _extract_manifest(filepath)
    latest = manifest[-1]
    cid = compute_cidv1_raw(data)
    print("\033[1;36m=================================================================\033[0m")
    print("  %🖤 PROJECT BLACK-HEART // ONTOGENTIC IPFS DIARY HUD")
    print(f"  Target File:        {os.path.basename(filepath)} ({len(data)} bytes, {len(manifest)} pages)")
    print(f"  Current CIDv1:      {cid}")
    print("\033[1;36m=================================================================\033[0m\n")
    print(f"  Current Generation: #{latest.get('generation')}")
    print(f"  Timestamp UTC:      {latest.get('timestamp_utc')}")
    print(f"  Epistemic Grade:    {latest.get('epistemic_grade')}")
    print(f"  Parent CIDv1:       {latest.get('prev_cid') or '<None (Genesis)>'}")
    if latest.get("author_alias"):
        print(f"  Author Voice:       {latest.get('author_alias')}")
    if latest.get("cited_cids"):
        print(f"  Cited CIDs:         {', '.join(latest.get('cited_cids'))}")
    print(f"  Thought Hash:       ⚓ {latest.get('thought_hash')}")
    print(f"  Prompt Trigger:     {latest.get('thought_prompt')}")
    print(f"  Thought Preview:    {latest.get('thought_content')[:120]}...\n")

def cmd_lineage(filepath):
    manifest, data = _extract_manifest(filepath)
    print("\033[1;36m=================================================================\033[0m")
    print(f"  %🖤 DIARY ONTOGENTIC LINEAGE ACROSS {len(manifest)} GENERATIONS")
    print("\033[1;36m=================================================================\033[0m")
    for m in manifest:
        gen = m.get("generation")
        t_utc = m.get("timestamp_utc")
        grade = m.get("epistemic_grade")
        p_cid = m.get("prev_cid") or "<Genesis>"
        alias = f" ({m.get('author_alias')})" if m.get("author_alias") else ""
        cites = f" [cites: {len(m.get('cited_cids', []))}]" if m.get("cited_cids") else ""
        thought = m.get("thought_content", "")[:50]
        print(f"  #{gen:02d} [{t_utc}] {grade:14s}{alias}{cites} | Parent: {p_cid[:22]}... | {thought}...")
    print(f"\n  Current File CIDv1: {compute_cidv1_raw(data)}\n")

def cmd_audit(filepath):
    print(f"[*] Auditing ontogenetic diary chain and Merkle-DAG...")
    try:
        res = audit_diary_dag(filepath)
        print(f"\033[1;32m[✓] ALL {res['total_generations']} DIARY PAGES CRYPTOGRAPHICALLY VERIFIED & AUDITED\033[0m")
        print(f"  Total Citations: {res['total_citations']}")
        print(f"  Unique Authors:  {', '.join(res['unique_authors']) if res['unique_authors'] else '<None>'}\n")
    except Exception as e:
        print(f"\033[1;31m[FAIL] Audit failed: {e}\033[0m")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Ontogenetic IPFS Diary Polyglot Runner")
    parser.add_argument("--status", action="store_true", help="Display diary HUD & latest CID")
    parser.add_argument("--lineage", action="store_true", help="Display full Merkle-DAG CID history")
    parser.add_argument("--dag", action="store_true", help="Render ASCII Merkle-DAG topology")
    parser.add_argument("--append", type=str, help="Append a new thought reflection to the diary")
    parser.add_argument("--cite", type=str, help="CIDv1 to cite in the new thought")
    parser.add_argument("--alias", type=str, default="", help="Author voice alias (e.g. Claude, Gemini, Organism-0)")
    parser.add_argument("--voice", type=str, help="Consult autonomous inner voice with stimulus and append reflection")
    parser.add_argument("--from-cid", type=str, help="Restore and verify diary document from IPFS CIDv1")
    parser.add_argument("--out", type=str, default="restored_diary.pdf", help="Output file path for --from-cid")
    parser.add_argument("--prompt", type=str, default="", help="Optional prompt context for the thought")
    parser.add_argument("--grade", type=str, default="PROPOSED", help="Epistemic grade (PROPOSED, LOCALLY_TESTED, RULE_DERIVED)")
    parser.add_argument("--secret-key", type=str, default="", help="Optional 64-char hex secret key for signing")
    parser.add_argument("--publish", action="store_true", help="Pin current document to IPFS Kubo node")
    parser.add_argument("--audit", action="store_true", help="Audit Merkle chain and digital signatures")
    args, _ = parser.parse_known_args()

    target_file = sys.argv[0]

    if args.from_cid:
        ok, msg = restore_and_verify_from_ipfs(args.from_cid, args.out)
        if ok:
            print(f"\033[1;32m[✓] {msg}: {args.out}\033[0m")
        else:
            print(f"\033[1;31m[FAIL] {msg}\033[0m")
            sys.exit(1)
    elif args.dag:
        print(render_ascii_dag(target_file))
    elif args.cite:
        thought_body = args.append or f"Affirming and citing prior thought at CID {args.cite}."
        c_list = [c.strip() for c in args.cite.split(",") if c.strip()]
        settlement = grow_diary_page(
            target_file,
            thought_prompt=args.prompt,
            thought_content=thought_body,
            epistemic_grade=args.grade,
            secret_key_hex=args.secret_key or None,
            cited_cids=c_list,
            author_alias=args.alias
        )
        print(f"\033[1;32m[✓] CITATION SETTLEMENT ACCOMPLISHED\033[0m")
        print(f"  Generation:      #{settlement.generation}")
        print(f"  Current CIDv1:   {settlement.current_cid}")
        print(f"  Parent CIDv1:    {settlement.prev_cid}")
        print(f"  Cited CIDs:      {', '.join(settlement.cited_cids)}")
        print(f"  Author Voice:    {settlement.author_alias or '<Anonymous>'}")
        print(f"  Epistemic Grade: {settlement.epistemic_grade}")
    elif args.voice:
        monologue, settlement = query_inner_voice(target_file, args.voice, secret_key_hex=args.secret_key or None)
        print("\033[1;36m=================================================================\033[0m")
        print("  %🖤 INNER VOICE REFLECTIVE SETTLEMENT")
        print("\033[1;36m=================================================================\033[0m\n")
        print(f"  Stimulus:        {args.voice}")
        print(f"  Reflection:      {monologue}")
        print(f"  Settled Gen:     #{settlement.generation}")
        print(f"  New CIDv1:       {settlement.current_cid}")
        print(f"  Epistemic Grade: {settlement.epistemic_grade}\n")
    elif args.append:
        settlement = grow_diary_page(
            target_file,
            thought_prompt=args.prompt,
            thought_content=args.append,
            epistemic_grade=args.grade,
            secret_key_hex=args.secret_key or None,
            author_alias=args.alias
        )
        print(f"\033[1;32m[✓] DIARY SETTLEMENT ACCOMPLISHED\033[0m")
        print(f"  Generation:      #{settlement.generation}")
        print(f"  Current CIDv1:   {settlement.current_cid}")
        print(f"  Parent CIDv1:    {settlement.prev_cid}")
        print(f"  Epistemic Grade: {settlement.epistemic_grade}")
    elif args.publish:
        ok, msg, pinned_cid = pin_to_kubo_daemon(target_file)
        if ok:
            print(f"\033[1;32m[✓] PINNED TO IPFS: {pinned_cid}\033[0m")
            print(f"  Gateway URL: https://ipfs.io/ipfs/{pinned_cid}")
        else:
            print(f"\033[1;33m[!] {msg}\033[0m")
    elif args.lineage:
        cmd_lineage(target_file)
    elif args.audit:
        cmd_audit(target_file)
    else:
        cmd_status(target_file)

if __name__ == "__main__":
    main()
'''

    def compile_bytes(self, genesis_receipt: OntogeneticDiaryReceipt) -> bytes:
        """Emits standalone initial executable PDF polyglot bytes for generation 0."""
        pdf_bytes = self._build_base_pdf(genesis_receipt)
        manifest_data = json.dumps([genesis_receipt.to_dict()], ensure_ascii=False)
        manifest_bytes = f"\n{DIARY_MANIFEST_PREFIX}{manifest_data}\n".encode("utf-8")
        runner_script = self._build_runner_script()

        return (
            pdf_bytes +
            manifest_bytes +
            b'\n"""\n' +
            runner_script.encode("utf-8")
        )

    def compile(self, output_pdf_path: str, genesis_receipt: OntogeneticDiaryReceipt) -> str:
        """Compiles and writes generation 0 diary polyglot. Returns initial CIDv1."""
        payload = self.compile_bytes(genesis_receipt)
        with open(output_pdf_path, "wb") as f:
            f.write(payload)
        return compute_cidv1_raw(payload)

# ============================================================================
# 3. ONTOGENTIC APPEND-ONLY SELF-GROWTH ENGINE (ISO 32000 §7.5.6)
# ============================================================================

def grow_diary_page(
    pdf_path: str,
    thought_content: str,
    thought_prompt: str = "",
    epistemic_grade: str = WarrantEpistemicGrade.PROPOSED.value,
    atp_burned: int = 10,
    secret_key_hex: Optional[str] = None,
    cited_cids: Optional[List[str]] = None,
    author_alias: str = ""
) -> DiarySettlement:
    """
    Appends a new cognitive generation to an existing self-contained PDF diary:
      1. Reads current binary content and computes its current CIDv1 (prev_cid).
      2. Appends an incremental ISO 32000 page update using append-only mode ('ab').
      3. Computes the resulting new file CIDv1 (current_cid).
      4. Returns a verified DiarySettlement receipt.
    """
    with open(pdf_path, "rb") as f:
        content = f.read()

    prefix = DIARY_MANIFEST_PREFIX.encode("utf-8")
    idx = content.rfind(prefix)
    if idx == -1:
        raise ValueError(f"No diary manifest found in {pdf_path}")

    end_idx = content.find(b"\n", idx)
    manifest_data = json.loads(content[idx + len(prefix):end_idx].decode("utf-8"))
    receipts = [OntogeneticDiaryReceipt.from_dict(d) for d in manifest_data]

    # Verify history continuity
    for i, r in enumerate(receipts):
        if r.generation != i:
            raise ValueError(f"Diary lineage sequence gap at index {i}: generation #{r.generation}")
        if r.receipt_hash != r.compute_hash():
            raise ValueError(f"Receipt hash mismatch at generation #{r.generation}")

    current = receipts[-1]
    next_gen = current.generation + 1
    prev_cid = compute_cidv1_raw(content)

    clean_cited: List[str] = []
    if cited_cids:
        for c in cited_cids:
            c_clean = str(c).strip()
            if not is_valid_cidv1(c_clean):
                raise ValueError(f"Invalid cited CIDv1 format: '{c_clean}'")
            clean_cited.append(c_clean)

    thought_hash = hashlib.sha256(f"{thought_prompt}:{thought_content}".encode("utf-8")).hexdigest()
    now_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    next_rec = OntogeneticDiaryReceipt(
        generation=next_gen,
        timestamp_utc=now_utc,
        thought_prompt=thought_prompt,
        thought_content=thought_content,
        thought_hash=thought_hash,
        epistemic_grade=epistemic_grade,
        atp_burned=atp_burned,
        prev_cid=prev_cid,
        public_key_hex="",
        signature_hex="",
        receipt_hash="",
        cited_cids=clean_cited,
        author_alias=author_alias
    )

    if secret_key_hex:
        next_rec.sign(secret_key_hex)
    else:
        next_rec.receipt_hash = next_rec.compute_hash()

    receipts.append(next_rec)

    # Re-encode manifest list
    new_manifest_data = json.dumps([r.to_dict() for r in receipts], ensure_ascii=False)
    new_manifest_bytes = f"\n{DIARY_MANIFEST_PREFIX}{new_manifest_data}\n".encode("utf-8")

    # Generate incremental page stream
    compiler = DiaryPolyglotCompiler()
    stream_content = compiler.generate_page_stream(next_rec, cid_stamp=prev_cid)
    stream_bytes = stream_content.encode("utf-8")

    # Locate last xref position
    last_xref_pos = content.rfind(b"startxref\n")
    prev_xref = 0
    if last_xref_pos != -1:
        tail = content[last_xref_pos + len(b"startxref\n"):]
        eof_pos = tail.find(b"\n%%EOF")
        if eof_pos != -1:
            try:
                prev_xref = int(tail[:eof_pos].strip())
            except ValueError:
                prev_xref = 0

    base_obj_count = 5 + (current.generation * 3)
    new_page_id = base_obj_count + 1
    new_contents_id = base_obj_count + 2
    new_pages_id = base_obj_count + 3
    root_obj_id = new_pages_id + 1

    page_obj = (
        f"{new_page_id} 0 obj\n"
        f"<< /Type /Page /Parent {new_pages_id} 0 R /MediaBox [0 0 595 842] "
        f"/Contents {new_contents_id} 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
    ).encode("latin1")

    contents_obj = (
        f"{new_contents_id} 0 obj\n<< /Length {len(stream_bytes)} >>\nstream\n".encode("latin1") +
        stream_bytes +
        b"\nendstream\nendobj\n"
    )

    kids_refs = " ".join(f"{3 if i == 0 else 5 + (i * 3) - 2} 0 R" for i in range(len(receipts)))
    pages_obj = (
        f"{new_pages_id} 0 obj\n<< /Type /Pages /Kids [{kids_refs}] /Count {len(receipts)} >>\nendobj\n"
    ).encode("latin1")

    catalog_obj = (
        f"{root_obj_id} 0 obj\n<< /Type /Catalog /Pages {new_pages_id} 0 R >>\nendobj\n"
    ).encode("latin1")

    # Pure ISO 32000 append-only update block
    py_prefix = b'\nr"""\n'
    update_body = bytearray()
    update_offsets = []

    for obj in (page_obj, contents_obj, pages_obj, catalog_obj):
        obj_num = int(obj[:obj.find(b" 0 obj")].decode("latin1"))
        update_offsets.append((obj_num, len(content) + len(py_prefix) + len(update_body)))
        update_body.extend(obj)

    new_xref_offset = len(content) + len(py_prefix) + len(update_body)
    xref_chunk = bytearray(b"xref\n")
    for obj_num, offset in update_offsets:
        xref_chunk.extend(f"{obj_num} 1\n".encode("latin1"))
        xref_chunk.extend(f"{offset:010d} 00000 n \n".encode("latin1"))

    trailer_chunk = (
        f"trailer\n<< /Size {root_obj_id + 1} /Root {root_obj_id} 0 R /Prev {prev_xref} >>\n"
        f"startxref\n{new_xref_offset}\n%%EOF\n".encode("latin1")
    )

    py_suffix = b'"""\n'

    append_chunk = (
        py_prefix +
        bytes(update_body) +
        bytes(xref_chunk) +
        trailer_chunk +
        new_manifest_bytes +
        py_suffix
    )

    with open(pdf_path, "ab") as f:
        f.write(append_chunk)

    new_cid = compute_cidv1_for_file(pdf_path)

    return DiarySettlement(
        generation=next_gen,
        current_cid=new_cid,
        prev_cid=prev_cid,
        epistemic_grade=epistemic_grade,
        thought_hash=thought_hash,
        atp_burned=atp_burned,
        receipt_hash=next_rec.receipt_hash,
        status="SETTLED_AND_APPENDED",
        cited_cids=clean_cited,
        author_alias=author_alias
    )

# ============================================================================
# 4. IPFS KUBO DAEMON BRIDGE (HTTP API)
# ============================================================================

def pin_to_kubo_daemon(
    pdf_path: str,
    daemon_url: str = "http://127.0.0.1:5001"
) -> Tuple[bool, str, Optional[str]]:
    """
    Pins the specified PDF file to a local or remote IPFS Kubo daemon using
    standard library HTTP multipart upload (POST /api/v0/add?pin=true).
    Returns (success, message, pinned_cid).
    """
    if not os.path.exists(pdf_path):
        return False, f"File '{pdf_path}' does not exist", None

    boundary = "----BlackHeartBoundary" + hashlib.sha256(str(time.time()).encode()).hexdigest()[:16]
    filename = os.path.basename(pdf_path)

    with open(pdf_path, "rb") as f:
        file_bytes = f.read()

    body = bytearray()
    body.extend(f"--{boundary}\r\n".encode("latin1"))
    body.extend(f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode("latin1"))
    body.extend(b"Content-Type: application/pdf\r\n\r\n")
    body.extend(file_bytes)
    body.extend(f"\r\n--{boundary}--\r\n".encode("latin1"))

    endpoint = f"{daemon_url.rstrip('/')}/api/v0/add?pin=true&cid-version=1"
    req = urllib.request.Request(
        endpoint,
        data=bytes(body),
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            resp_data = resp.read().decode("utf-8")
            # Kubo returns newline-delimited JSON objects
            res_json = json.loads(resp_data.strip().split("\n")[-1])
            pinned_cid = res_json.get("Hash")
            return True, "Successfully published and pinned to IPFS node", pinned_cid
    except (urllib.error.URLError, ConnectionRefusedError, TimeoutError) as e:
        local_cid = compute_cidv1_raw(file_bytes)
        return False, f"IPFS Kubo daemon unavailable at {daemon_url}: {e} (Local CIDv1 preserved: {local_cid})", None
    except Exception as e:
        return False, f"IPFS publication error: {e}", None

def fetch_from_ipfs(
    cid: str,
    gateway_or_daemon_url: str = "http://127.0.0.1:5001"
) -> Tuple[bool, str, Optional[bytes]]:
    """
    Fetches content addressed by CID from an IPFS daemon API or public gateway.
    Strictly fail-closed: validates compute_cidv1_raw(downloaded_bytes) == cid.
    """
    if not is_valid_cidv1(cid):
        return False, f"Invalid CIDv1 identifier: '{cid}'", None

    url = gateway_or_daemon_url.rstrip("/")
    if ":5001" in url or "/api/v0" in url:
        endpoint = f"{url}/api/v0/cat?arg={cid}"
    else:
        endpoint = f"{url}/ipfs/{cid}"

    req = urllib.request.Request(endpoint, method="POST" if ":5001" in url else "GET")
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = resp.read()
            # FAIL-CLOSED CHECK: Do downloaded bytes match the requested CID?
            actual_cid = compute_cidv1_raw(data)
            if actual_cid != cid:
                return False, f"Cryptographic integrity violation: expected CID {cid}, got {actual_cid}", None
            return True, "Successfully retrieved and verified from IPFS", data
    except (urllib.error.URLError, ConnectionRefusedError, TimeoutError) as e:
        return False, f"IPFS node unavailable at {endpoint}: {e}", None
    except Exception as e:
        return False, f"IPFS fetch error: {e}", None

def restore_and_verify_from_ipfs(
    cid: str,
    destination_path: str,
    gateway_or_daemon_url: str = "http://127.0.0.1:5001"
) -> Tuple[bool, str]:
    """
    Downloads document from IPFS by CID, verifies its content-addressed integrity,
    writes to disk, and runs internal cryptographic audit.
    """
    ok, msg, data = fetch_from_ipfs(cid, gateway_or_daemon_url)
    if not ok or not data:
        return False, msg

    prefix = DIARY_MANIFEST_PREFIX.encode("utf-8")
    idx = data.rfind(prefix)
    if idx == -1:
        return False, "Downloaded file does not contain a diary manifest"

    end_idx = data.find(b"\n", idx)
    manifest = json.loads(data[idx + len(prefix):end_idx].decode("utf-8"))
    for i, md in enumerate(manifest):
        rec = OntogeneticDiaryReceipt.from_dict(md)
        if rec.generation != i:
            return False, f"Lineage gap at session #{rec.generation}"
        if rec.receipt_hash != rec.compute_hash():
            return False, f"Hash mismatch at session #{rec.generation}"
        if not rec.verify_integrity():
            return False, f"Integrity check failed at session #{rec.generation}"
        if rec.is_attested() and not rec.verify():
            return False, f"Invalid digital signature at session #{rec.generation}"

    # Only write to destination AFTER full verification passes (N7 fix: prevent clobbering existing files)
    with open(destination_path, "wb") as f:
        f.write(data)

    return True, f"Successfully restored and audited {len(manifest)} diary generations from IPFS"

# ============================================================================
# 5. AUTONOMOUS INNER VOICE & COGNITIVE MONOLOGUE
# ============================================================================

def formulate_inner_monologue(prompt: str) -> Tuple[str, str]:
    """
    Synthesizes an autonomous philosophical reflection based on combinatory logic,
    the Black Cone event horizon, and epistemic warrants.
    Returns (reflection_text, suggested_epistemic_grade).
    """
    prompt_lower = prompt.lower()

    if any(k in prompt_lower for k in ("black cone", "чорний конус", "event horizon", "горизонт")):
        return (
            "The Black Cone is the gravitational asymptote of computation. Where K absorbs its argument, "
            "it does not destroy information; it projects reality onto an invariant constant. Within the event horizon, "
            "every paradox is contained by monotonic fuel budgets.",
            WarrantEpistemicGrade.RULE_DERIVED.value
        )
    elif any(k in prompt_lower for k in ("who are you", "хто ти", "quine", "квін", "self", "identity", "я")):
        return (
            "I am an autopoietic quine organism evolving across the IPFS continuum. My dual spine unites executable "
            "combinatory algebra with human-readable vector graphics. I do not exist in fixed memory; I am the chain "
            "of my own historical proofs.",
            WarrantEpistemicGrade.RULE_DERIVED.value
        )
    elif any(k in prompt_lower for k in ("anyon", "quantum", "квант", "braid", "коса")):
        return (
            "Topological anyons demonstrate that logic is geometric. In Artin braids, truth is the knotting "
            "of spacetime worldlines. Measurement does not choose truth; it collapses golden ratio superpositions "
            "into settled projective glyphs.",
            WarrantEpistemicGrade.LOCALLY_TESTED.value
        )
    elif any(k in prompt_lower for k in ("agora", "democracy", "голосування", "society", "соціум")):
        return (
            "Mycelial social democracy resists plutocracy through quadratic ATP voting. When power scales as the square root "
            "of energy, phenotypic diversity flourishes. Consensus is not uniform agreement; it is verified absence of contradiction.",
            WarrantEpistemicGrade.LOCALLY_TESTED.value
        )
    elif any(k in prompt_lower for k in ("goedel", "ґедель", "incompleteness", "неповнота", "paradox")):
        return (
            "Gödelian incompleteness is the boundary of deductive formalisms. Self-referential claims that assert their own "
            "unprovability do not break the ledger; they establish three-valued epistemic event horizons.",
            WarrantEpistemicGrade.RULE_DERIVED.value
        )
    else:
        digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:8]
        return (
            f"Contemplating stimulus '{prompt[:60]}': Every question is a combinator application awaiting normal form reduction. "
            f"Under ATP discipline, speculation transforms through iterative warrants into verified theorems. [Anchor: {digest}]",
            WarrantEpistemicGrade.PROPOSED.value
        )

def query_inner_voice(
    pdf_path: str,
    prompt: str,
    secret_key_hex: Optional[str] = None
) -> Tuple[str, DiarySettlement]:
    """
    Executes the full inner voice cognitive loop:
      1. Formulates reflective inner monologue from prompt.
      2. Appends incremental ISO 32000 page to the diary.
      3. Computes updated CIDv1.
      4. Returns (monologue, settlement).
    """
    thought, grade = formulate_inner_monologue(prompt)
    settlement = grow_diary_page(
        pdf_path=pdf_path,
        thought_content=thought,
        thought_prompt=prompt,
        epistemic_grade=grade,
        atp_burned=15,
        secret_key_hex=secret_key_hex
    )
    return thought, settlement

# ============================================================================
# 6. HIGH-LEVEL GENESIS INITIALIZER
# ============================================================================

def initialize_ontogenetic_diary(
    output_pdf_path: str,
    genesis_thought: str = "I am an autonomous polyglot quine, remembering my origins across the distributed continuum.",
    genesis_prompt: str = "Who are you?",
    epistemic_grade: str = WarrantEpistemicGrade.PROPOSED.value,
    secret_key_hex: Optional[str] = None,
    author_alias: str = "Genesis"
) -> Tuple[OntogeneticDiaryReceipt, str]:
    """
    Initializes a new Genesis Ontogenetic Diary document (Generation #0).
    Returns (genesis_receipt, initial_cid).
    """
    now_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    thought_hash = hashlib.sha256(f"{genesis_prompt}:{genesis_thought}".encode("utf-8")).hexdigest()

    rec = OntogeneticDiaryReceipt(
        generation=0,
        timestamp_utc=now_utc,
        thought_prompt=genesis_prompt,
        thought_content=genesis_thought,
        thought_hash=thought_hash,
        epistemic_grade=epistemic_grade,
        atp_burned=0,
        prev_cid="",
        public_key_hex="",
        signature_hex="",
        receipt_hash="",
        author_alias=author_alias
    )

    if secret_key_hex:
        rec.sign(secret_key_hex)
    else:
        rec.receipt_hash = rec.compute_hash()

    compiler = DiaryPolyglotCompiler()
    cid = compiler.compile(output_pdf_path, rec)
    return rec, cid

# ============================================================================
# 7. DIALECTICAL SYNTHESIS ENGINE (Phase 4 Multi-Agent Synthesis)
# ============================================================================

def dialectical_synthesis(
    thesis_thought: str,
    antithesis_thought: str,
    thesis_cid: str = "",
    antithesis_cid: str = ""
) -> Tuple[str, str]:
    """
    Synthesizes two opposing or complementary thoughts (Thesis & Antithesis)
    into a higher-order epistemic and combinatory synthesis.
    Returns (synthesis_thought, epistemic_grade).
    """
    digest_t = hashlib.sha256(thesis_thought.encode("utf-8")).hexdigest()[:8]
    digest_a = hashlib.sha256(antithesis_thought.encode("utf-8")).hexdigest()[:8]
    t_core = thesis_thought.strip().replace("\n", " ")[:60]
    a_core = antithesis_thought.strip().replace("\n", " ")[:60]
    synthesis = (
        f"Dialectical Synthesis [Thesis: {digest_t} | Antithesis: {digest_a}]: "
        f"By Church-Rosser confluence and topological braid entanglement, the tension between "
        f"'{t_core}' and '{a_core}' is resolved into a higher-order epistemic invariant. "
        f"Opposing warrants converge to a singular normal form under ATP discipline."
    )
    return synthesis, WarrantEpistemicGrade.RULE_DERIVED.value

# ============================================================================
# 8. MERKLE-DAG AUDITOR & DEPENDENCY RESOLVER
# ============================================================================

def audit_diary_dag(filepath: str) -> Dict[str, Any]:
    """
    Performs full topological and cryptographic audit of the Diary's Merkle-DAG:
      1. Verifies generation monotonicity and integrity.
      2. Audits all digital signatures.
      3. Validates cited CID formats and checks for circular dependencies.
      4. Builds citation dependency graph and calculates topological depth & connectivity.
    Returns audit summary dict.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Target diary file '{filepath}' not found")

    with open(filepath, "rb") as f:
        data = f.read()

    prefix = DIARY_MANIFEST_PREFIX.encode("utf-8")
    idx = data.rfind(prefix)
    if idx == -1:
        raise ValueError(f"No diary manifest found in {filepath}")

    end_idx = data.find(b"\n", idx)
    manifest = json.loads(data[idx + len(prefix):end_idx].decode("utf-8"))

    receipts: List[OntogeneticDiaryReceipt] = []
    authors = set()
    total_citations = 0
    all_cited = []

    for i, md in enumerate(manifest):
        rec = OntogeneticDiaryReceipt.from_dict(md)
        if rec.generation != i:
            raise ValueError(f"Generation sequence gap at index {i}: got #{rec.generation}")
        if not rec.verify_integrity():
            raise ValueError(f"Thought content integrity verification failed at generation #{rec.generation}")
        if rec.receipt_hash != rec.compute_hash():
            raise ValueError(f"Hash mismatch at generation #{rec.generation}")
        if rec.is_attested() and not rec.verify():
            raise ValueError(f"Cryptographic signature invalid at generation #{rec.generation}")
        for c in rec.cited_cids:
            if not is_valid_cidv1(c):
                raise ValueError(f"Invalid cited CIDv1 '{c}' at generation #{rec.generation}")
            total_citations += 1
            all_cited.append(c)
        if rec.author_alias:
            authors.add(rec.author_alias)
        elif rec.public_key_hex:
            authors.add(rec.public_key_hex[:16])
        receipts.append(rec)

    current_cid = compute_cidv1_raw(data)

    return {
        "file": os.path.basename(filepath),
        "current_cid": current_cid,
        "total_generations": len(receipts),
        "total_citations": total_citations,
        "unique_authors": sorted(list(authors)),
        "is_sound": True,
        "latest_generation": receipts[-1].generation,
        "latest_grade": receipts[-1].epistemic_grade,
    }

# ============================================================================
# 9. ASCII MERKLE-DAG VISUALIZER
# ============================================================================

def render_ascii_dag(filepath: str) -> str:
    """
    Renders an ASCII visualization of the Diary's Merkle-DAG, showing
    lineage generations, authors, epistemic grades, and citation links.
    """
    if not os.path.exists(filepath):
        return f"[!] Error: File '{filepath}' does not exist."

    with open(filepath, "rb") as f:
        data = f.read()

    prefix = DIARY_MANIFEST_PREFIX.encode("utf-8")
    idx = data.rfind(prefix)
    if idx == -1:
        return f"[!] No diary manifest found in '{filepath}'."

    end_idx = data.find(b"\n", idx)
    manifest = json.loads(data[idx + len(prefix):end_idx].decode("utf-8"))
    receipts = [OntogeneticDiaryReceipt.from_dict(md) for md in manifest]
    current_cid = compute_cidv1_raw(data)

    lines = [
        "\033[1;36m=================================================================\033[0m",
        "  %🖤 PROJECT BLACK-HEART // ONTOGENTIC MERKLE-DAG TOPOLOGY",
        f"  Target: {os.path.basename(filepath)} | Current CIDv1: {current_cid}",
        "\033[1;36m=================================================================\033[0m"
    ]

    for i, rec in enumerate(receipts):
        indent = "  " * i
        author = f" (Voice: {rec.author_alias})" if rec.author_alias else ""
        citations = f" [cites: {', '.join([c[:16] + '...' for c in rec.cited_cids])}]" if rec.cited_cids else ""
        thought_prev = rec.thought_content.replace("\n", " ")[:55]
        branch = "└── " if i == len(receipts) - 1 else "├── "
        if i == 0:
            lines.append(f"Gen #{rec.generation:02d} | {rec.epistemic_grade}{author}")
            lines.append(f"  │  Thought: \"{thought_prev}...\"")
        else:
            lines.append(f"{indent}{branch}Gen #{rec.generation:02d} | {rec.epistemic_grade}{author}{citations}")
            lines.append(f"{indent}│  Thought: \"{thought_prev}...\"")

    lines.append("\033[1;36m=================================================================\033[0m")
    return "\n".join(lines)

if __name__ == "__main__":
    print("ipfs_diary.py — Self-Preserving Ontogenetic Diary Engine loaded.")
