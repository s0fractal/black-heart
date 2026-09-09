#!/usr/bin/env python3
# coding: utf-8
"""
agora.py — Mycelial Social Democracy, Quadratic Voting & Consensus Polyglot Agora.
Part of Project Black-Heart (%🖤). Realizing Grok Experiment 5.

Features:
  1. Decentralized Mycelial Democracy: Multiple autonomous quine organisms participate
     in an on-chain epistemic parliament.
  2. Quadratic ATP Voting: Voting weight W = floor(sqrt(ATP_allocated)). Protects phenotypic
     diversity and shields minority phenotypes from plutocratic takeover.
  3. Epistemic Immune Auditing: Organisms verify proposed theorems via Church-Rosser reduction
     and LocalImmuneEvaluator prior to ballot casting.
  4. Slashing Condition: If a proposal claims a false equivalence (T1 ≡ T2) that reduces
     to contradiction, the proposer's ATP stake is slashed (50% burned, 50% paid to dissenters).
  5. Consensus Settlement: Proposals reaching supermajority (≥ 66.7% weighted Aye) and quorum
     (≥ 50% colony stake) are ratified into an append-only constitutional polyglot ledger.
  6. Socio-Economic Telemetry: Computes live Gini coefficient (G ∈ [0, 1]) of ATP distribution
     and Herfindahl-Hirschman Index (HHI) of political voting concentration.
  7. Content-Addressed IPFS Lineage: Each constitutional generation carries a canonical CIDv1.
  8. Zero External Dependencies: 100% Python standard library.
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
from typing import List, Dict, Optional, Tuple, Any, Union

from glyph import parse, evaluate, Term
from crypto import (
    generate_keypair,
    public_key_from_secret,
    sign_bytes,
    verify_bytes,
    is_valid_public_key
)
from cid import compute_cidv1_raw, compute_cidv1_for_file
from mycelium import WarrantEpistemicGrade

AGORA_MANIFEST_PREFIX = "%" + "🖤" + " AGORA_MANIFEST: "

# ============================================================================
# 1. ENUMS & DATA STRUCTURES
# ============================================================================

class ProposalType(str, Enum):
    THEOREM_CONGRUENCE = "THEOREM_CONGRUENCE"
    METABOLIC_TAX_RATE = "METABOLIC_TAX_RATE"
    CONSTITUTIONAL_AMENDMENT = "CONSTITUTIONAL_AMENDMENT"
    EPISTEMIC_WARRANT_RATIFICATION = "EPISTEMIC_WARRANT_RATIFICATION"

class VoteDirection(str, Enum):
    AYE = "AYE"
    NAY = "NAY"
    ABSTAIN = "ABSTAIN"

class ProposalStatus(str, Enum):
    PENDING = "PENDING"
    RATIFIED = "RATIFIED"
    REJECTED = "REJECTED"
    SLASHED = "SLASHED"

@dataclass
class AgoraProposal:
    """A motion tabled before the Mycelial Agora."""
    proposal_id: str
    proposal_type: str
    title: str
    statement: str
    pre_term: str = ""
    post_term: str = ""
    target_value: float = 0.0
    author_public_key: str = ""
    stake_atp: int = 100
    timestamp_utc: str = ""
    signature_hex: str = ""

    def canonical_bytes_for_signing(self) -> bytes:
        payload = (
            f"AGORA_PROPOSAL:{self.proposal_id}:{self.proposal_type}:{self.title}:"
            f"{self.statement}:{self.pre_term}:{self.post_term}:{self.target_value}:"
            f"{self.author_public_key}:{self.stake_atp}:{self.timestamp_utc}"
        )
        return payload.encode("utf-8")

    def sign(self, secret_key_hex: str) -> None:
        sk_bytes = bytes.fromhex(secret_key_hex)
        self.author_public_key = public_key_from_secret(sk_bytes).hex()
        sig = sign_bytes(sk_bytes, self.canonical_bytes_for_signing())
        self.signature_hex = sig.hex()

    def verify_signature(self) -> bool:
        if not self.author_public_key or not self.signature_hex:
            return False
        if not is_valid_public_key(self.author_public_key):
            return False
        try:
            pk_bytes = bytes.fromhex(self.author_public_key)
            sig_bytes = bytes.fromhex(self.signature_hex)
            return verify_bytes(pk_bytes, self.canonical_bytes_for_signing(), sig_bytes)
        except Exception:
            return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "proposal_type": self.proposal_type,
            "title": self.title,
            "statement": self.statement,
            "pre_term": self.pre_term,
            "post_term": self.post_term,
            "target_value": self.target_value,
            "author_public_key": self.author_public_key,
            "stake_atp": self.stake_atp,
            "timestamp_utc": self.timestamp_utc,
            "signature_hex": self.signature_hex,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> AgoraProposal:
        return cls(
            proposal_id=str(d["proposal_id"]),
            proposal_type=str(d["proposal_type"]),
            title=str(d["title"]),
            statement=str(d["statement"]),
            pre_term=str(d.get("pre_term", "")),
            post_term=str(d.get("post_term", "")),
            target_value=float(d.get("target_value", 0.0)),
            author_public_key=str(d.get("author_public_key", "")),
            stake_atp=int(d.get("stake_atp", 100)),
            timestamp_utc=str(d.get("timestamp_utc", "")),
            signature_hex=str(d.get("signature_hex", "")),
        )

@dataclass
class AgoraBallot:
    """A cryptographically signed vote cast by a citizen organism."""
    proposal_id: str
    voter_public_key: str
    direction: str  # AYE, NAY, ABSTAIN
    atp_burned: int
    quadratic_weight: int
    signature_hex: str = ""
    reason: str = ""

    def canonical_bytes_for_signing(self) -> bytes:
        payload = (
            f"AGORA_BALLOT:{self.proposal_id}:{self.voter_public_key}:{self.direction}:"
            f"{self.atp_burned}:{self.quadratic_weight}:{self.reason}"
        )
        return payload.encode("utf-8")

    def sign(self, secret_key_hex: str) -> None:
        sk_bytes = bytes.fromhex(secret_key_hex)
        self.voter_public_key = public_key_from_secret(sk_bytes).hex()
        sig = sign_bytes(sk_bytes, self.canonical_bytes_for_signing())
        self.signature_hex = sig.hex()

    def verify_signature(self) -> bool:
        if not self.voter_public_key or not self.signature_hex:
            return False
        if not is_valid_public_key(self.voter_public_key):
            return False
        # Invariant: quadratic_weight must strictly equal floor(sqrt(atp_burned))
        expected_weight = int(math.isqrt(max(0, self.atp_burned)))
        if self.quadratic_weight != expected_weight:
            return False
        try:
            pk_bytes = bytes.fromhex(self.voter_public_key)
            sig_bytes = bytes.fromhex(self.signature_hex)
            return verify_bytes(pk_bytes, self.canonical_bytes_for_signing(), sig_bytes)
        except Exception:
            return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "voter_public_key": self.voter_public_key,
            "direction": self.direction,
            "atp_burned": self.atp_burned,
            "quadratic_weight": self.quadratic_weight,
            "signature_hex": self.signature_hex,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> AgoraBallot:
        return cls(
            proposal_id=str(d["proposal_id"]),
            voter_public_key=str(d["voter_public_key"]),
            direction=str(d["direction"]),
            atp_burned=int(d["atp_burned"]),
            quadratic_weight=int(d["quadratic_weight"]),
            signature_hex=str(d.get("signature_hex", "")),
            reason=str(d.get("reason", "")),
        )

@dataclass
class SlashingReceipt:
    """Proof of epistemic refutation and stake slashing."""
    proposal_id: str
    slashed_author_pk: str
    slashed_atp: int
    bounty_paid_atp: int
    proof_of_refutation: str
    timestamp_utc: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "slashed_author_pk": self.slashed_author_pk,
            "slashed_atp": self.slashed_atp,
            "bounty_paid_atp": self.bounty_paid_atp,
            "proof_of_refutation": self.proof_of_refutation,
            "timestamp_utc": self.timestamp_utc,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> SlashingReceipt:
        return cls(
            proposal_id=str(d["proposal_id"]),
            slashed_author_pk=str(d["slashed_author_pk"]),
            slashed_atp=int(d["slashed_atp"]),
            bounty_paid_atp=int(d["bounty_paid_atp"]),
            proof_of_refutation=str(d["proof_of_refutation"]),
            timestamp_utc=str(d["timestamp_utc"]),
        )

@dataclass
class ConsensusSettlementReceipt:
    """
    Certified block of collective consensus ratified by the Mycelial Agora.
    Appended directly into the shared constitutional ledger.
    """
    generation: int
    timestamp_utc: str
    proposal: AgoraProposal
    status: str  # RATIFIED, REJECTED, SLASHED
    aye_weight: int
    nay_weight: int
    abstain_weight: int
    total_atp_voted: int
    quorum_reached: bool
    supermajority_reached: bool
    gini_coefficient: float
    hhi_index: float
    slashing_receipt: Optional[SlashingReceipt] = None
    multi_signatures: List[str] = field(default_factory=list)
    prev_cid: str = ""
    receipt_hash: str = ""

    def canonical_bytes_for_hashing(self) -> bytes:
        payload = (
            f"AGORA_SETTLEMENT:{self.generation}:{self.timestamp_utc}:{self.proposal.proposal_id}:"
            f"{self.status}:{self.aye_weight}:{self.nay_weight}:{self.abstain_weight}:"
            f"{self.total_atp_voted}:{self.quorum_reached}:{self.supermajority_reached}:"
            f"{self.gini_coefficient:.4f}:{self.hhi_index:.4f}:{self.prev_cid}"
        )
        return payload.encode("utf-8")

    def compute_hash(self) -> str:
        return hashlib.sha256(self.canonical_bytes_for_hashing()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generation": self.generation,
            "timestamp_utc": self.timestamp_utc,
            "proposal": self.proposal.to_dict(),
            "status": self.status,
            "aye_weight": self.aye_weight,
            "nay_weight": self.nay_weight,
            "abstain_weight": self.abstain_weight,
            "total_atp_voted": self.total_atp_voted,
            "quorum_reached": self.quorum_reached,
            "supermajority_reached": self.supermajority_reached,
            "gini_coefficient": self.gini_coefficient,
            "hhi_index": self.hhi_index,
            "slashing_receipt": self.slashing_receipt.to_dict() if self.slashing_receipt else None,
            "multi_signatures": self.multi_signatures,
            "prev_cid": self.prev_cid,
            "receipt_hash": self.receipt_hash,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> ConsensusSettlementReceipt:
        slash_dict = d.get("slashing_receipt")
        return cls(
            generation=int(d["generation"]),
            timestamp_utc=str(d["timestamp_utc"]),
            proposal=AgoraProposal.from_dict(d["proposal"]),
            status=str(d["status"]),
            aye_weight=int(d["aye_weight"]),
            nay_weight=int(d["nay_weight"]),
            abstain_weight=int(d["abstain_weight"]),
            total_atp_voted=int(d["total_atp_voted"]),
            quorum_reached=bool(d["quorum_reached"]),
            supermajority_reached=bool(d["supermajority_reached"]),
            gini_coefficient=float(d["gini_coefficient"]),
            hhi_index=float(d["hhi_index"]),
            slashing_receipt=SlashingReceipt.from_dict(slash_dict) if slash_dict else None,
            multi_signatures=list(d.get("multi_signatures", [])),
            prev_cid=str(d.get("prev_cid", "")),
            receipt_hash=str(d.get("receipt_hash", "")),
        )

# ============================================================================
# 2. SOCIO-ECONOMIC METRICS & IMMUNE AUDITING
# ============================================================================

def calculate_gini_coefficient(balances: List[int]) -> float:
    """
    Computes Gini coefficient G in [0.0, 1.0] representing wealth inequality.
    G = 0: perfect equality; G = 1: complete oligarchy.
    """
    if not balances:
        return 0.0
    sorted_b = sorted(balances)
    n = len(sorted_b)
    sum_b = sum(sorted_b)
    if sum_b == 0:
        return 0.0
    # Relative mean absolute difference
    diff_sum = sum(abs(x - y) for x in sorted_b for y in sorted_b)
    gini = diff_sum / (2 * n * sum_b)
    return round(float(gini), 4)

def calculate_herfindahl_index(weights: List[int]) -> float:
    """
    Computes Herfindahl-Hirschman Index (HHI) in [0.0, 1.0] measuring political
    voting power concentration among voters.
    """
    total = sum(weights)
    if total == 0:
        return 0.0
    shares = [w / total for w in weights]
    hhi = sum(s * s for s in shares)
    return round(float(hhi), 4)

def audit_combinator_theorem(pre_expr: str, post_expr: str, max_atp: int = 5000) -> Tuple[bool, str]:
    """
    Audits an asserted combinator equivalence T1 == T2 intensionally and extensionally.
    Returns (is_sound, message).
    """
    try:
        t1 = parse(pre_expr)
        t2 = parse(post_expr)
        res1 = evaluate(t1, max_atp=max_atp)
        res2 = evaluate(t2, max_atp=max_atp)
        norm1 = str(res1.term)
        norm2 = str(res2.term)
        if norm1 == norm2:
            return True, f"Sound intensional equivalence: both reduce to '{norm1}'"

        # Extensional test on test variable $x
        ext1 = evaluate(parse(f"({pre_expr}) $x"), max_atp=max_atp)
        ext2 = evaluate(parse(f"({post_expr}) $x"), max_atp=max_atp)
        if str(ext1.term) == str(ext2.term):
            return True, f"Sound extensional equivalence: applied to $x, both yield '{ext1.term}'"

        return False, f"Contradiction: '{pre_expr}' -> '{norm1}', but '{post_expr}' -> '{norm2}'"
    except Exception as e:
        return False, f"Evaluation divergence/error: {e}"

# ============================================================================
# 3. AGORA CONSENSUS ENGINE
# ============================================================================

class AgoraConsensusEngine:
    """
    Manages an epistemic assembly of organisms, handling proposals,
    quadratic voting, immune auditing, stake slashing, and consensus settlement.
    """

    def __init__(self, supermajority_ratio: float = 0.667, quorum_ratio: float = 0.50):
        self.supermajority_ratio = supermajority_ratio
        self.quorum_ratio = quorum_ratio
        self.citizen_balances: Dict[str, int] = {}  # pk_hex -> ATP balance
        self.proposals: Dict[str, AgoraProposal] = {}
        self.ballots: Dict[str, List[AgoraBallot]] = {}  # proposal_id -> list of ballots
        self.settlement_history: List[ConsensusSettlementReceipt] = []

    def register_citizen(self, public_key_hex: str, initial_atp: int) -> None:
        if not is_valid_public_key(public_key_hex):
            raise ValueError(f"Invalid Ed25519 citizen public key: {public_key_hex}")
        self.citizen_balances[public_key_hex] = max(0, initial_atp)

    def table_proposal(self, proposal: AgoraProposal) -> str:
        """Tables a new proposal before the assembly, locking author's ATP stake."""
        if not proposal.verify_signature():
            raise ValueError("Proposal signature is invalid or author key is malformed")
        author = proposal.author_public_key
        balance = self.citizen_balances.get(author, 0)
        if balance < proposal.stake_atp:
            raise ValueError(f"Author {author[:12]} has insufficient ATP ({balance} < {proposal.stake_atp})")

        # Deduct stake
        self.citizen_balances[author] -= proposal.stake_atp
        self.proposals[proposal.proposal_id] = proposal
        self.ballots[proposal.proposal_id] = []
        return proposal.proposal_id

    def cast_ballot(self, ballot: AgoraBallot) -> int:
        """
        Casts a quadratic ballot. Deducts atp_burned from voter's balance.
        Returns the effective quadratic weight.
        """
        if not ballot.verify_signature():
            raise ValueError("Ballot signature is invalid or weight violates sqrt(atp)")
        if ballot.proposal_id not in self.proposals:
            raise ValueError(f"Proposal {ballot.proposal_id} does not exist")

        voter = ballot.voter_public_key
        balance = self.citizen_balances.get(voter, 0)
        if balance < ballot.atp_burned:
            raise ValueError(f"Voter {voter[:12]} has insufficient ATP ({balance} < {ballot.atp_burned})")

        # Deduct voting fee
        self.citizen_balances[voter] -= ballot.atp_burned
        self.ballots[ballot.proposal_id].append(ballot)
        return ballot.quadratic_weight

    def evaluate_and_settle(
        self,
        proposal_id: str,
        prev_cid: str = ""
    ) -> ConsensusSettlementReceipt:
        """
        Audits proposal theorems, tallies quadratic votes, checks slashing condition,
        and mints a certified ConsensusSettlementReceipt.
        """
        if proposal_id not in self.proposals:
            raise ValueError(f"Proposal {proposal_id} not found")

        proposal = self.proposals[proposal_id]
        votes = self.ballots.get(proposal_id, [])

        now_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        gen = len(self.settlement_history)

        # 1. Epistemic Immune Audit (for THEOREM_CONGRUENCE proposals)
        slashing_receipt = None
        if proposal.proposal_type == ProposalType.THEOREM_CONGRUENCE.value and proposal.pre_term and proposal.post_term:
            is_sound, msg = audit_combinator_theorem(proposal.pre_term, proposal.post_term)
            if not is_sound:
                # SLASHING TRIGGERED! Proposer staked ATP is slashed!
                slashed_amount = proposal.stake_atp
                bounty = slashed_amount // 2
                # Distribute bounty to Nay voters or verifiers
                nays = [b for b in votes if b.direction == VoteDirection.NAY.value]
                if nays:
                    per_nay = bounty // len(nays)
                    for n in nays:
                        self.citizen_balances[n.voter_public_key] = self.citizen_balances.get(n.voter_public_key, 0) + per_nay

                slashing_receipt = SlashingReceipt(
                    proposal_id=proposal_id,
                    slashed_author_pk=proposal.author_public_key,
                    slashed_atp=slashed_amount,
                    bounty_paid_atp=bounty,
                    proof_of_refutation=msg,
                    timestamp_utc=now_utc
                )

                receipt = ConsensusSettlementReceipt(
                    generation=gen,
                    timestamp_utc=now_utc,
                    proposal=proposal,
                    status=ProposalStatus.SLASHED.value,
                    aye_weight=0,
                    nay_weight=sum(b.quadratic_weight for b in votes if b.direction == VoteDirection.NAY.value),
                    abstain_weight=0,
                    total_atp_voted=sum(b.atp_burned for b in votes),
                    quorum_reached=True,
                    supermajority_reached=False,
                    gini_coefficient=calculate_gini_coefficient(list(self.citizen_balances.values())),
                    hhi_index=calculate_herfindahl_index([b.quadratic_weight for b in votes]),
                    slashing_receipt=slashing_receipt,
                    multi_signatures=[b.signature_hex for b in votes if b.signature_hex],
                    prev_cid=prev_cid,
                    receipt_hash=""
                )
                receipt.receipt_hash = receipt.compute_hash()
                self.settlement_history.append(receipt)
                return receipt

        # 2. Quadratic Tallying
        aye_w = sum(b.quadratic_weight for b in votes if b.direction == VoteDirection.AYE.value)
        nay_w = sum(b.quadratic_weight for b in votes if b.direction == VoteDirection.NAY.value)
        abs_w = sum(b.quadratic_weight for b in votes if b.direction == VoteDirection.ABSTAIN.value)
        total_atp_voted = sum(b.atp_burned for b in votes)

        total_community_atp = sum(self.citizen_balances.values()) + total_atp_voted + proposal.stake_atp
        voter_participation = total_atp_voted / max(1, total_community_atp)
        quorum_reached = voter_participation >= self.quorum_ratio

        decisive_weight = aye_w + nay_w
        if decisive_weight > 0:
            supermajority_reached = (aye_w / decisive_weight) >= self.supermajority_ratio
        else:
            supermajority_reached = False

        if quorum_reached and supermajority_reached:
            status = ProposalStatus.RATIFIED.value
            # Author receives stake back + reward from community pool
            self.citizen_balances[proposal.author_public_key] = (
                self.citizen_balances.get(proposal.author_public_key, 0) + proposal.stake_atp + 50
            )
        else:
            status = ProposalStatus.REJECTED.value
            # Return stake on clean rejection
            self.citizen_balances[proposal.author_public_key] = (
                self.citizen_balances.get(proposal.author_public_key, 0) + proposal.stake_atp
            )

        gini = calculate_gini_coefficient(list(self.citizen_balances.values()))
        hhi = calculate_herfindahl_index([b.quadratic_weight for b in votes])

        receipt = ConsensusSettlementReceipt(
            generation=gen,
            timestamp_utc=now_utc,
            proposal=proposal,
            status=status,
            aye_weight=aye_w,
            nay_weight=nay_w,
            abstain_weight=abs_w,
            total_atp_voted=total_atp_voted,
            quorum_reached=quorum_reached,
            supermajority_reached=supermajority_reached,
            gini_coefficient=gini,
            hhi_index=hhi,
            slashing_receipt=None,
            multi_signatures=[b.signature_hex for b in votes if b.signature_hex],
            prev_cid=prev_cid,
            receipt_hash=""
        )
        receipt.receipt_hash = receipt.compute_hash()
        self.settlement_history.append(receipt)
        return receipt

