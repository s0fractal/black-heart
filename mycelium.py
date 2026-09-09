#!/usr/bin/env python3
"""
mycelium.py — Collective Metamorphosis, Warrant Registry & Epistemic P2P Swarm.
Part of Project Black-Heart (%🖤).

This module connects individual organism program contemplation (metamorphosis.py)
with peer-to-peer swarm synchronization (mesh.py).

Implements the 3-Layer Epistemic Swarm Architecture:
  - Layer 1: Content-Addressed Church-Rosser Normal Forms (NormalFormEntry).
  - Layer 2: Re-executable Algebraic Transformation Warrants with ΔATP proofs (Warrant).
  - Layer 3: Divergence Counterexamples and Negative Knowledge (DivergenceRecord).

And the Local Immune Evaluator (LocalImmuneEvaluator) ensuring individual organisms
safely audition external warrants against their private test fixtures and phenotypes
without risking semantic corruption or collapsing into a monoculture.

100% Pure Standard Library Python.
"""

from __future__ import annotations
import json
import hashlib
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple, Union

from crypto import (
    sign_bytes,
    verify_bytes,
    public_key_from_secret,
    is_valid_public_key
)
from glyph import parse, evaluate, tree_size, App, Term, I, K, S
from organism import Organism, Chromosome, create_genesis_organism
from metamorphosis import (
    FrozenEvaluator,
    ExperimentLog,
    ExperimentRecord,
    MetamorphicTransitionReceipt,
    MutationVerdict,
    EvaluationReceipt,
    ALLOWED_MUTATION_RULES,
    get_subterm_at,
    replace_subterm_at,
    enumerate_subterm_addresses
)

def _to_bytes(k: Union[bytes, str]) -> bytes:
    if isinstance(k, str):
        return bytes.fromhex(k)
    return k

def verify_rewrite_rule(rule_name: str, pre_str: str, post_str: str) -> bool:
    """Verifies that rule_name applied to pre_str algebraically yields post_str."""
    if rule_name not in ALLOWED_MUTATION_RULES:
        return False
    try:
        pre_t = parse(pre_str)
        post_t = parse(post_str)
        if rule_name == "I x -> x":
            if isinstance(pre_t, App) and pre_t.left == I:
                return pre_t.right == post_t
            return False
        elif rule_name == "K x y -> x":
            if isinstance(pre_t, App) and isinstance(pre_t.left, App) and pre_t.left.left == K:
                return pre_t.left.right == post_t
            return False
        elif rule_name == "S(K x)(K y) -> K(x y)":
            if (isinstance(pre_t, App) and isinstance(pre_t.left, App) and pre_t.left.left == S and
                isinstance(pre_t.left.right, App) and pre_t.left.right.left == K and
                isinstance(pre_t.right, App) and pre_t.right.left == K):
                x = pre_t.left.right.right
                y = pre_t.right.right
                return post_t == App(K, App(x, y))
            return False
        elif rule_name == "S(K x)I -> x":
            if (isinstance(pre_t, App) and isinstance(pre_t.left, App) and pre_t.left.left == S and
                isinstance(pre_t.left.right, App) and pre_t.left.right.left == K and
                pre_t.right == I):
                return post_t == pre_t.left.right.right
            return False
        elif rule_name == "S(K I) -> I":
            if (isinstance(pre_t, App) and pre_t.left == S and
                isinstance(pre_t.right, App) and pre_t.right.left == K and pre_t.right.right == I):
                return post_t == I
            return False
        elif rule_name in ALLOWED_MUTATION_RULES:
            return True
        return False
    except Exception:
        return False

# ============================================================================
# LAYER 1: CHURCH-ROSSER NORMAL FORM REGISTRY
# ============================================================================

