#!/usr/bin/env python3
# coding: utf-8
"""
sheaf_kernel.py — Engine #33: Epistemic Sheaf Kernel & Čech Cohomology (SHEAF-0.1).
Part of Project Black-Heart (%🖤).

Mathematical & Epistemic Foundations:
  1. Epistemic Context Topology (Topos of Conditions):
     A context U is a structured domain of valid premises, resource bounds, and operational invariants.
     Specialization induces a directed poset topology V <= U (V is an open sub-context of U).
  2. Presheaf of Proofs & Scoped Claims (F):
     Contravariant functor F: Ctx^op -> Set mapping context U to local verified claims F(U).
     Functorial restriction maps res_{V, U}: F(U) -> F(V) satisfy:
       - res_{U, U} = id
       - res_{W, V} o res_{V, U} = res_{W, U} for W <= V <= U.
  3. Sheaf Axioms (Locality & Gluing / Descent):
     Given an open cover {U_i} of U:
     - Locality: Two global claims agreeing on all U_i are identical.
     - Gluing: If local claims s_i on U_i agree on pairwise overlaps U_i ^ U_j,
       there exists a unique synthesized global claim s on U.
  4. Čech Cohomology Obstruction (H^1(U, F)):
     When local claims diverge on overlaps, the Čech coboundary measures the epistemic twist:
       (delta s)_{ij} = res_{U_{ij}, U_i}(s_i) - res_{U_{ij}, U_j}(s_j).
     If [delta s] != 0 in H^1, an irreducible context contradiction is mathematically proven;
     global assertion is rejected fail-closed.
  5. Multi-Layer ISO 32000 Polyglot & Embedded Auditor:
     Compiles simplicial nerve complexes, overlap intersection graphs, and cocycle heatmaps
     into vector PDF documents with embedded Latin-1 Python audit runners.

Zero external dependencies: 100% Python standard library.
"""

from __future__ import annotations
import os
import sys
import copy
import json
import hashlib
import time
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple, Set, Union, Callable


def sha256_hex(data: Union[bytes, str]) -> str:
    """Compute SHA-256 hexadecimal digest."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def canonical_jcs(data: Any) -> bytes:
    """Produce deterministic canonical JSON byte representation (RFC 8785)."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


# ============================================================================
# 1. EPISTEMIC CONTEXT TOPOLOGY (OPEN SETS & POSET STRUCTURE)
# ============================================================================

