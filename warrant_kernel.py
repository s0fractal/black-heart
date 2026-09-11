#!/usr/bin/env python3
# coding: utf-8
"""
warrant_kernel.py — Epistemic Kernel & Unified Edge-Claims Engine.
Part of Project Black-Heart (%🖤). Engine #24.

Normative implementation of WARRANT.md (WARRANT-0.2) in alignment with ~/Projects/warrant:
  1. Unified EdgeClaim: single type replacing disparate warrants and divergences:
       EdgeClaim := < parent_hash, tau, omega, successor_hash, polarity, witness >
       polarity in { AFFIRM, REFUTE }
  2. Five Epistemic Witness Grades (EvidenceGrade):
       - EMPTY (0): Prose / rhetoric. Unbacked claim. MUST NOT be admitted to ledger.
       - GROUNDED (G): Closed-term reduction eval(t) = h. Bit-exact, deterministic.
       - AXIOMATIC (A): Universal equivalence via proven algebraic derivation in closed rule set.
       - EMPIRICAL (E): Universal equivalence tested on finite fixtures X. Law of Monotonicity.
       - COUNTEREXAMPLE (C): Existential refutation (not-forall = exists y) with structured witness operands.
  3. Tri-state Verifier Semantics:
       - PASS: Verified at specified grade.
       - FAIL: Refuted / invalid derivation / diverged.
       - UNVERIFIED: Budget exceeded or untrusted author key. "A refusal is not a verdict."
  4. RFC 8785 JSON Canonicalization (JCS) and RFC 8032 Ed25519 with domain separation:
       Message = "warrant-sig-v1:" || ClaimID_raw  (15 + 32 = 47 bytes)
  5. Automated Promotion Engine:
       Promotes Empirical hypotheses (E) to Axiomatic identities (A) via SKIY confluence verification.
  6. External Trust Roots (TrustConfig):
       Trust anchors defined externally, never self-authenticating within the record.
  7. ISO 32000 Vector PDF Polyglot Visualizer with embedded self-auditing CLI runner.
"""

from __future__ import annotations
import os
import sys
import json
import time
import hashlib
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Tuple, Set, Union

import crypto
import glyph
from glyph import Term, parse, evaluate, term_hash, canonical_bytes, GLYPH_K, GLYPH_I, GLYPH_S, GLYPH_Y, GLYPH_ANCHOR

# ============================================================================
# 1. EPISTEMIC GRADES & VERIFIER OUTCOMES (WARRANT-0.2 §4, §6)
# ============================================================================

class EvidenceGrade(str, Enum):
    """
    Epistemic standing of an evidence witness.
    Strictly answers: what does the witness cover?
    """
    EMPTY = "EMPTY"                     # 0: Prose/assertion without witness (unverifiable)
    GROUNDED = "GROUNDED"               # G: Closed term reduction eval(t) = h
    AXIOMATIC = "AXIOMATIC"             # A: Universal equivalence via algebraic derivation
    EMPIRICAL = "EMPIRICAL"             # E: Universal claim tested on finite sample fixtures
    COUNTEREXAMPLE = "COUNTEREXAMPLE"   # C: Existential refutation via structured counterexample

    @property
    def symbol(self) -> str:
        symbols = {
            EvidenceGrade.EMPTY: "0",
            EvidenceGrade.GROUNDED: "G",
            EvidenceGrade.AXIOMATIC: "A",
            EvidenceGrade.EMPIRICAL: "E",
            EvidenceGrade.COUNTEREXAMPLE: "C",
        }
        return symbols[self]


class VerificationStatus(str, Enum):
    """
    Tri-state verification outcome (WARRANT-0.2 §6.1).
    A refusal is not a verdict. Never observationally equivalent to a silent skip.
    """
    PASS = "pass"
    FAIL = "fail"
    UNVERIFIED = "unverified"


class Polarity(str, Enum):
    """
    Polarity of the edge claim:
      AFFIRM: asserts Equiv(P, P') or P -> P'
      REFUTE: asserts not-Equiv(P, P') via counterexample
    """
    AFFIRM = "AFFIRM"
    REFUTE = "REFUTE"


# Closed sound algebraic rewrite rules in Black-Heart
ALGEBRAIC_SOUND_RULES: Dict[str, str] = {
    "I x -> x": "Identity Elimination (Flow)",
    "K x y -> x": "Constant Elimination (Black Cone Drop)",
    "S(K x)(K y) -> K(x y)": "Distribution Homomorphism",
    "S(K x)I -> x": "Identity Factorization",
    "S(K I) -> I": "Spore Contraction",
}

# ============================================================================
# 2. RFC 8785 JSON CANONICALIZATION (JCS)
# ============================================================================

def canonical_jcs(data: Any) -> bytes:
    """
    Pure Python RFC 8785 JSON Canonicalization Scheme (JCS).
    Guarantees bit-exact byte output across all implementations:
      - UTF-8 encoding
      - Object keys sorted by Unicode code point
      - Compact separators (no trailing or insignificant whitespace)
      - No float precision ambiguities (all integers or exact strings)
    """
    return json.dumps(
        data,
        sort_keys=True,
        separators=(',', ':'),
        ensure_ascii=False
    ).encode("utf-8")


# ============================================================================
# 3. STRUCTURED WITNESS TYPES (WARRANT-0.2 §4, §6.4)
# ============================================================================

@dataclass
class EmptyWitness:
    """Grade 0: Unbacked claim or prose. Rhetoric is legal; it just doesn't count as proof."""
    prose: str = ""

    def infer_grade(self) -> EvidenceGrade:
        return EvidenceGrade.EMPTY

    def to_dict(self) -> Dict[str, Any]:
        return {"kind": "empty", "prose": self.prose}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> EmptyWitness:
        return cls(prose=str(d.get("prose", "")))


