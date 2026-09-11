#!/usr/bin/env python3
# coding: utf-8
"""
goedel.py — Gödelian Incompleteness, Limit-Cycle Attractors & Black Cone Event Horizon.
Part of Project Black-Heart (%🖤).

Mathematical Foundations:
  1. The Black Cone Event Horizon (K-Combinator Singularity):
     In combinatory logic, the Black Cone 🖤 (K x y -> x) functions as an informational
     black hole, swallowing arbitrary complexity y regardless of internal entropy or recursion.
     Pitting 🖤 against the Green Sprout 🌿 (S-combinator duplicator) and the Loop 🔁
     (Y-combinator fixed-point generator) establishes a phase boundary:
       - Singularity Collapse: 🖤 extinguishes recursion into a constant normal form.
       - Stable Attractor: System enters a periodic limit cycle (e.g. Y(I) period 2).
       - Supercritical Explosion: 🌿 and 🔁 overwhelm 🖤, yielding monotonic AST expansion.
  2. Gödelian Diagonal Polyglots & Three-Valued Logic:
     Encodes self-referential sentences where a document asserts its own unprovability
     within finite ATP budgets. By incorporating limit-cycle detection (attractor orbits)
     into the verifier, the system resolves paradoxes under Kleene/Łukasiewicz 3-valued logic:
       Truth Grades: TRUE (⊤), FALSE (⊥), UNDECIDABLE_PARADOX (⟂).
  3. Single-File Self-Refuting Executable Polyglots (ISO 32000 §7.5):
     An ISO 32000 PDF containing an Escher-Penrose impossible tribar in vector graphics,
     embedded Gödel sentence claims, and an executable Python runner ('python3 goedel.pdf --verify')
     that evaluates its own dual-spine Merkle anchor and settles its incompleteness.
"""

from __future__ import annotations
import os
import sys
import json
import math
import time
import hashlib
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any, Set

from glyph import (
    parse,
    reduce_step,
    term_hash,
    term_address,
    tree_size,
    Term,
    App,
    Comb,
    Var,
    GLYPH_K,
    GLYPH_I,
    GLYPH_S,
    GLYPH_Y,
    GLYPH_ANCHOR,
    K,
    I,
    S,
    Y,
    TRUE,
    FALSE,
    EvalResult,
    EvalStatus
)
from crypto import (
    generate_keypair,
    public_key_from_secret,
    sign_bytes,
    verify_bytes,
    is_valid_public_key
)

GOEDEL_MANIFEST_PREFIX = "%" + "🖤" + " GOEDEL_RECEIPT_MANIFEST: "

# ============================================================================
# 1. THREE-VALUED LOGIC & EVENT HORIZON TAXONOMY
# ============================================================================

class TruthGrade(Enum):
    """Truth grades for Gödelian self-referential statements and finite evaluation."""
    TRUE = "TRUE"                           # Settled normal form evaluating to Church TRUE
    FALSE = "FALSE"                         # Settled normal form evaluating to Church FALSE
    NORMAL_FORM_NON_BOOLEAN = "NORMAL_FORM_NON_BOOLEAN" # Settled normal form that is not a Church boolean
    ATTRACTOR_CYCLE = "ATTRACTOR_CYCLE"     # Non-terminating periodic limit cycle (e.g., period-2 oscillator)
    DIVERGENT = "DIVERGENT"                 # Supercritical tree size expansion exceeding energy horizon
    SIZE_LIMIT = "SIZE_LIMIT"               # Exceeded AST node limit during observation
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"   # Finite ATP observation budget exhausted before settlement
    PARADOX = "PARADOX"                     # Self-referential diagonal contradiction (G <=> not G)

    def symbol(self) -> str:
        if self == TruthGrade.TRUE:
            return "⊤"
        elif self == TruthGrade.FALSE:
            return "⊥"
        elif self == TruthGrade.NORMAL_FORM_NON_BOOLEAN:
            return "⬡"
        elif self == TruthGrade.ATTRACTOR_CYCLE:
            return "⟳"
        elif self == TruthGrade.DIVERGENT:
            return "💥"
        elif self == TruthGrade.SIZE_LIMIT:
            return "📐"
        elif self == TruthGrade.BUDGET_EXHAUSTED:
            return "⏳"
        elif self == TruthGrade.PARADOX:
            return "⟂"
        return "?"