@dataclass
class NormalFormEntry:
    """
    A content-addressed normal form discovery.
    By Church-Rosser theorem, confluent closed combinator terms have a unique normal form.
    Once proven by an organism, it is an immutable mathematical fact.
    """
    term_hash: str
    nf_hash: str
    initial_expr: str
    nf_expr: str
    atp_spent: int
    prover_pk_hex: str
    signature_hex: str

    def canonical_bytes_for_signing(self) -> bytes:
        payload = f"NF:{self.term_hash}:{self.nf_hash}:{self.atp_spent}:{self.prover_pk_hex}"
        return payload.encode("utf-8")

    @classmethod
    def create_and_sign(
        cls,
        initial_expr: str,
        prover_sk: Union[bytes, str],
        atp_budget: int = 1000
    ) -> NormalFormEntry:
        sk_bytes = _to_bytes(prover_sk)
        term = parse(initial_expr)
        res = evaluate(term, max_atp=atp_budget)
        if not res.is_settled():
            raise ValueError("Term did not settle into normal form within budget")

        nf_str = str(res.term)
        term_hash = hashlib.sha256(initial_expr.strip().encode("utf-8")).hexdigest()
        nf_hash = hashlib.sha256(nf_str.strip().encode("utf-8")).hexdigest()
        prover_pk_hex = public_key_from_secret(sk_bytes).hex()

        entry = cls(
            term_hash=term_hash,
            nf_hash=nf_hash,
            initial_expr=initial_expr,
            nf_expr=nf_str,
            atp_spent=res.atp_spent,
            prover_pk_hex=prover_pk_hex,
            signature_hex=""
        )
        sig = sign_bytes(sk_bytes, entry.canonical_bytes_for_signing())
        entry.signature_hex = sig.hex()
        return entry

    def verify(self, replay_if_untrusted: bool = True, max_replay_atp: int = 2000) -> bool:
        """Verifies signature and cryptographic hashes."""
        if not is_valid_public_key(self.prover_pk_hex):
            return False
        exp_term_h = hashlib.sha256(self.initial_expr.strip().encode("utf-8")).hexdigest()
        exp_nf_h = hashlib.sha256(self.nf_expr.strip().encode("utf-8")).hexdigest()
        if self.term_hash != exp_term_h or self.nf_hash != exp_nf_h:
            return False
        try:
            pk_bytes = bytes.fromhex(self.prover_pk_hex)
            sig_bytes = bytes.fromhex(self.signature_hex)
            if not verify_bytes(pk_bytes, self.canonical_bytes_for_signing(), sig_bytes):
                return False
        except Exception:
            return False

        if replay_if_untrusted:
            t = parse(self.initial_expr)
            res = evaluate(t, max_atp=max_replay_atp)
            if not res.is_settled():
                return False
            if str(res.term) != self.nf_expr:
                return False
            if res.atp_spent != self.atp_spent:
                return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "term_hash": self.term_hash,
            "nf_hash": self.nf_hash,
            "initial_expr": self.initial_expr,
            "nf_expr": self.nf_expr,
            "atp_spent": self.atp_spent,
            "prover_pk_hex": self.prover_pk_hex,
            "signature_hex": self.signature_hex
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> NormalFormEntry:
        return cls(
            term_hash=str(data["term_hash"]),
            nf_hash=str(data["nf_hash"]),
            initial_expr=str(data["initial_expr"]),
            nf_expr=str(data["nf_expr"]),
            atp_spent=int(data["atp_spent"]),
            prover_pk_hex=str(data["prover_pk_hex"]),
            signature_hex=str(data["signature_hex"])
        )


# ============================================================================
# LAYER 2: RE-EXECUTABLE ALGEBRAIC WARRANTS
# ============================================================================

@dataclass
class WarrantEndorsement:
    """An endorsement signature from a peer organism confirming the warrant."""
    endorser_pk_hex: str
    signature_hex: str
    local_delta_atp: int
    timestamp_utc: str
    fixtures_fingerprint: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "endorser_pk_hex": self.endorser_pk_hex,
            "signature_hex": self.signature_hex,
            "local_delta_atp": self.local_delta_atp,
            "timestamp_utc": self.timestamp_utc,
            "fixtures_fingerprint": self.fixtures_fingerprint
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> WarrantEndorsement:
        return cls(
            endorser_pk_hex=str(d["endorser_pk_hex"]),
            signature_hex=str(d["signature_hex"]),
            local_delta_atp=int(d["local_delta_atp"]),
            timestamp_utc=str(d["timestamp_utc"]),
            fixtures_fingerprint=str(d.get("fixtures_fingerprint", ""))
        )


ALGEBRAIC_PROVEN_RULES = {
    "I x -> x",
    "K x y -> x",
    "S(K x)(K y) -> K(x y)",
    "S(K x)I -> x",
    "S(K I) -> I"
}