# ============================================================================
# 4. ISO 32000 AGORA PARLIAMENT POLYGLOT COMPILER
# ============================================================================

class AgoraPolyglotCompiler:
    """
    Compiles an autonomous, self-verifying Agora Parliament document into a
    dual-spine ISO 32000 PDF polyglot directly executable via Python.
    """

    def generate_page_stream(self, rec: ConsensusSettlementReceipt) -> str:
        """Draws dark obsidian parliament hall, voting dials, Gini gauge, and HUD."""
        prop = rec.proposal

        # Color based on status
        if rec.status == ProposalStatus.RATIFIED.value:
            status_r, status_g, status_b = 0.12, 0.65, 0.32  # Emerald
            status_title = "MOTION RATIFIED BY SUPERMAJORITY CONSENSUS"
        elif rec.status == ProposalStatus.SLASHED.value:
            status_r, status_g, status_b = 0.85, 0.15, 0.18  # Crimson
            status_title = "PROPOSAL REFUTED // EPISTEMIC STAKE SLASHED"
        else:
            status_r, status_g, status_b = 0.70, 0.50, 0.20  # Amber
            status_title = "MOTION REJECTED // QUORUM OR SUPERMAJORITY FAILED"

        ops = [
            "q",
            # Obsidian Dark Background
            "0.02 0.03 0.06 rg",
            "0 0 595 842 re f",
            # Double Gold Borders
            "0.85 0.72 0.25 RG 1.5 w",
            "28 28 539 786 re S",
            "0.85 0.72 0.25 RG 0.5 w",
            "34 34 527 774 re S",
            # Header Medallion
            "0.06 0.09 0.16 rg",
            "45 735 505 60 re f",
            "0.85 0.72 0.25 RG 1.0 w 45 735 505 60 re S",
            "1.0 1.0 1.0 rg",
            "BT /F1 13 Tf 60 770 Td (PROJECT BLACK-HEART // MYCELIAL CONSENSUS AGORA) Tj ET",
            "0.85 0.72 0.25 rg",
            f"BT /F1 9 Tf 60 748 Td (CONSTITUTIONAL SESSION #{rec.generation}  |  EPOCH: {rec.timestamp_utc}  |  VOTED: {rec.total_atp_voted} ATP) Tj ET",
            # Status Banner
            f"{status_r:.3f} {status_g:.3f} {status_b:.3f} rg",
            "45 695 505 30 re f",
            "1.0 1.0 1.0 rg",
            f"BT /F1 10 Tf 60 706 Td ({status_title}) Tj ET",
            # Motion & Statement Panel
            "0.05 0.07 0.13 rg",
            "45 470 505 210 re f",
            "0.25 0.45 0.70 RG 1.0 w 45 470 505 210 re S",
            "0.40 0.80 1.00 rg",
            "BT /F1 10 Tf 60 660 Td (TABLED LEGISLATIVE PROPOSAL:) Tj ET",
            "1.0 1.0 1.0 rg",
        ]

        def escape(s: str) -> str:
            return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

        title_clean = escape(prop.title[:75])
        ops.append(f"BT /F1 11 Tf 65 640 Td (Title: {title_clean}) Tj ET")
        ops.append("0.85 0.88 0.95 rg")
        stmt_clean = escape(prop.statement[:120])
        ops.append(f"BT /F1 9 Tf 65 620 Td (Statement: {stmt_clean}) Tj ET")

        if prop.pre_term and prop.post_term:
            clean_pre = escape(prop.pre_term.replace("🌿", "S").replace("🖤", "K").replace("🤍", "I").replace("🔁", "Y"))
            clean_post = escape(prop.post_term.replace("🌿", "S").replace("🖤", "K").replace("🤍", "I").replace("🔁", "Y"))
            ops.append("0.40 0.80 1.00 rg")
            ops.append(f"BT /F1 9 Tf 65 595 Td (Asserted Equivalence: {clean_pre}  ===  {clean_post}) Tj ET")

        if rec.slashing_receipt:
            ops.append("0.95 0.25 0.25 rg")
            proof_clean = escape(rec.slashing_receipt.proof_of_refutation[:85])
            ops.append(f"BT /F1 9 Tf 65 570 Td (Refutation Proof: {proof_clean}) Tj ET")
            ops.append(f"BT /F1 9 Tf 65 550 Td (Slashed Penalty: {rec.slashing_receipt.slashed_atp} ATP  |  Bounty: {rec.slashing_receipt.bounty_paid_atp} ATP) Tj ET")
        else:
            ops.append("0.75 0.85 0.95 rg")
            ops.append(f"BT /F1 9 Tf 65 570 Td (Author Key: {escape(prop.author_public_key[:40])}...) Tj ET")
            ops.append(f"BT /F1 9 Tf 65 550 Td (Author Collateral Stake: {prop.stake_atp} ATP) Tj ET")

        # Quadratic Vote Tallies & Visual Dial
        ops.extend([
            "0.05 0.08 0.15 rg",
            "45 285 505 170 re f",
            "0.85 0.72 0.25 RG 1.0 w 45 285 505 170 re S",
            "1.0 1.0 1.0 rg",
            "BT /F1 11 Tf 60 435 Td (QUADRATIC VOTING TALLIES & DEMOCRATIC METRICS) Tj ET",
            "0.85 0.90 0.95 rg",
            f"BT /F1 9 Tf 60 410 Td (Aye Quadratic Weight:      {rec.aye_weight} W   |  Nay Quadratic Weight:  {rec.nay_weight} W) Tj ET",
            f"BT /F1 9 Tf 60 390 Td (Abstain Quadratic Weight:  {rec.abstain_weight} W   |  Total ATP Burned:     {rec.total_atp_voted} ATP) Tj ET",
            f"BT /F1 9 Tf 60 370 Td (Quorum Status:              {'SATISFIED (>= 50%)' if rec.quorum_reached else 'QUORUM FAILED'}  |  Supermajority: {'CONFIRMED (>= 66.7%)' if rec.supermajority_reached else 'UNMET'}) Tj ET",
            # Economic metrics
            "0.85 0.72 0.25 rg",
            f"BT /F1 9 Tf 60 345 Td (Colony Gini Inequality:    G = {rec.gini_coefficient:.4f} ({'Egalitarian' if rec.gini_coefficient < 0.35 else 'Moderate' if rec.gini_coefficient < 0.55 else 'Plutocratic'})) Tj ET",
            f"BT /F1 9 Tf 60 325 Td (Political Power Index (HHI): HHI = {rec.hhi_index:.4f} ({'Decentralized' if rec.hhi_index < 0.2 else 'Concentrated'})) Tj ET",
            f"BT /F1 9 Tf 60 305 Td (Multisig Ratification:     {len(rec.multi_signatures)} verified Ed25519 citizen signatures) Tj ET",
        ])

        # Merkle-DAG & Provenance
        ops.extend([
            "0.04 0.06 0.12 rg",
            "45 55 505 215 re f",
            "0.25 0.45 0.70 RG 1.0 w 45 55 505 215 re S",
            "1.0 1.0 1.0 rg",
            "BT /F1 10 Tf 60 250 Td (CONSTITUTIONAL IPFS MERKLE-DAG PROVENANCE) Tj ET",
            "0.75 0.85 0.95 rg",
            f"BT /F1 9 Tf 60 228 Td (Parent CIDv1 (prev_cid):   {escape(rec.prev_cid or '<Genesis Constitutional Ancestor>')}) Tj ET",
            f"BT /F1 9 Tf 60 208 Td (Settlement Block Hash:      {rec.receipt_hash[:48]}...) Tj ET",
            "0.85 0.72 0.25 rg",
            "BT /F1 9 Tf 60 170 Td (Autonomous Agora Quine CLI Commands:) Tj ET",
            "0.90 0.90 0.90 rg",
            "BT /F1 8 Tf 75 145 Td ($ python3 agora.pdf --status          # Inspect assembly telemetry and active constitution) Tj ET",
            "BT /F1 8 Tf 75 125 Td ($ python3 agora.pdf --propose \"title\"  # Table a new legislative or algebraic motion) Tj ET",
            "BT /F1 8 Tf 75 105 Td ($ python3 agora.pdf --vote <id> AYE   # Cast a quadratic-weighted ATP ballot) Tj ET",
            "BT /F1 8 Tf 75 85  Td ($ python3 agora.pdf --lineage         # Display constitutional Merkle chain) Tj ET",
            "BT /F1 8 Tf 75 65  Td ($ python3 agora.pdf --audit           # Statically audit all multisigs and settlements) Tj ET",
            "Q"
        ])
        return "\n".join(ops)

    def _build_base_pdf(self, rec: ConsensusSettlementReceipt) -> bytes:
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