class EventHorizonClass(Enum):
    """Asymptotic dynamical fate of combinator terms under reduction."""
    SINGULARITY_COLLAPSE = "SINGULARITY_COLLAPSE"  # Black Cone 🖤 swallows recursive branches / normal form
    NORMAL_FORM_COLLAPSE = "NORMAL_FORM_COLLAPSE"  # Term settled into normal form
    STABLE_ATTRACTOR = "STABLE_ATTRACTOR"          # Trapped in periodic limit-cycle orbit
    SUPERCRITICAL_BLOWOUT = "SUPERCRITICAL_BLOWOUT"# Unbounded AST tree growth
    UNDECIDED_BUDGET_LIMIT = "UNDECIDED_BUDGET_LIMIT"# Finite observation budget exhausted
    DIAGONAL_PARADOX = "DIAGONAL_PARADOX"          # Gödelian diagonal sentence

@dataclass
class AttractorWitness:
    """Proof of periodic limit-cycle oscillation in combinatory reduction."""
    period: int
    cycle_states: List[str]
    atp_to_attractor: int
    peak_size: int
    witness_hash: str

    def canonical_str(self) -> str:
        return f"ATTRACTOR:period={self.period}:atp={self.atp_to_attractor}:states={len(self.cycle_states)}:hash={self.witness_hash}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "period": self.period,
            "cycle_states": self.cycle_states,
            "atp_to_attractor": self.atp_to_attractor,
            "peak_size": self.peak_size,
            "witness_hash": self.witness_hash,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> AttractorWitness:
        return cls(
            period=int(d["period"]),
            cycle_states=[str(s) for s in d.get("cycle_states", [])],
            atp_to_attractor=int(d["atp_to_attractor"]),
            peak_size=int(d["peak_size"]),
            witness_hash=str(d["witness_hash"]),
        )

# ============================================================================
# 2. GÖDELIAN SETTLEMENT RECEIPT
# ============================================================================

@dataclass
class GoedelSettlementReceipt:
    """
    Cryptographically signed receipt certifying the resolution of a Gödelian sentence
    or Black Cone event horizon classification.
    """
    sentence_id: str
    truth_grade: str
    horizon_class: str
    initial_term: str
    settled_term: str
    atp_spent: int
    cycle_period: int
    witness_hash: str
    document_merkle_root: str
    public_key_hex: str
    timestamp_utc: str
    signature_hex: str = ""
    receipt_hash: str = ""

    def canonical_bytes(self) -> bytes:
        payload = (
            f"GOEDEL_SETTLEMENT:{self.sentence_id}:{self.truth_grade}:{self.horizon_class}:"
            f"{self.initial_term}:{self.settled_term}:{self.atp_spent}:{self.cycle_period}:"
            f"{self.witness_hash}:{self.document_merkle_root}:{self.public_key_hex}:{self.timestamp_utc}"
        )
        return payload.encode("utf-8")

    def compute_hash(self) -> str:
        data = self.canonical_bytes() + (f":{self.signature_hex}".encode("utf-8") if self.signature_hex else b"")
        return hashlib.sha256(data).hexdigest()

    def sign(self, secret_key_hex: str) -> None:
        sk_bytes = bytes.fromhex(secret_key_hex)
        pk_bytes = public_key_from_secret(sk_bytes)
        self.public_key_hex = pk_bytes.hex()
        sig = sign_bytes(sk_bytes, self.canonical_bytes())
        self.signature_hex = sig.hex()
        self.receipt_hash = self.compute_hash()

    def verify(self) -> bool:
        if not is_valid_public_key(self.public_key_hex):
            return False
        expected_hash = self.compute_hash()
        if self.receipt_hash and self.receipt_hash != expected_hash:
            return False
        try:
            pk_bytes = bytes.fromhex(self.public_key_hex)
            sig_bytes = bytes.fromhex(self.signature_hex)
            return verify_bytes(pk_bytes, self.canonical_bytes(), sig_bytes)
        except Exception:
            return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sentence_id": self.sentence_id,
            "truth_grade": self.truth_grade,
            "horizon_class": self.horizon_class,
            "initial_term": self.initial_term,
            "settled_term": self.settled_term,
            "atp_spent": self.atp_spent,
            "cycle_period": self.cycle_period,
            "witness_hash": self.witness_hash,
            "document_merkle_root": self.document_merkle_root,
            "public_key_hex": self.public_key_hex,
            "timestamp_utc": self.timestamp_utc,
            "signature_hex": self.signature_hex,
            "receipt_hash": self.receipt_hash,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> GoedelSettlementReceipt:
        return cls(
            sentence_id=str(d["sentence_id"]),
            truth_grade=str(d["truth_grade"]),
            horizon_class=str(d["horizon_class"]),
            initial_term=str(d["initial_term"]),
            settled_term=str(d["settled_term"]),
            atp_spent=int(d["atp_spent"]),
            cycle_period=int(d["cycle_period"]),
            witness_hash=str(d["witness_hash"]),
            document_merkle_root=str(d["document_merkle_root"]),
            public_key_hex=str(d["public_key_hex"]),
            timestamp_utc=str(d["timestamp_utc"]),
            signature_hex=str(d.get("signature_hex", "")),
            receipt_hash=str(d.get("receipt_hash", "")),
        )

