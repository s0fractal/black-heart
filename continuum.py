#!/usr/bin/env python3
"""
continuum.py — Suspended Continuum Computations & Resumable Polyglot Documents.
Part of Project Black-Heart (%🖤).
Formal Specification: CONTINUUM.md

Features:
  - Non-destructive combinator reduction with ATP fuel budgets.
  - Suspended Thunks: Preserves partial computation states as content-addressed ASTs.
  - Deterministic Checkpointing: Hash chain of computation checkpoints.
  - Resumable Polyglot PDF: A single ISO 32000 PDF document that holds an active
    computation, can be executed via 'python3 computation.pdf --fuel <N>', and
    appends incremental update blocks (ISO 32000 §7.5.6) as work progresses.
  - Visual Progress Gauge: Native vector graphics fuel/completion meter.
"""

from __future__ import annotations
import os
import sys
import json
import time
import hashlib
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple

from glyph import (
    parse, evaluate, reduce_step, tree_size, term_hash, canonical_bytes,
    Term, Comb, Var, App, EvalResult, EvalStatus,
    GLYPH_K, GLYPH_I, GLYPH_S, GLYPH_Y, GLYPH_ANCHOR
)
from crypto import generate_keypair, sign_hex, verify_hex

CONTINUUM_MANIFEST_PREFIX = "%🖤 CONTINUUM_THUNK: "

# ============================================================================
# THUNK STATE & CHECKPOINTING
# ============================================================================

@dataclass
class ThunkCheckpoint:
    height: int
    timestamp_utc: str
    initial_expr: str
    current_expr: str
    atp_spent_step: int
    atp_accumulated: int
    peak_size: int
    status: str  # "SUSPENDED" or "SETTLED"
    prev_hash: str
    checkpoint_hash: str = ""
    public_key_hex: str = ""
    signature_hex: str = ""

    def canonical_bytes(self) -> bytes:
        data = {
            "height": self.height,
            "timestamp_utc": self.timestamp_utc,
            "initial_expr": self.initial_expr,
            "current_expr": self.current_expr,
            "atp_spent_step": self.atp_spent_step,
            "atp_accumulated": self.atp_accumulated,
            "peak_size": self.peak_size,
            "status": self.status,
            "prev_hash": self.prev_hash,
            "public_key_hex": self.public_key_hex,
        }
        return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

    def compute_hash(self) -> str:
        return hashlib.sha256(self.canonical_bytes()).hexdigest()

    def sign(self, secret_key_hex: str) -> None:
        self.checkpoint_hash = self.compute_hash()
        self.signature_hex = sign_hex(secret_key_hex, self.checkpoint_hash.encode("utf-8"))

    def verify(self) -> bool:
        expected_hash = self.compute_hash()
        if self.checkpoint_hash != expected_hash:
            return False
        if self.public_key_hex:
            if not self.signature_hex:
                return False
            return verify_hex(self.public_key_hex, self.checkpoint_hash.encode("utf-8"), self.signature_hex)
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "height": self.height,
            "timestamp_utc": self.timestamp_utc,
            "initial_expr": self.initial_expr,
            "current_expr": self.current_expr,
            "atp_spent_step": self.atp_spent_step,
            "atp_accumulated": self.atp_accumulated,
            "peak_size": self.peak_size,
            "status": self.status,
            "prev_hash": self.prev_hash,
            "checkpoint_hash": self.checkpoint_hash,
            "public_key_hex": self.public_key_hex,
            "signature_hex": self.signature_hex,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> ThunkCheckpoint:
        return cls(
            height=d["height"],
            timestamp_utc=d["timestamp_utc"],
            initial_expr=d["initial_expr"],
            current_expr=d["current_expr"],
            atp_spent_step=d["atp_spent_step"],
            atp_accumulated=d["atp_accumulated"],
            peak_size=d["peak_size"],
            status=d["status"],
            prev_hash=d["prev_hash"],
            checkpoint_hash=d.get("checkpoint_hash", ""),
            public_key_hex=d.get("public_key_hex", ""),
            signature_hex=d.get("signature_hex", ""),
        )