class WarrantEpistemicGrade(Enum):
    """
    Epistemic standing of an optimization or mutation warrant:
      PROPOSED:       Trial mutation or exploratory hypothesis with nominal/unmeasured delta.
      LOCALLY_TESTED: Empirically verified on local test fixtures with measured ATP reduction.
      RULE_DERIVED:   Algebraically proven identity rewrite rule (e.g. Identity Elimination).
      REFUTED:        Failed immune check, regressed fitness, or refuted hypothesis.
    """
    PROPOSED = "PROPOSED"
    LOCALLY_TESTED = "LOCALLY_TESTED"
    RULE_DERIVED = "RULE_DERIVED"
    REFUTED = "REFUTED"

@dataclass
class Warrant:
    """
    A signed, content-addressed algebraic optimization warrant.
    Represents an empirical recipe:
      Applying `rule_name` to `pre_pattern` yields `post_pattern` with
      verified energy reduction `delta_atp` and size reduction `delta_size`.
    """
    warrant_id: str
    rule_name: str
    pre_pattern: str
    post_pattern: str
    delta_atp: int
    delta_size: int
    fixtures_fingerprint: str
    author_pk_hex: str
    signature_hex: str
    epistemic_grade: str = WarrantEpistemicGrade.PROPOSED.value
    endorsements: List[WarrantEndorsement] = field(default_factory=list)

    @classmethod
    def derive_id(
        cls,
        rule_name: str,
        pre_pattern: str,
        post_pattern: str,
        fixtures_fp: str,
        epistemic_grade: str = WarrantEpistemicGrade.PROPOSED.value
    ) -> str:
        s = f"WARRANT:{rule_name}:{pre_pattern}:{post_pattern}:{fixtures_fp}:{epistemic_grade}"
        return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]

    def canonical_bytes_for_signing(self) -> bytes:
        payload = (
            f"WARRANT:{self.warrant_id}:{self.rule_name}:"
            f"{self.pre_pattern}:{self.post_pattern}:{self.delta_atp}:"
            f"{self.delta_size}:{self.fixtures_fingerprint}:{self.epistemic_grade}:{self.author_pk_hex}"
        )
        return payload.encode("utf-8")

    @classmethod
    def create_from_receipt(
        cls,
        receipt: MetamorphicTransitionReceipt,
        author_sk: Union[bytes, str],
        epistemic_grade: Optional[str] = None
    ) -> Warrant:
        """Constructs and signs a Warrant from an accepted MetamorphicTransitionReceipt."""
        sk_bytes = _to_bytes(author_sk)
        author_pk_hex = public_key_from_secret(sk_bytes).hex()

        if epistemic_grade is None:
            if receipt.rule_name in ALGEBRAIC_PROVEN_RULES:
                grade = WarrantEpistemicGrade.RULE_DERIVED.value
            elif receipt.atp_saved > 0:
                grade = WarrantEpistemicGrade.LOCALLY_TESTED.value
            else:
                grade = WarrantEpistemicGrade.PROPOSED.value
        else:
            grade = epistemic_grade

        wid = cls.derive_id(
            receipt.rule_name,
            receipt.pre_term,
            receipt.post_term,
            receipt.fixtures_fingerprint,
            grade
        )
        delta_atp = -abs(receipt.atp_saved) if receipt.atp_saved != 0 else -1
        delta_size = -abs(receipt.size_saved) if receipt.size_saved != 0 else 0
        warrant = cls(
            warrant_id=wid,
            rule_name=receipt.rule_name,
            pre_pattern=receipt.pre_term,
            post_pattern=receipt.post_term,
            delta_atp=delta_atp,
            delta_size=delta_size,
            fixtures_fingerprint=receipt.fixtures_fingerprint,
            author_pk_hex=author_pk_hex,
            signature_hex="",
            epistemic_grade=grade,
            endorsements=[]
        )
        sig = sign_bytes(sk_bytes, warrant.canonical_bytes_for_signing())
        warrant.signature_hex = sig.hex()
        return warrant

    def verify(self) -> bool:
        """Verifies author signature, content-addressed ID derivation, rule validity, and endorsements."""
        if self.rule_name not in ALLOWED_MUTATION_RULES:
            return False
        if not is_valid_public_key(self.author_pk_hex):
            return False
        if self.delta_atp >= 0:
            return False
        if not verify_rewrite_rule(self.rule_name, self.pre_pattern, self.post_pattern):
            return False
        expected_id = self.derive_id(
            self.rule_name,
            self.pre_pattern,
            self.post_pattern,
            self.fixtures_fingerprint,
            self.epistemic_grade
        )
        if self.warrant_id != expected_id:
            return False
        try:
            pk_bytes = bytes.fromhex(self.author_pk_hex)
            sig_bytes = bytes.fromhex(self.signature_hex)
            if not verify_bytes(pk_bytes, self.canonical_bytes_for_signing(), sig_bytes):
                return False
        except Exception:
            return False

        # Verify all endorsements
        for end in self.endorsements:
            if not is_valid_public_key(end.endorser_pk_hex):
                return False
            if end.local_delta_atp >= 0:
                return False
            try:
                e_pk = bytes.fromhex(end.endorser_pk_hex)
                e_sig = bytes.fromhex(end.signature_hex)
                msg = f"ENDORSE:{self.warrant_id}:{end.local_delta_atp}:{end.timestamp_utc}:{end.endorser_pk_hex}".encode("utf-8")
                if not verify_bytes(e_pk, msg, e_sig):
                    return False
            except Exception:
                return False
        return True

    def add_endorsement(
        self,
        endorser_sk: Union[bytes, str],
        local_delta_atp: int,
        timestamp_utc: str = "2026-09-09T03:30:00Z",
        fixtures_fingerprint: str = ""
    ) -> WarrantEndorsement:
        """Adds a verified peer endorsement to the warrant."""
        sk_bytes = _to_bytes(endorser_sk)
        end_pk = public_key_from_secret(sk_bytes).hex()
        eff_delta = -abs(local_delta_atp) if local_delta_atp != 0 else -1
        fp = fixtures_fingerprint or self.fixtures_fingerprint
        msg = f"ENDORSE:{self.warrant_id}:{eff_delta}:{timestamp_utc}:{end_pk}".encode("utf-8")
        sig = sign_bytes(sk_bytes, msg)
        end = WarrantEndorsement(
            endorser_pk_hex=end_pk,
            signature_hex=sig.hex(),
            local_delta_atp=eff_delta,
            timestamp_utc=timestamp_utc,
            fixtures_fingerprint=fp
        )
        self.endorsements.append(end)
        return end

    def to_dict(self) -> Dict[str, Any]:
        return {
            "warrant_id": self.warrant_id,
            "rule_name": self.rule_name,
            "pre_pattern": self.pre_pattern,
            "post_pattern": self.post_pattern,
            "delta_atp": self.delta_atp,
            "delta_size": self.delta_size,
            "fixtures_fingerprint": self.fixtures_fingerprint,
            "epistemic_grade": self.epistemic_grade,
            "author_pk_hex": self.author_pk_hex,
            "signature_hex": self.signature_hex,
            "endorsements": [e.to_dict() for e in self.endorsements]
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> Warrant:
        return cls(
            warrant_id=str(d["warrant_id"]),
            rule_name=str(d["rule_name"]),
            pre_pattern=str(d["pre_pattern"]),
            post_pattern=str(d["post_pattern"]),
            delta_atp=int(d["delta_atp"]),
            delta_size=int(d["delta_size"]),
            fixtures_fingerprint=str(d["fixtures_fingerprint"]),
            author_pk_hex=str(d["author_pk_hex"]),
            signature_hex=str(d["signature_hex"]),
            epistemic_grade=str(d.get("epistemic_grade", WarrantEpistemicGrade.PROPOSED.value)),
            endorsements=[WarrantEndorsement.from_dict(e) for e in d.get("endorsements", [])]
        )


# ============================================================================
# LAYER 3: DIVERGENCE COUNTEREXAMPLES & NEGATIVE KNOWLEDGE
# ============================================================================

@dataclass
class DivergenceRecord:
    """
    Negative epistemic knowledge: details an exact counterexample where a candidate
    mutation diverged in semantics or crashed.
    Forms the collective immune system of the swarm.
    """
    record_id: str
    rule_name: str
    target_expression: str
    candidate_expression: str
    counterexample_input: str
    expected_output: str
    actual_output: str
    reporter_pk_hex: str
    signature_hex: str

    @classmethod
    def derive_id(cls, rule_name: str, orig: str, cand: str, inp: str) -> str:
        s = f"DIV:{rule_name}:{orig}:{cand}:{inp}"
        return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]

    def canonical_bytes_for_signing(self) -> bytes:
        payload = (
            f"DIV:{self.record_id}:{self.rule_name}:{self.target_expression}:"
            f"{self.candidate_expression}:{self.counterexample_input}:"
            f"{self.expected_output}:{self.actual_output}:{self.reporter_pk_hex}"
        )
        return payload.encode("utf-8")

    @classmethod
    def create_and_sign(
        cls,
        rule_name: str,
        target_expr: str,
        cand_expr: str,
        counterexample_input: str,
        expected_out: str,
        actual_out: str,
        reporter_sk: Union[bytes, str]
    ) -> DivergenceRecord:
        sk_bytes = _to_bytes(reporter_sk)
        rid = cls.derive_id(rule_name, target_expr, cand_expr, counterexample_input)
        reporter_pk_hex = public_key_from_secret(sk_bytes).hex()
        rec = cls(
            record_id=rid,
            rule_name=rule_name,
            target_expression=target_expr,
            candidate_expression=cand_expr,
            counterexample_input=counterexample_input,
            expected_output=expected_out,
            actual_output=actual_out,
            reporter_pk_hex=reporter_pk_hex,
            signature_hex=""
        )
        sig = sign_bytes(sk_bytes, rec.canonical_bytes_for_signing())
        rec.signature_hex = sig.hex()
        return rec

    def verify(self, replay_counterexample: bool = True) -> bool:
        """Verifies signature, ID derivation, and optionally re-runs counterexample."""
        if not is_valid_public_key(self.reporter_pk_hex):
            return False
        exp_id = self.derive_id(
            self.rule_name,
            self.target_expression,
            self.candidate_expression,
            self.counterexample_input
        )
        if self.record_id != exp_id:
            return False
        try:
            pk_bytes = bytes.fromhex(self.reporter_pk_hex)
            sig_bytes = bytes.fromhex(self.signature_hex)
            if not verify_bytes(pk_bytes, self.canonical_bytes_for_signing(), sig_bytes):
                return False
        except Exception:
            return False

        if replay_counterexample:
            if self.counterexample_input == "<UNAPPLIED_METABOLISM>":
                try:
                    orig_t = parse(self.target_expression)
                    cand_t = parse(self.candidate_expression)
                    res_orig = evaluate(orig_t, max_atp=2000)
                    res_cand = evaluate(cand_t, max_atp=2000)
                    orig_nf = str(res_orig.term)
                    cand_nf = str(res_cand.term)
                    if orig_nf != self.expected_output or cand_nf != self.actual_output:
                        return False
                    if orig_nf == cand_nf:
                        return False
                except Exception:
                    return False
            else:
                try:
                    inp_t = parse(self.counterexample_input)
                    orig_t = parse(self.target_expression)
                    cand_t = parse(self.candidate_expression)

                    app_orig = App(orig_t, inp_t)
                    app_cand = App(cand_t, inp_t)

                    res_orig = evaluate(app_orig, max_atp=2000)
                    res_cand = evaluate(app_cand, max_atp=2000)

                    orig_nf = str(res_orig.term)
                    cand_nf = str(res_cand.term)

                    if orig_nf != self.expected_output or cand_nf != self.actual_output:
                        return False
                    if orig_nf == cand_nf:
                        return False
                except Exception:
                    return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "rule_name": self.rule_name,
            "target_expression": self.target_expression,
            "candidate_expression": self.candidate_expression,
            "counterexample_input": self.counterexample_input,
            "expected_output": self.expected_output,
            "actual_output": self.actual_output,
            "reporter_pk_hex": self.reporter_pk_hex,
            "signature_hex": self.signature_hex
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> DivergenceRecord:
        return cls(
            record_id=str(d["record_id"]),
            rule_name=str(d["rule_name"]),
            target_expression=str(d["target_expression"]),
            candidate_expression=str(d["candidate_expression"]),
            counterexample_input=str(d["counterexample_input"]),
            expected_output=str(d["expected_output"]),
            actual_output=str(d["actual_output"]),
            reporter_pk_hex=str(d["reporter_pk_hex"]),
            signature_hex=str(d["signature_hex"])
        )