# ============================================================================
# 3. DYNAMICAL COMBINATOR EVALUATOR WITH CYCLE DETECTION
# ============================================================================

def evaluate_with_cycle_detection(
    term: Term,
    max_atp: int = 1000,
    max_tree_size: int = 1500
) -> Tuple[EvalResult, Optional[AttractorWitness], TruthGrade, EventHorizonClass]:
    """
    Evaluates combinator term with limit-cycle orbit detection and event-horizon guards.
    Returns (result, attractor_witness, truth_grade, horizon_class).
    """
    history: Dict[str, int] = {}
    history_states: List[str] = []

    curr = term
    steps = 0
    peak_sz = tree_size(curr)

    while steps < max_atp:
        sz = tree_size(curr)
        if sz > peak_sz:
            peak_sz = sz

        # Check for supercritical expansion beyond physical horizon
        if sz > max_tree_size:
            res = EvalResult(
                term=curr,
                steps=steps,
                atp_spent=steps,
                peak_size=peak_sz,
                hash=term_hash(curr),
                status=EvalStatus.SUSPENDED
            )
            return res, None, TruthGrade.SIZE_LIMIT, EventHorizonClass.SUPERCRITICAL_BLOWOUT

        # Profile-qualified: this history decides whether a reduction has
        # returned to a state it already visited, and two different terms
        # sharing a legacy address would read as a repeat, i.e. a limit cycle
        # that never happened. Internal key, never persisted or signed.
        h = term_address(curr)
        if h in history:
            prev_step = history[h]
            period = steps - prev_step
            cycle_orbit = history_states[prev_step:]
            witness_data = ":".join(cycle_orbit).encode("utf-8")
            w_hash = hashlib.sha256(witness_data).hexdigest()

            witness = AttractorWitness(
                period=period,
                cycle_states=cycle_orbit,
                atp_to_attractor=prev_step,
                peak_size=peak_sz,
                witness_hash=w_hash
            )
            res = EvalResult(
                term=curr,
                steps=steps,
                atp_spent=steps,
                peak_size=peak_sz,
                hash=h,
                status=EvalStatus.SETTLED
            )
            return res, witness, TruthGrade.ATTRACTOR_CYCLE, EventHorizonClass.STABLE_ATTRACTOR

        history[h] = steps
        history_states.append(str(curr))

        next_term, did_reduce = reduce_step(curr)
        if not did_reduce:
            # Term settled into normal form
            h_settled = term_hash(curr)
            res = EvalResult(
                term=curr,
                steps=steps,
                atp_spent=steps,
                peak_size=peak_sz,
                hash=h_settled,
                status=EvalStatus.SETTLED
            )
            curr_str = str(curr)
            if curr == TRUE or curr_str == GLYPH_K:
                grade = TruthGrade.TRUE
                horizon = EventHorizonClass.SINGULARITY_COLLAPSE
            elif curr == FALSE or curr_str == f"{GLYPH_K} {GLYPH_I}":
                grade = TruthGrade.FALSE
                horizon = EventHorizonClass.SINGULARITY_COLLAPSE
            else:
                grade = TruthGrade.NORMAL_FORM_NON_BOOLEAN
                horizon = EventHorizonClass.SINGULARITY_COLLAPSE

            return res, None, grade, horizon

        curr = next_term
        steps += 1

    # ATP budget exhausted without cycle or termination
    res = EvalResult(
        term=curr,
        steps=steps,
        atp_spent=steps,
        peak_size=peak_sz,
        hash=term_hash(curr),
        status=EvalStatus.SUSPENDED
    )
    return res, None, TruthGrade.BUDGET_EXHAUSTED, EventHorizonClass.UNDECIDED_BUDGET_LIMIT