# ============================================================================
# CONTINUUM REDUCER
# ============================================================================

def step_continuum(
    current_thunk: ThunkCheckpoint,
    fuel: int,
    secret_key_hex: Optional[str] = None
) -> ThunkCheckpoint:
    """
    Takes an existing thunk checkpoint, executes up to 'fuel' ATP reduction steps,
    and returns a new checkpoint (either SUSPENDED or SETTLED).
    Refuses to step if current_thunk is invalid or tampered.
    """
    if not current_thunk.verify():
        raise ValueError("Refusing to step from invalid or tampered predecessor checkpoint")

    if current_thunk.status == "SETTLED":
        return current_thunk

    term = parse(current_thunk.current_expr)
    result = evaluate(term, max_atp=fuel, raise_on_limit=False)

    new_expr = str(result.term)
    new_status = "SETTLED" if result.is_settled() else "SUSPENDED"
    accumulated_atp = current_thunk.atp_accumulated + result.atp_spent
    peak = max(current_thunk.peak_size, result.peak_size)
    now_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    next_cp = ThunkCheckpoint(
        height=current_thunk.height + 1,
        timestamp_utc=now_utc,
        initial_expr=current_thunk.initial_expr,
        current_expr=new_expr,
        atp_spent_step=result.atp_spent,
        atp_accumulated=accumulated_atp,
        peak_size=peak,
        status=new_status,
        prev_hash=current_thunk.checkpoint_hash,
        public_key_hex=current_thunk.public_key_hex,
    )

    if secret_key_hex:
        next_cp.sign(secret_key_hex)
    else:
        next_cp.checkpoint_hash = next_cp.compute_hash()

    return next_cp

# ============================================================================
# RESUMABLE COMPUTATION POLYGLOT COMPILER
# ============================================================================

