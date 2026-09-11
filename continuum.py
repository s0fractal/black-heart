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

    def verify(self, expected_public_key_hex: Optional[str] = None) -> bool:
        expected_hash = self.compute_hash()
        if self.checkpoint_hash != expected_hash:
            return False
        if expected_public_key_hex is not None:
            if self.public_key_hex != expected_public_key_hex:
                return False
            if not self.signature_hex:
                return False
            return verify_hex(self.public_key_hex, self.checkpoint_hash.encode("utf-8"), self.signature_hex)
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
# CONTINUUM COMPUTATIONAL VERIFIER & REDUCER
# ============================================================================

DEFAULT_MAX_AUDIT_ATP = 100_000

ALLOWED_CHECKPOINT_STATUSES = frozenset({"SETTLED", "SUSPENDED"})

def verify_checkpoint_computation(
    cp: ThunkCheckpoint,
    max_verifier_atp: int = DEFAULT_MAX_AUDIT_ATP
) -> Tuple[bool, str]:
    """
    Independently verifies the computational authenticity of a continuum checkpoint:
    1. Validates syntactic structure of expressions.
    2. Enforces strict typing and non-negative ATP accounting within bounded verifier budget.
    3. Enforces single-checkpoint invariants (step <= accumulated, genesis step == accumulated).
    4. Enforces closed status set (SETTLED or SUSPENDED).
    5. Replays deterministic combinatory reduction from initial_expr.
    6. For SETTLED checkpoints:
       - Enforces that current_expr is genuinely irreducible (normal form).
       - Enforces that replayed reduction reaches normal form.
       - Enforces that replayed term strictly matches claimed current_expr.
       - Enforces that replayed fuel consumed strictly matches claimed atp_accumulated.
    7. For SUSPENDED checkpoints:
       - If atp_accumulated == 0, initial_expr must equal current_expr and atp_spent_step must be 0.
       - If atp_accumulated > 0, replaying for atp_accumulated must match current_expr and atp_spent.
       - Enforces that replayed term is not already settled (cannot claim SUSPENDED if irreducible).
    Returns: (is_valid: bool, reason: str)
    """
    # Strict integer types for numeric fields (reject bool, float, str, None, etc.)
    if (type(cp.height) is not int or 
        type(cp.atp_spent_step) is not int or 
        type(cp.atp_accumulated) is not int or 
        type(cp.peak_size) is not int):
        return False, "Checkpoint numeric fields must be strict integers"

    if cp.height < 0 or cp.atp_spent_step < 0 or cp.atp_accumulated < 0 or cp.peak_size < 0:
        return False, f"Negative numeric values claimed: height={cp.height}, spent_step={cp.atp_spent_step}, accumulated={cp.atp_accumulated}"

    if cp.atp_spent_step > cp.atp_accumulated:
        return False, f"Step ATP ({cp.atp_spent_step}) exceeds accumulated total ATP ({cp.atp_accumulated})"

    if cp.height == 0 and cp.atp_spent_step != cp.atp_accumulated:
        return False, f"Genesis checkpoint (height 0) step ATP ({cp.atp_spent_step}) must equal accumulated ATP ({cp.atp_accumulated})"

    if not isinstance(cp.status, str) or cp.status not in ALLOWED_CHECKPOINT_STATUSES:
        return False, f"Invalid or unrecognized checkpoint status: {cp.status!r}"

    if cp.atp_accumulated > max_verifier_atp:
        return False, f"Claimed ATP {cp.atp_accumulated} exceeds verifier budget limit {max_verifier_atp} (BUDGET_EXHAUSTED)"

    try:
        from glyph import parse, reduce_step, evaluate
    except ImportError:
        try:
            from sk_combinators import parse, reduce_step, evaluate
        except Exception as e:
            return False, f"Combinatory logic runtime unavailable: {e}"

    try:
        cur_term = parse(cp.current_expr)
        init_term = parse(cp.initial_expr)
    except Exception as e:
        return False, f"Syntax parsing failure: {e}"

    if cp.status == "SETTLED":
        _, reduced = reduce_step(cur_term)
        if reduced:
            return False, f"Checkpoint claims SETTLED but expression '{cp.current_expr}' is reducible"

        res = evaluate(init_term, max_atp=max_verifier_atp, raise_on_limit=False)
        if not res.is_settled():
            return False, f"Replay did not settle within verifier budget {max_verifier_atp} (BUDGET_EXHAUSTED)"

        if str(res.term) != cp.current_expr:
            return False, f"Computational transition mismatch: replaying '{cp.initial_expr}' produced '{res.term}', not claimed '{cp.current_expr}'"

        if res.atp_spent != cp.atp_accumulated:
            return False, f"Computational ATP accounting mismatch: actual reduction cost was {res.atp_spent} ATP, claimed {cp.atp_accumulated} ATP"

    elif cp.status == "SUSPENDED":
        _, reduced = reduce_step(cur_term)
        if not reduced:
            return False, f"Checkpoint claims SUSPENDED but expression '{cp.current_expr}' is already in normal form (irreducible)"

        if cp.atp_accumulated == 0:
            if cp.initial_expr != cp.current_expr:
                return False, f"Suspended checkpoint at 0 ATP has divergent expressions: initial='{cp.initial_expr}', current='{cp.current_expr}'"
        else:
            res = evaluate(init_term, max_atp=cp.atp_accumulated, raise_on_limit=False)
            if res.atp_spent != cp.atp_accumulated or str(res.term) != cp.current_expr:
                return False, f"Computational transition mismatch for suspended thunk: replaying '{cp.initial_expr}' for {cp.atp_accumulated} ATP yielded '{res.term}' ({res.atp_spent} ATP), not claimed '{cp.current_expr}'"
            if res.is_settled():
                return False, f"Checkpoint claims SUSPENDED but computation settled into normal form '{res.term}' at {res.atp_spent} ATP"

    return True, "SOUND"