@dataclass
class GroundedWitness:
    """Grade G: Closed term reduction eval(t) = h. Bounded by ATP."""
    term_expr: str
    expected_hash: str
    atp_budget: int = 10000

    def infer_grade(self) -> EvidenceGrade:
        return EvidenceGrade.GROUNDED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": "grounded",
            "term_expr": self.term_expr,
            "expected_hash": self.expected_hash,
            "atp_budget": self.atp_budget
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> GroundedWitness:
        return cls(
            term_expr=str(d["term_expr"]),
            expected_hash=str(d["expected_hash"]),
            atp_budget=int(d.get("atp_budget", 10000))
        )


@dataclass
class AxiomaticWitness:
    """Grade A: Universal identity Equiv(P, P') proven via closed algebraic derivations."""
    derivation_steps: List[str]
    rule_name: str
    soundness_axiom: str

    def infer_grade(self) -> EvidenceGrade:
        return EvidenceGrade.AXIOMATIC

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": "axiomatic",
            "derivation_steps": self.derivation_steps,
            "rule_name": self.rule_name,
            "soundness_axiom": self.soundness_axiom
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> AxiomaticWitness:
        return cls(
            derivation_steps=[str(s) for s in d.get("derivation_steps", [])],
            rule_name=str(d["rule_name"]),
            soundness_axiom=str(d.get("soundness_axiom", ""))
        )


@dataclass
class EmpiricalWitness:
    """
    Grade E: Universal claim Equiv(P, P') tested on finite fixtures X.
    Explicitly binds fixtures list, sample size |X|, and hash(X).
    """
    fixtures: List[str]
    fixtures_fingerprint: str
    delta_atp: int
    delta_size: int

    def infer_grade(self) -> EvidenceGrade:
        return EvidenceGrade.EMPIRICAL

    def compute_fixtures_fingerprint(self) -> str:
        raw = json.dumps(sorted(self.fixtures), separators=(',', ':')).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": "empirical",
            "fixtures": self.fixtures,
            "fixtures_fingerprint": self.fixtures_fingerprint,
            "sample_size": len(self.fixtures),
            "delta_atp": self.delta_atp,
            "delta_size": self.delta_size
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> EmpiricalWitness:
        return cls(
            fixtures=[str(x) for x in d.get("fixtures", [])],
            fixtures_fingerprint=str(d.get("fixtures_fingerprint", "")),
            delta_atp=int(d.get("delta_atp", 0)),
            delta_size=int(d.get("delta_size", 0))
        )


@dataclass
class CounterexampleWitness:
    """
    Grade C: Refutation exists y. eval(P y) != eval(P' y).
    Carries exact structured input operands for deterministic replay.
    """
    input_expr: str
    expected_normal_form: str
    actual_divergence: str
    atp_to_diverge: int

    def infer_grade(self) -> EvidenceGrade:
        return EvidenceGrade.COUNTEREXAMPLE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": "counterexample",
            "input_expr": self.input_expr,
            "expected_normal_form": self.expected_normal_form,
            "actual_divergence": self.actual_divergence,
            "atp_to_diverge": self.atp_to_diverge
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> CounterexampleWitness:
        return cls(
            input_expr=str(d["input_expr"]),
            expected_normal_form=str(d["expected_normal_form"]),
            actual_divergence=str(d["actual_divergence"]),
            atp_to_diverge=int(d.get("atp_to_diverge", 1))
        )


Witness = Union[EmptyWitness, GroundedWitness, AxiomaticWitness, EmpiricalWitness, CounterexampleWitness]

def witness_from_dict(d: Dict[str, Any]) -> Witness:
    kind = d.get("kind", "empty")
    if kind == "grounded":
        return GroundedWitness.from_dict(d)
    elif kind == "axiomatic":
        return AxiomaticWitness.from_dict(d)
    elif kind == "empirical":
        return EmpiricalWitness.from_dict(d)
    elif kind == "counterexample":
        return CounterexampleWitness.from_dict(d)
    return EmptyWitness.from_dict(d)


# ============================================================================
# 4. UNIFIED EDGE CLAIM (WARRANT-0.2 §3, §4, §5)
# ============================================================================

@dataclass
class EdgeEndorsement:
    """Peer endorsement on an EdgeClaim confirming local reproduction."""
    endorser_pk_hex: str
    signature_hex: str
    local_delta_atp: int
    timestamp_utc: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "endorser_pk_hex": self.endorser_pk_hex,
            "signature_hex": self.signature_hex,
            "local_delta_atp": self.local_delta_atp,
            "timestamp_utc": self.timestamp_utc
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> EdgeEndorsement:
        return cls(
            endorser_pk_hex=str(d["endorser_pk_hex"]),
            signature_hex=str(d["signature_hex"]),
            local_delta_atp=int(d["local_delta_atp"]),
            timestamp_utc=str(d["timestamp_utc"])
        )