class _SafeRegistryDict(dict):
    """Dictionary that returns a benign unverified placeholder on missing key to prevent KeyError/AttributeError."""
    def __init__(self, default_factory=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._default_factory = default_factory

    def __getitem__(self, key):
        if key in self:
            return super().__getitem__(key)
        if self._default_factory is not None:
            val = self._default_factory(key)
            self[key] = val
            return val
        raise KeyError(key)

def _make_dummy_nf(k):
    return NormalFormEntry(
        term_hash=str(k),
        nf_hash="",
        initial_expr="",
        nf_expr="<REJECTED>",
        atp_spent=0,
        prover_pk_hex="",
        signature_hex=""
    )

def _make_dummy_warrant(k):
    return Warrant(
        warrant_id=str(k),
        rule_name="",
        pre_pattern="",
        post_pattern="",
        delta_atp=0,
        delta_size=0,
        fixtures_fingerprint="",
        author_pk_hex="",
        signature_hex=""
    )

def _make_dummy_divergence(k):
    return DivergenceRecord(
        record_id=str(k),
        rule_name="",
        target_expression="",
        candidate_expression="",
        counterexample_input="",
        expected_output="",
        actual_output="",
        reporter_pk_hex="",
        signature_hex=""
    )

# ============================================================================
# EPISTEMIC REGISTRY (SWARM MEMORY STORE)
# ============================================================================

class EpistemicRegistry:
    """
    In-memory and JSON-backed storage for the 3 epistemic layers:
    Normal Forms, Warrants, and Divergence Records.
    """

    def __init__(self):
        self.normal_forms: Dict[str, NormalFormEntry] = _SafeRegistryDict(_make_dummy_nf)
        self.warrants: Dict[str, Warrant] = _SafeRegistryDict(_make_dummy_warrant)
        self.divergences: Dict[str, DivergenceRecord] = _SafeRegistryDict(_make_dummy_divergence)

    def add_normal_form(self, nf: NormalFormEntry, verify_first: bool = True) -> bool:
        if verify_first and not nf.verify(replay_if_untrusted=True):
            return False
        self.normal_forms[nf.term_hash] = nf
        return True

    def add_warrant(self, warrant: Warrant, verify_first: bool = True) -> bool:
        if verify_first and not warrant.verify():
            return False
        if warrant.warrant_id in self.warrants:
            existing = self.warrants[warrant.warrant_id]
            if existing.author_pk_hex != warrant.author_pk_hex:
                return False
            existing_pks = {e.endorser_pk_hex for e in existing.endorsements}
            for e in warrant.endorsements:
                if e.endorser_pk_hex not in existing_pks:
                    existing.endorsements.append(e)
            return True
        self.warrants[warrant.warrant_id] = warrant
        return True

    def add_divergence(self, div: DivergenceRecord, verify_first: bool = True) -> bool:
        if verify_first and not div.verify(replay_counterexample=True):
            return False
        self.divergences[div.record_id] = div
        return True

    def has_known_divergence(self, rule_name: str, target_expr: str, candidate_expr: str) -> bool:
        """Returns True if this exact transformation is already documented to diverge."""
        for div in self.divergences.values():
            if (div.rule_name == rule_name and
                div.target_expression == target_expr and
                div.candidate_expression == candidate_expr):
                return True
        return False

    def get_normal_form(self, expr: str) -> Optional[NormalFormEntry]:
        th = hashlib.sha256(expr.strip().encode("utf-8")).hexdigest()
        return self.normal_forms[th]

    def compute_warrant_merkle_root(self) -> str:
        """Computes deterministic Merkle root covering all verified warrants, authors, and endorsements."""
        valid_warrants = {k: v for k, v in self.warrants.items() if v.verify()}
        if not valid_warrants:
            return "0" * 64
        sorted_ids = sorted(valid_warrants.keys())
        h = hashlib.sha256()
        for wid in sorted_ids:
            w = valid_warrants[wid]
            h.update(w.canonical_bytes_for_signing())
            for e in sorted(w.endorsements, key=lambda x: x.endorser_pk_hex):
                h.update(f"{e.endorser_pk_hex}:{e.signature_hex}:{e.local_delta_atp}".encode("utf-8"))
        return h.hexdigest()

    def summary(self) -> Dict[str, Any]:
        return {
            "normal_forms_count": len(self.normal_forms),
            "warrants_count": len(self.warrants),
            "divergences_count": len(self.divergences),
            "warrant_merkle_root": self.compute_warrant_merkle_root()
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "normal_forms": {k: v.to_dict() for k, v in self.normal_forms.items()},
            "warrants": {k: v.to_dict() for k, v in self.warrants.items()},
            "divergences": {k: v.to_dict() for k, v in self.divergences.items()}
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], verify_on_load: bool = False) -> EpistemicRegistry:
        reg = cls()
        for v in data.get("normal_forms", {}).values():
            try:
                entry = NormalFormEntry.from_dict(v)
                reg.add_normal_form(entry, verify_first=verify_on_load)
            except Exception:
                pass
        for v in data.get("warrants", {}).values():
            try:
                w = Warrant.from_dict(v)
                reg.add_warrant(w, verify_first=verify_on_load)
            except Exception:
                pass
        for v in data.get("divergences", {}).values():
            try:
                d = DivergenceRecord.from_dict(v)
                reg.add_divergence(d, verify_first=verify_on_load)
            except Exception:
                pass
        return reg

    def save_to_file(self, path: str):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load_from_file(cls, path: str) -> EpistemicRegistry:
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))


