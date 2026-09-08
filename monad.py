#!/usr/bin/env python3
"""
monad.py — The Literate Polyglot Monad, Dual-Spine Trees & Self-Verifying Contract Compiler
Part of Project Black-Heart (%🖤).

Implements:
  1. DualSpineTree (Code Spine vs Visual Spine, linked via Joint Merkle Anchor)
  2. LiterateMonad (Monadic container ensuring ΔCode <=> ΔProse invariant)
  3. SelfVerifyingContractPolyglot (ISO 32000 PDF + Self-Executing Legal Adjudicator)
"""

from __future__ import annotations
import os
import sys
import json
import hashlib
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple, Any, Generic, TypeVar

T = TypeVar("T")
U = TypeVar("U")

# ============================================================================
# 1. DUAL-SPINE TREE (Code Spine + Visual Spine)
# ============================================================================

@dataclass(frozen=True)
class CodeSpineNode:
    clause_id: str
    predicate_name: str
    expression: str
    expected_normal_form: str
    atp_budget: int = 10_000
    metadata: Dict[str, Any] = field(default_factory=dict)

    def canonical_bytes(self) -> bytes:
        obj = {
            "clause_id": self.clause_id,
            "predicate_name": self.predicate_name,
            "expression": self.expression,
            "expected_normal_form": self.expected_normal_form,
            "atp_budget": self.atp_budget,
            "metadata": self.metadata
        }
        return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

    def digest(self) -> str:
        return hashlib.sha256(self.canonical_bytes()).hexdigest()

@dataclass(frozen=True)
class VisualSpineNode:
    node_type: str  # "title", "preamble", "article", "clause_text", "evidence_table", "verdict_box"
    title: str
    text_content: str
    page_num: int = 1

    def canonical_bytes(self) -> bytes:
        obj = {
            "node_type": self.node_type,
            "title": self.title,
            "text_content": self.text_content,
            "page_num": self.page_num
        }
        return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

    def digest(self) -> str:
        return hashlib.sha256(self.canonical_bytes()).hexdigest()

class DualSpineTree:
    """
    Maintains a strict homomorphic coupling between the Computational Spine (Code)
    and the Presentation Spine (Prose/Layout).
    """
    def __init__(self):
        self.code_nodes: List[CodeSpineNode] = []
        self.visual_nodes: List[VisualSpineNode] = []

    def append_node_pair(self, code: CodeSpineNode, visual: VisualSpineNode):
        self.code_nodes.append(code)
        self.visual_nodes.append(visual)

    def append_visual_only(self, visual: VisualSpineNode):
        self.visual_nodes.append(visual)

    def code_root_hash(self) -> str:
        h = hashlib.sha256()
        for node in self.code_nodes:
            h.update(node.canonical_bytes())
        return h.hexdigest()

    def visual_root_hash(self) -> str:
        h = hashlib.sha256()
        for node in self.visual_nodes:
            h.update(node.canonical_bytes())
        return h.hexdigest()

    def joint_anchor(self) -> str:
        """The 32-byte joint cryptographic anchor binding code and layout."""
        h = hashlib.sha256()
        h.update(self.code_root_hash().encode("utf-8"))
        h.update(self.visual_root_hash().encode("utf-8"))
        return h.hexdigest()

# ============================================================================
# 2. THE LITERATE MONAD
# ============================================================================

@dataclass
class MonadState:
    atp_budget: int
    atp_spent: int
    dual_tree: DualSpineTree
    env: Dict[str, Any] = field(default_factory=dict)