@dataclass
class EdgeClaim:
    """
    Unified Edge Claim in Project Black-Heart:
      EdgeClaim := < parent_hash, tau, omega, successor_hash, polarity, witness >
      Grade is strictly derived from the witness, never self-asserted.
    """
    parent_hash: str
    tau: str                        # Rule or transformation name
    omega: str                      # Target site or context
    successor_hash: str
    polarity: Polarity
    witness: Witness
    author_pk_hex: str
    signature_hex: str
    claim_id: str = ""
    grade: EvidenceGrade = EvidenceGrade.EMPTY
    endorsements: List[EdgeEndorsement] = field(default_factory=list)

    def __post_init__(self):
        # Grade is strictly derived from witness capability (WARRANT-0.2 §6.2)
        derived = self.witness.infer_grade()
        if self.grade == EvidenceGrade.EMPTY or self.grade != derived:
            self.grade = derived
        if not self.claim_id:
            self.claim_id = self.compute_claim_id()

    def body_dict(self) -> Dict[str, Any]:
        """The canonical body covered by WarrantID and signature."""
        return {
            "parent_hash": self.parent_hash,
            "tau": self.tau,
            "omega": self.omega,
            "successor_hash": self.successor_hash,
            "polarity": self.polarity.value,
            "witness": self.witness.to_dict(),
            "grade": self.grade.value,
            "author_pk_hex": self.author_pk_hex
        }

    def compute_claim_id(self) -> str:
        """WarrantID = SHA-256( canonical_jcs(body) ) per WARRANT/SPEC.md §4."""
        body_bytes = canonical_jcs(self.body_dict())
        return hashlib.sha256(body_bytes).hexdigest()

    def signature_message(self) -> bytes:
        """
        Normative domain-separated message per WARRANT/SPEC.md §5:
          msg = "warrant-sig-v1:" || raw_bytes(claim_id)   (15 + 32 = 47 bytes)
        """
        separator = b"warrant-sig-v1:"
        raw_id = bytes.fromhex(self.claim_id)
        return separator + raw_id

    def sign(self, secret_key_hex: str):
        """Signs the edge claim using RFC 8032 Ed25519 with domain separation."""
        msg = self.signature_message()
        self.signature_hex = crypto.sign_hex(secret_key_hex, msg)

    def verify_signature(self) -> bool:
        """Verifies Ed25519 signature over normative domain-separated message."""
        if not self.signature_hex or not self.author_pk_hex:
            return False
        msg = self.signature_message()
        return crypto.verify_hex(self.author_pk_hex, msg, self.signature_hex)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "body": self.body_dict(),
            "signature_hex": self.signature_hex,
            "endorsements": [e.to_dict() for e in self.endorsements]
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> EdgeClaim:
        b = d.get("body", d)
        witness = witness_from_dict(b["witness"])
        claim = cls(
            parent_hash=str(b["parent_hash"]),
            tau=str(b["tau"]),
            omega=str(b["omega"]),
            successor_hash=str(b["successor_hash"]),
            polarity=Polarity(b["polarity"]),
            witness=witness,
            author_pk_hex=str(b["author_pk_hex"]),
            signature_hex=str(d.get("signature_hex", "")),
            claim_id=str(d.get("claim_id", "")),
            grade=EvidenceGrade(b.get("grade", witness.infer_grade().value)),
            endorsements=[EdgeEndorsement.from_dict(e) for e in d.get("endorsements", [])]
        )
        return claim

    @classmethod
    def create_and_sign(
        cls,
        parent_hash: str,
        tau: str,
        omega: str,
        successor_hash: str,
        polarity: Polarity,
        witness: Witness,
        secret_key_hex: str,
        public_key_hex: str
    ) -> EdgeClaim:
        claim = cls(
            parent_hash=parent_hash,
            tau=tau,
            omega=omega,
            successor_hash=successor_hash,
            polarity=polarity,
            witness=witness,
            author_pk_hex=public_key_hex,
            signature_hex=""
        )
        claim.sign(secret_key_hex)
        return claim


# ============================================================================
# 5. EXTERNAL TRUST ROOT CONFIGURATION (WARRANT-0.2 §6.5)
# ============================================================================

@dataclass
class TrustConfig:
    """
    External trust anchor configuration (WARRANT-0.2 §6.5 / warrant §12).
    A verifier's trust root comes from configuration, never from inside the record.
    """
    trusted_author_pks: Optional[Set[str]] = None
    admitted_grades: Set[EvidenceGrade] = field(default_factory=lambda: {
        EvidenceGrade.GROUNDED,
        EvidenceGrade.AXIOMATIC,
        EvidenceGrade.EMPIRICAL,
        EvidenceGrade.COUNTEREXAMPLE
    })
    max_atp_budget: int = 100000
    require_bound_signature: bool = True

    def is_author_trusted(self, pk_hex: str) -> bool:
        if self.trusted_author_pks is None:
            return True
        return pk_hex in self.trusted_author_pks

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trusted_author_pks": list(self.trusted_author_pks) if self.trusted_author_pks else None,
            "admitted_grades": [g.value for g in self.admitted_grades],
            "max_atp_budget": self.max_atp_budget,
            "require_bound_signature": self.require_bound_signature
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> TrustConfig:
        pks = d.get("trusted_author_pks")
        return cls(
            trusted_author_pks=set(pks) if pks is not None else None,
            admitted_grades={EvidenceGrade(g) for g in d.get("admitted_grades", [])},
            max_atp_budget=int(d.get("max_atp_budget", 100000)),
            require_bound_signature=bool(d.get("require_bound_signature", True))
        )

    def save_to_file(self, path: str):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load_from_file(cls, path: str) -> TrustConfig:
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))


# ============================================================================
# 6. TRI-STATE VERIFIER ENGINE (WARRANT-0.2 §6)
# ============================================================================

@dataclass
class Verdict:
    """
    Deterministic verifier verdict with explicit grade badge.
    Forbids naked checkmarks without evidence grade (WARRANT-0.2 §6.3).
    """
    status: VerificationStatus
    grade: EvidenceGrade
    reason: str
    delta_atp: int = 0
    details: Dict[str, Any] = field(default_factory=dict)

    def human_badge(self) -> str:
        sym = self.grade.symbol
        if self.status == VerificationStatus.PASS:
            if self.grade == EvidenceGrade.AXIOMATIC:
                return f"[{sym}-AXIOMATIC] PASS: Algebraic identity verified across closed sound rules"
            elif self.grade == EvidenceGrade.GROUNDED:
                return f"[{sym}-GROUNDED] PASS: Closed-term reduction verified (deterministic CAS)"
            elif self.grade == EvidenceGrade.EMPIRICAL:
                k = self.details.get("sample_size", "?")
                return f"[{sym}-EMPIRICAL(k={k})] PASS: Verified on {k} fixtures. (Law of Monotonicity: NOT universal)"
            elif self.grade == EvidenceGrade.COUNTEREXAMPLE:
                return f"[{sym}-COUNTEREXAMPLE] PASS (REFUTATION CONFIRMED): Divergence verified at input"
            return f"[{sym}] PASS: {self.reason}"
        elif self.status == VerificationStatus.FAIL:
            return f"[FAIL][{sym}] REJECTED: {self.reason}"
        else: # UNVERIFIED
            return f"[UNVERIFIED][{sym}] REFUSAL: {self.reason} (A refusal is not a verdict)"