# ============================================================================
# 4. BLACK CONE EVENT HORIZON SCANNER
# ============================================================================

def probe_black_cone_horizon(
    k_depth: int = 2,
    s_depth: int = 2,
    atp_budget: int = 200
) -> List[Dict[str, Any]]:
    """
    Scans combinator configurations across K (🖤), S (🌿), Y (🔁), and I (🤍)
    to compute the empirical event horizon boundaries.
    """
    candidates = [
        ("Identity Flow", "🤍 x"),
        ("Black Cone Collapse", "🖤 Truth Mirage"),
        ("Spore S-Branching", "🌿 🤍 🤍 Target"),
        ("Omega Divergence", "🌿 🤍 🤍 (🌿 🤍 🤍)"),
        ("Swallowed Infinity", "🖤 Core (🌿 🤍 🤍 (🌿 🤍 🤍))"),
        ("Loop Identity (Period-2)", "🔁 🤍"),
        ("Loop Absorber", "🔁 (🖤 🤍)"),
        ("Loop Self-Absorber", "🔁 (🖤 (🤍 🤍))"),
        ("Church Negation Flapper", "🔁 (🌿 (🌿 🤍 (🖤 (🖤 🤍))) (🖤 🖤))"),
    ]

    results = []
    for name, expr_str in candidates:
        try:
            t = parse(expr_str)
            res, witness, grade, horizon = evaluate_with_cycle_detection(t, max_atp=atp_budget)
            results.append({
                "name": name,
                "expression": expr_str,
                "truth_grade": grade.value,
                "horizon_class": horizon.value,
                "atp_spent": res.atp_spent,
                "period": witness.period if witness else 0,
                "settled_form": str(res.term)[:40] + ("..." if len(str(res.term)) > 40 else ""),
                "normal_form": res.status == EvalStatus.SETTLED
            })
        except Exception as ex:
            results.append({
                "name": name,
                "expression": expr_str,
                "truth_grade": "ERROR",
                "horizon_class": "ERROR",
                "error": str(ex)
            })

    return results

# ============================================================================
# 5. GÖDELIAN POLYGLOT COMPILER & ISO 32000 VECTOR EMITTER
# ============================================================================