class ResumableComputationPolyglot:
    """
    Compiles and incrementally maintains an ISO 32000 PDF document
    embedding a resumable continuum computation.
    """
    def __init__(self, title: str = "BLACK-HEART CONTINUUM COMPUTATION"):
        self.title = title
        self.checkpoints: List[ThunkCheckpoint] = []

    def initialize(
        self,
        initial_expr: str,
        initial_fuel: int,
        secret_key_hex: str,
        public_key_hex: str,
    ) -> ThunkCheckpoint:
        """
        Initializes checkpoint #0 (Genesis thunk).
        """
        now_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        term = parse(initial_expr)
        res = evaluate(term, max_atp=initial_fuel, raise_on_limit=False)
        status = "SETTLED" if res.is_settled() else "SUSPENDED"

        cp = ThunkCheckpoint(
            height=0,
            timestamp_utc=now_utc,
            initial_expr=initial_expr,
            current_expr=str(res.term),
            atp_spent_step=res.atp_spent,
            atp_accumulated=res.atp_spent,
            peak_size=res.peak_size,
            status=status,
            prev_hash="0" * 64,
            public_key_hex=public_key_hex,
        )
        cp.sign(secret_key_hex)
        self.checkpoints = [cp]
        return cp

    def compile(self, output_pdf_path: str) -> None:
        """Compiles the initial PDF polyglot with checkpoint #0."""
        if not self.checkpoints:
            raise ValueError("No checkpoints present to compile.")

        cp0 = self.checkpoints[0]
        pdf_bytes = self._build_base_pdf(cp0)
        runner_script = self._build_runner_script()

        manifest_bytes = f"\n{CONTINUUM_MANIFEST_PREFIX}{json.dumps([cp0.to_dict()], ensure_ascii=False)}\n".encode("utf-8")

        full_content = (
            pdf_bytes +
            manifest_bytes +
            b'\n"""\n' +
            runner_script.encode("utf-8")
        )

        with open(output_pdf_path, "wb") as f:
            f.write(full_content)

    def _build_base_pdf(self, cp: ThunkCheckpoint) -> bytes:
        """Generates standard ISO 32000 PDF bytes for checkpoint 0."""
        stream_content = self._generate_page_stream(cp)
        stream_bytes = stream_content.encode("utf-8")

        objects = []
        objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
        objects.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
        objects.append(
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>"
        )
        objects.append(
            f"<< /Length {len(stream_bytes)} >>\nstream\n".encode("latin1") +
            stream_bytes +
            b"\nendstream"
        )
        objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

        out = bytearray(b"# coding: utf-8\nr\"\"\"%PDF-1.7\n%\xf0\x9f\x96\xa4\n")
        offsets = [0]
        for i, obj in enumerate(objects, 1):
            offsets.append(len(out))
            out.extend(f"{i} 0 obj\n".encode("latin1"))
            out.extend(obj)
            out.extend(b"\nendobj\n")

        xref_offset = len(out)
        out.extend(f"xref\n0 {len(objects)+1}\n".encode("latin1"))
        out.extend(b"0000000000 65535 f \n")
        for off in offsets[1:]:
            out.extend(f"{off:010d} 00000 n \n".encode("latin1"))

        out.extend(
            f"trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF".encode("latin1")
        )
        return bytes(out)

    def _generate_page_stream(self, cp: ThunkCheckpoint) -> str:
        """Draws visual layout with vector ATP fuel gauge and checkpoint table."""
        status_color = "0.15 0.65 0.25" if cp.status == "SETTLED" else "0.85 0.45 0.1"
        status_label = "SETTLED (Q.E.D.)" if cp.status == "SETTLED" else "SUSPENDED (IN PROGRESS)"

        gauge_width = 495
        # Visual progress ratio (cap display at reasonable scale)
        pct = 1.0 if cp.status == "SETTLED" else min(0.85, cp.atp_accumulated / (cp.atp_accumulated + 5000))
        fill_w = max(10, int(gauge_width * pct))

        ops = [
            "q",
            # Header banner
            "0.08 0.12 0.25 rg",
            "50 780 495 40 re f",
            "1 1 1 rg",
            "BT /F1 16 Tf 65 795 Td (BLACK-HEART CONTINUUM COMPUTATION) Tj ET",
            "0.7 0.8 1 rg",
            "BT /F1 9 Tf 65 785 Td (ISO 32000 Resumable Polyglot Thunk Engine) Tj ET",
            # Status badge
            f"{status_color} rg",
            "50 735 495 28 re f",
            "1 1 1 rg",
            f"BT /F1 12 Tf 65 744 Td (STATE: {status_label}  |  HEIGHT: #{cp.height}) Tj ET",
            # Vector Progress Bar
            "0.9 0.92 0.95 rg",
            f"50 700 {gauge_width} 16 re f",
            f"{status_color} rg",
            f"50 700 {fill_w} 16 re f",
            "0.3 0.3 0.3 RG 1 w",
            f"50 700 {gauge_width} 16 re S",
            # Details Card
            "0.96 0.97 0.99 rg",
            "50 490 495 190 re f",
            "0.75 0.8 0.9 RG 1 w",
            "50 490 495 190 re S",
            "0.1 0.1 0.1 rg",
            f"BT /F1 10 Tf 65 655 Td (Initial Expr:     {cp.initial_expr[:50]}) Tj ET",
            f"BT /F1 10 Tf 65 635 Td (Current State:    {cp.current_expr[:50]}) Tj ET",
            f"BT /F1 10 Tf 65 615 Td (Cumulative ATP:  {cp.atp_accumulated} fuel burned) Tj ET",
            f"BT /F1 10 Tf 65 595 Td (Peak AST Nodes:   {cp.peak_size}) Tj ET",
            f"BT /F1 10 Tf 65 575 Td (Checkpoint Hash:  {cp.checkpoint_hash[:32]}...) Tj ET",
            f"BT /F1 10 Tf 65 555 Td (Signer Public PK: {cp.public_key_hex[:32]}...) Tj ET",
            f"BT /F1 10 Tf 65 535 Td (Timestamp UTC:    {cp.timestamp_utc}) Tj ET",
            f"BT /F1 9 Tf 65 505 Td (Resume via CLI:   'python3 <this_file>.pdf --fuel 5000') Tj ET",
            "Q"
        ]
        return "\n".join(ops)

    def _build_runner_script(self) -> str:
        return r'''
import os
import sys
import json
import argparse
import hashlib
import time

current_dir = os.path.dirname(os.path.abspath(__file__))
for candidate in [os.getcwd(), current_dir, os.path.dirname(current_dir), "/Users/s0fractal/Projects/black-heart"]:
    if os.path.isdir(candidate) and candidate not in sys.path:
        sys.path.insert(0, candidate)

PREFIX = "%" + "🖤" + " CONTINUUM_THUNK: "

def audit_self(filepath: str):
    with open(filepath, "rb") as f:
        content = f.read()

    prefix_bytes = PREFIX.encode("utf-8")
    idx = content.rfind(prefix_bytes)  # Find latest manifest
    if idx == -1:
        print("[FAIL] No continuum thunk manifest found.")
        sys.exit(1)

    end_idx = content.find(b"\n", idx)
    raw_json = content[idx + len(prefix_bytes):end_idx].decode("utf-8")
    checkpoints = json.loads(raw_json)

    print("=================================================================")
    print("  %🖤 BLACK-HEART CONTINUUM COMPUTATION AUDITOR")
    print(f"  Target File: {os.path.basename(filepath)} ({len(content)} bytes)")
    print("=================================================================\n")

    if not checkpoints:
        print("[FAIL] Manifest contains no checkpoints.")
        sys.exit(1)

    try:
        from continuum import ThunkCheckpoint
        try:
            from glyph import parse, reduce_step
        except ImportError:
            from sk_combinators import parse, reduce_step
    except Exception as e:
        print(f"[FAIL] Required runtime modules unavailable: {e}")
        sys.exit(1)

    parsed_cps = []
    for i, cpd in enumerate(checkpoints):
        try:
            cp = ThunkCheckpoint.from_dict(cpd)
        except Exception as e:
            print(f"[FAIL] Malformed checkpoint entry #{i}: {e}")
            sys.exit(1)
        if not cp.verify():
            print(f"[FAIL] Checkpoint #{cp.height} cryptographic/integrity verification failed.")
            sys.exit(1)
        if i == 0:
            if cp.height != 0:
                print(f"[FAIL] Genesis checkpoint must have height 0, got {cp.height}.")
                sys.exit(1)
            if cp.prev_hash != "0" * 64:
                print(f"[FAIL] Genesis checkpoint prev_hash must be 64 zeros, got {cp.prev_hash}.")
                sys.exit(1)
        else:
            prev = parsed_cps[i - 1]
            if cp.height != prev.height + 1:
                print(f"[FAIL] Sequence error at #{cp.height}: expected #{prev.height + 1}.")
                sys.exit(1)
            if cp.prev_hash != prev.checkpoint_hash:
                print(f"[FAIL] Hash chaining broken at #{cp.height}: expected {prev.checkpoint_hash}, got {cp.prev_hash}.")
                sys.exit(1)
            if cp.initial_expr != prev.initial_expr:
                print(f"[FAIL] Checkpoint #{cp.height} altered initial_expr.")
                sys.exit(1)
        parsed_cps.append(cp)

    latest = parsed_cps[-1]
    print(f"[*] Checkpoint Height:  #{latest.height}")
    print(f"[*] Execution Status:   {latest.status}")
    print(f"[*] Cumulative ATP:     {latest.atp_accumulated}")
    print(f"[*] Initial Term:       {latest.initial_expr}")
    print(f"[*] Current Term:       {latest.current_expr}")
    print(f"[*] Checkpoint Hash:    ⚓ {latest.checkpoint_hash}\n")

    if latest.status == "SETTLED":
        try:
            term = parse(latest.current_expr)
            _, reduced = reduce_step(term)
            if reduced:
                print(f"[FAIL] Checkpoint claims SETTLED but expression '{latest.current_expr}' is reducible!")
                sys.exit(1)
        except Exception as e:
            print(f"[FAIL] Could not verify normal form for SETTLED expression: {e}")
            sys.exit(1)
        print("\033[1;32m[✓] COMPUTATION REACHED NORMAL FORM (Q.E.D.)\033[0m\n")
    else:
        print("\033[1;33m[⏳] COMPUTATION SUSPENDED (Ready for resumption)\033[0m")
        print("     To resume: run with '--fuel <N>' or use Black-Heart CLI.\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Black-Heart Continuum Polyglot")
    parser.add_argument("--fuel", type=int, help="Additional ATP fuel to evaluate")
    parser.add_argument("--secret-key", help="Optional secret key hex to sign next checkpoint")
    args, _ = parser.parse_known_args()

    if args.fuel:
        from continuum import resume_computation_in_pdf
        resume_computation_in_pdf(sys.argv[0], additional_atp=args.fuel, secret_key_hex=args.secret_key)
    else:
        audit_self(sys.argv[0])
'''