def step_continuum(
    current_thunk: ThunkCheckpoint,
    fuel: int,
    secret_key_hex: Optional[str] = None
) -> ThunkCheckpoint:
    """
    Takes an existing thunk checkpoint, executes up to 'fuel' ATP reduction steps,
    and returns a new checkpoint (either SUSPENDED or SETTLED).
    Refuses to step if current_thunk is invalid or tampered.
    If current_thunk was signed, requires matching secret_key_hex to sign the successor,
    or produces an explicitly unsigned successor without claiming predecessor's key.
    """
    if not current_thunk.verify():
        raise ValueError("Refusing to step from invalid or tampered predecessor checkpoint")

    valid, err = verify_checkpoint_computation(current_thunk)
    if not valid:
        raise ValueError(f"Continuum step refused: input checkpoint failed computational verification ({err})")

    if current_thunk.status == "SETTLED":
        return current_thunk

    term = parse(current_thunk.current_expr)
    result = evaluate(term, max_atp=fuel, raise_on_limit=False)

    new_expr = str(result.term)
    new_status = "SETTLED" if result.is_settled() else "SUSPENDED"
    accumulated_atp = current_thunk.atp_accumulated + result.atp_spent
    peak = max(current_thunk.peak_size, result.peak_size)
    now_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # Signer continuity: if predecessor was signed, successor is signed if secret key is provided,
    # or explicitly unsigned (public_key_hex="") if no secret key is provided.
    if secret_key_hex:
        from crypto import public_key_from_secret
        next_pk = public_key_from_secret(bytes.fromhex(secret_key_hex)).hex()
        if current_thunk.public_key_hex and next_pk != current_thunk.public_key_hex:
            raise ValueError(f"Secret key mismatch: expected {current_thunk.public_key_hex}, got {next_pk}")
    else:
        next_pk = ""

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
        public_key_hex=next_pk,
    )

    if secret_key_hex:
        next_cp.sign(secret_key_hex)
    else:
        next_cp.checkpoint_hash = next_cp.compute_hash()

    ok_succ, err_succ = verify_checkpoint_computation(next_cp)
    if not ok_succ:
        raise ValueError(f"Continuum step produced computationally invalid successor: {err_succ}")

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
# Put this module's OWN directory first, so every in-process import is
# self-located and nothing on sys.path can precede and shadow it: this is what
# makes the test suite hermetic (S9). Before S9 this block inserted os.getcwd(),
# a parent, and a hard-coded checkout AT POSITION 0, any of which could shadow
# the checkout under test.
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
# The polyglot document that embeds this source still has to find the engine
# when executed from elsewhere (e.g. a temp dir). A last-resort checkout path is
# APPENDED -- never ahead of current_dir -- so it can satisfy that standalone
# self-import without ever preceding, or substituting for, the checkout under
# test. A suite run resolves everything from current_dir first; test_all's
# closure guard fails the run if any dependency is nonetheless served from here.
_LAST_RESORT_CHECKOUT = "/Users/s0fractal/Projects/black-heart"
if os.path.isdir(_LAST_RESORT_CHECKOUT) and _LAST_RESORT_CHECKOUT not in sys.path:
    sys.path.append(_LAST_RESORT_CHECKOUT)

PREFIX = "%" + "🖤" + " CONTINUUM_THUNK: "