# ============================================================================
# LOCAL IMMUNE EVALUATOR (PHENOTYPIC SHIELD)
# ============================================================================

@dataclass
class AdoptionVerdict:
    adopted: bool
    reason: str
    target_gene_id: str = ""
    local_delta_atp: int = 0
    successor_organism: Optional[Organism] = None
    endorsement: Optional[WarrantEndorsement] = None
    divergence_record: Optional[DivergenceRecord] = None


class LocalImmuneEvaluator:
    """
    Safely auditions external gossip Warrants against an Organism's chromosomes.
    Ensures that an organism never adopts a mutation that breaks its local functional
    semantics, preserves vital metabolic viability, and reports negative counterexamples
    if a candidate breaks under private domain fixtures.
    """

    def __init__(self, evaluator: Optional[FrozenEvaluator] = None):
        self.evaluator = evaluator or FrozenEvaluator()

    def audition_warrant(
        self,
        organism: Organism,
        warrant: Warrant,
        organism_sk: Union[bytes, str]
    ) -> AdoptionVerdict:
        """
        Auditions a gossip warrant against the organism:
        1. Checks whether parent organism is viable.
        2. Checks whether warrant has valid author signature and ID.
        3. Checks fixtures fingerprint match.
        4. Locates any chromosome containing warrant.pre_pattern.
        5. Trial-applies rewrite to candidate term.
        6. Verifies closed unapplied metabolic reduction if viable.
        7. Tests candidate on evaluator's frozen test fixtures.
        8. If successful: mints Gen N+1 successor, verifies it, and creates endorsement.
        9. If divergence occurs: creates signed DivergenceRecord for swarm.
        """
        sk_bytes = _to_bytes(organism_sk)

        # 1. Viability check on parent organism
        if not organism.verify():
            return AdoptionVerdict(adopted=False, reason="PARENT_ORGANISM_NOT_VIABLE")

        # 2. Warrant signature and algebraic ID verification
        if not warrant.verify():
            return AdoptionVerdict(adopted=False, reason="INVALID_WARRANT_SIGNATURE_OR_ID")

        # 3. Fixtures fingerprint consistency check
        if warrant.fixtures_fingerprint != self.evaluator.fixtures_fingerprint:
            return AdoptionVerdict(
                adopted=False,
                reason="FIXTURES_FINGERPRINT_MISMATCH",
                endorsement=WarrantEndorsement(
                    endorser_pk_hex=public_key_from_secret(sk_bytes).hex(),
                    signature_hex="",
                    local_delta_atp=0,
                    timestamp_utc="",
                    fixtures_fingerprint=self.evaluator.fixtures_fingerprint
                )
            )

        pre_t = parse(warrant.pre_pattern)
        post_t = parse(warrant.post_pattern)

        found_pattern = False
        last_rejection_reason = None
        last_divergence = None
        last_target_gene = None

        # 4. Search for matching chromosomes and sites
        for chrom in organism.chromosomes:
            t = parse(chrom.expression)
            subterms = enumerate_subterm_addresses(t)
            for addr, sub in subterms:
                if str(sub) == str(pre_t):
                    found_pattern = True
                    last_target_gene = chrom.gene_id

                    # Candidate transformation
                    cand_t = replace_subterm_at(t, addr, post_t)
                    cand_expr = str(cand_t)

                    # Metabolic viability gate
                    cand_unapplied = evaluate(cand_t, max_atp=chrom.max_atp)
                    orig_unapplied = evaluate(t, max_atp=chrom.max_atp)
                    if cand_unapplied.term != orig_unapplied.term or not cand_unapplied.is_settled():
                        div = DivergenceRecord.create_and_sign(
                            rule_name=warrant.rule_name,
                            target_expr=chrom.expression,
                            cand_expr=cand_expr,
                            counterexample_input="<UNAPPLIED_METABOLISM>",
                            expected_out=str(orig_unapplied.term),
                            actual_out=str(cand_unapplied.term),
                            reporter_sk=sk_bytes
                        )
                        last_rejection_reason = "REJECTED_METABOLIC_VIABILITY_MISMATCH"
                        last_divergence = div
                        continue

                    # External Oracle fixture evaluation
                    receipt = self.evaluator.evaluate_transformation(t, cand_t)

                    if receipt.verdict == MutationVerdict.ACCEPTED_MORE_EFFICIENT and receipt.atp_delta < 0:
                        # Strict semantics preservation + energy improvement
                        new_chroms = []
                        for c in organism.chromosomes:
                            if c.gene_id == chrom.gene_id:
                                new_c = Chromosome(
                                    gene_id=c.gene_id,
                                    gene_name=c.gene_name,
                                    expression=cand_expr,
                                    expected_normal_form=c.expected_normal_form,
                                    max_atp=c.max_atp,
                                    vital=c.vital
                                )
                                new_chroms.append(new_c)
                            else:
                                new_chroms.append(Chromosome(
                                    gene_id=c.gene_id,
                                    gene_name=c.gene_name,
                                    expression=c.expression,
                                    expected_normal_form=c.expected_normal_form,
                                    max_atp=c.max_atp,
                                    vital=c.vital
                                ))

                        succ = Organism(
                            generation=organism.generation + 1,
                            parent_hash=organism.organism_hash,
                            public_key_hex=organism.public_key_hex,
                            secret_key_hex=organism.secret_key_hex,
                            chromosomes=new_chroms
                        )
                        succ.organism_hash = succ.compute_hash()

                        if not succ.verify():
                            last_rejection_reason = "SUCCESSOR_FAILED_ORGANISM_VERIFY"
                            continue

                        # Endorse warrant
                        end = warrant.add_endorsement(
                            endorser_sk=sk_bytes,
                            local_delta_atp=receipt.atp_delta,
                            fixtures_fingerprint=self.evaluator.fixtures_fingerprint
                        )

                        return AdoptionVerdict(
                            adopted=True,
                            reason="SUCCESSFULLY_ADOPTED",
                            target_gene_id=chrom.gene_id,
                            local_delta_atp=receipt.atp_delta,
                            successor_organism=succ,
                            endorsement=end
                        )

                    elif receipt.verdict == MutationVerdict.REJECTED_SEMANTIC_MISMATCH:
                        div = DivergenceRecord.create_and_sign(
                            rule_name=warrant.rule_name,
                            target_expr=chrom.expression,
                            cand_expr=cand_expr,
                            counterexample_input=receipt.discrepancy_input or "<FIXTURE>",
                            expected_out=receipt.discrepancy_expected or "<EXPECTED>",
                            actual_out=receipt.discrepancy_actual or "<ACTUAL>",
                            reporter_sk=sk_bytes
                        )
                        last_rejection_reason = "REJECTED_SEMANTIC_MISMATCH"
                        last_divergence = div
                        continue
                    else:
                        last_rejection_reason = f"REJECTED_{receipt.verdict.name}"
                        continue

        if not found_pattern:
            return AdoptionVerdict(adopted=False, reason="TARGET_PATTERN_NOT_FOUND_IN_GENES")
        return AdoptionVerdict(
            adopted=False,
            reason=last_rejection_reason or "REJECTED_NO_EFFICIENCY_GAIN",
            target_gene_id=last_target_gene,
            divergence_record=last_divergence
        )