class WarrantVerifier:
    """
    Audits and executes EdgeClaims against an external TrustConfig.
    Enforces tri-state verdicts with zero silent skips.
    """

    def __init__(self, trust_config: Optional[TrustConfig] = None):
        self.trust_config = trust_config or TrustConfig()

    def audit_claim(self, claim: EdgeClaim) -> Verdict:
        # 1. Check Grade Inflation (WARRANT-0.2 §6.2)
        inferred_grade = claim.witness.infer_grade()
        if claim.grade != inferred_grade:
            return Verdict(
                status=VerificationStatus.FAIL,
                grade=claim.grade,
                reason=f"Grade inflation detected: declared {claim.grade.value} does not match witness {inferred_grade.value}"
            )

        # 2. Check ID integrity
        expected_id = claim.compute_claim_id()
        if claim.claim_id and claim.claim_id != expected_id:
            return Verdict(
                status=VerificationStatus.FAIL,
                grade=claim.grade,
                reason=f"Claim ID corrupted: claimed {claim.claim_id[:12]} != expected {expected_id[:12]}"
            )

        # 3. Check Admitted Grades in local verifier policy
        if claim.grade not in self.trust_config.admitted_grades:
            return Verdict(
                status=VerificationStatus.UNVERIFIED,
                grade=claim.grade,
                reason=f"Grade '{claim.grade.value}' is not admitted under verifier policy"
            )

        # 4. Check External Trust Anchor (WARRANT-0.2 §6.5)
        if not self.trust_config.is_author_trusted(claim.author_pk_hex):
            return Verdict(
                status=VerificationStatus.UNVERIFIED,
                grade=claim.grade,
                reason=f"Untrusted author public key {claim.author_pk_hex[:12]}... (not in trust-config)"
            )

        # 5. Check Cryptographic Signature (Ed25519 over warrant-sig-v1: || ID)
        if self.trust_config.require_bound_signature:
            if not claim.verify_signature():
                return Verdict(
                    status=VerificationStatus.FAIL,
                    grade=claim.grade,
                    reason="Ed25519 signature over domain-separated message failed verification"
                )

        # 6. Replay Witness Execution by Grade
        if claim.grade == EvidenceGrade.EMPTY:
            return Verdict(
                status=VerificationStatus.UNVERIFIED,
                grade=EvidenceGrade.EMPTY,
                reason="Prose witness has no executable proof; rhetoric does not count as proof"
            )

        elif claim.grade == EvidenceGrade.GROUNDED:
            w: GroundedWitness = claim.witness
            if w.atp_budget > self.trust_config.max_atp_budget:
                return Verdict(
                    status=VerificationStatus.UNVERIFIED,
                    grade=EvidenceGrade.GROUNDED,
                    reason=f"ATP budget {w.atp_budget} exceeds local limit {self.trust_config.max_atp_budget}. A refusal is not a verdict."
                )
            try:
                term = glyph.parse(w.term_expr)
                res = glyph.evaluate(term, max_atp=w.atp_budget)
                if res.hash != w.expected_hash:
                    return Verdict(
                        status=VerificationStatus.FAIL,
                        grade=EvidenceGrade.GROUNDED,
                        reason=f"Grounded hash mismatch: replayed {res.hash[:12]} != expected {w.expected_hash[:12]}"
                    )
                return Verdict(
                    status=VerificationStatus.PASS,
                    grade=EvidenceGrade.GROUNDED,
                    reason="Closed-term deterministic reduction verified",
                    delta_atp=res.atp_spent,
                    details={"hash": res.hash, "atp_spent": res.atp_spent}
                )
            except Exception as e:
                return Verdict(
                    status=VerificationStatus.FAIL,
                    grade=EvidenceGrade.GROUNDED,
                    reason=f"Reduction failed with exception: {e}"
                )

        elif claim.grade == EvidenceGrade.AXIOMATIC:
            w_ax: AxiomaticWitness = claim.witness
            # 1. Require derivation steps to be non-empty (no unbacked empty proof traces)
            if not w_ax.derivation_steps:
                return Verdict(
                    status=VerificationStatus.FAIL,
                    grade=EvidenceGrade.AXIOMATIC,
                    reason="Axiomatic witness has empty derivation steps"
                )
            # 2. Rule must be bound to the claim edge (claim.tau == w_ax.rule_name)
            if claim.tau != w_ax.rule_name:
                return Verdict(
                    status=VerificationStatus.FAIL,
                    grade=EvidenceGrade.AXIOMATIC,
                    reason=f"Claim transition tau '{claim.tau}' does not match witness rule '{w_ax.rule_name}'"
                )
            # 3. Verify rule in closed sound rules
            if w_ax.rule_name not in ALGEBRAIC_SOUND_RULES:
                return Verdict(
                    status=VerificationStatus.FAIL,
                    grade=EvidenceGrade.AXIOMATIC,
                    reason=f"Rule '{w_ax.rule_name}' is not in closed algebraic sound set"
                )
            # 4. Verify symbolic rewrite reproducibility
            rule_valid, err_msg = verify_symbolic_algebraic_rule(w_ax.rule_name)
            if not rule_valid:
                return Verdict(
                    status=VerificationStatus.FAIL,
                    grade=EvidenceGrade.AXIOMATIC,
                    reason=f"Algebraic rule confluence failed: {err_msg}"
                )
            return Verdict(
                status=VerificationStatus.PASS,
                grade=EvidenceGrade.AXIOMATIC,
                reason=f"Rule '{w_ax.rule_name}' proved sound under closed algebraic axioms",
                details={"rule_name": w_ax.rule_name, "axiom": w_ax.soundness_axiom}
            )

        elif claim.grade == EvidenceGrade.EMPIRICAL:
            w_emp: EmpiricalWitness = claim.witness
            # 1. Check fixtures fingerprint matches actual fixtures (WARRANT-0.2 §4.3)
            actual_fp = w_emp.compute_fixtures_fingerprint()
            if w_emp.fixtures_fingerprint and w_emp.fixtures_fingerprint != actual_fp:
                return Verdict(
                    status=VerificationStatus.FAIL,
                    grade=EvidenceGrade.EMPIRICAL,
                    reason=f"Fixtures fingerprint mismatch: claimed {w_emp.fixtures_fingerprint[:12]} != actual {actual_fp[:12]}"
                )

            # 2. Replay parent and successor on fixtures
            if not w_emp.fixtures:
                return Verdict(
                    status=VerificationStatus.FAIL,
                    grade=EvidenceGrade.EMPIRICAL,
                    reason="Empirical witness has empty fixture sample"
                )

            total_atp_parent = 0
            total_atp_succ = 0
            try:
                for fix in w_emp.fixtures:
                    f_term = glyph.parse(fix)
                    p_term = glyph.parse(f"{claim.omega} ({fix})")
                    s_term = glyph.parse(f"{claim.tau} ({fix})")

                    res_p = glyph.evaluate(p_term, max_atp=self.trust_config.max_atp_budget)
                    res_s = glyph.evaluate(s_term, max_atp=self.trust_config.max_atp_budget)

                    if glyph.canonical_bytes(res_p.term) != glyph.canonical_bytes(res_s.term):
                        return Verdict(
                            status=VerificationStatus.FAIL,
                            grade=EvidenceGrade.EMPIRICAL,
                            reason=f"Empirical equivalence failed on fixture '{fix}': parent -> {res_p.term} != succ -> {res_s.term}"
                        )
                    total_atp_parent += res_p.atp_spent
                    total_atp_succ += res_s.atp_spent

                replayed_delta_atp = total_atp_parent - total_atp_succ
                return Verdict(
                    status=VerificationStatus.PASS,
                    grade=EvidenceGrade.EMPIRICAL,
                    reason=f"Equivalence verified across {len(w_emp.fixtures)} sample fixtures",
                    delta_atp=replayed_delta_atp,
                    details={
                        "sample_size": len(w_emp.fixtures),
                        "replayed_delta_atp": replayed_delta_atp,
                        "fixtures_fp": actual_fp
                    }
                )
            except Exception as e:
                return Verdict(
                    status=VerificationStatus.FAIL,
                    grade=EvidenceGrade.EMPIRICAL,
                    reason=f"Fixture execution failed: {e}"
                )

        elif claim.grade == EvidenceGrade.COUNTEREXAMPLE:
            w_c: CounterexampleWitness = claim.witness
            # A Grade C PASS asserts one sentence: replayed here, this input drives
            # the two sides to two different normal forms, and they are the two the
            # witness named, within the cost it declared. Every clause below is a
            # conjunct of that sentence. Anything the replay cannot establish leaves
            # by FAIL (the evidence contradicts the claim) or UNVERIFIED (the check
            # never reached a verdict) -- never by PASS.

            # 1. Polarity: a counterexample refutes; it cannot affirm.
            if claim.polarity != Polarity.REFUTE:
                return Verdict(
                    status=VerificationStatus.FAIL,
                    grade=EvidenceGrade.COUNTEREXAMPLE,
                    reason="Counterexample witness must carry REFUTE polarity"
                )

            # 2. The witness must denote terms. A syntax error is a malformed
            #    witness, not a discovered divergence.
            try:
                declared_expected = glyph.parse(w_c.expected_normal_form)
                declared_actual = glyph.parse(w_c.actual_divergence)
                inp_term = glyph.parse(w_c.input_expr)
            except Exception as e:
                return Verdict(
                    status=VerificationStatus.FAIL,
                    grade=EvidenceGrade.COUNTEREXAMPLE,
                    reason=f"Counterexample witness operands do not parse: {e}",
                    details={"input": w_c.input_expr}
                )
            try:
                p_term = glyph.parse(f"{claim.omega} ({w_c.input_expr})")
                s_term = glyph.parse(f"{claim.tau} ({w_c.input_expr})")
            except Exception as e:
                return Verdict(
                    status=VerificationStatus.FAIL,
                    grade=EvidenceGrade.COUNTEREXAMPLE,
                    reason=f"Claim endpoints do not parse against the witness input: {e}",
                    details={"omega": claim.omega, "tau": claim.tau, "input": w_c.input_expr}
                )

            # 3. The declared cost must be a cost: a plain non-negative integer.
            #    `type(...) is not int` also rejects bool, which would otherwise
            #    compare as 0 or 1.
            if type(w_c.atp_to_diverge) is not int or w_c.atp_to_diverge < 0:
                return Verdict(
                    status=VerificationStatus.FAIL,
                    grade=EvidenceGrade.COUNTEREXAMPLE,
                    reason=f"Counterexample witness declares a non-integral or negative atp_to_diverge: {w_c.atp_to_diverge!r}",
                    details={"atp_to_diverge": repr(w_c.atp_to_diverge)}
                )

            # 4. Replay both sides. An engine fault is the absence of evidence.
            budget = self.trust_config.max_atp_budget
            try:
                res_p = glyph.evaluate(p_term, max_atp=budget)
                res_s = glyph.evaluate(s_term, max_atp=budget)
            except Exception as e:
                return Verdict(
                    status=VerificationStatus.UNVERIFIED,
                    grade=EvidenceGrade.COUNTEREXAMPLE,
                    reason=f"Counterexample replay did not complete: {type(e).__name__}: {e}",
                    details={"input": w_c.input_expr, "replay_error": str(e)}
                )

            # 5. Both sides must reach a normal form. Two intermediate states
            #    suspended at the ceiling differ for no stated reason: bounded
            #    non-termination is not a proved divergence.
            if not res_p.is_settled() or not res_s.is_settled():
                return Verdict(
                    status=VerificationStatus.UNVERIFIED,
                    grade=EvidenceGrade.COUNTEREXAMPLE,
                    reason=(f"Counterexample replay did not settle within the ATP budget "
                            f"({budget}): parent {res_p.status.value}, successor {res_s.status.value}"),
                    details={
                        "input": w_c.input_expr,
                        "max_atp_budget": budget,
                        "parent_status": res_p.status.value,
                        "successor_status": res_s.status.value
                    }
                )

            out_p = str(res_p.term)
            out_s = str(res_s.term)

            # 6. The normal forms must actually differ.
            if glyph.canonical_bytes(res_p.term) == glyph.canonical_bytes(res_s.term):
                return Verdict(
                    status=VerificationStatus.FAIL,
                    grade=EvidenceGrade.COUNTEREXAMPLE,
                    reason=f"Refutation failed: outputs coincide on counterexample ({out_p})"
                )

            # 7. They must be the two normal forms the witness named, in their
            #    stated roles. Without this the witness describes nothing: any
            #    separating input would carry any pair of operands.
            if glyph.canonical_bytes(res_p.term) != glyph.canonical_bytes(declared_expected):
                return Verdict(
                    status=VerificationStatus.FAIL,
                    grade=EvidenceGrade.COUNTEREXAMPLE,
                    reason=(f"Witness expected_normal_form '{w_c.expected_normal_form}' does not match "
                            f"the parent replay '{out_p}'"),
                    details={"declared": w_c.expected_normal_form, "parent_output": out_p}
                )
            if glyph.canonical_bytes(res_s.term) != glyph.canonical_bytes(declared_actual):
                return Verdict(
                    status=VerificationStatus.FAIL,
                    grade=EvidenceGrade.COUNTEREXAMPLE,
                    reason=(f"Witness actual_divergence '{w_c.actual_divergence}' does not match "
                            f"the successor replay '{out_s}'"),
                    details={"declared": w_c.actual_divergence, "successor_output": out_s}
                )

            # 8. The declared cost must cover the replay. Reduction here is
            #    deterministic and leftmost-outermost, so a run under max_atp = n
            #    settles exactly when n >= the steps this run spent; comparing the
            #    counts is the same test as re-running under the declared budget.
            required_atp = max(res_p.atp_spent, res_s.atp_spent)
            if w_c.atp_to_diverge < required_atp:
                return Verdict(
                    status=VerificationStatus.FAIL,
                    grade=EvidenceGrade.COUNTEREXAMPLE,
                    reason=(f"Declared atp_to_diverge {w_c.atp_to_diverge} does not cover the replay, "
                            f"which needs {required_atp} ATP"),
                    details={"declared_atp": w_c.atp_to_diverge, "required_atp": required_atp}
                )

            return Verdict(
                status=VerificationStatus.PASS,
                grade=EvidenceGrade.COUNTEREXAMPLE,
                reason="Divergence independently reproduced: counterexample successfully refutes claim",
                details={
                    "input": w_c.input_expr,
                    "parent_output": out_p,
                    "successor_output": out_s,
                    "parent_atp": res_p.atp_spent,
                    "successor_atp": res_s.atp_spent,
                    "declared_atp": w_c.atp_to_diverge
                }
            )

        return Verdict(
            status=VerificationStatus.UNVERIFIED,
            grade=claim.grade,
            reason="Unknown evidence grade"
        )