# ============================================================================
# INCREMENTAL PDF RESUMPTION (ISO 32000 §7.5.6)
# ============================================================================

def resume_computation_in_pdf(
    pdf_path: str,
    additional_atp: int,
    secret_key_hex: Optional[str] = None
) -> ThunkCheckpoint:
    """
    Loads an existing continuum polyglot PDF, extracts the latest checkpoint,
    audits the entire history chain, executes up to additional_atp steps,
    appends an incremental update block (with new visual page and manifest),
    and updates the PDF in-place!
    """
    with open(pdf_path, "rb") as f:
        content = f.read()

    prefix = CONTINUUM_MANIFEST_PREFIX.encode("utf-8")
    idx = content.rfind(prefix)
    if idx == -1:
        raise ValueError(f"No continuum thunk manifest found in {pdf_path}")

    end_idx = content.find(b"\n", idx)
    checkpoints_data = json.loads(content[idx + len(prefix):end_idx].decode("utf-8"))
    if not checkpoints_data:
        raise ValueError(f"Continuum manifest in {pdf_path} is empty")

    checkpoints = [ThunkCheckpoint.from_dict(d) for d in checkpoints_data]
    for i, cp in enumerate(checkpoints):
        if cp.height != i:
            raise ValueError(f"Continuum chain discontinuity: checkpoint #{cp.height} at index {i}")
        if not cp.verify():
            raise ValueError(f"Continuum chain integrity failure: checkpoint #{cp.height} failed verification")
        if i == 0:
            if cp.prev_hash != "0" * 64:
                raise ValueError("Genesis checkpoint prev_hash must be 64 zeros")
        else:
            prev = checkpoints[i - 1]
            if cp.prev_hash != prev.checkpoint_hash:
                raise ValueError(f"Continuum chain hash broken at #{cp.height}: expected {prev.checkpoint_hash}, found {cp.prev_hash}")
            if cp.initial_expr != prev.initial_expr:
                raise ValueError(f"Continuum chain altered initial_expr at #{cp.height}")

    current = checkpoints[-1]

    if current.status == "SETTLED":
        print(f"[*] Computation already SETTLED at checkpoint #{current.height}. Nothing to reduce.")
        return current

    # Step computation
    next_cp = step_continuum(current, additional_atp, secret_key_hex)
    checkpoints.append(next_cp)

    # Re-encode manifest
    new_manifest = (
        f"\n{CONTINUUM_MANIFEST_PREFIX}{json.dumps([c.to_dict() for c in checkpoints], ensure_ascii=False)}\n"
    ).encode("utf-8")

    # Generate incremental visual update
    builder = ResumableComputationPolyglot()
    stream_content = builder._generate_page_stream(next_cp)
    stream_bytes = stream_content.encode("utf-8")

    # Find previous xref and root
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

    # Incremental update object IDs
    base_obj_count = 5 + (current.height * 3)
    new_page_id = base_obj_count + 1
    new_contents_id = base_obj_count + 2
    new_pages_id = base_obj_count + 3

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

    kids_refs = " ".join(f"{3 if i == 0 else 5 + (i * 3) - 2} 0 R" for i in range(len(checkpoints)))
    pages_obj = (
        f"{new_pages_id} 0 obj\n<< /Type /Pages /Kids [{kids_refs}] /Count {len(checkpoints)} >>\nendobj\n"
    ).encode("latin1")

    root_obj_id = new_pages_id + 1
    catalog_obj = (
        f"{root_obj_id} 0 obj\n<< /Type /Catalog /Pages {new_pages_id} 0 R >>\nendobj\n"
    ).encode("latin1")

    # Split existing content to keep all PDF bytes inside the raw Python docstring
    docstring_marker = b'\n"""\n'
    split_pos = content.find(docstring_marker)
    if split_pos != -1:
        pdf_prefix = content[:split_pos]
        runner_suffix = content[split_pos + len(docstring_marker):]
        # Remove old manifest from pdf_prefix if present
        m_idx = pdf_prefix.find(prefix)
        if m_idx != -1:
            m_end = pdf_prefix.find(b"\n", m_idx)
            pdf_prefix = pdf_prefix[:m_idx] + pdf_prefix[m_end + 1:]
        # Remove old manifest from runner suffix if present
        m_idx2 = runner_suffix.find(prefix)
        if m_idx2 != -1:
            m_end2 = runner_suffix.find(b"\n", m_idx2)
            runner_suffix = runner_suffix[:m_idx2] + runner_suffix[m_end2 + 1:]
    else:
        pdf_prefix = content
        runner_suffix = b""

    update_body = bytearray()
    update_offsets = []

    # Calculate offsets based on pdf_prefix
    for obj in (page_obj, contents_obj, pages_obj, catalog_obj):
        obj_num = int(obj[:obj.find(b" 0 obj")].decode("latin1"))
        update_offsets.append((obj_num, len(pdf_prefix) + len(update_body)))
        update_body.extend(obj)

    new_xref_offset = len(pdf_prefix) + len(update_body)
    xref_chunk = bytearray(f"xref\n".encode("latin1"))
    for obj_num, off in update_offsets:
        xref_chunk.extend(f"{obj_num} 1\n{off:010d} 00000 n \n".encode("latin1"))

    trailer = (
        f"trailer\n<< /Size {root_obj_id + 1} /Root {root_obj_id} 0 R /Prev {prev_xref} >>\n"
        f"startxref\n{new_xref_offset}\n%%EOF\n"
    ).encode("latin1")

    updated_full = (
        pdf_prefix +
        update_body +
        xref_chunk +
        trailer +
        new_manifest +
        b'\n"""\n' +
        runner_suffix
    )

    with open(pdf_path, "wb") as f:
        f.write(updated_full)

    print(f"\033[1;32m[✓] Incremental Continuum Update Applied to {os.path.basename(pdf_path)}\033[0m")
    print(f"    Height: #{next_cp.height} | Status: {next_cp.status} | Cumulative ATP: {next_cp.atp_accumulated}")
    print(f"    Current Form: {next_cp.current_expr[:50]}...")
    print(f"    Checkpoint Hash: ⚓ {next_cp.checkpoint_hash[:16]}...\n")

    return next_cp

if __name__ == "__main__":
    print("Continuum Engine Standalone Test...")
    sk, pk = generate_keypair()
    poly = ResumableComputationPolyglot("TEST CONTINUUM")
    # A combinator expression that takes several steps to reduce:
    # (S (K (K I)) (K I)) x y
    test_expr = "🌿 (🖤 (🖤 🤍)) (🖤 🤍) Alpha Beta"
    cp0 = poly.initialize(test_expr, initial_fuel=2, secret_key_hex=sk, public_key_hex=pk)
    print(f"Genesis Checkpoint: status={cp0.status}, atp={cp0.atp_accumulated}, term={cp0.current_expr}")
    poly.compile("/tmp/test_continuum.pdf")
    print("[✓] Compiled /tmp/test_continuum.pdf")

    res = resume_computation_in_pdf("/tmp/test_continuum.pdf", additional_atp=5, secret_key_hex=sk)
    print(f"[✓] Resumed: status={res.status}, atp={res.atp_accumulated}, term={res.current_expr}")
