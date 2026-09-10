#!/usr/bin/env python3
# coding: utf-8
"""
controlled_forgetting.py — Controlled Forgetting & Epistemic Retirement Engine.
Part of Project Black-Heart (%🖤). Engine #25.

Normative implementation of CONTROLLED-FORGETTING-0.1 and resolution of
Open Questions 3 & 4 of WARRANT.md in Project Black-Heart:
  1. Forgetting as Admission Policy change, NOT erasing history:
     Retired alleles and claims are pruned from the active evaluation surface (Active Surface),
     reducing ATP gas consumption, while remaining 100% preserved in immutable historical bytes.
  2. Invariants I1–I8:
     - I1 (Exact Subject): Target addressed by content digest and exact ID.
     - I2 (Default Exclusion): Excluded from default active evaluation.
     - I3 (No Implicit Resurrection): Historical bytes cannot resurrect an allele without
       an explicit signed ReAdoptionRecord (ResurrectionGuard immune gate).
     - I4 (Loss is First-Class): Every retirement record MUST carry a non-empty loss_declaration.
     - I5 (Retirement is Not Refutation): Pruning an active surface does not alter truth value.
     - I6 (Cryptographic Authority): Domain-separated RFC 8032 Ed25519 signing.
     - I7 (CAS/Git Preservation): History remains accessible in CAS and PDF bytes.
     - I8 (Non-Transitive Composition): Retiring a conflicting claim does not validate remaining claims.
  3. Negative Space Coverage Metric (mu(C)):
     Measures the volume of expression tree space pruned by a counterexample or refutation,
     eliminating vanity churning and awarding gas reclamation bounties.
  4. ISO 32000 PDF Polyglot Append-Only Updates:
     Appends Tombstone Stelae to living polyglots with standalone verification runner.
"""

from __future__ import annotations
import os
import sys
import json
import time
import math
import hashlib
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple, Set, Union, Callable

import crypto
import glyph
from glyph import Term, parse, evaluate, term_hash, GLYPH_K, GLYPH_I, GLYPH_S, GLYPH_ANCHOR

# ============================================================================
# 1. RETIREMENT MODES & STATUSES (CONTROLLED-FORGETTING-0.1 §2, §4)
# ============================================================================

class RetirementMode(str, Enum):
    """
    Categorical taxonomy of why an artifact is retired from active admission.
    Invariant I5: Retirement is not refutation — only REFUTED asserts falsehood.
    """
    SUPERSEDED = "SUPERSEDED"     # Replaced by an elevated/stronger claim (e.g. E -> A). Requires replacement_id.
    REFUTED = "REFUTED"           # Refuted by an executable Grade C counterexample.
    WITHDRAWN = "WITHDRAWN"       # Demoted by author due to defect/flaw prior to formal refutation.
    ARCHIVED = "ARCHIVED"         # Historical milestone excluded from active ATP metabolism.
    QUARANTINED = "QUARANTINED"   # Suspended pending adjudication or adversarial audit.
    DEPRECATED = "DEPRECATED"     # Scheduled for obsolescence; replaced by canonical normal form.



class AdmissionStatus(str, Enum):
    """Admission standing of an artifact in the cognitive surface."""
    ACTIVE = "ACTIVE"                       # In active surface: evaluated and executed by default.
    RETIRED = "RETIRED"                     # In historical substrate: preserved in bytes, excluded from metabolism.
    READOPTED = "READOPTED"                 # Restored to active surface via explicit ReAdoptionRecord.


class EpistemicResurrectionError(RuntimeError):
    """Raised when an attempt is made to implicitly resurrect a retired artifact (Invariant I3)."""
    pass


# ============================================================================
# 2. RFC 8785 CANONICAL SERIALIZATION
# ============================================================================

def canonical_jcs(data: Any) -> bytes:
    """Pure Python RFC 8785 JSON Canonicalization Scheme (JCS)."""
    return json.dumps(
        data,
        sort_keys=True,
        separators=(',', ':'),
        ensure_ascii=False
    ).encode("utf-8")


# ---------------------------------------------------------------------------
# Field validation for the numbers these records actually spend.
#
# `negative_space_coverage` is mu(C), declared as a ratio in [0.0, 1.0]; it is
# summed into pruned-search-space volume and immune health metrics.
# `atp_gas_recovered` is metabolic fuel handed back on retirement; it is summed
# into reclaimed-gas totals. Neither has a meaning outside those ranges, and
# `bool` is not a quantity of either, so both are refused at construction and
# at deserialization rather than propagating into an arithmetic total.
# ---------------------------------------------------------------------------