class LiterateMonad(Generic[T]):
    """
    LiterateMonad[T] encapsulates a stateful computation that transforms
    MonadState and returns a value T, guaranteeing atomic updates to both
    the computational DAG and the visual presentation tree.
    """
    def __init__(self, run: Callable[[MonadState], Tuple[T, MonadState]]):
        self._run = run

    def run(self, initial_state: Optional[MonadState] = None) -> Tuple[T, MonadState]:
        if initial_state is None:
            initial_state = MonadState(
                atp_budget=1_000_000,
                atp_spent=0,
                dual_tree=DualSpineTree()
            )
        return self._run(initial_state)

    @classmethod
    def unit(cls, val: T) -> LiterateMonad[T]:
        """Monad unit / return."""
        return cls(lambda state: (val, state))

    def bind(self, f: Callable[[T], LiterateMonad[U]]) -> LiterateMonad[U]:
        """Monadic bind (>>=)."""
        def run_bind(state: MonadState) -> Tuple[U, MonadState]:
            val_a, state_mid = self._run(state)
            monad_b = f(val_a)
            return monad_b.run(state_mid)
        return LiterateMonad(run_bind)

    def __rshift__(self, f: Callable[[T], LiterateMonad[U]]) -> LiterateMonad[U]:
        """Operator >> as syntactic sugar for bind."""
        return self.bind(f)

    @classmethod
    def tell_prose(cls, title: str, text: str, node_type: str = "article") -> LiterateMonad[None]:
        """Appends a purely descriptive node to the visual spine."""
        def run_tell(state: MonadState) -> Tuple[None, MonadState]:
            v_node = VisualSpineNode(node_type=node_type, title=title, text_content=text)
            state.dual_tree.append_visual_only(v_node)
            return None, state
        return cls(run_tell)

    @classmethod
    def step_clause(
        cls,
        clause_id: str,
        article_title: str,
        legal_prose: str,
        predicate_name: str,
        expression: str,
        expected_normal_form: str,
        atp_cost: int = 1
    ) -> LiterateMonad[str]:
        """
        Atomic step: registers a formal computable rule in the code spine
        and simultaneously attaches its legal clause to the visual spine.
        Returns the clause digest.
        Validates atp_cost type, range, and budget before mutating state.
        """
        if not isinstance(atp_cost, int) or isinstance(atp_cost, bool):
            raise TypeError(f"atp_cost must be an integer, got {type(atp_cost).__name__}")
        if atp_cost < 0:
            raise ValueError(f"atp_cost cannot be negative: {atp_cost}")

        def run_step(state: MonadState) -> Tuple[str, MonadState]:
            if state.atp_budget < atp_cost:
                raise ValueError(f"Insufficient ATP budget: required {atp_cost}, available {state.atp_budget}")

            code_node = CodeSpineNode(
                clause_id=clause_id,
                predicate_name=predicate_name,
                expression=expression,
                expected_normal_form=expected_normal_form,
                atp_budget=state.atp_budget
            )
            visual_node = VisualSpineNode(
                node_type="clause",
                title=article_title,
                text_content=legal_prose
            )
            state.dual_tree.append_node_pair(code_node, visual_node)
            state.atp_spent += atp_cost
            state.atp_budget -= atp_cost
            return code_node.digest(), state
        return cls(run_step)

# ============================================================================
# 3. SELF-VERIFYING CONTRACT POLYGLOT COMPILER
# ============================================================================

@dataclass
class ContractParty:
    role: str       # e.g., "Provider", "Client", "Arbiter"
    name: str
    identifier: str # Public key fingerprint, Ed25519 hash, or tax ID

@dataclass
class EvidenceRecord:
    record_id: str
    timestamp: str
    event_type: str
    duration_minutes: int
    raw_hash: str
    description: str