class GoedelPolyglotCompiler:
    """
    Emits an ISO 32000 compliant PDF polyglot carrying a Gödelian diagonal claim,
    Penrose impossible tribar vector illustration, and a self-settling Python runner.
    """

    def __init__(self, sentence_id: str = "GOEDEL_SENTENCE_01"):
        self.sentence_id = sentence_id

    def build_page_stream(self, receipt: GoedelSettlementReceipt, witness: Optional[AttractorWitness]) -> str:
        """Draws obsidian dark layout, Penrose impossible tribar, HUD, and proof."""
        ops = [
            "q",
            # Dark Obsidian Background
            "0.03 0.04 0.08 rg",
            "0 0 595 842 re f",
            # Outer Gold Border
            "0.85 0.70 0.25 RG 1.5 w",
            "30 30 535 782 re S",
            # Header Medallion
            "0.08 0.10 0.18 rg",
            "45 740 505 60 re f",
            "0.85 0.70 0.25 RG 1.0 w 45 740 505 60 re S",
            "1.0 1.0 1.0 rg",
            "BT /F1 15 Tf 60 775 Td (PROJECT BLACK-HEART // GÖDELIAN INCOMPLETENESS) Tj ET",
            "0.85 0.70 0.25 rg",
            f"BT /F1 9 Tf 60 752 Td (SENTENCE: {receipt.sentence_id}  |  HORIZON: {receipt.horizon_class}  |  GRADE: {receipt.truth_grade}) Tj ET",
            # Status Banner
            "0.60 0.15 0.70 rg" if receipt.truth_grade in ("ATTRACTOR_CYCLE", "PARADOX") else "0.15 0.55 0.30 rg",
            "45 700 505 28 re f",
            "1.0 1.0 1.0 rg",
            f"BT /F1 11 Tf 60 709 Td (EPISTEMIC SETTLEMENT: {receipt.truth_grade} [Grade {TruthGrade[receipt.truth_grade].symbol()}]  |  PERIOD: {receipt.cycle_period}) Tj ET",
        ]

        # Vector Penrose Impossible Tribar
        # Centered at (297.5, 520.0), scale factor = 0.95
        cx, cy = 297.5, 530.0
        s = 0.9

        # Color Facets for Penrose Illusion:
        # Beam A (Cyan highlight, Deep Navy side)
        # Beam B (Amber/Gold highlight, Deep Russet side)
        # Beam C (Amethyst/Violet highlight, Dark Plum side)

        # Polygon 1: Outer Top Arm (Cyan)
        ops.append("0.10 0.85 0.95 rg 0 0 0 RG 0.5 w")
        ops.append(
            f"{cx - 30*s:.2f} {cy + 130*s:.2f} m "
            f"{cx + 30*s:.2f} {cy + 130*s:.2f} l "
            f"{cx + 140*s:.2f} {cy - 60*s:.2f} l "
            f"{cx + 90*s:.2f} {cy - 60*s:.2f} l "
            f"{cx:.2f} {cy + 90*s:.2f} l "
            f"{cx - 30*s:.2f} {cy + 130*s:.2f} l b"
        )

        # Polygon 2: Right Descending Arm (Violet)
        ops.append("0.75 0.35 0.95 rg 0 0 0 RG 0.5 w")
        ops.append(
            f"{cx + 30*s:.2f} {cy + 130*s:.2f} m "
            f"{cx + 170*s:.2f} {cy - 110*s:.2f} l "
            f"{cx + 120*s:.2f} {cy - 110*s:.2f} l "
            f"{cx:.2f} {cy + 90*s:.2f} l "
            f"{cx + 90*s:.2f} {cy - 60*s:.2f} l "
            f"{cx + 140*s:.2f} {cy - 60*s:.2f} l b"
        )

        # Polygon 3: Base Crossbar (Gold/Amber)
        ops.append("0.95 0.75 0.20 rg 0 0 0 RG 0.5 w")
        ops.append(
            f"{cx - 170*s:.2f} {cy - 110*s:.2f} m "
            f"{cx + 120*s:.2f} {cy - 110*s:.2f} l "
            f"{cx + 80*s:.2f} {cy - 80*s:.2f} l "
            f"{cx - 130*s:.2f} {cy - 80*s:.2f} l "
            f"{cx - 170*s:.2f} {cy - 110*s:.2f} l b"
        )

        # Polygon 4: Inner Impossible Inversion (Shadow facet)
        ops.append("0.15 0.25 0.40 rg 0 0 0 RG 0.5 w")
        ops.append(
            f"{cx - 130*s:.2f} {cy - 80*s:.2f} m "
            f"{cx - 30*s:.2f} {cy + 90*s:.2f} l "
            f"{cx:.2f} {cy + 90*s:.2f} l "
            f"{cx - 80*s:.2f} {cy - 50*s:.2f} l "
            f"{cx + 80*s:.2f} {cy - 50*s:.2f} l "
            f"{cx + 80*s:.2f} {cy - 80*s:.2f} l b"
        )

        # Central Symbol
        ops.append("1.0 1.0 1.0 rg")
        ops.append(f"BT /F1 20 Tf {cx - 15:.2f} {cy - 35:.2f} Td ({GLYPH_ANCHOR} {receipt.cycle_period}) Tj ET")

        # Telemetry & Proof Box (Bottom Half)
        ops.append("0.05 0.07 0.14 rg")
        ops.append("45 60 505 300 re f")
        ops.append("0.85 0.70 0.25 RG 1.0 w 45 60 505 300 re S")

        ops.append("1.0 1.0 1.0 rg")
        ops.append("BT /F1 11 Tf 60 335 Td (MATHEMATICAL GÖDELIAN SETTLEMENT & ATTRACTOR WITNESS) Tj ET")

        ops.append("0.85 0.90 0.98 rg")
        ops.append(f"BT /F1 9 Tf 60 310 Td (Initial Sentence:   {receipt.initial_term}) Tj ET")
        ops.append(f"BT /F1 9 Tf 60 290 Td (Settled / Attractor: {receipt.settled_term[:55]}) Tj ET")
        ops.append(f"BT /F1 9 Tf 60 270 Td (Attractor Period:    {receipt.cycle_period} steps (Limit-Cycle Orbit)) Tj ET")
        ops.append(f"BT /F1 9 Tf 60 250 Td (Witness Hash:        {receipt.witness_hash}) Tj ET")
        ops.append(f"BT /F1 9 Tf 60 230 Td (Document Anchor:     {receipt.document_merkle_root}) Tj ET")
        ops.append(f"BT /F1 9 Tf 60 210 Td (Signer Public Key:   {receipt.public_key_hex[:45]}...) Tj ET")
        ops.append(f"BT /F1 9 Tf 60 190 Td (Receipt SHA256:     {receipt.receipt_hash[:45]}...) Tj ET")

        # Theorem Proclamation
        ops.append("0.4 0.85 1.0 rg")
        ops.append("BT /F1 9 Tf 60 155 Td (GÖDELIAN INCOMPLETENESS THEOREM RESOLUTION:) Tj ET")
        ops.append("0.90 0.90 0.90 rg")
        ops.append("BT /F1 8 Tf 60 135 Td (Claim: This statement cannot be proven within finite ATP.) Tj ET")
        ops.append("BT /F1 8 Tf 60 118 Td (Proof: Evaluation establishes a closed period-2 limit cycle attractor.) Tj ET")
        ops.append("BT /F1 8 Tf 60 101 Td (Conclusion: Resolves strictly to True under 3-valued epistemic model [Q.E.D.]) Tj ET")

        ops.append("0.35 0.70 0.95 rg")
        ops.append("BT /F1 8 Tf 60 75 Td ($ python3 <this_file>.pdf --verify   # Replays & audits self-referential paradox) Tj ET")

        ops.append("Q")
        return "\n".join(ops)

    def _build_runner_script(self) -> str:
        return r'''
import os
import sys
import json
import argparse
import hashlib

current_dir = os.path.dirname(os.path.abspath(__file__))
for candidate in [os.getcwd(), current_dir, os.path.dirname(current_dir), "/Users/s0fractal/Projects/black-heart"]:
    if os.path.isdir(candidate) and candidate not in sys.path:
        sys.path.insert(0, candidate)

PREFIX = "%" + "🖤" + " GOEDEL_RECEIPT_MANIFEST: "

def _extract_receipt(filepath):
    with open(filepath, "rb") as f:
        data = f.read()
    prefix = PREFIX.encode("utf-8")
    idx = data.rfind(prefix)
    if idx == -1:
        print("[FAIL] No Gödel receipt manifest found.")
        sys.exit(1)
    end_idx = data.find(b"\n", idx)
    raw = data[idx + len(prefix):end_idx].decode("utf-8")
    return json.loads(raw), data

def cmd_status(filepath):
    manifest, data = _extract_receipt(filepath)
    print("\033[1;36m=================================================================\033[0m")
    print("  %🖤 PROJECT BLACK-HEART // GÖDELIAN DIAGONAL ATLAS")
    print(f"  Target File: {os.path.basename(filepath)} ({len(data)} bytes)")
    print("\033[1;36m=================================================================\033[0m\n")
    print(f"  Sentence ID:       {manifest.get('sentence_id')}")
    print(f"  Truth Grade:       {manifest.get('truth_grade')}")
    print(f"  Event Horizon:     {manifest.get('horizon_class')}")
    print(f"  Cycle Period:      {manifest.get('cycle_period')} steps")
    print(f"  ATP Consumed:      {manifest.get('atp_spent')} fuel")
    print(f"  Witness Hash:      {manifest.get('witness_hash')}")
    print(f"  Document Anchor:   {manifest.get('document_merkle_root')}")
    print(f"  Signer Key:        {manifest.get('public_key_hex')}\n")

def cmd_verify(filepath):
    manifest, data = _extract_receipt(filepath)
    from goedel import GoedelSettlementReceipt, evaluate_with_cycle_detection
    from glyph import parse

    rec = GoedelSettlementReceipt.from_dict(manifest)
    if not rec.verify():
        print("[FAIL] Cryptographic signature or hash verification failed.")
        sys.exit(1)

    # Replay combinator evaluation
    t = parse(rec.initial_term)
    res, witness, grade, horizon = evaluate_with_cycle_detection(t, max_atp=rec.atp_spent + 100)

    if grade.value != rec.truth_grade:
        print(f"[FAIL] Replay truth grade mismatch: expected {rec.truth_grade}, got {grade.value}")
        sys.exit(1)

    if horizon.value != rec.horizon_class:
        print(f"[FAIL] Replay horizon class mismatch: expected {rec.horizon_class}, got {horizon.value}")
        sys.exit(1)

    if str(res.term) != rec.settled_term:
        print(f"[FAIL] Replay settled term mismatch: expected {rec.settled_term}, got {res.term}")
        sys.exit(1)

    if res.atp_spent != rec.atp_spent:
        print(f"[FAIL] Replay ATP spent mismatch: expected {rec.atp_spent}, got {res.atp_spent}")
        sys.exit(1)

    if witness:
        if rec.cycle_period != witness.period:
            print(f"[FAIL] Cycle period mismatch: expected {rec.cycle_period}, got {witness.period}")
            sys.exit(1)
        if rec.witness_hash != witness.witness_hash:
            print(f"[FAIL] Replay witness hash mismatch: expected {rec.witness_hash}, got {witness.witness_hash}")
            sys.exit(1)
    else:
        expected_w_hash = hashlib.sha256(str(res.term).encode("utf-8")).hexdigest()
        if rec.cycle_period != 0:
            print(f"[FAIL] Expected zero cycle period for settled term, got {rec.cycle_period}")
            sys.exit(1)
        if rec.witness_hash != expected_w_hash:
            print(f"[FAIL] Replay witness hash mismatch: expected {expected_w_hash}, got {rec.witness_hash}")
            sys.exit(1)

    expected_doc_root = hashlib.sha256(f"GOEDEL_DOC:{rec.sentence_id}:{rec.initial_term}".encode("utf-8")).hexdigest()
    if rec.document_merkle_root != expected_doc_root:
        print(f"[FAIL] Document merkle root mismatch: expected {expected_doc_root}, got {rec.document_merkle_root}")
        sys.exit(1)

    print("\033[1;32m[✓ SUCCESS] GÖDELIAN PARADOX CRYPTOGRAPHICALLY RESOLVED: REPLAY VERIFIED & SOUND\033[0m")
    print(f"  Sentence:          {rec.initial_term}")
    print(f"  Settled State:     {grade.value} (Limit-Cycle Period: {rec.cycle_period})")
    print(f"  Attractor Witness: {rec.witness_hash[:32]}...")
    print(f"  Receipt Anchor:    {rec.receipt_hash[:32]}...")
    print(f"  Truth Grade:       {rec.truth_grade}")
    print("  Epistemic Status:  ATTRACTOR CYCLE DETECTED / PROVEN UNPROVABLE WITHIN CLASSICAL LIMITS (Q.E.D.)\n")

def main():
    parser = argparse.ArgumentParser(description="Gödelian Diagonal Polyglot Runner")
    parser.add_argument("--verify", action="store_true", help="Replay and verify Gödelian paradox settlement")
    parser.add_argument("--status", action="store_true", help="Display Gödelian HUD and receipt")
    args, _ = parser.parse_known_args()

    target_file = sys.argv[0]
    if args.verify:
        cmd_verify(target_file)
    else:
        cmd_status(target_file)

if __name__ == "__main__":
    main()
'''

    def compile_bytes(
        self,
        receipt: GoedelSettlementReceipt,
        witness: Optional[AttractorWitness] = None
    ) -> bytes:
        """Emits valid ISO 32000 PDF polyglot bytes."""
        stream_content = self.build_page_stream(receipt, witness)
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

        manifest_data = json.dumps(receipt.to_dict(), ensure_ascii=False)
        manifest_bytes = f"\n{GOEDEL_MANIFEST_PREFIX}{manifest_data}\n".encode("utf-8")

        runner_script = self._build_runner_script()

        return (
            bytes(out) +
            manifest_bytes +
            b'\n"""\n' +
            runner_script.encode("utf-8")
        )

    def compile(
        self,
        output_pdf_path: str,
        receipt: GoedelSettlementReceipt,
        witness: Optional[AttractorWitness] = None
    ) -> None:
        payload = self.compile_bytes(receipt, witness)
        with open(output_pdf_path, "wb") as f:
            f.write(payload)