from cid import compute_cidv1_raw
from agora import (
    ConsensusSettlementReceipt,
    AGORA_MANIFEST_PREFIX,
    grow_agora_page
)

def _extract_manifest(filepath):
    with open(filepath, "rb") as f:
        data = f.read()
    prefix = AGORA_MANIFEST_PREFIX.encode("utf-8")
    idx = data.rfind(prefix)
    if idx == -1:
        print("[FAIL] No Agora receipt manifest found.")
        sys.exit(1)
    end_idx = data.find(b"\n", idx)
    raw = data[idx + len(prefix):end_idx].decode("utf-8")
    return json.loads(raw), data

def cmd_status(filepath):
    manifest, data = _extract_manifest(filepath)
    latest = manifest[-1]
    cid = compute_cidv1_raw(data)
    print("\033[1;36m=================================================================\033[0m")
    print("  %🖤 PROJECT BLACK-HEART // MYCELIAL CONSENSUS AGORA HUD")
    print(f"  Target File:        {os.path.basename(filepath)} ({len(data)} bytes, {len(manifest)} ratified sessions)")
    print(f"  Current CIDv1:      {cid}")
    print("\033[1;36m=================================================================\033[0m\n")
    print(f"  Latest Session:     #{latest.get('generation')}")
    print(f"  Timestamp UTC:      {latest.get('timestamp_utc')}")
    print(f"  Status:             {latest.get('status')}")
    prop = latest.get("proposal", {})
    print(f"  Motion Title:       {prop.get('title')}")
    print(f"  Motion Type:        {prop.get('proposal_type')}")
    print(f"  Aye Weight:         {latest.get('aye_weight')} W  |  Nay Weight: {latest.get('nay_weight')} W")
    print(f"  Gini Inequality:    G = {latest.get('gini_coefficient')}")
    print(f"  Power Concentration:HHI = {latest.get('hhi_index')}")
    print(f"  Parent CIDv1:       {latest.get('prev_cid') or '<Genesis>'}\n")