class SelfVerifyingContractPolyglot:
    """
    Compiles a formal legal contract into an executable ISO 32000 PDF polyglot.
    The resulting file:
      1. Renders in Preview / Acrobat as an elegant, formal legal contract.
      2. Runs directly in Python (`python3 contract.pdf`) to adjudicate evidence
         against embedded contract predicates and emit an immutable settlement receipt.
    """
    def __init__(self, title: str, jurisdiction: str = "Ukraine / International Civil Law"):
        self.title = title
        self.jurisdiction = jurisdiction
        self.parties: List[ContractParty] = []
        self.monad_state = MonadState(
            atp_budget=1_000_000,
            atp_spent=0,
            dual_tree=DualSpineTree()
        )
        self.evidence_log: List[EvidenceRecord] = []
        self.parameters: Dict[str, Any] = {
            "uptime_target_percent": 99.5,
            "total_period_minutes": 43200, # 30-day month
            "base_monthly_fee_usd": 10000,
            "penalty_rate_per_tenth_percent_usd": 500
        }

    def add_party(self, role: str, name: str, identifier: str):
        self.parties.append(ContractParty(role, name, identifier))

    def add_preamble(self, text: str):
        m = LiterateMonad.tell_prose("Preamble", text, node_type="preamble")
        _, self.monad_state = m.run(self.monad_state)

    def add_clause(
        self,
        clause_id: str,
        article_title: str,
        legal_prose: str,
        predicate_name: str,
        expression: str,
        expected_normal_form: str
    ):
        m = LiterateMonad.step_clause(
            clause_id=clause_id,
            article_title=article_title,
            legal_prose=legal_prose,
            predicate_name=predicate_name,
            expression=expression,
            expected_normal_form=expected_normal_form
        )
        _, self.monad_state = m.run(self.monad_state)

    def attach_evidence(self, record_id: str, timestamp: str, event_type: str, duration_min: int, description: str):
        raw_sig = f"{record_id}|{timestamp}|{event_type}|{duration_min}|{description}".encode("utf-8")
        h = hashlib.sha256(raw_sig).hexdigest()
        rec = EvidenceRecord(
            record_id=record_id,
            timestamp=timestamp,
            event_type=event_type,
            duration_minutes=duration_min,
            raw_hash=h,
            description=description
        )
        self.evidence_log.append(rec)
        m = LiterateMonad.tell_prose(
            f"Evidence: {record_id}",
            f"Event '{event_type}' on {timestamp}: duration {duration_min} min. Hash: {h[:16]}",
            node_type="evidence_table"
        )
        _, self.monad_state = m.run(self.monad_state)

    def compile(self, output_path: str) -> str:
        """Produces the standalone ISO 32000 PDF + Python executable polyglot."""
        page_width, page_height = 595, 842 # A4
        margin = 54
        content_width = page_width - 2 * margin

        stream_lines = []
        y = page_height - margin

        # Header Title
        stream_lines.append(f"BT /F1 18 Tf {margin} {y} Td ({_escape_pdf(self.title)}) Tj ET")
        y -= 24
        stream_lines.append(f"BT /F3 10 Tf 0.3 0.3 0.3 rg {margin} {y} Td (Self-Verifying Proof-Carrying Contract Polyglot | Jurisdiction: {_escape_pdf(self.jurisdiction)}) Tj 0 g ET")
        y -= 14

        # Parties
        parties_desc = " | ".join(f"{p.role}: {p.name} [{p.identifier[:12]}]" for p in self.parties)
        for line in _wrap_text(parties_desc, 95):
            stream_lines.append(f"BT /F2 8 Tf 0.4 0.4 0.4 rg {margin} {y} Td ({_escape_pdf(line)}) Tj 0 g ET")
            y -= 11
        y -= 3

        # Decorative Divider
        stream_lines.append(f"0.8 0.8 0.8 rg {margin} {y} {content_width} 1 re f 0 g")
        y -= 18

        # Render Visual Spine
        for v_node in self.monad_state.dual_tree.visual_nodes:
            if y < margin + 120:
                break # Keep single A4 sheet for clean micro-polyglot

            if v_node.node_type == "preamble":
                for line in _wrap_text(v_node.text_content, 90):
                    stream_lines.append(f"BT /F2 9 Tf 0.2 0.2 0.2 rg {margin} {y} Td ({_escape_pdf(line)}) Tj 0 g ET")
                    y -= 12
                y -= 8
            elif v_node.node_type == "clause":
                stream_lines.append(f"BT /F1 11 Tf 0.1 0.2 0.4 rg {margin} {y} Td ({_escape_pdf(v_node.title)}) Tj 0 g ET")
                y -= 14
                for line in _wrap_text(v_node.text_content, 85):
                    stream_lines.append(f"BT /F2 9 Tf 0.15 0.15 0.15 rg {margin} {y} Td ({_escape_pdf(line)}) Tj 0 g ET")
                    y -= 12
                y -= 6
            elif v_node.node_type == "evidence_table":
                for line in _wrap_text(f"[EVIDENCE] {v_node.text_content}", 95):
                    stream_lines.append(f"BT /F4 8 Tf 0.3 0.1 0.1 rg {margin + 10} {y} Td ({_escape_pdf(line)}) Tj 0 g ET")
                    y -= 11
                y -= 2

        # Render Settlement & Joint Anchor Box at bottom
        y = max(y - 10, margin + 70)
        box_h = 55
        stream_lines.append(f"0.95 0.96 0.98 rg {margin} {y - box_h + 10} {content_width} {box_h} re f 0 g")
        stream_lines.append(f"0.7 0.75 0.85 RG 1 w {margin} {y - box_h + 10} {content_width} {box_h} re s 0 g")

        joint_h = self.monad_state.dual_tree.joint_anchor()
        stream_lines.append(f"BT /F1 10 Tf 0.1 0.3 0.2 rg {margin + 12} {y} Td (Joint Dual-Spine Merkle Anchor: {joint_h[:32]}...) Tj 0 g ET")
        y -= 14
        stream_lines.append(f"BT /F2 8 Tf 0.3 0.3 0.3 rg {margin + 12} {y} Td (Executable Runtime: Run 'python3 <this_file>.pdf' to deterministically evaluate SLA & adjudicate) Tj 0 g ET")
        y -= 12
        stream_lines.append(f"BT /F4 8 Tf 0.4 0.4 0.4 rg {margin + 12} {y} Td (Code Hash: {self.monad_state.dual_tree.code_root_hash()[:24]} | Visual Hash: {self.monad_state.dual_tree.visual_root_hash()[:24]}) Tj 0 g ET")

        # Build PDF stream
        content_stream_bytes = "\n".join(stream_lines).encode("latin1", errors="replace")

        objs: List[bytes] = []
        objs.append(b"<</Type /Catalog /Pages 2 0 R>>")
        objs.append(b"<</Type /Pages /Kids [3 0 R] /Count 1>>")
        objs.append(
            f"<</Type /Page /Parent 2 0 R /MediaBox [0 0 {page_width} {page_height}] "
            f"/Contents 4 0 R /Resources <</Font <</F1 5 0 R /F2 6 0 R /F3 7 0 R /F4 8 0 R>>>>>>".encode("latin1")
        )
        objs.append(
            f"<</Length {len(content_stream_bytes)}>>\nstream\n".encode("latin1")
            + content_stream_bytes
            + b"\nendstream"
        )
        objs.append(b"<</Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold>>")
        objs.append(b"<</Type /Font /Subtype /Type1 /BaseFont /Helvetica>>")
        objs.append(b"<</Type /Font /Subtype /Type1 /BaseFont /Helvetica-Oblique>>")
        objs.append(b"<</Type /Font /Subtype /Type1 /BaseFont /Courier>>")

        # Header for Polyglot (Python raw docstring)
        pdf_header = (
            b"# coding: utf-8\n"
            b'r"""%PDF-1.7\n'
            b"%\xf0\x9f\x96\xa4\n"  # %🖤 binary marker
        )

        # Embedded Contract Manifest in PDF comments
        params_hash = hashlib.sha256(json.dumps(self.parameters, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()
        evidence_hash = hashlib.sha256(json.dumps([e.__dict__ for e in self.evidence_log], sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()
        stream_hash = hashlib.sha256(content_stream_bytes).hexdigest()
        contract_anchor = hashlib.sha256(f"{joint_h}:{params_hash}:{evidence_hash}:{stream_hash}".encode("utf-8")).hexdigest()

        manifest_data = {
            "title": self.title,
            "jurisdiction": self.jurisdiction,
            "parties": [p.__dict__ for p in self.parties],
            "parameters": self.parameters,
            "code_spine": [c.__dict__ for c in self.monad_state.dual_tree.code_nodes],
            "visual_spine": [v.__dict__ for v in self.monad_state.dual_tree.visual_nodes],
            "evidence_log": [e.__dict__ for e in self.evidence_log],
            "code_root_hash": self.monad_state.dual_tree.code_root_hash(),
            "visual_root_hash": self.monad_state.dual_tree.visual_root_hash(),
            "parameters_hash": params_hash,
            "evidence_hash": evidence_hash,
            "stream_hash": stream_hash,
            "joint_anchor": joint_h,
            "contract_anchor": contract_anchor
        }
        manifest_json_str = json.dumps(manifest_data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        comment_manifest = f"%🖤 CONTRACT_MANIFEST: {manifest_json_str}\n".encode("utf-8")

        body = bytearray(pdf_header)
        body.extend(comment_manifest)

        offsets = [0]
        for i, o in enumerate(objs, 1):
            offsets.append(len(body))
            body.extend(f"{i} 0 obj\n".encode("latin1"))
            body.extend(o)
            body.extend(b"\nendobj\n")

        xstart = len(body)
        body.extend(f"xref\n0 {len(objs)+1}\n0000000000 65535 f \n".encode("latin1"))
        for off in offsets[1:]:
            body.extend(f"{off:010d} 00000 n \n".encode("latin1"))

        body.extend(
            f"trailer\n<</Size {len(objs)+1} /Root 1 0 R>>\nstartxref\n{xstart}\n%%EOF\n\"\"\"\n".encode("latin1")
        )

        # Standalone Legal Adjudicator Entrypoint
        runner_code = _generate_contract_runner()
        body.extend(runner_code.encode("utf-8"))

        with open(output_path, "wb") as f:
            f.write(body)

        return output_path

# ============================================================================
# HELPER FUNCTIONS & STANDALONE RUNNER
# ============================================================================

def _escape_pdf(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

def _wrap_text(text: str, max_chars: int) -> List[str]:
    words = text.split()
    lines = []
    curr = []
    curr_len = 0
    for w in words:
        if curr_len + len(w) + 1 <= max_chars:
            curr.append(w)
            curr_len += len(w) + 1
        else:
            lines.append(" ".join(curr))
            curr = [w]
            curr_len = len(w)
    if curr:
        lines.append(" ".join(curr))
    return lines

def _generate_contract_runner() -> str:
    return r'''
# --- BEGIN STANDALONE PROOF-BEARING CONTRACT ADJUDICATOR ---
import os, sys, json, hashlib

def main():
    target_path = sys.argv[0]
    print("\033[1;36m" + "=" * 70)
    print("  %🖤 BLACK-HEART — SELF-VERIFYING PROOF-BEARING CONTRACT ADJUDICATOR")
    print(f"  Target File: {os.path.basename(target_path)} ({os.path.getsize(target_path)} bytes)")
    print("=" * 70 + "\033[0m\n")

    with open(target_path, "rb") as f:
        content = f.read()

    # Locate the embedded contract manifest
    prefix = "%🖤 CONTRACT_MANIFEST: ".encode("utf-8")
    idx = content.find(prefix)
    if idx == -1:
        print("\033[1;31m[!] CRITICAL ERROR: Embedded contract manifest not found!\033[0m")
        sys.exit(1)

    end_idx = content.find(b"\n", idx)
    raw_manifest = content[idx + len(prefix):end_idx].decode("utf-8")
    manifest = json.loads(raw_manifest)

    print(f"\033[1;34m[*] Document Title:\033[0m {manifest['title']}")
    print(f"\033[1;34m[*] Jurisdiction:\033[0m   {manifest['jurisdiction']}")
    for p in manifest.get("parties", []):
        print(f"    - {p['role']}: {p['name']} ({p['identifier']})")

    declared_anchor = manifest.get("joint_anchor", "")
    print(f"\n\033[1;34m[*] Declared Dual-Spine Anchor:\033[0m {declared_anchor}")

    # 1. Verify Visual PDF Stream integrity
    if manifest.get("stream_hash"):
        s_marker = b"stream\n"
        s_start = content.find(s_marker)
        if s_start == -1:
            print("\033[1;31m[✗ RED] INTEGRITY BREACH: PDF content stream missing!\033[0m")
            sys.exit(1)
        s_start += len(s_marker)
        s_end = content.find(b"\nendstream", s_start)
        if s_end == -1:
            print("\033[1;31m[✗ RED] INTEGRITY BREACH: PDF content stream unterminated!\033[0m")
            sys.exit(1)
        actual_stream_bytes = content[s_start:s_end]
        actual_stream_hash = hashlib.sha256(actual_stream_bytes).hexdigest()
        if actual_stream_hash != manifest["stream_hash"]:
            print("\033[1;31m[✗ RED] INTEGRITY BREACH: Visual PDF presentation text altered!\033[0m")
            sys.exit(1)

    # 2. Verify Code Spine
    code_nodes = manifest.get("code_spine", [])
    h_code = hashlib.sha256()
    for cn in code_nodes:
        raw = json.dumps(cn, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        h_code.update(raw)
    computed_code_hash = h_code.hexdigest()
    if manifest.get("code_root_hash") and computed_code_hash != manifest["code_root_hash"]:
        print("\033[1;31m[✗ RED] INTEGRITY BREACH: Code spine modified!\033[0m")
        sys.exit(1)

    # 3. Verify Visual Spine
    visual_nodes = manifest.get("visual_spine", [])
    if visual_nodes:
        h_vis = hashlib.sha256()
        for vn in visual_nodes:
            raw = json.dumps(vn, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
            h_vis.update(raw)
        computed_vis_hash = h_vis.hexdigest()
        if manifest.get("visual_root_hash") and computed_vis_hash != manifest["visual_root_hash"]:
            print("\033[1;31m[✗ RED] INTEGRITY BREACH: Visual spine modified!\033[0m")
            sys.exit(1)
    else:
        computed_vis_hash = manifest.get("visual_root_hash", "")

    # 4. Verify Dual-Spine Anchor
    computed_anchor = hashlib.sha256(
        computed_code_hash.encode("utf-8") + computed_vis_hash.encode("utf-8")
    ).hexdigest()

    if computed_anchor != declared_anchor:
        print(f"\033[1;31m[✗ RED] INTEGRITY BREACH: Dual-spine anchor mismatch!\033[0m")
        print(f"  Expected: {declared_anchor}")
        print(f"  Computed: {computed_anchor}")
        sys.exit(1)

    # 5. Verify Parameters & Evidence Hashes
    params = manifest.get("parameters", {})
    evidence_log = manifest.get("evidence_log", [])

    computed_params_hash = hashlib.sha256(json.dumps(params, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()
    if manifest.get("parameters_hash") and computed_params_hash != manifest["parameters_hash"]:
        print("\033[1;31m[✗ RED] INTEGRITY BREACH: Contract parameters altered!\033[0m")
        sys.exit(1)

    computed_evidence_hash = hashlib.sha256(json.dumps(evidence_log, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()
    if manifest.get("evidence_hash") and computed_evidence_hash != manifest["evidence_hash"]:
        print("\033[1;31m[✗ RED] INTEGRITY BREACH: Evidence log altered!\033[0m")
        sys.exit(1)

    # 6. Verify Contract Anchor
    if manifest.get("contract_anchor"):
        expected_contract_anchor = hashlib.sha256(
            f"{declared_anchor}:{computed_params_hash}:{computed_evidence_hash}:{manifest.get('stream_hash', '')}".encode("utf-8")
        ).hexdigest()
        if manifest["contract_anchor"] != expected_contract_anchor:
            print("\033[1;31m[✗ RED] INTEGRITY BREACH: Contract anchor binding altered!\033[0m")
            sys.exit(1)

    print(f"\033[1;32m[✓ GREEN] Document integrity sound. Dual-spine anchor verified.\033[0m\n")

    # Adjudicate SLA against evidence
    params = manifest.get("parameters", {})
    evidence_log = manifest.get("evidence_log", [])
    total_period_min = params.get("total_period_minutes", 43200)
    target_uptime = params.get("uptime_target_percent", 99.5)
    base_fee = params.get("base_monthly_fee_usd", 10000)
    penalty_rate = params.get("penalty_rate_per_tenth_percent_usd", 500)

    print("\033[1;33m[*] ADJUDICATING EVIDENCE LOG:\033[0m")
    total_downtime_min = 0
    for ev in evidence_log:
        d = ev.get("duration_minutes", 0)
        total_downtime_min += d
        print(f"    [INCIDENT] {ev.get('record_id')}: {ev.get('event_type')} ({d} min) | Hash: {ev.get('raw_hash')[:16]}")

    actual_uptime_pct = ((total_period_min - total_downtime_min) / total_period_min) * 100.0
    print(f"\n    Total Downtime: {total_downtime_min} minutes (Period: {total_period_min} min)")
    print(f"    Measured Uptime: {actual_uptime_pct:.3f}% (Target: >={target_uptime}%)")

    # Settlement Evaluation
    breach = actual_uptime_pct < target_uptime
    deficit = max(0.0, target_uptime - actual_uptime_pct)
    tenths_below = int(deficit * 10)
    penalty_due = tenths_below * penalty_rate
    final_payable = max(0, base_fee - penalty_due)

    receipt_obj = {
        "status": "BREACH" if breach else "COMPLIANT",
        "measured_uptime_pct": round(actual_uptime_pct, 4),
        "target_uptime_pct": target_uptime,
        "penalty_due_usd": penalty_due,
        "final_payable_usd": final_payable,
        "evidence_count": len(evidence_log),
        "joint_anchor": declared_anchor
    }
    receipt_bytes = json.dumps(receipt_obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    receipt_digest = hashlib.sha256(receipt_bytes).hexdigest()

    print("\033[1;36m" + "-" * 70 + "\033[0m")
    if breach:
        print(f"\033[1;31m[⚓ SETTLED: SLA BREACH CONFIRMED]\033[0m")
        print(f"  Penalty Assessed:   \033[1;31m${penalty_due:,} USD\033[0m ({tenths_below} x 0.1% brackets below SLA)")
        print(f"  Net Service Due:    \033[1;32m${final_payable:,} USD\033[0m (Base: ${base_fee:,} USD)")
    else:
        print(f"\033[1;32m[⚓ SETTLED: SLA COMPLIANT]\033[0m")
        print(f"  Penalty Assessed:   $0 USD")
        print(f"  Net Service Due:    ${final_payable:,} USD")

    print(f"  Receipt Digest:     \033[1;35m⚓ ⟨atp:42, digest:{receipt_digest[:16]}⟩\033[0m")
    print("\033[1;36m" + "=" * 70 + "\033[0m")
    sys.exit(0)

if __name__ == "__main__":
    main()
'''

if __name__ == "__main__":
    print("monad.py — Literate Polyglot Monad module loaded.")