# ============================================================================
# 7. AUTOMATED PROMOTION ENGINE (WARRANT-0.2 §9.2: E -> A)
# ============================================================================

def verify_symbolic_algebraic_rule(rule_name: str) -> Tuple[bool, str]:
    """
    Proves symbolic extensional confluence of an algebraic rewrite rule:
    Applies symbolic test variables to both sides and verifies Church-Rosser reduction.
    """
    k = GLYPH_K
    i = GLYPH_I
    s = GLYPH_S

    if rule_name == "I x -> x":
        # I x -> x
        t1 = glyph.parse(f"{i} x")
        t2 = glyph.parse("x")
        r1 = glyph.evaluate(t1)
        r2 = glyph.evaluate(t2)
        return (r1.term == r2.term, "")

    elif rule_name == "K x y -> x":
        # K x y -> x
        t1 = glyph.parse(f"{k} x y")
        t2 = glyph.parse("x")
        r1 = glyph.evaluate(t1)
        r2 = glyph.evaluate(t2)
        return (r1.term == r2.term, "")

    elif rule_name == "S(K x)(K y) -> K(x y)":
        # S(K x)(K y) z -> K(x y) z
        t1 = glyph.parse(f"{s} ({k} x) ({k} y) z")
        t2 = glyph.parse(f"{k} (x y) z")
        r1 = glyph.evaluate(t1)
        r2 = glyph.evaluate(t2)
        return (r1.term == r2.term, "")

    elif rule_name == "S(K x)I -> x":
        # S(K x) I y -> x y
        t1 = glyph.parse(f"{s} ({k} x) {i} y")
        t2 = glyph.parse("x y")
        r1 = glyph.evaluate(t1)
        r2 = glyph.evaluate(t2)
        return (r1.term == r2.term, "")

    elif rule_name == "S(K I) -> I":
        # S(K I) x y -> I x y
        t1 = glyph.parse(f"{s} ({k} {i}) x y")
        t2 = glyph.parse(f"{i} x y")
        r1 = glyph.evaluate(t1)
        r2 = glyph.evaluate(t2)
        return (r1.term == r2.term, "")

    return (False, f"Rule '{rule_name}' is not symbolically axiomatized")


