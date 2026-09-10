#!/usr/bin/env python3
# coding: utf-8
"""
epistemic_swarm.py — Epistemic Swarm Membrane & Symbiotic Quine Evolution.
Part of Project Black-Heart (%🖤). Engine #27.

Normative implementation of SWARM-0.1:
  1. Multi-Agent Epistemic Arena & Reaction-Diffusion Substrate:
     Organisms inhabit a 2D toroidal Gray-Scott morphogenetic lattice.
     Local activator/inhibitor concentrations (U, V) drive environmental energetics,
     granting metabolic ATP harvest yields:
       ATP_harvest(x, y) = floor(20 * (1.0 - U(x, y)) + 30 * V(x, y))
  2. Epistemic Inoculation Cascades (Swarm Epidemic Gossip Protocol):
     When any organism discovers an epistemic divergence or refutation (Grade C claim),
     it emits a signed TombstoneSignal with hop-count TTL. The signal propagates
     through the spatial swarm membrane. Recipient organisms ingest the tombstone,
     gain negative space coverage mu(C) and metabolic bounty, and achieve herd immunity
     without running the flawed code or burning metabolic ATP.
  3. Bilateral Quine Symbiosis & Mating (Invariant S1):
     Two adjacent organisms with sufficient metabolic reserves can initiate mating.
     Pre-flight Epistemic Compatibility Check enforces Invariant S1:
     neither parent's active chromosomes may contain terms tombstoned in the other
     parent's registry (fail-closed biological incompatibility).
     Offspring inherits vital chromosomes from both lineages, unifies tombstone defenses,
     synthesizes a new quine identity and Ed25519 keypair, and receives fuel endowments.
  4. The Swarm Agora Commons (Quadratic Epistemic Consensus):
     Organisms table high-grade theorems (Grade A/E) before the colony parliament.
     Living organisms audit expressions via Church-Rosser reduction and cast ballots
     weighted quadratically by stake and epistemic fitness. Motions reaching supermajority
     (>= 66.7% weighted Aye) are canonized into the collective Swarm Canon and
     integrated into all active organisms' rewrite cores.
  5. Dynamic Homeostasis & Starvation Decomposition:
     Under severe metabolic stress, organisms trigger Starvation Autophagy.
     If ATP drops to zero, organisms perish, releasing their remaining biomass back
     into the local morphogen grid as activator nutrients.
  6. ISO 32000 Append-Only Polyglot Swarm Membrane:
     Compiles the collective swarm state into an obsidian/cyan/emerald vector HUD
     with 2D spatial heatmap, cascade graphs, and embedded Latin-1 Python audit runner.

Zero external dependencies: 100% Python standard library.
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
from crypto import (
    generate_keypair,
    public_key_from_secret,
    sign_bytes,
    verify_bytes,
    is_valid_public_key,
)
import glyph
from glyph import (
    Term, parse, evaluate, term_hash, tree_size,
    GLYPH_K, GLYPH_I, GLYPH_S, GLYPH_ANCHOR
)
from organism import Chromosome
import warrant_kernel
from warrant_kernel import (
    EvidenceGrade, VerificationStatus, Polarity,
    EdgeClaim, CounterexampleWitness, AxiomaticWitness, EmpiricalWitness,
    TrustConfig, WarrantVerifier, promote_empirical_to_axiomatic
)
import controlled_forgetting
from controlled_forgetting import (
    RetirementMode, AdmissionStatus, NegativeSpaceMeter,
    RetirementRecord, ReAdoptionRecord, EpistemicTombstoneRegistry,
    ResurrectionGuard, EpistemicResurrectionError, append_retirement_tombstone_to_pdf
)
import epistemic_immune
from epistemic_immune import (
    ImmuneHealthStatus, EpistemicOrganism, ResurrectionDefense,
    CounterexampleMetabolism, HypothesisElevationCycle, HorizontalInoculation,
    StarvationAutophagy
)
import morphogenesis
from morphogenesis import MorphogeneticField, TuringArchetype

SWARM_MEMBRANE_MANIFEST_PREFIX = "%" + "🖤" + " SWARM_MEMBRANE_MANIFEST: "

# ============================================================================
# 1. SPATIAL MORPHOGENESIS GRID & ENERGETICS
# ============================================================================

class SwarmMorphogenGrid:
    """
    Toroidal 2D Reaction-Diffusion Grid providing environmental energetics
    and spatial signaling for the epistemic swarm.
    """
    def __init__(self, width: int = 16, height: int = 16, F: float = 0.035, k: float = 0.060):
        self.width = max(8, width)
        self.height = max(8, height)
        self.field = MorphogeneticField(
            width=self.width,
            height=self.height,
            F=F,
            k=k,
            Du=0.2097,
            Dv=0.1050
        )
        # Deterministically seed 2 energetic centers
        self.field.seed_patch(self.width // 4, self.height // 4, radius=3, seed_val=42)
        self.field.seed_patch(3 * self.width // 4, 3 * self.height // 4, radius=3, seed_val=1337)

    def step(self, dt: float = 1.0) -> None:
        self.field.step(dt=dt)

    def get_concentrations(self, x: int, y: int) -> Tuple[float, float]:
        gx = x % self.width
        gy = y % self.height
        idx = gy * self.width + gx
        return self.field.u[idx], self.field.v[idx]

    def harvest_atp(self, x: int, y: int) -> int:
        """
        Harvests metabolic fuel from local morphogen concentrations.
        ATP_harvest = floor(20 * (1 - U) + 30 * V)
        Consumes a small fraction of local activator V.
        """
        gx = x % self.width
        gy = y % self.height
        idx = gy * self.width + gx
        u = self.field.u[idx]
        v = self.field.v[idx]
        yield_atp = int(math.floor(20.0 * (1.0 - u) + 30.0 * v))
        yield_atp = max(5, min(40, yield_atp))
        # Metabolic consumption lowers local activator
        self.field.v[idx] = max(0.01, v * 0.90)
        return yield_atp

    def deposit_biomass(self, x: int, y: int, atp_amount: int) -> None:
        """Decomposing organism releases fuel nutrients back into morphogen activator V."""
        gx = x % self.width
        gy = y % self.height
        idx = gy * self.width + gx
        added_v = min(0.4, atp_amount * 0.002)
        self.field.v[idx] = min(0.95, self.field.v[idx] + added_v)


# ============================================================================
# 2. SWARM GOSSIP & INOCULATION SIGNALS
# ============================================================================

@dataclass
class TombstoneSignal:
    """
    Cryptographically signed epidemic gossip message broadcasting a refutation
    tombstone across the swarm membrane.
    """
    tombstone: RetirementRecord
    origin_organism_id: str
    hop_count: int = 3
    max_hops: int = 3
    signal_hash: str = ""
    signature_hex: str = ""

    def __post_init__(self):
        if not self.signal_hash:
            payload = f"{self.origin_organism_id}:{self.tombstone.target_id}:{self.tombstone.record_id}:{self.hop_count}"
            self.signal_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def sign(self, secret_key_hex: str) -> None:
        sk_bytes = bytes.fromhex(secret_key_hex)
        sig = sign_bytes(sk_bytes, self.signal_hash.encode("utf-8"))
        self.signature_hex = sig.hex()

    def verify_signature(self, public_key_hex: str) -> bool:
        if not self.signature_hex or not public_key_hex:
            return False
        try:
            pk_bytes = bytes.fromhex(public_key_hex)
            sig_bytes = bytes.fromhex(self.signature_hex)
            return verify_bytes(pk_bytes, self.signal_hash.encode("utf-8"), sig_bytes)
        except Exception:
            return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tombstone": self.tombstone.to_dict(),
            "origin_organism_id": self.origin_organism_id,
            "hop_count": self.hop_count,
            "max_hops": self.max_hops,
            "signal_hash": self.signal_hash,
            "signature_hex": self.signature_hex,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> TombstoneSignal:
        tomb = RetirementRecord.from_dict(d["tombstone"])
        sig = cls(
            tombstone=tomb,
            origin_organism_id=d["origin_organism_id"],
            hop_count=d.get("hop_count", 3),
            max_hops=d.get("max_hops", 3),
            signal_hash=d.get("signal_hash", ""),
            signature_hex=d.get("signature_hex", "")
        )
        return sig


@dataclass
class CascadeReport:
    """Telemetry report recording the epidemic spread of a tombstone defense."""
    signal_hash: str
    target_id: str
    origin_id: str
    hops_reached: int
    organisms_inoculated: List[str]
    total_negative_space_pruned: float
    reproduction_number_r0: float


# ============================================================================
# 3. SWARM AGENT SPATIAL STATE
# ============================================================================

@dataclass
class SwarmOrganismState:
    """Spatial and demographic state of an organism inside the swarm membrane."""
    organism_id: str
    x: int
    y: int
    heading: Tuple[int, int] = (1, 0)
    is_alive: bool = True
    age_ticks: int = 0
    children_count: int = 0
    signals_relayed: int = 0
    signals_absorbed: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "organism_id": self.organism_id,
            "x": self.x,
            "y": self.y,
            "heading": list(self.heading),
            "is_alive": self.is_alive,
            "age_ticks": self.age_ticks,
            "children_count": self.children_count,
            "signals_relayed": self.signals_relayed,
            "signals_absorbed": self.signals_absorbed,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> SwarmOrganismState:
        return cls(
            organism_id=d["organism_id"],
            x=d["x"],
            y=d["y"],
            heading=tuple(d.get("heading", (1, 0))),
            is_alive=d.get("is_alive", True),
            age_ticks=d.get("age_ticks", 0),
            children_count=d.get("children_count", 0),
            signals_relayed=d.get("signals_relayed", 0),
            signals_absorbed=d.get("signals_absorbed", 0),
        )


# ============================================================================
# 4. INOCULATION CASCADE ENGINE
# ============================================================================

class SwarmInoculationCascade:
    """
    Propagates epistemic defenses across spatial neighborhoods using epidemic gossip.
    Organisms that absorb the tombstone gain herd immunity against divergent mutations
    without repeating costly reductions.
    """

    @staticmethod
    def broadcast_tombstone(
        swarm: SwarmMembrane,
        origin_id: str,
        tombstone: RetirementRecord,
        max_hops: int = 3,
        comm_radius: int = 4
    ) -> CascadeReport:
        if origin_id not in swarm.organisms or origin_id not in swarm.organism_states:
            raise ValueError(f"Origin organism {origin_id} does not exist in swarm.")

        # One complete check before the cascade writes into any peer: the body
        # names the subject it will be filed under, its declared numbers are in
        # domain, and the signature covers that body.
        if not tombstone.is_admissible_for(tombstone.target_id):
            raise ValueError(
                "Cannot broadcast tombstone: it is not admissible for its own subject "
                "(subject binding, declared numeric domains, or signature over its body)."
            )

        origin_state = swarm.organism_states[origin_id]
        origin_org = swarm.organisms[origin_id]
        origin_sk = swarm.organism_keys[origin_id][1]

        initial_signal = TombstoneSignal(
            tombstone=tombstone,
            origin_organism_id=origin_id,
            hop_count=max_hops,
            max_hops=max_hops
        )
        initial_signal.sign(origin_sk)

        inoculated_set: Set[str] = set()
        queue: List[Tuple[str, TombstoneSignal]] = [(origin_id, initial_signal)]
        visited_nodes: Set[str] = {origin_id}
        max_hop_depth = 0
        total_branches = 0

        while queue:
            current_id, current_signal = queue.pop(0)
            cur_st = swarm.organism_states[current_id]
            current_depth = current_signal.max_hops - current_signal.hop_count
            if current_depth > max_hop_depth:
                max_hop_depth = current_depth

            if current_signal.hop_count <= 0:
                continue

            # Find neighbors within spatial radius
            neighbors = []
            for peer_id, peer_st in swarm.organism_states.items():
                if peer_id == current_id or not peer_st.is_alive:
                    continue
                # Toroidal Chebyshev distance
                dx = abs(peer_st.x - cur_st.x)
                dy = abs(peer_st.y - cur_st.y)
                dx = min(dx, swarm.grid.width - dx)
                dy = min(dy, swarm.grid.height - dy)
                if max(dx, dy) <= comm_radius:
                    neighbors.append(peer_id)

            branches_from_node = 0
            for peer_id in neighbors:
                peer_org = swarm.organisms[peer_id]
                peer_st = swarm.organism_states[peer_id]

                # Check if peer already has this tombstone
                if tombstone.target_id in peer_org.tombstone_registry.tombstones:
                    continue

                # Ingest tombstone defense
                peer_org.tombstone_registry.tombstones[tombstone.target_id] = tombstone
                peer_org.inoculated_tombstones_count += 1
                peer_st.signals_absorbed += 1
                inoculated_set.add(peer_id)
                branches_from_node += 1

                # Reward peer with metabolic immunity bonus (+25 ATP)
                peer_org.atp_reserve += 25

                # Relay signal if hops remain
                if current_signal.hop_count > 1 and peer_id not in visited_nodes:
                    visited_nodes.add(peer_id)
                    peer_st.signals_relayed += 1
                    relay_signal = TombstoneSignal(
                        tombstone=tombstone,
                        origin_organism_id=peer_id,
                        hop_count=current_signal.hop_count - 1,
                        max_hops=current_signal.max_hops
                    )
                    relay_sk = swarm.organism_keys[peer_id][1]
                    relay_signal.sign(relay_sk)
                    queue.append((peer_id, relay_signal))

            total_branches += branches_from_node

        # Calculate empirical reproduction rate R0
        r0 = float(total_branches) / max(1.0, float(len(visited_nodes)))
        total_vol = round(len(inoculated_set) * tombstone.negative_space_coverage, 4)

        report = CascadeReport(
            signal_hash=initial_signal.signal_hash,
            target_id=tombstone.target_id,
            origin_id=origin_id,
            hops_reached=max_hop_depth,
            organisms_inoculated=list(inoculated_set),
            total_negative_space_pruned=total_vol,
            reproduction_number_r0=round(r0, 2)
        )
        swarm.cascade_history.append(report)
        return report


# ============================================================================
# 5. BILATERAL QUINE SYMBIOSIS & MATING (INVARIANT S1)
# ============================================================================

class EpistemicIncompatibilityError(Exception):
    """Raised when mating is rejected due to Invariant S1 (cross-refutation)."""
    pass


class BilateralQuineSymbiosis:
    """
    Bilateral Quine Symbiosis and Mating Protocol.
    Enforces Invariant S1: Fail-Closed Epistemic Mating Compatibility.
    Two organisms can only mate if neither parent's active chromosomes contain
    terms tombstoned in the other parent's registry.
    """

    @staticmethod
    def check_mating_compatibility(
        parent_a: EpistemicOrganism,
        parent_b: EpistemicOrganism
    ) -> Tuple[bool, str]:
        """
        Validates Invariant S1:
          For every active chromosome c_A in parent_a:
            assert c_A.expression not in parent_b.tombstones
          For every active chromosome c_B in parent_b:
            assert c_B.expression not in parent_a.tombstones
        """
        # Check A's genes against B's tombstones
        for c in parent_a.chromosomes:
            try:
                t = glyph.parse(c.expression)
                thash = glyph.term_hash(t)
            except Exception:
                thash = c.expression
            if thash in parent_b.tombstone_registry.tombstones or c.expression in parent_b.tombstone_registry.tombstones:
                return False, f"Parent A active gene '{c.gene_id}' is tombstoned/refuted by Parent B registry."

        # Check B's genes against A's tombstones
        for c in parent_b.chromosomes:
            try:
                t = glyph.parse(c.expression)
                thash = glyph.term_hash(t)
            except Exception:
                thash = c.expression
            if thash in parent_a.tombstone_registry.tombstones or c.expression in parent_a.tombstone_registry.tombstones:
                return False, f"Parent B active gene '{c.gene_id}' is tombstoned/refuted by Parent A registry."

        # Check active axioms against tombstones
        for ax in parent_a.active_axioms:
            if ax in parent_b.tombstone_registry.tombstones:
                return False, f"Parent A axiom '{ax}' is tombstoned by Parent B."
        for ax in parent_b.active_axioms:
            if ax in parent_a.tombstone_registry.tombstones:
                return False, f"Parent B axiom '{ax}' is tombstoned by Parent A."

        return True, "COMPATIBLE"

    @staticmethod
    def recombine_and_mate(
        swarm: SwarmMembrane,
        parent_a_id: str,
        parent_b_id: str,
        mating_cost_atp: int = 60
    ) -> Tuple[EpistemicOrganism, SwarmOrganismState]:
        if parent_a_id not in swarm.organisms or parent_b_id not in swarm.organisms:
            raise ValueError("Both parents must exist in swarm.")

        parent_a = swarm.organisms[parent_a_id]
        parent_b = swarm.organisms[parent_b_id]
        state_a = swarm.organism_states[parent_a_id]
        state_b = swarm.organism_states[parent_b_id]

        if not state_a.is_alive or not state_b.is_alive:
            raise ValueError("Both parents must be alive to mate.")

        if parent_a.atp_reserve < mating_cost_atp or parent_b.atp_reserve < mating_cost_atp:
            raise ValueError(f"Insufficient ATP for mating: Parent A has {parent_a.atp_reserve}, Parent B has {parent_b.atp_reserve}.")

        # Invariant S1: Check epistemic compatibility
        compat, reason = BilateralQuineSymbiosis.check_mating_compatibility(parent_a, parent_b)
        if not compat:
            raise EpistemicIncompatibilityError(f"Mating rejected: {reason}")

        # Deduct mating fuel from parents
        parent_a.atp_reserve -= mating_cost_atp
        parent_b.atp_reserve -= mating_cost_atp
        state_a.children_count += 1
        state_b.children_count += 1

        # Recombine chromosomes (preserve vital, deduplicate identical expressions)
        child_chromosomes: List[Chromosome] = []
        seen_exprs: Set[str] = set()

        for c in parent_a.chromosomes:
            if c.expression not in seen_exprs:
                child_chromosomes.append(c)
                seen_exprs.add(c.expression)

        for c in parent_b.chromosomes:
            if c.expression not in seen_exprs:
                child_chromosomes.append(c)
                seen_exprs.add(c.expression)

        # Merge active axioms
        child_axioms = sorted(list(set(parent_a.active_axioms).union(set(parent_b.active_axioms))))

        # Merge tombstone registries
        child_registry = EpistemicTombstoneRegistry()
        for tid, t in parent_a.tombstone_registry.tombstones.items():
            child_registry.tombstones[tid] = t
        for tid, t in parent_b.tombstone_registry.tombstones.items():
            child_registry.tombstones[tid] = t

        # Child identity and cryptographic keypair
        lineage_seed = f"{parent_a_id}:{parent_b_id}:{swarm.tick_count}"
        child_sk_hex, child_pk_hex = generate_keypair()
        child_id = f"quine-child-{hashlib.sha256(lineage_seed.encode('utf-8')).hexdigest()[:12]}"

        # Endow child with combined fuel minus metabolic friction
        child_atp = int(mating_cost_atp * 2 * 0.85)

        child_org = EpistemicOrganism(
            organism_id=child_id,
            generation=max(parent_a.generation, parent_b.generation) + 1,
            chromosomes=child_chromosomes,
            public_key_hex=child_pk_hex,
            atp_reserve=child_atp,
            tombstone_registry=child_registry,
            inoculated_tombstones_count=len(child_registry.tombstones),
            active_axioms=child_axioms
        )

        # Place child in nearest adjacent free cell
        cx = (state_a.x + 1) % swarm.grid.width
        cy = (state_a.y + 1) % swarm.grid.height
        child_state = SwarmOrganismState(
            organism_id=child_id,
            x=cx,
            y=cy,
            heading=state_a.heading,
            is_alive=True,
            age_ticks=0
        )

        swarm.add_organism(child_org, child_state, child_pk_hex, child_sk_hex)
        return child_org, child_state


# ============================================================================
# 6. SWARM AGORA COMMONS & CONSTITUTIONAL CANON
# ============================================================================

@dataclass
class SwarmProposal:
    """A theorem motion submitted to the Swarm Agora for collective canonization."""
    proposal_id: str
    author_id: str
    expression: str
    expected_normal_form: str
    evidence_grade: str
    stake_atp: int
    status: str = "PENDING"
    aye_weight: float = 0.0
    nay_weight: float = 0.0
    voters: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "author_id": self.author_id,
            "expression": self.expression,
            "expected_normal_form": self.expected_normal_form,
            "evidence_grade": self.evidence_grade,
            "stake_atp": self.stake_atp,
            "status": self.status,
            "aye_weight": round(self.aye_weight, 2),
            "nay_weight": round(self.nay_weight, 2),
            "voters": self.voters,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> SwarmProposal:
        return cls(
            proposal_id=d["proposal_id"],
            author_id=d["author_id"],
            expression=d["expression"],
            expected_normal_form=d["expected_normal_form"],
            evidence_grade=d["evidence_grade"],
            stake_atp=d["stake_atp"],
            status=d.get("status", "PENDING"),
            aye_weight=d.get("aye_weight", 0.0),
            nay_weight=d.get("nay_weight", 0.0),
            voters=d.get("voters", [])
        )


@dataclass
class SwarmAxiom:
    """A canonized mathematical truth ratified into the swarm constitution."""
    axiom_id: str
    expression: str
    expected_normal_form: str
    ratified_tick: int
    supermajority_ratio: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "axiom_id": self.axiom_id,
            "expression": self.expression,
            "expected_normal_form": self.expected_normal_form,
            "ratified_tick": self.ratified_tick,
            "supermajority_ratio": round(self.supermajority_ratio, 3)
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> SwarmAxiom:
        return cls(
            axiom_id=d["axiom_id"],
            expression=d["expression"],
            expected_normal_form=d["expected_normal_form"],
            ratified_tick=d["ratified_tick"],
            supermajority_ratio=d["supermajority_ratio"]
        )


class SwarmAgoraCommons:
    """Parliamentary engine conducting quadratic voting on candidate theorems."""

    @staticmethod
    def table_proposal(
        swarm: SwarmMembrane,
        author_id: str,
        expression: str,
        expected_normal_form: str,
        evidence_grade: str = "A",
        stake_atp: int = 50
    ) -> SwarmProposal:
        if author_id not in swarm.organisms:
            raise ValueError(f"Author {author_id} not in swarm.")
        author = swarm.organisms[author_id]
        if author.atp_reserve < stake_atp:
            raise ValueError(f"Author has insufficient ATP ({author.atp_reserve} < {stake_atp}).")

        author.atp_reserve -= stake_atp
        pid = f"prop-{hashlib.sha256(f'{author_id}:{expression}:{swarm.tick_count}'.encode('utf-8')).hexdigest()[:8]}"
        proposal = SwarmProposal(
            proposal_id=pid,
            author_id=author_id,
            expression=expression,
            expected_normal_form=expected_normal_form,
            evidence_grade=evidence_grade,
            stake_atp=stake_atp
        )
        return proposal

    @staticmethod
    def vote_and_settle(
        swarm: SwarmMembrane,
        proposal: SwarmProposal,
        supermajority_threshold: float = 0.667,
        quorum_ratio: float = 0.50
    ) -> Tuple[bool, str]:
        living_orgs = [
            (oid, org) for oid, org in swarm.organisms.items()
            if swarm.organism_states[oid].is_alive
        ]
        if not living_orgs:
            proposal.status = "REJECTED"
            return False, "No living organisms in swarm."

        aye_weight = 0.0
        nay_weight = 0.0
        voters = []

        for oid, org in living_orgs:
            # Organism audits the theorem via Church-Rosser reduction
            is_sound = False
            try:
                t = glyph.parse(proposal.expression)
                res = glyph.evaluate(t, max_atp=100)
                expected_t = glyph.parse(proposal.expected_normal_form)
                expected_res = glyph.evaluate(expected_t, max_atp=100)
                if glyph.canonical_bytes(res.normal_form) == glyph.canonical_bytes(expected_res.normal_form):
                    is_sound = True
            except Exception:
                is_sound = False

            # Check if expression is tombstoned in this organism's registry
            if proposal.expression in org.tombstone_registry.tombstones:
                is_sound = False

            # Quadratic weight: floor(sqrt(ATP)) * (1 + 0.1 * num_axioms)
            base_w = math.floor(math.sqrt(max(1, org.atp_reserve)))
            fitness_mult = 1.0 + 0.1 * len(org.active_axioms)
            weight = base_w * fitness_mult

            if is_sound:
                aye_weight += weight
            else:
                nay_weight += weight
            voters.append(oid)

        proposal.aye_weight = aye_weight
        proposal.nay_weight = nay_weight
        proposal.voters = voters

        total_weight = aye_weight + nay_weight
        quorum_met = (len(voters) / len(living_orgs)) >= quorum_ratio

        if not quorum_met or total_weight <= 0:
            proposal.status = "REJECTED"
            return False, "Quorum not met."

        ratio = aye_weight / total_weight
        if ratio >= supermajority_threshold:
            proposal.status = "RATIFIED"
            # Return stake plus reward to author
            if proposal.author_id in swarm.organisms:
                swarm.organisms[proposal.author_id].atp_reserve += proposal.stake_atp + 30

            # Add to canon
            ax_id = f"axiom-{hashlib.sha256(proposal.expression.encode('utf-8')).hexdigest()[:8]}"
            canon_axiom = SwarmAxiom(
                axiom_id=ax_id,
                expression=proposal.expression,
                expected_normal_form=proposal.expected_normal_form,
                ratified_tick=swarm.tick_count,
                supermajority_ratio=ratio
            )
            swarm.canon.append(canon_axiom)

            # Broadcast new axiom to all living organisms
            for _, org in living_orgs:
                if proposal.expression not in org.active_axioms:
                    org.active_axioms.append(proposal.expression)

            return True, f"RATIFIED with {ratio * 100:.1f}% supermajority."
        else:
            proposal.status = "REJECTED"
            return False, f"REJECTED: Supermajority not reached ({ratio * 100:.1f}% < {supermajority_threshold * 100:.1f}%)."


# ============================================================================
# 7. SWARM MEMBRANE MASTER CONTAINER
# ============================================================================

class SwarmMembrane:
    """
    Master Coordinator for the decentralized epistemic swarm membrane.
    Manages grid kinetics, multi-agent lifecycles, gossip cascades, and canon.
    """
    def __init__(self, grid_width: int = 16, grid_height: int = 16):
        self.grid = SwarmMorphogenGrid(width=grid_width, height=grid_height)
        self.organisms: Dict[str, EpistemicOrganism] = {}
        self.organism_states: Dict[str, SwarmOrganismState] = {}
        self.organism_keys: Dict[str, Tuple[str, str]] = {}
        self.canon: List[SwarmAxiom] = []
        self.cascade_history: List[CascadeReport] = []
        self.proposals: List[SwarmProposal] = []
        self.tick_count: int = 0

    def add_organism(
        self,
        organism: EpistemicOrganism,
        state: SwarmOrganismState,
        public_key_hex: str,
        secret_key_hex: str
    ) -> None:
        self.organisms[organism.organism_id] = organism
        self.organism_states[organism.organism_id] = state
        self.organism_keys[organism.organism_id] = (public_key_hex, secret_key_hex)

    def step(self, num_ticks: int = 1) -> Dict[str, Any]:
        """Advances simulation by num_ticks time-steps."""
        total_atp_harvested = 0
        extinctions = 0
        autophagies = 0

        for _ in range(num_ticks):
            self.tick_count += 1
            self.grid.step(dt=1.0)

            for oid, state in list(self.organism_states.items()):
                if not state.is_alive:
                    continue
                org = self.organisms[oid]
                state.age_ticks += 1

                # 1. Living cost
                org.atp_reserve -= 5
                if org.atp_reserve <= 0:
                    state.is_alive = False
                    extinctions += 1
                    self.grid.deposit_biomass(state.x, state.y, atp_amount=30)
                    continue

                # 2. Movement & Energetic Harvesting
                # Organisms move along heading
                dx, dy = state.heading
                state.x = (state.x + dx) % self.grid.width
                state.y = (state.y + dy) % self.grid.height

                # Harvest ATP from new cell
                harvest = self.grid.harvest_atp(state.x, state.y)
                org.atp_reserve += harvest
                total_atp_harvested += harvest

                # 3. Metabolic Homeostasis & Starvation Autophagy
                if org.atp_reserve <= 80:
                    sk = self.organism_keys[oid][1]
                    pk = self.organism_keys[oid][0]
                    report = StarvationAutophagy.trigger_autophagy(org, sk, pk)
                    if report.triggered:
                        autophagies += 1

                # 4. Extinction check
                if org.atp_reserve <= 0:
                    state.is_alive = False
                    extinctions += 1
                    # Decompose biomass back to grid
                    self.grid.deposit_biomass(state.x, state.y, atp_amount=30)

        living_count = sum(1 for s in self.organism_states.values() if s.is_alive)
        herd_immunity_rate = 0.0
        if living_count > 0:
            total_tombstones = sum(len(self.organisms[oid].tombstone_registry.tombstones) for oid, s in self.organism_states.items() if s.is_alive)
            herd_immunity_rate = round(total_tombstones / (living_count * 10.0), 2)

        return {
            "tick": self.tick_count,
            "living_organisms": living_count,
            "total_atp_harvested": total_atp_harvested,
            "autophagies": autophagies,
            "extinctions": extinctions,
            "canonized_axioms": len(self.canon),
            "herd_immunity_rate": herd_immunity_rate,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tick_count": self.tick_count,
            "grid_width": self.grid.width,
            "grid_height": self.grid.height,
            "organisms": {oid: org.to_dict() for oid, org in self.organisms.items()},
            "organism_states": {oid: st.to_dict() for oid, st in self.organism_states.items()},
            "organism_keys": {oid: list(keys) for oid, keys in self.organism_keys.items()},
            "canon": [ax.to_dict() for ax in self.canon],
            "proposals": [p.to_dict() for p in self.proposals],
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> SwarmMembrane:
        swarm = cls(
            grid_width=d.get("grid_width", 16),
            grid_height=d.get("grid_height", 16)
        )
        swarm.tick_count = d.get("tick_count", 0)
        for oid, o_dict in d.get("organisms", {}).items():
            org = EpistemicOrganism.from_dict(o_dict)
            st_dict = d["organism_states"][oid]
            st = SwarmOrganismState.from_dict(st_dict)
            keys = tuple(d["organism_keys"][oid])
            swarm.add_organism(org, st, keys[0], keys[1])
        swarm.canon = [SwarmAxiom.from_dict(ax) for ax in d.get("canon", [])]
        swarm.proposals = [SwarmProposal.from_dict(p) for p in d.get("proposals", [])]
        return swarm


# ============================================================================
# 8. ISO 32000 APPEND-ONLY POLYGLOT SWARM MEMBRANE
# ============================================================================

def generate_swarm_membrane_pdf(
    swarm: SwarmMembrane,
    output_path: str
) -> bytes:
    """
    Creates an ISO 32000 compliant vector PDF polyglot document containing:
      - Vector Swarm Membrane HUD & Population Matrix.
      - 2D Reaction-Diffusion Morphogen Grid Heatmap.
      - Epistemic Inoculation Cascade Graph.
      - Ratified Swarm Canon Table.
      - Embedded JCS-canonical JSON swarm manifest.
      - Embedded self-executing Latin-1 Python runner (`python3 swarm.pdf`).
    """
    living = [oid for oid, st in swarm.organism_states.items() if st.is_alive]
    extinct = [oid for oid, st in swarm.organism_states.items() if not st.is_alive]
    total_atp = sum(swarm.organisms[oid].atp_reserve for oid in living)
    avg_atp = total_atp // max(1, len(living))

    total_inoculated = sum(swarm.organisms[oid].inoculated_tombstones_count for oid in living)
    total_axioms = len(swarm.canon)

    stream_lines = [
        "q",
        # Page background: Deep cosmic obsidian
        "0.03 0.04 0.06 rg",
        "0 0 612 792 re f",

        # Banner Header
        "0.06 0.09 0.13 rg",
        "30 710 552 60 re f",
        "0.15 0.35 0.50 RG 1.5 w",
        "30 710 552 60 re S",
        "BT",
        "/F1 15 Tf",
        "0.95 0.98 1.0 rg",
        "45 745 Td",
        "(%# BLACK-HEART: EPISTEMIC SWARM MEMBRANE) Tj",
        "/F1 9 Tf",
        "0.40 0.80 0.95 rg",
        "0 -20 Td",
        "(SWARM-0.1 | Quine Symbiosis, Morphogen Kinetics & Collective Canon) Tj",
        "ET",

        # Swarm Demographic & Energetics Card
        "0.05 0.07 0.10 rg",
        "30 570 552 125 re f",
        "0.18 0.55 0.40 RG 1.5 w",
        "30 570 552 125 re S",
        "BT",
        "/F1 12 Tf",
        "0.30 0.95 0.60 rg",
        "45 668 Td",
        "(SWARM METRIC & COLONY HOMEOSTASIS) Tj",
        "/F1 9 Tf",
        "0.85 0.90 0.95 rg",
        "0 -20 Td",
        f"(Simulation Tick:    #{swarm.tick_count} | Living Population: {len(living)} / {len(swarm.organisms)} organisms) Tj",
        "0 -15 Td",
        f"(Metabolic Reserves: {total_atp} ATP (Colony Avg: {avg_atp} ATP/org)) Tj",
        "0 -15 Td",
        f"(Herd Immunity:      {total_inoculated} external refutations absorbed | Extinctions: {len(extinct)}) Tj",
        "0 -15 Td",
        f"(Swarm Canon:        {total_axioms} ratified algebraic identities across colony) Tj",
        "ET",

        # Spatial Morphogen Grid Heatmap Box
        "0.04 0.05 0.08 rg",
        "30 310 265 245 re f",
        "0.25 0.40 0.60 RG 1 w",
        "30 310 265 245 re S",
        "BT",
        "/F1 10 Tf",
        "0.70 0.85 1.0 rg",
        "40 535 Td",
        "(MORPHOGEN ARENA (16x16 GRID)) Tj",
        "ET",
    ]

    # Draw 16x16 grid cells inside the box (x: 45 to 275, y: 320 to 520)
    grid_w = swarm.grid.width
    grid_h = swarm.grid.height
    cell_size = 12
    origin_x = 45
    origin_y = 325

    # Draw grid cells
    for gy in range(min(16, grid_h)):
        for gx in range(min(16, grid_w)):
            u, v = swarm.grid.get_concentrations(gx, gy)
            # Map U, V to Cyan/Teal intensity
            r_col = 0.02 + 0.15 * v
            g_col = 0.05 + 0.50 * v
            b_col = 0.10 + 0.60 * (1.0 - u)
            cx = origin_x + gx * cell_size
            cy = origin_y + gy * cell_size
            stream_lines.append(f"{r_col:.2f} {g_col:.2f} {b_col:.2f} rg")
            stream_lines.append(f"{cx} {cy} {cell_size - 1} {cell_size - 1} re f")

    # Overlay living organisms on grid
    for oid in living:
        st = swarm.organism_states[oid]
        ox = origin_x + (st.x % 16) * cell_size + cell_size // 2
        oy = origin_y + (st.y % 16) * cell_size + cell_size // 2
        # Draw glowing dot
        stream_lines.append("1.0 0.85 0.20 rg")
        stream_lines.append(f"{ox - 3} {oy - 3} 6 6 re f")

    # Inoculation & Canon Card (Right side)
    stream_lines.extend([
        "0.04 0.05 0.08 rg",
        "310 310 272 245 re f",
        "0.25 0.40 0.60 RG 1 w",
        "310 310 272 245 re S",
        "BT",
        "/F1 10 Tf",
        "0.70 0.85 1.0 rg",
        "325 535 Td",
        "(EPIDEMIC CASCADES & RATIFIED CANON) Tj",
        "/F1 8 Tf",
        "0.75 0.80 0.85 rg",
        "0 -18 Td",
        f"(Total Cascades Recorded: {len(swarm.cascade_history)}) Tj",
    ])

    # List last 3 cascades
    recent_cascades = swarm.cascade_history[-3:] if swarm.cascade_history else []
    for c in recent_cascades:
        stream_lines.extend([
            "0 -14 Td",
            f"([CASCADE] Target: {c.target_id[:16]}... | Hops: {c.hops_reached} | R0: {c.reproduction_number_r0}) Tj",
        ])

    stream_lines.extend([
        "0 -20 Td",
        "/F1 10 Tf",
        "0.40 0.90 0.70 rg",
        "(RATIFIED SWARM CANON AXIOMS:) Tj",
        "/F1 8 Tf",
        "0.80 0.85 0.90 rg",
    ])

    if swarm.canon:
        for ax in swarm.canon[:4]:
            stream_lines.extend([
                "0 -14 Td",
                f"(* {ax.expression[:28]} = {ax.expected_normal_form[:8]} (Ratified #{ax.ratified_tick})) Tj",
            ])
    else:
        stream_lines.extend([
            "0 -14 Td",
            "(No axioms ratified yet. Submit motions to Swarm Agora.) Tj",
        ])

    stream_lines.append("ET")

    # Organism Census Table (Bottom Card)
    stream_lines.extend([
        "0.05 0.06 0.09 rg",
        "30 50 552 245 re f",
        "0.20 0.25 0.35 RG 1 w",
        "30 50 552 245 re S",
        "BT",
        "/F1 10 Tf",
        "0.90 0.95 1.0 rg",
        "45 275 Td",
        "(ACTIVE ORGANISM CENSUS & CRYPTOGRAPHIC STANDING) Tj",
        "/F1 8 Tf",
        "0.60 0.65 0.75 rg",
        "0 -16 Td",
        "(Organism ID                     | Gen | Pos     | ATP  | Active Genes | Inoculated | Status) Tj",
        "0 -12 Td",
        "(-----------------------------------------------------------------------------------------) Tj",
    ])

    all_org_ids = list(swarm.organisms.keys())[:9]
    for oid in all_org_ids:
        org = swarm.organisms[oid]
        st = swarm.organism_states[oid]
        status_str = "ALIVE" if st.is_alive else "EXTINCT"
        col_str = f"{oid[:28]:<28} | #{org.generation:<2} | ({st.x:>2},{st.y:>2}) | {org.atp_reserve:>4} | {len(org.chromosomes):>12} | {org.inoculated_tombstones_count:>10} | {status_str}"
        stream_lines.extend([
            "0 -13 Td",
            f"({col_str}) Tj",
        ])

    stream_lines.extend([
        "ET",
        # Footer notice
        "BT",
        "/F1 8 Tf",
        "0.40 0.45 0.55 rg",
        "30 25 Td",
        "(ISO 32000 Polyglot: Run 'python3 <file>.pdf' for trustless cryptographic verification) Tj",
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

    manifest_json = json.dumps(swarm.to_dict(), sort_keys=True)
    manifest_line = (
        b"# %" + bytes([0xf0, 0x9f, 0x96, 0xa4])
        + b" SWARM_MEMBRANE_MANIFEST: " + manifest_json.encode("utf-8") + b"\n"
    )

    py_runner = f"""