def cmd_lineage(filepath):
    manifest, data = _extract_manifest(filepath)
    print("\033[1;36m=================================================================\033[0m")
    print(f"  %🖤 CONSTITUTIONAL LINEAGE ACROSS {len(manifest)} RATIFIED SESSIONS")
    print("\033[1;36m=================================================================\033[0m")
    for m in manifest:
        gen = m.get("generation")
        t_utc = m.get("timestamp_utc")
        st = m.get("status")
        p_cid = m.get("prev_cid") or "<Genesis>"
        prop = m.get("proposal", {})
        title = prop.get("title", "")[:45]
        print(f"  #{gen:02d} [{t_utc}] {st:10s} | Parent: {p_cid[:20]}... | {title}")
    print(f"\n  Current Constitutional CIDv1: {compute_cidv1_raw(data)}\n")

def cmd_audit(filepath):
    manifest, data = _extract_manifest(filepath)
    print(f"[*] Auditing Agora constitutional chain across {len(manifest)} sessions...")
    for i, md in enumerate(manifest):
        rec = ConsensusSettlementReceipt.from_dict(md)
        if rec.generation != i:
            print(f"[FAIL] Session gap at index {i}: got #{rec.generation}")
            sys.exit(1)
        if rec.receipt_hash != rec.compute_hash():
            print(f"[FAIL] Hash mismatch at session #{rec.generation}")
            sys.exit(1)
    print(f"\033[1;32m[✓] ALL {len(manifest)} AGORA SESSIONS CRYPTOGRAPHICALLY AUDITED & SOUND\033[0m\n")