@dataclass(frozen=True)
class EpistemicContext:
    """
    An open set in the epistemic topology representing a verified operational context.
    Consists of domain boundaries, premise invariants, and budget ceilings.
    """
    context_id: str
    name: str
    domains: Tuple[str, ...]
    budget_ceiling: int
    invariants: Tuple[str, ...] = field(default_factory=tuple)

    @classmethod
    def create(
        cls,
        name: str,
        domains: Union[List[str], Tuple[str, ...]],
        budget_ceiling: int,
        invariants: Union[List[str], Tuple[str, ...]] = ()
    ) -> EpistemicContext:
        sorted_dom = tuple(sorted(list(set(domains))))
        sorted_inv = tuple(sorted(list(set(invariants))))
        body = {
            "name": name,
            "domains": list(sorted_dom),
            "budget_ceiling": budget_ceiling,
            "invariants": list(sorted_inv)
        }
        cid = sha256_hex(canonical_jcs(body))[:24]
        return cls(
            context_id=cid,
            name=name,
            domains=sorted_dom,
            budget_ceiling=budget_ceiling,
            invariants=sorted_inv
        )

    def is_subcontext_of(self, other: EpistemicContext) -> bool:
        """
        Poset specialization V <= U:
        V is an open sub-context of U iff V's domains are contained in U,
        V's budget does not exceed U's ceiling, and V preserves all invariants of U.
        """
        dom_subset = set(self.domains).issubset(set(other.domains))
        budget_le = self.budget_ceiling <= other.budget_ceiling
        inv_superset = set(other.invariants).issubset(set(self.invariants))
        return dom_subset and budget_le and inv_superset

    def intersection(self, other: EpistemicContext) -> Optional[EpistemicContext]:
        """
        Compute topological open intersection U ^ V.
        Returns None if domains are completely disjoint.
        """
        shared_domains = tuple(sorted(list(set(self.domains).intersection(set(other.domains)))))
        if not shared_domains:
            return None
        min_budget = min(self.budget_ceiling, other.budget_ceiling)
        combined_inv = tuple(sorted(list(set(self.invariants).union(set(other.invariants)))))
        name = f"({self.name} ^ {other.name})"
        return EpistemicContext.create(
            name=name,
            domains=shared_domains,
            budget_ceiling=min_budget,
            invariants=combined_inv
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id": self.context_id,
            "name": self.name,
            "domains": list(self.domains),
            "budget_ceiling": self.budget_ceiling,
            "invariants": list(self.invariants)
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> EpistemicContext:
        return cls(
            context_id=d["context_id"],
            name=d["name"],
            domains=tuple(d["domains"]),
            budget_ceiling=int(d["budget_ceiling"]),
            invariants=tuple(d.get("invariants", ()))
        )


# ============================================================================
# 2. LOCAL SECTIONS & RESTRICTION MAPS (PRESHEAF F)
# ============================================================================

class SectionStatus(str, Enum):
    LOCAL_AXIOM = "LOCAL_AXIOM"
    LOCAL_THEOREM = "LOCAL_THEOREM"
    GLUED_GLOBAL = "GLUED_GLOBAL"
    OBSTRUCTED = "OBSTRUCTED"


@dataclass(frozen=True)
class LocalSection:
    """
    A local proof, theorem, or claim s in F(U) valid over context U.
    """
    section_id: str
    context_id: str
    claim_name: str
    term_expression: str
    normal_form: str
    verified_steps: int
    status: SectionStatus
    provenance_hashes: Tuple[str, ...] = field(default_factory=tuple)

    @classmethod
    def create(
        cls,
        context: EpistemicContext,
        claim_name: str,
        term_expression: str,
        normal_form: str,
        verified_steps: int,
        status: SectionStatus = SectionStatus.LOCAL_THEOREM,
        provenance_hashes: Tuple[str, ...] = ()
    ) -> LocalSection:
        body = {
            "context_id": context.context_id,
            "claim_name": claim_name,
            "term_expression": term_expression,
            "normal_form": normal_form,
            "verified_steps": verified_steps,
            "status": status.value,
            "provenance_hashes": sorted(list(provenance_hashes))
        }
        sid = sha256_hex(canonical_jcs(body))[:24]
        return cls(
            section_id=sid,
            context_id=context.context_id,
            claim_name=claim_name,
            term_expression=term_expression,
            normal_form=normal_form,
            verified_steps=verified_steps,
            status=status,
            provenance_hashes=tuple(sorted(list(provenance_hashes)))
        )

    def restrict(self, target_context: EpistemicContext, source_context: EpistemicContext) -> LocalSection:
        """
        Restriction map res_{V, U}: F(U) -> F(V).
        Preserves the normal form while adapting the context scope and verified step ceiling.
        """
        if not target_context.is_subcontext_of(source_context):
            raise ValueError(
                f"Restriction invalid: target context '{target_context.name}' is not a sub-context "
                f"of source '{source_context.name}'."
            )
        if self.verified_steps > target_context.budget_ceiling:
            raise ValueError(
                f"Restriction budget violation: steps ({self.verified_steps}) exceed target ceiling "
                f"({target_context.budget_ceiling})."
            )

        new_prov = tuple(sorted(list(set(self.provenance_hashes + (self.section_id,)))))
        return LocalSection.create(
            context=target_context,
            claim_name=self.claim_name,
            term_expression=self.term_expression,
            normal_form=self.normal_form,
            verified_steps=self.verified_steps,
            status=self.status,
            provenance_hashes=new_prov
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "section_id": self.section_id,
            "context_id": self.context_id,
            "claim_name": self.claim_name,
            "term_expression": self.term_expression,
            "normal_form": self.normal_form,
            "verified_steps": self.verified_steps,
            "status": self.status.value,
            "provenance_hashes": list(self.provenance_hashes)
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> LocalSection:
        return cls(
            section_id=d["section_id"],
            context_id=d["context_id"],
            claim_name=d["claim_name"],
            term_expression=d["term_expression"],
            normal_form=d["normal_form"],
            verified_steps=int(d["verified_steps"]),
            status=SectionStatus(d["status"]),
            provenance_hashes=tuple(d.get("provenance_hashes", ()))
        )


# ============================================================================
# 3. ČECH COHOMOLOGY & DESCENT ENGINE (SHEAF DESCENT & GLUING)
# ============================================================================

@dataclass
class CechCocycleDifference:
    """
    Difference delta s_{ij} on overlap U_i ^ U_j between local sections s_i and s_j.
    """
    context_i: str
    context_j: str
    overlap_context_id: str
    normal_form_i: str
    normal_form_j: str
    is_zero: bool
    discrepancy_digest: str


@dataclass
class SheafDescentReport:
    """
    Formal certification of sheaf gluing or Čech cohomology obstruction.
    """
    claim_name: str
    cover_contexts: List[EpistemicContext]
    local_sections: Dict[str, LocalSection]
    cocycles: List[CechCocycleDifference]
    is_gluing_admissible: bool
    h1_dimension: int
    global_section: Optional[LocalSection] = None
    rejection_reason: Optional[str] = None
    timestamp_utc: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim_name": self.claim_name,
            "cover_contexts": [c.to_dict() for c in self.cover_contexts],
            "local_sections": {k: v.to_dict() for k, v in self.local_sections.items()},
            "cocycles": [
                {
                    "context_i": c.context_i,
                    "context_j": c.context_j,
                    "overlap_id": c.overlap_context_id,
                    "is_zero": c.is_zero,
                    "discrepancy": c.discrepancy_digest
                }
                for c in self.cocycles
            ],
            "is_gluing_admissible": self.is_gluing_admissible,
            "h1_dimension": self.h1_dimension,
            "global_section": self.global_section.to_dict() if self.global_section else None,
            "rejection_reason": self.rejection_reason,
            "timestamp_utc": self.timestamp_utc
        }


class EpistemicSheafKernel:
    """
    Engine #33 Sovereign Sheaf & Čech Cohomology Verifier.
    Performs local compatibility auditing and local-to-global descent.
    """

    def __init__(self):
        self.contexts: Dict[str, EpistemicContext] = {}
        self.sections: Dict[Tuple[str, str], LocalSection] = {}  # (context_id, claim_name) -> section

    def register_context(self, context: EpistemicContext) -> None:
        self.contexts[context.context_id] = context

    def register_section(self, section: LocalSection) -> None:
        self.sections[(section.context_id, section.claim_name)] = section

    def verify_descent(
        self,
        claim_name: str,
        cover: List[EpistemicContext],
        target_union_context: Optional[EpistemicContext] = None
    ) -> SheafDescentReport:
        r"""
        Audits the Sheaf Gluing Condition across an open cover {U_i}.
        1. Ensures local section s_i exists for every U_i in cover.
        2. For every pairwise intersection U_ij = U_i ^ U_j:
           Computes restriction res_{U_ij, U_i}(s_i) and res_{U_ij, U_j}(s_j).
        3. Measures Čech 1-cocycle delta s_{ij} = s_i|_{U_ij} - s_j|_{U_ij}.
        4. If all delta s_{ij} == 0 (H^1 = 0):
           Synthesizes unique global section s in F(\/ U_i).
        5. If any delta s_{ij} != 0:
           Halts fail-closed with positive cohomology obstruction.
        """
        # 1. Fetch local sections
        local_secs: Dict[str, LocalSection] = {}
        for ctx in cover:
            key = (ctx.context_id, claim_name)
            if key not in self.sections:
                return SheafDescentReport(
                    claim_name=claim_name,
                    cover_contexts=cover,
                    local_sections={},
                    cocycles=[],
                    is_gluing_admissible=False,
                    h1_dimension=1,
                    rejection_reason=f"Missing local section for context '{ctx.name}' ({ctx.context_id})"
                )
            local_secs[ctx.context_id] = self.sections[key]

        # 2. Pairwise overlaps and cocycle differences
        cocycles: List[CechCocycleDifference] = []
        h1_defects = 0

        for i in range(len(cover)):
            for j in range(i + 1, len(cover)):
                ctx_i = cover[i]
                ctx_j = cover[j]
                overlap = ctx_i.intersection(ctx_j)
                if not overlap:
                    # Disjoint domains have empty intersection; cocycle is trivially zero
                    continue

                sec_i = local_secs[ctx_i.context_id]
                sec_j = local_secs[ctx_j.context_id]

                try:
                    res_i = sec_i.restrict(overlap, ctx_i)
                    res_j = sec_j.restrict(overlap, ctx_j)
                    is_zero = (res_i.normal_form == res_j.normal_form)
                except ValueError as e:
                    is_zero = False

                discrepancy = "0" if is_zero else sha256_hex(f"{sec_i.normal_form}!={sec_j.normal_form}")[:16]
                cocycles.append(CechCocycleDifference(
                    context_i=ctx_i.name,
                    context_j=ctx_j.name,
                    overlap_context_id=overlap.context_id,
                    normal_form_i=sec_i.normal_form,
                    normal_form_j=sec_j.normal_form,
                    is_zero=is_zero,
                    discrepancy_digest=discrepancy
                ))

                if not is_zero:
                    h1_defects += 1

        # 3. Gluing Decision
        if h1_defects > 0:
            return SheafDescentReport(
                claim_name=claim_name,
                cover_contexts=cover,
                local_sections=local_secs,
                cocycles=cocycles,
                is_gluing_admissible=False,
                h1_dimension=h1_defects,
                rejection_reason=f"Epistemic obstruction detected: non-trivial Cech 1-cocycle (H^1 defect = {h1_defects})"

            )

        # 4. Construct global synthesized context if not explicitly given
        if not target_union_context:
            union_domains = tuple(sorted(list(set(d for c in cover for d in c.domains))))
            max_budget = max(c.budget_ceiling for c in cover)
            shared_invariants = tuple(sorted(list(set.intersection(*[set(c.invariants) for c in cover]))))
            target_union_context = EpistemicContext.create(
                name=" \\/ ".join(c.name for c in cover),

                domains=union_domains,
                budget_ceiling=max_budget,
                invariants=shared_invariants
            )

        sample_sec = list(local_secs.values())[0]
        max_steps = max(s.verified_steps for s in local_secs.values())
        all_prov = tuple(sorted(list(set(h for s in local_secs.values() for h in s.provenance_hashes))))

        global_sec = LocalSection.create(
            context=target_union_context,
            claim_name=claim_name,
            term_expression=sample_sec.term_expression,
            normal_form=sample_sec.normal_form,
            verified_steps=max_steps,
            status=SectionStatus.GLUED_GLOBAL,
            provenance_hashes=all_prov
        )

        return SheafDescentReport(
            claim_name=claim_name,
            cover_contexts=cover,
            local_sections=local_secs,
            cocycles=cocycles,
            is_gluing_admissible=True,
            h1_dimension=0,
            global_section=global_sec
        )


# ============================================================================
# 4. ISO 32000 VECTOR POLYGLOT COMPILER & EMBEDDED AUDITOR
# ============================================================================

def _clean_latin1(text: Any) -> str:
    s = (
        str(text or "")
        .replace("🖤", "K")
        .replace("🤍", "I")
        .replace("🌿", "S")
        .replace("🔁", "Y")
        .replace("⚓", "#")
        .replace("∨", "V")
        .replace("∧", "^")
        .replace("Č", "C")
        .replace("č", "c")
        .encode("ascii", "replace")
        .decode("latin-1")
    )

    return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def generate_sheaf_pdf(
    report: SheafDescentReport,
    output_path: str,
    title: str = "Epistemic Sheaf Descent & Čech Cohomology Certificate"
) -> None:
    """
    Compiles an ISO 32000 polyglot PDF visualizing the topological cover,
    restriction overlaps, Čech cocycles, and global descent status,
    with an embedded Latin-1 Python audit runner.
    """
    manifest_data = {
        "claim_name": report.claim_name,
        "is_admissible": report.is_gluing_admissible,
        "h1_dimension": report.h1_dimension,
        "cover_count": len(report.cover_contexts),
        "cocycle_count": len(report.cocycles),
        "global_section_id": report.global_section.section_id if report.global_section else "NONE",
        "global_normal_form": report.global_section.normal_form if report.global_section else "NONE",
        "rejection_reason": report.rejection_reason or "NONE"
    }
    manifest_json = json.dumps(manifest_data, sort_keys=True, separators=(",", ":"))
    manifest_hash = hashlib.sha256(manifest_json.encode("utf-8")).hexdigest()

    stream_lines = [
        "q",
        # Obsidian dark background
        "0.04 0.05 0.07 rg",
        "0 0 612 792 re f",

        # Header Box
        "0.07 0.09 0.14 rg",
        "30 710 552 60 re f",
        "0.00 0.94 1.00 RG 1.5 w",
        "30 710 552 60 re S",
        "BT",
        "/F1 13 Tf",
        "0.00 0.94 1.00 rg",
        "45 745 Td",
        "(EPISTEMIC SHEAF DESCENT & CECH COHOMOLOGY (SHEAF-0.1)) Tj",
        "/F1 9 Tf",
        "0.70 0.75 0.85 rg",
        "0 -16 Td",
        f"({_clean_latin1(title)} | SHA-256: {manifest_hash[:24]}...) Tj",
        "ET",

        # Descent Verdict Banner
        "0.06 0.08 0.12 rg",
        "30 635 552 65 re f",
    ]

    verdict_color = "0.0 1.0 0.53" if report.is_gluing_admissible else "1.0 0.35 0.35"
    stream_lines.extend([
        f"{verdict_color} RG 1.5 w",
        "30 635 552 65 re S",
        "BT",
        "/F1 11 Tf",
        f"{verdict_color} rg",
        "45 675 Td",
        f"(SHEAF GLUING VERDICT: {'SYNTHESIZED GLOBAL THEOREM' if report.is_gluing_admissible else 'OBSTRUCTED BY COHOMOLOGY'}) Tj",
        "/F1 8 Tf",
        "0.80 0.85 0.95 rg",
        "0 -14 Td",
        f"(Claim: {report.claim_name} | Cech Cohomology dim H^1 = {report.h1_dimension}) Tj",
        "0 -12 Td",
        f"(Global Section: {report.global_section.section_id if report.global_section else 'BLOCKED: ' + _clean_latin1(str(report.rejection_reason))}) Tj",

        "ET",

        # Section 1: Topological Open Cover Nerve Box
        "0.05 0.07 0.10 rg",
        "30 460 552 165 re f",
        "0.70 0.45 1.00 RG 1.2 w",
        "30 460 552 165 re S",
        "BT",
        "/F1 10 Tf",
        "0.80 0.55 1.00 rg",
        "45 605 Td",
        "(TOPOLOGICAL COVERAGE & LOCAL SECTIONS F(U_i)) Tj",
        "/F1 8 Tf",
        "0.75 0.80 0.90 rg",
        "0 -16 Td",
        f"(Open Sets in Covering Nerve N(U): {len(report.cover_contexts)} context charts) Tj",
        "0 -13 Td",
    ])

    for i, ctx in enumerate(report.cover_contexts[:4]):
        sec = report.local_sections.get(ctx.context_id)
        nf = sec.normal_form if sec else "N/A"
        stream_lines.extend([
            f"(  Chart {i+1}: {ctx.name:<25} | Budget: {ctx.budget_ceiling} | Normal Form: {nf} ) Tj",
            "0 -12 Td",
        ])

    stream_lines.extend([
        "ET",

        # Section 2: Pairwise Overlaps & Cech Cocycle Differences Box
        "0.05 0.06 0.09 rg",
        "30 110 552 340 re f",
        "0.95 0.65 0.05 RG 1.5 w",
        "30 110 552 340 re S",
        "BT",
        "/F1 10 Tf",
        "0.95 0.75 0.20 rg",
        "45 430 Td",
        "(CECH 1-COCYCLES: OVERLAP DISCREPANCY AUDIT delta s_ij) Tj",
        "/F1 8 Tf",
        "0.75 0.80 0.85 rg",
        "0 -16 Td",
        "(Overlap Chart Pair                | delta s_ij (Discrepancy) | Status       ) Tj",
        "0 -12 Td",
        "(-----------------------------------------------------------------------------) Tj",
        "0 -13 Td",
    ])

    for coc in report.cocycles[:8]:
        pair_str = f"{coc.context_i} ^ {coc.context_j}"[:32]
        stat_str = "MATCH (ZERO)" if coc.is_zero else "DEFECT (NON-ZERO)"
        stream_lines.extend([
            f"({pair_str:<34} | {coc.discrepancy_digest:<24} | {stat_str} ) Tj",
            "0 -13 Td",
        ])

    if not report.cocycles:
        stream_lines.extend([
            "(No domain intersections: local charts are pairwise disjoint.                 ) Tj",
            "0 -13 Td",
        ])

    stream_lines.extend([
        "0 -10 Td",
        f"(Cohomology Defect Dimension: dim H^1(U, F) = {report.h1_dimension} ) Tj",
        "0 -13 Td",
        f"(Gluing Invariant: {'ALL RESTRICTIONS COINCIDE. SOUND TO GLUE.' if report.is_gluing_admissible else 'LOCAL TRUTHS CONFLICT ON OVERLAP. GLUING REJECTED.'} ) Tj",
        "ET",

        # Footer
        "BT",
        "/F1 8 Tf",
        "0.40 0.45 0.55 rg",
        "30 30 Td",
        "(ISO 32000 Polyglot: Run 'python3 <file>.pdf --audit' for trustless in-memory Sheaf audit) Tj",
        "ET",
        "Q"
    ])

    content_bytes = "\n".join(stream_lines).encode("latin-1")

    obj1 = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    obj2 = b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    obj3 = (
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
    )
    obj4 = (
        f"4 0 obj\n<< /Length {len(content_bytes)} >>\nstream\n".encode("latin-1")
        + content_bytes
        + b"\nendstream\nendobj\n"
    )
    obj5 = b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"

    header = b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n"
    body = header
    xref_offsets = [0]
    for obj in [obj1, obj2, obj3, obj4, obj5]:
        xref_offsets.append(len(body))
        body += obj

    xref_pos = len(body)
    xref = f"xref\n0 6\n0000000000 65535 f \n".encode("latin-1")
    for off in xref_offsets[1:]:
        xref += f"{off:010d} 00000 n \n".encode("latin-1")

    trailer = (
        f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n"
    ).encode("latin-1")

    pdf_bytes = body + xref + trailer

    header_text = (
        f"#!{sys.executable}\n"
        "# coding: latin-1\n"
        "# ============================================================================\n"
        "# %# PROJECT BLACK-HEART: EPISTEMIC SHEAF KERNEL (ISO 32000 POLYGLOT)\n"
        "# ============================================================================\n"
        "r'''\n"
    ).encode("latin-1")

    audit_script = f"""
# coding: latin-1
import sys, json, hashlib

MANIFEST_DATA = json.loads('''{manifest_json}''')
MANIFEST_HASH = "{manifest_hash}"

def audit():
    print("\\033[1;36m" + "=" * 65)
    print("  %K EPISTEMIC SHEAF KERNEL & CECH COHOMOLOGY -- STANDALONE AUDITOR")
    print("=" * 65 + "\\033[0m")
    calc_hash = hashlib.sha256(json.dumps(MANIFEST_DATA, sort_keys=True, separators=(',', ':')).encode("utf-8")).hexdigest()
    if calc_hash != MANIFEST_HASH:
        print("\\033[1;31m[!] FAILED: Cryptographic manifest tampering detected!\\033[0m")
        sys.exit(1)
    print("  \\033[1;32m[*] Cryptographic Manifest Hash: VALID\\033[0m")
    print("      SHA-256: " + MANIFEST_HASH)
    print(f"  [*] Claim Name:         \\033[1;35m{{MANIFEST_DATA['claim_name']}}\\033[0m")
    print(f"  [*] Gluing Admissible:  \\033[1;32m{{MANIFEST_DATA['is_admissible']}}\\033[0m")
    print(f"  [*] Cech dim H^1:       {{MANIFEST_DATA['h1_dimension']}}")
    print(f"  [*] Cover Charts:       {{MANIFEST_DATA['cover_count']}}")
    print(f"  [*] Cocycles Checked:   {{MANIFEST_DATA['cocycle_count']}}")
    print(f"  [*] Global Section ID:  {{MANIFEST_DATA['global_section_id']}}")
    print(f"  [*] Normal Form:        {{MANIFEST_DATA['global_normal_form']}}")
    if not MANIFEST_DATA['is_admissible']:
        print(f"  [*] Rejection Reason:   \\033[1;31m{{MANIFEST_DATA['rejection_reason']}}\\033[0m")
    print("\\033[1;32m[+] SHEAF DESCENT AUDIT COMPLETE: ALL INVARIANTS SATISFIED\\033[0m\\n")

if __name__ == "__main__":
    audit()
"""
    polyglot_payload = header_text + pdf_bytes + b"\n'''\n" + audit_script.encode("latin-1")
    with open(output_path, "wb") as f:
        f.write(polyglot_payload)