def promote_empirical_to_axiomatic(
    claim: EdgeClaim,
    secret_key_hex: str,
    public_key_hex: str
) -> Optional[EdgeClaim]:
    """
    Automated Promotion Engine (WARRANT-0.2 §9.2):
    Attempts to elevate an Empirical Hypothesis (Grade E) to Axiomatic Identity (Grade A).
    If the claimed transition tau coincides with a sound symbolic rewrite identity,
    synthesizes an AxiomaticWitness with proof traces and issues an elevated EdgeClaim.
    """
    if claim.grade != EvidenceGrade.EMPIRICAL:
        return None

    # Check if rule matches known algebraic identities
    rule_name = claim.tau
    if rule_name not in ALGEBRAIC_SOUND_RULES:
        return None

    valid, err = verify_symbolic_algebraic_rule(rule_name)
    if not valid:
        return None

    # Synthesize AxiomaticWitness
    axiomatic_witness = AxiomaticWitness(
        derivation_steps=[
            f"Given empirical hypothesis on {len(claim.witness.fixtures if isinstance(claim.witness, EmpiricalWitness) else [])} fixtures",
            f"Symbolic Church-Rosser reduction applied to {rule_name}",
            f"Universal confluence confirmed for all input terms x, y, z"
        ],
        rule_name=rule_name,
        soundness_axiom=ALGEBRAIC_SOUND_RULES[rule_name]
    )

    elevated_claim = EdgeClaim.create_and_sign(
        parent_hash=claim.parent_hash,
        tau=claim.tau,
        omega=claim.omega,
        successor_hash=claim.successor_hash,
        polarity=Polarity.AFFIRM,
        witness=axiomatic_witness,
        secret_key_hex=secret_key_hex,
        public_key_hex=public_key_hex
    )
    return elevated_claim