def audit_self(filepath: str, expected_signer_pk=None):
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
        if cp.status not in ("SETTLED", "SUSPENDED"):
            print(f"[FAIL] Checkpoint #{cp.height} has invalid status: {cp.status!r}")
            sys.exit(1)
        if i == 0:
            if cp.height != 0:
                print(f"[FAIL] Genesis checkpoint must have height 0, got {cp.height}.")
                sys.exit(1)
            if cp.prev_hash != "0" * 64:
                print(f"[FAIL] Genesis checkpoint prev_hash must be 64 zeros, got {cp.prev_hash}.")
                sys.exit(1)
            if cp.atp_spent_step != cp.atp_accumulated:
                print(f"[FAIL] Genesis checkpoint step ATP ({cp.atp_spent_step}) != accumulated ATP ({cp.atp_accumulated}).")
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
            if cp.atp_accumulated != prev.atp_accumulated + cp.atp_spent_step:
                print(f"[FAIL] ATP chain delta mismatch at #{cp.height}: accumulated {cp.atp_accumulated} != prev ({prev.atp_accumulated}) + step ({cp.atp_spent_step})")
                sys.exit(1)
        parsed_cps.append(cp)

        try:
            from continuum import verify_checkpoint_computation
            valid_comp, err_comp = verify_checkpoint_computation(cp)
            if not valid_comp:
                print(f"[FAIL] Checkpoint #{cp.height} failed computational authenticity verification: {err_comp}")
                sys.exit(1)
        except Exception as e:
            print(f"[FAIL] Could not verify computational authenticity at #{cp.height}: {e}")
            sys.exit(1)

    genesis_pk = parsed_cps[0].public_key_hex
    if expected_signer_pk is not None and genesis_pk != expected_signer_pk:
        print(f"[FAIL] Genesis signer mismatch: expected {expected_signer_pk}, got {genesis_pk or 'unsigned'}!")
        sys.exit(1)
    if genesis_pk:
        for cp in parsed_cps:
            if cp.public_key_hex != genesis_pk or not cp.signature_hex:
                print(f"[FAIL] Signer continuity breach at checkpoint #{cp.height}: missing or altered signer key!")
                sys.exit(1)

    latest = parsed_cps[-1]
    print(f"[*] Checkpoint Height:  #{latest.height}")
    print(f"[*] Execution Status:   {latest.status}")
    print(f"[*] Cumulative ATP:     {latest.atp_accumulated}")
    print(f"[*] Initial Term:       {latest.initial_expr}")
    print(f"[*] Current Term:       {latest.current_expr}")
    print(f"[*] Checkpoint Hash:    ⚓ {latest.checkpoint_hash}\n")

    if latest.status == "SETTLED":
        print("\033[1;32m[✓] COMPUTATION REACHED NORMAL FORM (Q.E.D.)\033[0m\n")
    elif latest.status == "SUSPENDED":
        print("\033[1;33m[⏳] COMPUTATION SUSPENDED (Ready for resumption)\033[0m")
        print("     To resume: run with '--fuel <N>' or use Black-Heart CLI.\n")
    else:
        print(f"[FAIL] Invalid or unrecognized checkpoint status: {latest.status!r}")
        sys.exit(1)

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
    audits the entire history chain (including signer continuity), executes up to
    additional_atp steps, appends an incremental update block (with new visual
    page and manifest), and updates the PDF in-place!
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
    genesis_pk = checkpoints[0].public_key_hex

    for i, cp in enumerate(checkpoints):
        if cp.height != i:
            raise ValueError(f"Continuum chain discontinuity: checkpoint #{cp.height} at index {i}")
        if cp.status not in ("SETTLED", "SUSPENDED"):
            raise ValueError(f"Continuum chain invalid status at #{cp.height}: {cp.status!r}")
        if genesis_pk:
            if cp.public_key_hex != genesis_pk or not cp.signature_hex:
                raise ValueError(f"Continuum chain signer continuity failure: checkpoint #{cp.height} missing or altered signature under {genesis_pk}")
        if not cp.verify():
            raise ValueError(f"Continuum chain integrity failure: checkpoint #{cp.height} failed verification")
        if i == 0:
            if cp.prev_hash != "0" * 64:
                raise ValueError("Genesis checkpoint prev_hash must be 64 zeros")
            if cp.atp_spent_step != cp.atp_accumulated:
                raise ValueError(f"Genesis checkpoint step ATP ({cp.atp_spent_step}) != accumulated ATP ({cp.atp_accumulated})")
        else:
            prev = checkpoints[i - 1]
            if cp.prev_hash != prev.checkpoint_hash:
                raise ValueError(f"Continuum chain hash broken at #{cp.height}: expected {prev.checkpoint_hash}, found {cp.prev_hash}")
            if cp.initial_expr != prev.initial_expr:
                raise ValueError(f"Continuum chain altered initial_expr at #{cp.height}")
            if cp.atp_accumulated != prev.atp_accumulated + cp.atp_spent_step:
                raise ValueError(f"Continuum chain ATP delta mismatch at #{cp.height}: accumulated {cp.atp_accumulated} != prev ({prev.atp_accumulated}) + step ({cp.atp_spent_step})")

        valid_comp, err_comp = verify_checkpoint_computation(cp)
        if not valid_comp:
            raise ValueError(f"Continuum chain computational authenticity failure at #{cp.height}: {err_comp}")

    current = checkpoints[-1]

    if current.status == "SETTLED":
        print(f"[*] Computation already SETTLED at checkpoint #{current.height}. Nothing to reduce.")
        return current

    if genesis_pk and secret_key_hex is None:
        raise ValueError("Cannot resume signed continuum polyglot without secret_key_hex: chain signer continuity required.")

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