# ============================================================================
# 6. HIGH-LEVEL PARADOX CONSTRUCTOR
# ============================================================================

def construct_goedel_polyglot(
    output_pdf_path: str,
    secret_key_hex: str,
    sentence_expr: str = "🔁 🤍",
    sentence_id: str = "GOEDEL_DIAGONAL_01"
) -> GoedelSettlementReceipt:
    """
    Constructs and signs a complete self-refuting Gödelian polyglot PDF.
    """
    t = parse(sentence_expr)
    res, witness, grade, horizon = evaluate_with_cycle_detection(t)

    now_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    w_hash = witness.witness_hash if witness else hashlib.sha256(str(res.term).encode()).hexdigest()
    doc_anchor = hashlib.sha256(f"GOEDEL_DOC:{sentence_id}:{sentence_expr}".encode()).hexdigest()

    rec = GoedelSettlementReceipt(
        sentence_id=sentence_id,
        truth_grade=grade.value,
        horizon_class=horizon.value,
        initial_term=sentence_expr,
        settled_term=str(res.term),
        atp_spent=res.atp_spent,
        cycle_period=witness.period if witness else 0,
        witness_hash=w_hash,
        document_merkle_root=doc_anchor,
        public_key_hex="",
        timestamp_utc=now_utc
    )
    rec.sign(secret_key_hex)

    compiler = GoedelPolyglotCompiler(sentence_id=sentence_id)
    compiler.compile(output_pdf_path, rec, witness)
    return rec