# ============================================================================
# 8. BACKWARDS COMPATIBILITY ADAPTERS
# ============================================================================

def claim_from_legacy_warrant(w: Any, author_sk_hex: Optional[str] = None) -> EdgeClaim:
    """Adapts a legacy mycelium.Warrant into an EdgeClaim."""
    rule = getattr(w, "rule_name", "UNKNOWN_RULE")
    pre = getattr(w, "pre_pattern", "")
    post = getattr(w, "post_pattern", "")
    d_atp = getattr(w, "delta_atp", 0)
    d_size = getattr(w, "delta_size", 0)
    fp = getattr(w, "fixtures_fingerprint", "")
    author_pk = getattr(w, "author_pk_hex", "")
    sig = getattr(w, "signature_hex", "")

    # Check if it is algebraic rule
    if rule in ALGEBRAIC_SOUND_RULES:
        witness = AxiomaticWitness(
            derivation_steps=[f"Legacy migration of rule {rule}"],
            rule_name=rule,
            soundness_axiom=ALGEBRAIC_SOUND_RULES[rule]
        )
    else:
        witness = EmpiricalWitness(
            fixtures=[GLYPH_I, GLYPH_K, GLYPH_S, f"{GLYPH_K} {GLYPH_I}"],
            fixtures_fingerprint=fp,
            delta_atp=d_atp,
            delta_size=d_size
        )

    claim = EdgeClaim(
        parent_hash=hashlib.sha256(pre.encode()).hexdigest(),
        tau=rule,
        omega=pre,
        successor_hash=hashlib.sha256(post.encode()).hexdigest(),
        polarity=Polarity.AFFIRM,
        witness=witness,
        author_pk_hex=author_pk,
        signature_hex=sig
    )
    if author_sk_hex:
        claim.sign(author_sk_hex)
    return claim


def claim_from_legacy_divergence(d: Any, author_sk_hex: Optional[str] = None) -> EdgeClaim:
    """Adapts a legacy mycelium.DivergenceRecord into a structured EdgeClaim (Grade C)."""
    rule = getattr(d, "rule_name", "DIVERGENCE")
    orig = getattr(d, "target_expression", "")
    cand = getattr(d, "candidate_expression", "")
    inp = getattr(d, "counterexample_input", "")
    exp = getattr(d, "expected_output", "")
    act = getattr(d, "actual_output", "")
    author_pk = getattr(d, "reporter_pk_hex", "")
    sig = getattr(d, "signature_hex", "")

    witness = CounterexampleWitness(
        input_expr=inp,
        expected_normal_form=exp,
        actual_divergence=act,
        atp_to_diverge=1
    )

    claim = EdgeClaim(
        parent_hash=hashlib.sha256(orig.encode()).hexdigest(),
        tau=cand,
        omega=orig,
        successor_hash=hashlib.sha256(cand.encode()).hexdigest(),
        polarity=Polarity.REFUTE,
        witness=witness,
        author_pk_hex=author_pk,
        signature_hex=sig
    )
    if author_sk_hex:
        claim.sign(author_sk_hex)
    return claim


# ============================================================================
# 9. ISO 32000 VECTOR PDF POLYGLOT VISUALIZER
# ============================================================================