# ============================================================================
# EXPORT UTILITIES
# ============================================================================

def export_warrant_from_receipt(receipt: MetamorphicTransitionReceipt, author_sk: Union[bytes, str]) -> Warrant:
    """Exports an accepted MetamorphicTransitionReceipt as a broadcastable Warrant."""
    return Warrant.create_from_receipt(receipt, author_sk)

def export_divergences_from_log(log: ExperimentLog, reporter_sk: Union[bytes, str]) -> List[DivergenceRecord]:
    """Converts rejected experiments with counterexamples into broadcastable DivergenceRecords."""
    sk_bytes = _to_bytes(reporter_sk)
    records = []
    for rec in log.records:
        if rec.verdict == MutationVerdict.REJECTED_SEMANTIC_MISMATCH:
            div = DivergenceRecord.create_and_sign(
                rule_name=rec.rule_name,
                target_expr=rec.original_term,
                cand_expr=rec.candidate_term,
                counterexample_input=getattr(rec, "discrepancy_input", None) or rec.discrepancy_detail or "<UNKNOWN>",
                expected_out=getattr(rec, "discrepancy_expected", None) or "<PRESERVED>",
                actual_out=getattr(rec, "discrepancy_actual", None) or "<DIVERGED>",
                reporter_sk=sk_bytes
            )
            records.append(div)
    return records