# coding: latin-1
import sys, json, os

cwd = os.getcwd()
if cwd not in sys.path:
    sys.path.insert(0, cwd)

def audit_swarm_membrane():
    print("\\033[1;36m" + "=" * 70)
    print("  %# EPISTEMIC SWARM MEMBRANE AUDITOR (SWARM-0.1)")
    print("=" * 70 + "\\033[0m")
    with open(__file__, 'rb') as f:
        data = f.read()
    prefix = bytes([0x23, 0x20, 0x25, 0xf0, 0x9f, 0x96, 0xa4]) + b" SWARM_MEMBRANE_MANIFEST: "
    idx = data.rfind(prefix)
    if idx == -1:
        print("\\033[1;31m[-] No swarm membrane manifest found.\\033[0m")
        sys.exit(1)
    end = data.find(b"\\n", idx)
    swarm_json = json.loads(data[idx + len(prefix):end].decode('utf-8'))
    import epistemic_swarm
    swarm = epistemic_swarm.SwarmMembrane.from_dict(swarm_json)

    living = [oid for oid, st in swarm.organism_states.items() if st.is_alive]
    print(f"[*] Simulation Tick: #{swarm.tick_count}")
    print(f"[*] Population: {{len(living)}} living / {{len(swarm.organisms)}} total organisms")
    print(f"[*] Ratified Canon Axioms: {{len(swarm.canon)}}")

    for ax in swarm.canon:
        print(f"  [AXIOM] {{ax.expression}} == {{ax.expected_normal_form}} (Supermajority: {{ax.supermajority_ratio * 100:.1f}}%)")

    all_valid = True
    for oid, org in swarm.organisms.items():
        for tid, t in org.tombstone_registry.tombstones.items():
            if not t.verify_signature():
                print(f"\\033[1;31m[!] Signature INVALID for tombstone '{{tid}}' in {{oid}}\\033[0m")
                all_valid = False

    print("\\033[1;36m" + "=" * 70 + "\\033[0m")
    if all_valid:
        print("\\033[1;32m[+] Swarm membrane state and cryptographic signatures verified.\\033[0m")
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    audit_swarm_membrane()
"""

    header_text = (
        f"#!{sys.executable}\n"
        "# coding: latin-1\n"
        "# ============================================================================\n"
        "# %# PROJECT BLACK-HEART: EPISTEMIC SWARM MEMBRANE (ISO 32000 POLYGLOT)\n"
        "# ============================================================================\n"
        "r'''\n"
    ).encode("latin-1")

    polyglot = header_text + body + xref + trailer + manifest_line + b"'''\n" + py_runner.encode("latin-1")
    with open(output_path, "wb") as f:
        f.write(polyglot)
    return polyglot


def append_swarm_membrane_hud(
    source_pdf_bytes: bytes,
    output_path: str,
    swarm: SwarmMembrane
) -> bytes:
    """
    Appends an ISO 32000 §7.5.6 incremental update with the Swarm Membrane HUD
    to an existing polyglot document. Preserves byte prefix:
    output.startswith(source_pdf_bytes) == True.
    """
    living = [oid for oid, st in swarm.organism_states.items() if st.is_alive]
    total_atp = sum(swarm.organisms[oid].atp_reserve for oid in living)
    avg_atp = total_atp // max(1, len(living))

    stream_lines = [
        "q",
        "0.03 0.04 0.06 rg",
        "0 0 612 792 re f",
        "0.06 0.09 0.13 rg",
        "30 710 552 60 re f",
        "0.15 0.35 0.50 RG 1.5 w",
        "30 710 552 60 re S",
        "BT",
        "/F1 15 Tf",
        "0.95 0.98 1.0 rg",
        "45 745 Td",
        "(%# BLACK-HEART: EPISTEMIC SWARM MEMBRANE) Tj",
        "/F1 9 Tf",
        "0.40 0.80 0.95 rg",
        "0 -20 Td",
        f"(SWARM-0.1 | Incremental Update | Tick #{swarm.tick_count}) Tj",
        "ET",
        "0.05 0.07 0.10 rg",
        "30 570 552 125 re f",
        "0.18 0.55 0.40 RG 1.5 w",
        "30 570 552 125 re S",
        "BT",
        "/F1 12 Tf",
        "0.30 0.95 0.60 rg",
        "45 668 Td",
        "(SWARM HOMEOSTASIS UPDATE) Tj",
        "/F1 9 Tf",
        "0.85 0.90 0.95 rg",
        "0 -20 Td",
        f"(Tick #{swarm.tick_count} | Living: {len(living)} organisms | Total ATP: {total_atp}) Tj",
        "0 -15 Td",
        f"(Ratified Canon Axioms: {len(swarm.canon)}) Tj",
        "ET",
        "Q"
    ]
    content_bytes = "\n".join(stream_lines).encode("latin-1")

    obj_num = 100 + swarm.tick_count * 2
    c_obj_num = obj_num + 1

    content_obj = (
        f"{c_obj_num} 0 obj\n<< /Length {len(content_bytes)} >>\nstream\n".encode("latin-1")
        + content_bytes
        + b"\nendstream\nendobj\n"
    )

    page_obj = (
        f"{obj_num} 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        f"/Contents {c_obj_num} 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
    ).encode("latin-1")

    new_body = page_obj + content_obj

    start_xref = len(source_pdf_bytes)
    xref_table = (
        f"xref\n{obj_num} 2\n"
        f"{start_xref:010d} 00000 n \n"
        f"{start_xref + len(page_obj):010d} 00000 n \n"
    ).encode("latin-1")

    trailer_dict = (
        f"trailer\n<< /Size {c_obj_num + 1} /Root 1 0 R >>\n"
        f"startxref\n{start_xref + len(new_body)}\n%%EOF\n"
    ).encode("latin-1")

    manifest_json = json.dumps(swarm.to_dict(), sort_keys=True)
    manifest_line = (
        b"# %" + bytes([0xf0, 0x9f, 0x96, 0xa4])
        + b" SWARM_MEMBRANE_MANIFEST: " + manifest_json.encode("utf-8") + b"\n"
    )

    incremental_update = source_pdf_bytes + new_body + xref_table + trailer_dict + manifest_line
    with open(output_path, "wb") as f:
        f.write(incremental_update)
    return incremental_update