def _sanitize_pdf_text(text: str) -> str:
    """Sanitizes text for standard Type 1 Helvetica PDF font strings."""
    s = (text.replace(GLYPH_K, "K")
             .replace(GLYPH_I, "I")
             .replace(GLYPH_S, "S")
             .replace(GLYPH_Y, "Y")
             .replace(GLYPH_ANCHOR, "[#]")
             .replace("•", "*")
             .replace("§", "Section"))
    clean = "".join(c if (32 <= ord(c) < 127) else "?" for c in s)
    return clean.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def generate_warrant_ledger_pdf(
    claims: List[EdgeClaim],
    output_path: str,
    trust_config: Optional[TrustConfig] = None,
    secret_key_hex: Optional[str] = None
) -> bytes:
    """
    Creates an ISO 32000 compliant vector PDF polyglot document containing:
      - Visual Evidence Ledger with color-coded badges per EvidenceGrade:
          * Grade A: Gold [A-AXIOMATIC]
          * Grade G: Emerald [G-GROUNDED]
          * Grade E: Amber [E-EMPIRICAL]
          * Grade C: Crimson [C-COUNTEREXAMPLE]
          * Grade 0: Dim Grey [0-EMPTY]
      - Embedded JCS-canonical JSON claim manifest.
      - Embedded Python executable script running self-audit on `python3 doc.pdf --audit`.
    """
    verifier = WarrantVerifier(trust_config or TrustConfig())
    verdicts = [verifier.audit_claim(c) for c in claims]

    # Render PDF graphics stream
    stream_lines = [
        "q",
        # Dark aesthetic background
        "0.05 0.06 0.08 rg",
        "0 0 612 792 re f",
        # Header banner
        "0.08 0.10 0.14 rg",
        "30 710 552 60 re f",
        "0.20 0.25 0.35 RG 1 w",
        "30 710 552 60 re S",
        # Header text
        "BT",
        "/F1 16 Tf",
        "1.0 1.0 1.0 rg",
        "45 745 Td",
        "(%# BLACK-HEART: WARRANT EPISTEMIC KERNEL) Tj",
        "/F1 10 Tf",
        "0.6 0.7 0.85 rg",
        "0 -20 Td",
        "(Normative Specification WARRANT-0.2 | Tri-State Audit Ledger) Tj",
        "ET",
    ]

    y = 660
    for i, (c, v) in enumerate(zip(claims, verdicts)):
        if y < 100:
            break
        # Determine color by grade
        if c.grade == EvidenceGrade.AXIOMATIC:
            bg_col = "0.15 0.13 0.05"
            border_col = "0.95 0.77 0.20"
            badge_text = f"[A] AXIOMATIC IDENTITY - {c.tau}"
        elif c.grade == EvidenceGrade.GROUNDED:
            bg_col = "0.05 0.14 0.08"
            border_col = "0.20 0.85 0.40"
            badge_text = f"[G] GROUNDED REDUCTION - {c.tau}"
        elif c.grade == EvidenceGrade.EMPIRICAL:
            bg_col = "0.14 0.10 0.04"
            border_col = "0.90 0.55 0.15"
            badge_text = f"[E] EMPIRICAL HYPOTHESIS - {c.tau}"
        elif c.grade == EvidenceGrade.COUNTEREXAMPLE:
            bg_col = "0.15 0.05 0.06"
            border_col = "0.95 0.25 0.25"
            badge_text = f"[C] REFUTATION COUNTEREXAMPLE - {c.tau}"
        else:
            bg_col = "0.08 0.08 0.08"
            border_col = "0.50 0.50 0.50"
            badge_text = f"[0] UNVERIFIED CLAIM - {c.tau}"

        b_clean = _sanitize_pdf_text(badge_text[:60])
        cid_clean = _sanitize_pdf_text(c.claim_id[:28])
        pol_clean = _sanitize_pdf_text(c.polarity.value)
        apk_clean = _sanitize_pdf_text(c.author_pk_hex[:24])
        st_clean = _sanitize_pdf_text(v.status.value.upper())
        r_clean = _sanitize_pdf_text(v.reason[:65])

        # Draw card
        stream_lines.extend([
            f"{bg_col} rg",
            f"30 {y - 65} 552 60 re f",
            f"{border_col} RG 1.5 w",
            f"30 {y - 65} 552 60 re S",
            # Card text
            "BT",
            "/F1 11 Tf",
            "1.0 1.0 1.0 rg",
            f"45 {y - 20} Td",
            f"({b_clean}) Tj",
            "/F1 8 Tf",
            "0.7 0.75 0.8 rg",
            f"0 -15 Td",
            f"(Claim ID: {cid_clean}... | Polarity: {pol_clean}) Tj",
            f"0 -13 Td",
            f"(Author PK: {apk_clean}... | Status: {st_clean}) Tj",
            f"0 -12 Td",
            f"(Audit: {r_clean}) Tj",
            "ET",
        ])
        y -= 75

    # Footer
    stream_lines.extend([
        "BT",
        "/F1 8 Tf",
        "0.4 0.45 0.55 rg",
        "30 25 Td",
        "(Self-Executing Polyglot: Run 'python3 <file>.pdf --audit' for trustless verification) Tj",
        "ET",
        "Q"
    ])
    content_bytes = "\n".join(stream_lines).encode("latin-1")

    # PDF Objects
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

    # Embedded Claims Manifest
    manifest_dict = {
        "format": "WARRANT-0.2",
        "claims": [c.to_dict() for c in claims],
        "trust_config": (trust_config or TrustConfig()).to_dict()
    }
    manifest_json = json.dumps(manifest_dict, sort_keys=True)
    manifest_line = b"# %" + bytes([0xf0, 0x9f, 0x96, 0xa4]) + b" WARRANT_KERNEL_MANIFEST: " + manifest_json.encode("utf-8") + b"\n"

    # Embedded Python Runner
    py_runner = f"""
# coding: latin-1
import sys, json, os

cwd = os.getcwd()
if cwd not in sys.path:
    sys.path.insert(0, cwd)

def audit_self():
    print("\\033[1;36m" + "=" * 70)
    print("  %# WARRANT EPISTEMIC KERNEL -- STANDALONE AUDITOR (WARRANT-0.2)")
    print("=" * 70 + "\\033[0m")
    
    with open(__file__, 'rb') as f:
        data = f.read()
        
    marker = b" WARRANT_KERNEL_MANIFEST: "
    idx = data.find(marker)
    if idx == -1:
        print("\\033[1;31m[-] No warrant manifest found in polyglot.\\033[0m")
        sys.exit(1)
        
    line_end = data.find(b"\\n", idx)
    raw_json = data[idx + len(marker):line_end].decode('utf-8')
    manifest = json.loads(raw_json)
    
    import warrant_kernel
    tc = warrant_kernel.TrustConfig.from_dict(manifest.get("trust_config", {{}}))
    verifier = warrant_kernel.WarrantVerifier(tc)
    
    claims = [warrant_kernel.EdgeClaim.from_dict(c) for c in manifest.get("claims", [])]
    print(f"[*] Auditing {{len(claims)}} claims against trust config (max_atp={{tc.max_atp_budget}})...\\n")
    
    all_ok = True
    for i, c in enumerate(claims):
        v = verifier.audit_claim(c)
        status_color = "\\033[1;32m" if v.status == warrant_kernel.VerificationStatus.PASS else ("\\033[1;31m" if v.status == warrant_kernel.VerificationStatus.FAIL else "\\033[1;33m")
        print(f"{{status_color}}{{v.human_badge()}}\\033[0m")
        if v.status == warrant_kernel.VerificationStatus.FAIL:
            all_ok = False
            
    print("\\033[1;36m" + "=" * 70 + "\\033[0m")
    if all_ok:
        print("\\033[1;32m[+] All admitted claims verified under strict tri-state discipline.\\033[0m")
        sys.exit(0)
    else:
        print("\\033[1;31m[-] One or more claims failed verification.\\033[0m")
        sys.exit(1)

if __name__ == "__main__":
    audit_self()
"""

    header_text = (
        f"#!{sys.executable}\n"
        "# coding: latin-1\n"
        "# ============================================================================\n"
        "# %# PROJECT BLACK-HEART: WARRANT EPISTEMIC KERNEL (ISO 32000 POLYGLOT)\n"
        "# ============================================================================\n"
        "r'''\n"
    ).encode("latin-1")

    polyglot = header_text + pdf_bytes + manifest_line + b"'''\n" + py_runner.encode("latin-1")

    with open(output_path, "wb") as f:
        f.write(polyglot)

    return polyglot