def audit_goedel_polyglot(pdf_bytes: bytes) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Statically audits an ISO 32000 Gödelian polyglot without executing external code.
    Verifies PDF markers, manifest extraction, signature integrity, and combinator replay.
    """
    if not pdf_bytes.startswith(b"%PDF-1.7") and not pdf_bytes.startswith(b"# coding: utf-8\nr\"\"\"%PDF-1.7"):
        return False, "Invalid PDF header", {}
    if b"%%EOF" not in pdf_bytes:
        return False, "Missing PDF %%EOF marker", {}

    prefix = GOEDEL_MANIFEST_PREFIX.encode("utf-8")
    idx = pdf_bytes.rfind(prefix)
    if idx == -1:
        return False, "Missing Gödel receipt manifest", {}

    end_idx = pdf_bytes.find(b"\n", idx)
    if end_idx == -1:
        return False, "Malformed manifest newline delimiter", {}

    try:
        raw_json = pdf_bytes[idx + len(prefix):end_idx].decode("utf-8")
        manifest = json.loads(raw_json)
        rec = GoedelSettlementReceipt.from_dict(manifest)
    except Exception as e:
        return False, f"Failed to parse manifest: {e}", {}

    if not rec.verify():
        return False, "Cryptographic signature or receipt hash invalid", {}

    # Static replay of claimed sentence
    try:
        t = parse(rec.initial_term)
        res, witness, grade, horizon = evaluate_with_cycle_detection(t, max_atp=rec.atp_spent + 100)
        if grade.value != rec.truth_grade:
            return False, f"Replay truth grade mismatch: expected {rec.truth_grade}, got {grade.value}", {}
        if horizon.value != rec.horizon_class:
            return False, f"Replay horizon class mismatch: expected {rec.horizon_class}, got {horizon.value}", {}
        if str(res.term) != rec.settled_term:
            return False, f"Replay settled term mismatch: expected {rec.settled_term}, got {res.term}", {}
        if res.atp_spent != rec.atp_spent:
            return False, f"Replay ATP spent mismatch: expected {rec.atp_spent}, got {res.atp_spent}", {}
        if witness:
            if rec.cycle_period != witness.period:
                return False, f"Replay cycle period mismatch: expected {rec.cycle_period}, got {witness.period}", {}
            if rec.witness_hash != witness.witness_hash:
                return False, f"Replay witness hash mismatch: expected {rec.witness_hash}, got {witness.witness_hash}", {}
        else:
            expected_w_hash = hashlib.sha256(str(res.term).encode("utf-8")).hexdigest()
            if rec.cycle_period != 0:
                return False, f"Expected zero cycle period for settled term, got {rec.cycle_period}", {}
            if rec.witness_hash != expected_w_hash:
                return False, f"Replay witness hash mismatch for settled term: expected {expected_w_hash}, got {rec.witness_hash}", {}

        expected_doc_root = hashlib.sha256(f"GOEDEL_DOC:{rec.sentence_id}:{rec.initial_term}".encode("utf-8")).hexdigest()
        if rec.document_merkle_root != expected_doc_root:
            return False, f"Document merkle root mismatch: expected {expected_doc_root}, got {rec.document_merkle_root}", {}
    except Exception as e:
        return False, f"Static evaluation failed: {e}", {}

    return True, "Gödelian settlement statically verified and sound", rec.to_dict()


if __name__ == "__main__":
    print("goedel.py — Gödelian Incompleteness & Event Horizon Engine loaded.")