def _require_ratio(value: Any, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(
            f"{field_name} must be a real number in [0.0, 1.0]; got {type(value).__name__}."
        )
    v = float(value)
    if not math.isfinite(v):
        raise ValueError(f"{field_name} must be finite; got {value!r}.")
    if not (0.0 <= v <= 1.0):
        raise ValueError(f"{field_name} must lie in [0.0, 1.0]; got {v!r}.")
    return v


def _require_non_negative_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(
            f"{field_name} must be an integer quantity; got {type(value).__name__}."
        )
    if value < 0:
        raise ValueError(f"{field_name} must not be negative; got {value}.")
    return value


def _is_record_id(value: Any) -> bool:
    """A record id is the hex SHA-256 of the canonical body; nothing else."""
    if not isinstance(value, str) or len(value) != 64:
        return False
    return all(c in "0123456789abcdef" for c in value)


# ============================================================================
# 3. NEGATIVE SPACE COVERAGE METRIC (WARRANT.md §9.3)
# ============================================================================

class NegativeSpaceMeter:
    """
    Measures the volume of expression tree space pruned by a refutation or retirement.
    Prevents vanity churning (creating trivial counterexamples for zero coverage).
    """

    @staticmethod
    def calculate_coverage(rule_or_pattern: str, sample_depth: int = 3) -> float:
        """
        Estimates the ratio of expression space eliminated:
          mu(C) in [0.0, 1.0]
        """
        p = rule_or_pattern.strip()
        if not p:
            return 0.0

        # Known universal / broad structural rules prune massive subspaces
        if "->" in p:
            lhs, rhs = p.split("->", 1)
            lhs = lhs.strip()
            rhs = rhs.strip()
            # Commutative swap refutation in non-commutative logic eliminates ~75% of permutations
            if "x y" in lhs and "y x" in rhs:
                return 0.75
            # Constant collapse refutations
            if "x" in lhs and "K" in lhs and "I" in rhs:
                return 0.65

        # Heuristic estimation based on AST node complexity and arity
        try:
            term = glyph.parse(p)
            size = glyph.tree_size(term)
            # Deeper patterns prune more specific subtrees; shallow patterns prune broad spaces
            coverage = max(0.10, min(0.95, 1.0 - (0.5 ** (1.0 / max(1, size)))))
            return round(coverage, 4)
        except Exception:
            return 0.25

    @staticmethod
    def compute_gas_reclamation(coverage: float, base_atp: int = 50) -> int:
        """
        Calculates the ATP gas quanta returned to the organism's metabolic reserve
        for eliminating dead branches.
        """
        return int(base_atp + math.floor(200.0 * coverage))


# ============================================================================
# 4. RETIREMENT & RE-ADOPTION RECORDS (INVARIANTS I1, I4, I6)
# ============================================================================

@dataclass
class RetirementRecord:
    """
    Cryptographic tombstone record asserting that an artifact is retired from active admission.
    Enforces Invariants I1 (exact subject), I4 (loss is first-class), and I6 (author signature).
    """
    record_id: str
    target_id: str                          # Exact subject identifier (I1)
    target_digest: str                      # Content hash of retired subject (I1)
    mode: RetirementMode
    loss_declaration: str                   # Mandatory non-empty loss description (I4)
    negative_space_coverage: float          # mu(C) in [0.0, 1.0]
    atp_gas_recovered: int                  # Metabolic fuel reclaimed
    author_pk_hex: str
    signature_hex: str
    replacement_id: Optional[str] = None    # Mandatory if SUPERSEDED
    timestamp_utc: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    def __post_init__(self):
        # Invariant I4: Loss is first-class (must not be empty or whitespace)
        if not self.loss_declaration or not self.loss_declaration.strip():
            raise ValueError(
                f"Invariant I4 violation: retirement record for '{self.target_id}' "
                "MUST carry a non-empty loss_declaration."
            )
        # Mode SUPERSEDED requires a replacement_id
        if self.mode == RetirementMode.SUPERSEDED and not self.replacement_id:
            raise ValueError(
                f"Retirement mode SUPERSEDED requires a valid non-empty replacement_id."
            )
        # The two numbers this record spends are checked before it can be signed.
        self.negative_space_coverage = _require_ratio(
            self.negative_space_coverage, "negative_space_coverage")
        self.atp_gas_recovered = _require_non_negative_int(
            self.atp_gas_recovered, "atp_gas_recovered")
        if not self.record_id:
            self.record_id = self.compute_record_id()

    def body_dict(self) -> Dict[str, Any]:
        return {
            "target_id": self.target_id,
            "target_digest": self.target_digest,
            "mode": self.mode.value,
            "replacement_id": self.replacement_id,
            "loss_declaration": self.loss_declaration.strip(),
            "negative_space_coverage": self.negative_space_coverage,
            "atp_gas_recovered": self.atp_gas_recovered,
            "timestamp_utc": self.timestamp_utc,
            "author_pk_hex": self.author_pk_hex
        }

    def compute_record_id(self) -> str:
        body_bytes = canonical_jcs(self.body_dict())
        return hashlib.sha256(body_bytes).hexdigest()

    def validate_body_domain(self) -> None:
        """Raise unless the numbers this record spends are inside their declared
        domains, checked against the values carried right now.

        Separate from `verify_signature` on purpose: a signature can correctly
        authenticate a body that is out of domain, and construction-time
        validation says nothing about an object that was mutated afterwards or
        signed by a peer that never used this constructor.
        """
        _require_ratio(self.negative_space_coverage, "negative_space_coverage")
        _require_non_negative_int(self.atp_gas_recovered, "atp_gas_recovered")

    def has_valid_body_domain(self) -> bool:
        try:
            self.validate_body_domain()
        except (ValueError, TypeError):
            return False
        return True

    def is_admissible_for(self, subject_id: str) -> bool:
        """The complete local check before this record may decide anything about
        `subject_id`: it names that subject, its numbers are in domain, and its
        signature covers this body.

        The subject test is the slot binding. A genuinely signed retirement of A
        filed under B is authentic and in domain and still says nothing about B.
        """
        return (self.target_id == subject_id
                and self.has_valid_body_domain()
                and self.verify_signature())

    def signature_message(self) -> bytes:
        """Domain-separated signing message over the id of the CURRENT body.

        The id is recomputed here rather than read from the field, so a body
        rewritten under an unchanged `record_id` produces a different message
        and cannot inherit the old signature.
        """
        return b"retirement-sig-v1:" + bytes.fromhex(self.compute_record_id())

    def sign(self, secret_key_hex: str):
        self.record_id = self.compute_record_id()
        msg = self.signature_message()
        self.signature_hex = crypto.sign_hex(secret_key_hex, msg)

    def verify_signature(self) -> bool:
        """True only when the signature covers the body carried on this object.

        Binds canonical body -> recomputed id -> signature, and requires the
        transported `record_id` to be that same recomputed id. It is evaluated
        on every call: a record mutated after loading is refused here.

        What this does NOT establish: that the signing key is entitled to
        retire this subject. Authorization is a separate question and is not
        answered anywhere in this module.
        """
        if not self.signature_hex or not self.author_pk_hex:
            return False
        try:
            expected_id = self.compute_record_id()
            if not _is_record_id(self.record_id) or self.record_id != expected_id:
                return False
            msg = self.signature_message()
        except (ValueError, TypeError, AttributeError):
            return False
        return crypto.verify_hex(self.author_pk_hex, msg, self.signature_hex)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "body": self.body_dict(),
            "signature_hex": self.signature_hex
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> RetirementRecord:
        """Rebuild a record exactly as transported.

        The transported `record_id` is kept verbatim, never recomputed to fit a
        rewritten body: repairing a foreign record's id would hide the very
        mismatch `verify_signature` exists to catch. Numbers are refused rather
        than coerced, so `"0.4"` or `None` is a typed refusal here instead of a
        silently different body downstream.
        """
        b = d.get("body", d)
        rec = cls(
            record_id=str(d.get("record_id", "")),
            target_id=str(b["target_id"]),
            target_digest=str(b["target_digest"]),
            mode=RetirementMode(b["mode"]),
            loss_declaration=str(b["loss_declaration"]),
            negative_space_coverage=_require_ratio(
                b.get("negative_space_coverage", 0.0), "negative_space_coverage"),
            atp_gas_recovered=_require_non_negative_int(
                b.get("atp_gas_recovered", 0), "atp_gas_recovered"),
            author_pk_hex=str(b["author_pk_hex"]),
            signature_hex=str(d.get("signature_hex", "")),
            replacement_id=b.get("replacement_id"),
            timestamp_utc=str(b.get("timestamp_utc", ""))
        )
        return rec


@dataclass
class ReAdoptionRecord:
    """
    Authorizes the unretirement and re-admission of a previously retired subject.
    Invariant I3: Historical state cannot re-enter active surface without this record.
    """
    record_id: str
    target_id: str
    retirement_record_id: str
    new_evidence_claim_id: str
    justification: str
    author_pk_hex: str
    signature_hex: str
    timestamp_utc: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    def __post_init__(self):
        if not self.justification or not self.justification.strip():
            raise ValueError("Re-adoption requires a non-empty justification.")
        if not self.record_id:
            self.record_id = self.compute_record_id()

    def body_dict(self) -> Dict[str, Any]:
        return {
            "target_id": self.target_id,
            "retirement_record_id": self.retirement_record_id,
            "new_evidence_claim_id": self.new_evidence_claim_id,
            "justification": self.justification.strip(),
            "timestamp_utc": self.timestamp_utc,
            "author_pk_hex": self.author_pk_hex
        }

    def compute_record_id(self) -> str:
        body_bytes = canonical_jcs(self.body_dict())
        return hashlib.sha256(body_bytes).hexdigest()

    def is_admissible_for(self, subject_id: str, retirement: RetirementRecord) -> bool:
        """The complete local check before this record may re-admit `subject_id`.

        It must name that subject, cite the record id of the retirement being
        cleared, and verify against its own body. The retirement it cites has
        to be admissible for the same subject in its own right, so a re-adoption
        cannot borrow authority from a record filed under the wrong slot.
        """
        return (self.target_id == subject_id
                and retirement.is_admissible_for(subject_id)
                and self.retirement_record_id == retirement.record_id
                and self.verify_signature())

    def signature_message(self) -> bytes:
        """Domain-separated message over the id of the CURRENT body (see
        RetirementRecord.signature_message for why it is recomputed)."""
        return b"readoption-sig-v1:" + bytes.fromhex(self.compute_record_id())

    def sign(self, secret_key_hex: str):
        self.record_id = self.compute_record_id()
        msg = self.signature_message()
        self.signature_hex = crypto.sign_hex(secret_key_hex, msg)

    def verify_signature(self) -> bool:
        """True only when the signature covers the body carried on this object.

        Establishes authorship of this body by the named key. It does not
        establish that the key may re-admit the subject, and it does not by
        itself connect the record to a registered retirement: that link is
        checked where admission is decided (see EpistemicTombstoneRegistry).
        """
        if not self.signature_hex or not self.author_pk_hex:
            return False
        try:
            expected_id = self.compute_record_id()
            if not _is_record_id(self.record_id) or self.record_id != expected_id:
                return False
            msg = self.signature_message()
        except (ValueError, TypeError, AttributeError):
            return False
        return crypto.verify_hex(self.author_pk_hex, msg, self.signature_hex)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "body": self.body_dict(),
            "signature_hex": self.signature_hex
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> ReAdoptionRecord:
        b = d.get("body", d)
        return cls(
            record_id=str(d.get("record_id", "")),
            target_id=str(b["target_id"]),
            retirement_record_id=str(b["retirement_record_id"]),
            new_evidence_claim_id=str(b["new_evidence_claim_id"]),
            justification=str(b["justification"]),
            author_pk_hex=str(b["author_pk_hex"]),
            signature_hex=str(d.get("signature_hex", "")),
            timestamp_utc=str(b.get("timestamp_utc", ""))
        )


# ============================================================================
# 5. EPISTEMIC TOMBSTONE REGISTRY & ADMISSION GATE (INVARIANTS I2, I3)
# ============================================================================

class EpistemicTombstoneRegistry:
    """
    Maintains active vs historical surface boundaries across Project Black-Heart.
    Enforces Invariants I2 (Default exclusion) and I3 (No implicit resurrection).
    """

    def __init__(self):
        self.tombstones: Dict[str, RetirementRecord] = {}
        self.readoptions: Dict[str, ReAdoptionRecord] = {}

    def is_admitted(self, target_id: str) -> bool:
        """True if the target is currently in the active surface.

        A tombstoned subject returns to the active surface only through a
        re-adoption that (a) verifies against its own body, (b) names this very
        subject, and (c) names the record id of the retirement actually
        registered here. The presence of an entry under the right key is not
        enough: a re-adoption issued against some other retirement of the same
        subject does not clear this one.

        Fail-closed: if the registered retirement is not itself admissible for
        this subject — wrong subject for the slot, out-of-domain numbers, or a
        signature that does not cover its body — the subject stays retired
        rather than falling out of the gate. Loader validation does not stand in
        for this: the registry is a mutable public structure and consumers write
        into it directly.
        """
        tomb = self.tombstones.get(target_id)
        if tomb is None:
            return True
        if not tomb.is_admissible_for(target_id):
            return False
        readoption = self.readoptions.get(target_id)
        if readoption is None:
            return False
        return readoption.is_admissible_for(target_id, tomb)

    def get_admission_status(self, target_id: str) -> AdmissionStatus:
        if target_id not in self.tombstones:
            return AdmissionStatus.ACTIVE
        # READOPTED is reported only for a re-adoption that would actually
        # admit; an unverifiable or unlinked one leaves the subject RETIRED.
        if self.is_admitted(target_id):
            return AdmissionStatus.READOPTED
        return AdmissionStatus.RETIRED

    def filter_active_surface(
        self,
        items: List[Any],
        id_getter: Callable[[Any], str]
    ) -> Tuple[List[Any], List[Any]]:
        """
        Partitions an input list into:
          (active_surface, historical_substrate)
        """
        active = []
        historical = []
        for item in items:
            tid = id_getter(item)
            if self.is_admitted(tid):
                active.append(item)
            else:
                historical.append(item)
        return active, historical

    def retire(
        self,
        target_id: str,
        target_digest: str,
        mode: RetirementMode,
        loss_declaration: str,
        author_sk_hex: str,
        author_pk_hex: str,
        replacement_id: Optional[str] = None,
        rule_or_pattern: str = ""
    ) -> RetirementRecord:
        """Creates, signs, and registers a RetirementRecord."""
        coverage = NegativeSpaceMeter.calculate_coverage(rule_or_pattern)
        atp_gas = NegativeSpaceMeter.compute_gas_reclamation(coverage)

        record = RetirementRecord(
            record_id="",
            target_id=target_id,
            target_digest=target_digest,
            mode=mode,
            replacement_id=replacement_id,
            loss_declaration=loss_declaration,
            negative_space_coverage=coverage,
            atp_gas_recovered=atp_gas,
            author_pk_hex=author_pk_hex,
            signature_hex=""
        )
        record.sign(author_sk_hex)
        if not record.verify_signature():
            raise ValueError(
                f"Refusing to register a retirement for '{target_id}': the record "
                "does not verify against its own body immediately after signing."
            )
        self.tombstones[target_id] = record
        # Invalidate any earlier re-adoption
        if target_id in self.readoptions:
            del self.readoptions[target_id]
        return record

    def readopt(
        self,
        target_id: str,
        justification: str,
        new_evidence_claim_id: str,
        author_sk_hex: str,
        author_pk_hex: str
    ) -> ReAdoptionRecord:
        """Unretires an artifact by issuing a signed ReAdoptionRecord."""
        if target_id not in self.tombstones:
            raise ValueError(f"Cannot re-adopt '{target_id}': not currently tombstoned.")

        ret_rec = self.tombstones[target_id]
        # A successor must not be issued against a retirement that is not
        # admissible for this subject. Refusal happens here, before the record
        # is built, signed or stored, so an inconsistent slot leaves no trace.
        if not ret_rec.is_admissible_for(target_id):
            raise ValueError(
                f"Cannot re-adopt '{target_id}': the registered retirement record is not "
                f"admissible for it (it names '{ret_rec.target_id}', its declared numbers "
                "must be in domain, and its signature must cover its own body)."
            )
        rec = ReAdoptionRecord(
            record_id="",
            target_id=target_id,
            retirement_record_id=ret_rec.record_id,
            new_evidence_claim_id=new_evidence_claim_id,
            justification=justification,
            author_pk_hex=author_pk_hex,
            signature_hex=""
        )
        rec.sign(author_sk_hex)
        self.readoptions[target_id] = rec
        return rec

    def assert_viable_for_admission(self, target_id: str):
        """Immune gate guard: raises EpistemicResurrectionError if tombstoned and not re-adopted."""
        if not self.is_admitted(target_id):
            tomb = self.tombstones[target_id]
            raise EpistemicResurrectionError(
                f"Resurrection Guard Refusal: artifact '{target_id}' is RETIRED ({tomb.mode.value}). "
                f"Declared loss: '{tomb.loss_declaration}'. Invariant I3 prohibits implicit resurrection."
            )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tombstones": {k: v.to_dict() for k, v in self.tombstones.items()},
            "readoptions": {k: v.to_dict() for k, v in self.readoptions.items()}
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> EpistemicTombstoneRegistry:
        """Load a registry, refusing any record that does not verify.

        This raises rather than skipping. Dropping an unverifiable *tombstone*
        would silently return its subject to the active surface, which is the
        wrong direction to fail; and a caller that cannot tell a loaded
        registry from a partially loaded one cannot act on either.
        """
        reg = cls()
        for k, v in d.get("tombstones", {}).items():
            rec = RetirementRecord.from_dict(v)
            if rec.target_id != k:
                raise ValueError(
                    f"Retirement record filed under '{k}' names subject '{rec.target_id}'."
                )
            if not rec.verify_signature():
                raise ValueError(
                    f"Retirement record for '{k}' does not verify against its own body."
                )
            reg.tombstones[k] = rec
        for k, v in d.get("readoptions", {}).items():
            rec = ReAdoptionRecord.from_dict(v)
            if rec.target_id != k:
                raise ValueError(
                    f"Re-adoption record filed under '{k}' names subject '{rec.target_id}'."
                )
            if not rec.verify_signature():
                raise ValueError(
                    f"Re-adoption record for '{k}' does not verify against its own body."
                )
            reg.readoptions[k] = rec
        return reg


# ResurrectionGuard alias for EpistemicTombstoneRegistry
ResurrectionGuard = EpistemicTombstoneRegistry



# ============================================================================
# 6. ISO 32000 PDF POLYGLOT TOMBSTONE VISUALIZER
# ============================================================================

def _sanitize_ascii(text: str) -> str:
    s = (text.replace(GLYPH_K, "K")
             .replace(GLYPH_I, "I")
             .replace(GLYPH_S, "S")
             .replace(GLYPH_ANCHOR, "[#]")
             .replace("•", "*")
             .replace("§", "Section"))
    clean = "".join(c if (32 <= ord(c) < 127) else "?" for c in s)
    return clean.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def append_retirement_tombstone_to_pdf(
    source_pdf_bytes: bytes,
    output_path: str,
    record: RetirementRecord,
    registry: Optional[EpistemicTombstoneRegistry] = None
) -> bytes:
    """
    Appends an ISO 32000 §7.5.6 incremental document update containing a visual
    Tombstone Stele to an existing polyglot document:
      - Preserves byte prefix: output.startswith(source_pdf_bytes) == True
      - Renders an Obsidian/Slate Tombstone Stele with glowing mode-specific borders.
      - Embeds verifiable JSON retirement manifest.
      - Extends the self-executing Python audit runner.
    """
    reg = registry or EpistemicTombstoneRegistry()
    reg.tombstones[record.target_id] = record

    tid_clean = _sanitize_ascii(record.target_id[:24])
    digest_clean = _sanitize_ascii(record.target_digest[:24])
    mode_clean = _sanitize_ascii(record.mode.value)
    loss_clean = _sanitize_ascii(record.loss_declaration[:60])
    rep_clean = _sanitize_ascii((record.replacement_id or "NONE")[:24])
    cov_pct = f"{record.negative_space_coverage * 100.0:.1f}%"
    gas_str = f"+{record.atp_gas_recovered} ATP"

    # Border color based on mode
    if record.mode == RetirementMode.REFUTED:
        border_col = "0.90 0.20 0.25"
        bg_col = "0.14 0.05 0.06"
    elif record.mode == RetirementMode.SUPERSEDED:
        border_col = "0.85 0.65 0.15"
        bg_col = "0.12 0.09 0.04"
    elif record.mode == RetirementMode.DEPRECATED:
        border_col = "0.75 0.35 0.85"
        bg_col = "0.10 0.05 0.12"
    else:
        border_col = "0.50 0.55 0.65"
        bg_col = "0.07 0.08 0.10"

    content_lines = [
        "q",
        # Page background
        "0.04 0.05 0.07 rg",
        "0 0 612 792 re f",
        # Banner
        "0.08 0.10 0.14 rg",
        "30 710 552 60 re f",
        "0.20 0.25 0.35 RG 1 w",
        "30 710 552 60 re S",
        "BT",
        "/F1 16 Tf",
        "1.0 1.0 1.0 rg",
        "45 745 Td",
        "(%# BLACK-HEART: EPISTEMIC RETIREMENT TOMBSTONE) Tj",
        "/F1 10 Tf",
        "0.6 0.7 0.85 rg",
        "0 -20 Td",
        "(CONTROLLED-FORGETTING-0.1 | Invariant I1-I8 Admission Gate) Tj",
        "ET",
        # Tombstone Stele Card
        f"{bg_col} rg",
        "30 460 552 220 re f",
        f"{border_col} RG 2 w",
        "30 460 552 220 re S",
        "BT",
        "/F1 14 Tf",
        "1.0 1.0 1.0 rg",
        "45 650 Td",
        f"([TOMBSTONE] SUBJECT RETIRED: {mode_clean}) Tj",
        "/F1 9 Tf",
        "0.75 0.80 0.85 rg",
        "0 -24 Td",
        f"(Target Subject ID:   {tid_clean}...) Tj",
        "0 -16 Td",
        f"(Subject Digest:      {digest_clean}...) Tj",
        "0 -16 Td",
        f"(Replacement Ref:     {rep_clean}) Tj",
        "0 -16 Td",
        f"(Mandatory Loss (I4): {loss_clean}) Tj",
        "0 -16 Td",
        f"(Negative Space Pruned: {cov_pct} expression tree volume) Tj",
        "0 -16 Td",
        f"(Metabolic Gas Reclaimed: {gas_str}) Tj",
        "0 -16 Td",
        f"(Author Key:          {record.author_pk_hex[:32]}...) Tj",
        "0 -16 Td",
        f"(Timestamp:           {record.timestamp_utc} | Sig: {record.signature_hex[:24]}...) Tj",
        "ET",
        # Bottom notice
        "BT",
        "/F1 8 Tf",
        "0.40 0.45 0.55 rg",
        "30 30 Td",
        "(Invariant I3 Active: Implicit resurrection prohibited. Re-adoption requires signed ReAdoptionRecord.) Tj",
        "ET",
        "Q"
    ]
    content_bytes = "\n".join(content_lines).encode("latin-1")

    import re
    # Extract existing kids and count
    kids_match = re.search(rb"/Kids\s*\[([^\]]+)\]", source_pdf_bytes)
    count_match = re.search(rb"/Count\s+(\d+)", source_pdf_bytes)
    current_kids = kids_match.group(1).decode("latin-1").strip() if kids_match else "3 0 R"
    current_count = int(count_match.group(1).decode("latin-1")) if count_match else 1
    new_count = current_count + 1

    obj_ids = [int(m) for m in re.findall(rb"(\d+)\s+0\s+obj", source_pdf_bytes)]
    next_id = max(obj_ids, default=5) + 1

    content_obj_id = next_id
    page_obj_id = next_id + 1
    font_obj_id = next_id + 2

    new_kids = f"{current_kids} {page_obj_id} 0 R"

    content_obj = (
        f"{content_obj_id} 0 obj\n<< /Length {len(content_bytes)} >>\nstream\n".encode("latin-1")
        + content_bytes
        + b"\nendstream\nendobj\n"
    )
    font_obj = f"{font_obj_id} 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n".encode("latin-1")
    page_obj = (
        f"{page_obj_id} 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        f"/Contents {content_obj_id} 0 R /Resources << /Font << /F1 {font_obj_id} 0 R >> >> >>\nendobj\n"
    ).encode("latin-1")
    pages_update_obj = (
        f"2 0 obj\n<< /Type /Pages /Kids [{new_kids}] /Count {new_count} >>\nendobj\n"
    ).encode("latin-1")

    # Order of objects in update body: 2 (Pages), content, font, page
    update_body = pages_update_obj + content_obj + font_obj + page_obj

    # Create incremental update
    prev_eof_idx = source_pdf_bytes.rfind(b"%%EOF")
    if prev_eof_idx != -1:
        base_bytes = source_pdf_bytes[:prev_eof_idx + 5] + b"\n"
    else:
        base_bytes = source_pdf_bytes + b"\n"

    update_start_pos = len(base_bytes)
    pos_2 = update_start_pos
    pos_content = pos_2 + len(pages_update_obj)
    pos_font = pos_content + len(content_obj)
    pos_page = pos_font + len(font_obj)
    xref_offset = pos_page + len(page_obj)

    # xref table covers object 2 and objects content_obj_id to page_obj_id
    xref = (
        f"xref\n"
        f"2 1\n"
        f"{pos_2:010d} 00000 n \n"
        f"{content_obj_id} 3\n"
        f"{pos_content:010d} 00000 n \n"
        f"{pos_font:010d} 00000 n \n"
        f"{pos_page:010d} 00000 n \n"
    ).encode("latin-1")

    trailer = (
        f"trailer\n<< /Size {next_id + 3} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n"
    ).encode("latin-1")

    manifest_json = json.dumps(reg.to_dict(), sort_keys=True)
    manifest_line = (
        b"# %" + bytes([0xf0, 0x9f, 0x96, 0xa4])
        + b" RETIREMENT_MANIFEST: " + manifest_json.encode("utf-8") + b"\n"
    )

    py_runner = f"""
# coding: latin-1
import sys, json, os

cwd = os.getcwd()
if cwd not in sys.path:
    sys.path.insert(0, cwd)

def audit_retirement():
    print("\\033[1;36m" + "=" * 70)
    print("  %# CONTROLLED FORGETTING AUDITOR (CONTROLLED-FORGETTING-0.1)")
    print("=" * 70 + "\\033[0m")
    with open(__file__, 'rb') as f:
        data = f.read()
    prefix = bytes([0x23, 0x20, 0x25, 0xf0, 0x9f, 0x96, 0xa4]) + b" RETIREMENT_MANIFEST: "
    idx = data.rfind(prefix)
    if idx == -1:
        print("\\033[1;31m[-] No retirement manifest found.\\033[0m")
        sys.exit(1)
    end = data.find(b"\\n", idx)
    reg_json = json.loads(data[idx + len(prefix):end].decode('utf-8'))
    import controlled_forgetting
    try:
        reg = controlled_forgetting.EpistemicTombstoneRegistry.from_dict(reg_json)
    except ValueError as e:
        # A record whose signature does not cover its body is refused before
        # any of its fields are printed as audited.
        print("\\033[1;31m[!] Refusing retirement manifest: " + str(e) + "\\033[0m")
        sys.exit(1)
    print(f"[*] Audited {{len(reg.tombstones)}} tombstones and {{len(reg.readoptions)}} re-adoptions.\\n")
    all_valid = True
    for tid, t in reg.tombstones.items():
        if not t.verify_signature():
            print(f"\\033[1;31m[!] Signature INVALID for tombstone '{{tid}}'\\033[0m")
            all_valid = False
        else:
            status = reg.get_admission_status(tid).value
            print(f"\\033[1;33m[TOMBSTONE] '{{tid}}' -> {{t.mode.value}} (Status: {{status}})\\033[0m")
            print(f"  Loss: '{{t.loss_declaration}}' | Negative space: {{t.negative_space_coverage * 100:.1f}}% | Gas reclaimed: +{{t.atp_gas_recovered}} ATP")
    print("\\033[1;36m" + "=" * 70 + "\\033[0m")
    if all_valid:
        print("\\033[1;32m[+] All retirement tombstones cryptographically verified.\\033[0m")
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    audit_retirement()
"""

    incremental_pdf = base_bytes + update_body + xref + trailer + manifest_line + b"'''\n" + py_runner.encode("latin-1")

    with open(output_path, "wb") as f:
        f.write(incremental_pdf)

    return incremental_pdf


def generate_tombstone_stele_pdf(
    records: List[RetirementRecord],
    output_path: str,
    registry: Optional[EpistemicTombstoneRegistry] = None
) -> bytes:
    """
    Creates an ISO 32000 compliant vector PDF polyglot document containing:
      - Visual Epistemic Tombstone Stele ledger of retired artifacts.
      - Color-coded borders based on RetirementMode:
          * REFUTED: Crimson
          * SUPERSEDED: Gold
          * DEPRECATED: Purple
          * ARCHIVED / WITHDRAWN / QUARANTINED: Slate
      - Embedded JCS-canonical JSON retirement manifest.
      - Embedded self-executing Python audit runner (`python3 doc.pdf`).
    """
    reg = registry or EpistemicTombstoneRegistry()
    for r in records:
        reg.tombstones[r.target_id] = r

    stream_lines = [
        "q",
        # Page background
        "0.04 0.05 0.07 rg",
        "0 0 612 792 re f",
        # Banner
        "0.08 0.10 0.14 rg",
        "30 710 552 60 re f",
        "0.20 0.25 0.35 RG 1 w",
        "30 710 552 60 re S",
        "BT",
        "/F1 16 Tf",
        "1.0 1.0 1.0 rg",
        "45 745 Td",
        "(%# BLACK-HEART: EPISTEMIC RETIREMENT TOMBSTONE STELE) Tj",
        "/F1 10 Tf",
        "0.6 0.7 0.85 rg",
        "0 -20 Td",
        "(CONTROLLED-FORGETTING-0.1 | Epistemic Retirement & Negative Space Ledger) Tj",
        "ET",
    ]

    y = 690
    card_h = 78
    for i, r in enumerate(records):
        if y - card_h < 60:
            break
        tid_clean = _sanitize_ascii(r.target_id[:28])
        digest_clean = _sanitize_ascii(r.target_digest[:20])
        mode_clean = _sanitize_ascii(r.mode.value)
        loss_clean = _sanitize_ascii(r.loss_declaration[:65])
        rep_clean = _sanitize_ascii((r.replacement_id or "NONE")[:20])
        cov_pct = f"{r.negative_space_coverage * 100.0:.1f}%"
        gas_str = f"+{r.atp_gas_recovered} ATP"

        if r.mode == RetirementMode.REFUTED:
            border_col = "0.90 0.20 0.25"
            bg_col = "0.14 0.05 0.06"
        elif r.mode == RetirementMode.SUPERSEDED:
            border_col = "0.85 0.65 0.15"
            bg_col = "0.12 0.09 0.04"
        elif r.mode == RetirementMode.DEPRECATED:
            border_col = "0.75 0.35 0.85"
            bg_col = "0.10 0.05 0.12"
        else:
            border_col = "0.50 0.55 0.65"
            bg_col = "0.07 0.08 0.10"

        stream_lines.extend([
            f"{bg_col} rg",
            f"30 {y - card_h} 552 {card_h} re f",
            f"{border_col} RG 1.5 w",
            f"30 {y - card_h} 552 {card_h} re S",
            "BT",
            "/F1 11 Tf",
            "1.0 1.0 1.0 rg",
            f"45 {y - 20} Td",
            f"([TOMBSTONE] {tid_clean} -> {mode_clean}) Tj",
            "/F1 8 Tf",
            "0.75 0.80 0.85 rg",
            "0 -16 Td",
            f"(Digest: {digest_clean}... | Replacement: {rep_clean} | Gas: {gas_str} | Pruned: {cov_pct}) Tj",
            "0 -14 Td",
            f"(Loss (I4): {loss_clean}) Tj",
            "0 -13 Td",
            f"(Author: {r.author_pk_hex[:24]}... | Timestamp: {r.timestamp_utc}) Tj",
            "ET",
        ])
        y -= (card_h + 12)

    stream_lines.extend([
        "BT",
        "/F1 8 Tf",
        "0.40 0.45 0.55 rg",
        "30 25 Td",
        "(Invariant I3 Active: Implicit resurrection prohibited. Re-adoption requires signed ReAdoptionRecord.) Tj",
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

    manifest_json = json.dumps(reg.to_dict(), sort_keys=True)
    manifest_line = (
        b"# %" + bytes([0xf0, 0x9f, 0x96, 0xa4])
        + b" RETIREMENT_MANIFEST: " + manifest_json.encode("utf-8") + b"\n"
    )

    py_runner = f"""
# coding: latin-1
import sys, json, os

cwd = os.getcwd()
if cwd not in sys.path:
    sys.path.insert(0, cwd)

def audit_retirement():
    print("\\033[1;36m" + "=" * 70)
    print("  %# CONTROLLED FORGETTING AUDITOR (CONTROLLED-FORGETTING-0.1)")
    print("=" * 70 + "\\033[0m")
    with open(__file__, 'rb') as f:
        data = f.read()
    prefix = bytes([0x23, 0x20, 0x25, 0xf0, 0x9f, 0x96, 0xa4]) + b" RETIREMENT_MANIFEST: "
    idx = data.rfind(prefix)
    if idx == -1:
        print("\\033[1;31m[-] No retirement manifest found.\\033[0m")
        sys.exit(1)
    end = data.find(b"\\n", idx)
    reg_json = json.loads(data[idx + len(prefix):end].decode('utf-8'))
    import controlled_forgetting
    try:
        reg = controlled_forgetting.EpistemicTombstoneRegistry.from_dict(reg_json)
    except ValueError as e:
        # A record whose signature does not cover its body is refused before
        # any of its fields are printed as audited.
        print("\\033[1;31m[!] Refusing retirement manifest: " + str(e) + "\\033[0m")
        sys.exit(1)
    print(f"[*] Audited {{len(reg.tombstones)}} tombstones and {{len(reg.readoptions)}} re-adoptions.\\n")
    all_valid = True
    for tid, t in reg.tombstones.items():
        if not t.verify_signature():
            print(f"\\033[1;31m[!] Signature INVALID for tombstone '{{tid}}'\\033[0m")
            all_valid = False
        else:
            status = reg.get_admission_status(tid).value
            print(f"\\033[1;33m[TOMBSTONE] '{{tid}}' -> {{t.mode.value}} (Status: {{status}})\\033[0m")
            print(f"  Loss: '{{t.loss_declaration}}' | Negative space: {{t.negative_space_coverage * 100:.1f}}% | Gas reclaimed: +{{t.atp_gas_recovered}} ATP")
    print("\\033[1;36m" + "=" * 70 + "\\033[0m")
    if all_valid:
        print("\\033[1;32m[+] All retirement tombstones cryptographically verified.\\033[0m")
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    audit_retirement()
"""

    header_text = (
        f"#!{sys.executable}\n"
        "# coding: latin-1\n"
        "# ============================================================================\n"
        "# %# PROJECT BLACK-HEART: EPISTEMIC RETIREMENT TOMBSTONE STELE\n"
        "# ============================================================================\n"
        "r'''\n"
    ).encode("latin-1")

    polyglot = header_text + body + xref + trailer + manifest_line + b"'''\n" + py_runner.encode("latin-1")
    with open(output_path, "wb") as f:
        f.write(polyglot)
    return polyglot