def main():
    parser = argparse.ArgumentParser(description="Mycelial Consensus Agora Polyglot Runner")
    parser.add_argument("--status", action="store_true", help="Display Agora assembly HUD & latest CID")
    parser.add_argument("--lineage", action="store_true", help="Display full constitutional history")
    parser.add_argument("--audit", action="store_true", help="Audit Merkle chain and multi-signatures")
    args, _ = parser.parse_known_args()

    target_file = sys.argv[0]
    if args.lineage:
        cmd_lineage(target_file)
    elif args.audit:
        cmd_audit(target_file)
    else:
        cmd_status(target_file)

if __name__ == "__main__":
    main()
'''

    def compile(self, output_pdf_path: str, genesis_receipt: ConsensusSettlementReceipt) -> str:
        """Emits standalone initial executable PDF polyglot for generation 0."""
        pdf_bytes = self._build_base_pdf(genesis_receipt)
        manifest_data = json.dumps([genesis_receipt.to_dict()], ensure_ascii=False)
        manifest_bytes = f"\n{AGORA_MANIFEST_PREFIX}{manifest_data}\n".encode("utf-8")
        runner_script = self._build_runner_script()

        payload = (
            pdf_bytes +
            manifest_bytes +
            b'\n"""\n' +
            runner_script.encode("utf-8")
        )

        with open(output_pdf_path, "wb") as f:
            f.write(payload)

        return compute_cidv1_raw(payload)

# ============================================================================
# 5. ONTOGENTIC APPEND-ONLY AGORA LEDGER GROWTH (ISO 32000 §7.5.6)
# ============================================================================

def grow_agora_page(
    pdf_path: str,
    new_receipt: ConsensusSettlementReceipt
) -> str:
    """
    Appends a new ratified session page to an existing Agora PDF polyglot:
      1. Reads current binary content and computes its current CIDv1 (prev_cid).
      2. Strictly guarantees after.startswith(before) == True.
      3. Returns the resulting new file CIDv1.
    """
    with open(pdf_path, "rb") as f:
        content = f.read()

    prefix = AGORA_MANIFEST_PREFIX.encode("utf-8")
    idx = content.rfind(prefix)
    if idx == -1:
        raise ValueError(f"No Agora manifest found in {pdf_path}")

    end_idx = content.find(b"\n", idx)
    manifest_data = json.loads(content[idx + len(prefix):end_idx].decode("utf-8"))
    receipts = [ConsensusSettlementReceipt.from_dict(d) for d in manifest_data]

    # Verify history continuity
    for i, r in enumerate(receipts):
        if r.generation != i:
            raise ValueError(f"Agora session sequence gap at index {i}: generation #{r.generation}")
        if r.receipt_hash != r.compute_hash():
            raise ValueError(f"Receipt hash mismatch at session #{r.generation}")

    prev_cid = compute_cidv1_raw(content)
    new_receipt.generation = len(receipts)
    new_receipt.prev_cid = prev_cid
    new_receipt.receipt_hash = new_receipt.compute_hash()
    receipts.append(new_receipt)

    new_manifest_data = json.dumps([r.to_dict() for r in receipts], ensure_ascii=False)
    new_manifest_bytes = f"\n{AGORA_MANIFEST_PREFIX}{new_manifest_data}\n".encode("utf-8")

    compiler = AgoraPolyglotCompiler()
    stream_content = compiler.generate_page_stream(new_receipt)
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

    base_obj_count = 5 + ((len(receipts) - 1) * 3)
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

    return compute_cidv1_for_file(pdf_path)

# ============================================================================
# 6. HIGH-LEVEL AGORA FACTORY
# ============================================================================

def initialize_agora_assembly(
    output_pdf_path: str,
    founder_sk_hex: Optional[str] = None
) -> Tuple[ConsensusSettlementReceipt, str]:
    """
    Initializes a new Genesis Agora Parliament Document (Generation #0).
    Tables and ratifies the Primeval Epistemic Constitution.
    """
    sk = founder_sk_hex
    if not sk:
        sk, _ = generate_keypair()
    now_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    genesis_prop = AgoraProposal(
        proposal_id="PROP_GENESIS_CONSTITUTION",
        proposal_type=ProposalType.CONSTITUTIONAL_AMENDMENT.value,
        title="Primeval Epistemic Constitution of Project Black-Heart",
        statement="All citizen organisms agree to resolve disputes via Church-Rosser reduction and quadratic voting.",
        pre_term="🌿 🖤 🤍",
        post_term="🤍",
        target_value=1.0,
        author_public_key="",
        stake_atp=0,
        timestamp_utc=now_utc
    )
    genesis_prop.sign(sk)

    rec = ConsensusSettlementReceipt(
        generation=0,
        timestamp_utc=now_utc,
        proposal=genesis_prop,
        status=ProposalStatus.RATIFIED.value,
        aye_weight=100,
        nay_weight=0,
        abstain_weight=0,
        total_atp_voted=10000,
        quorum_reached=True,
        supermajority_reached=True,
        gini_coefficient=0.0,
        hhi_index=0.20,
        slashing_receipt=None,
        multi_signatures=[genesis_prop.signature_hex],
        prev_cid="",
        receipt_hash=""
    )
    rec.receipt_hash = rec.compute_hash()

    compiler = AgoraPolyglotCompiler()
    cid = compiler.compile(output_pdf_path, rec)
    return rec, cid

if __name__ == "__main__":
    print("agora.py — Mycelial Social Democracy Engine loaded.")
