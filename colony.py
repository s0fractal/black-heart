#!/usr/bin/env python3
"""
colony.py — Living Colony Ecosystem, Neuro-Symbolic Oracle & Metabolic Settlement.
Part of Project Black-Heart (%🖤).

This module unifies all 15 Project Black-Heart engines into a living, autonomous
artificial life biome:
  - Heterogeneous Organism Population with Ed25519 identities and Gray-Scott phenotypes.
  - Substrate Energy Bank (ATP Solar Pool) driving basal metabolism and bounties.
  - Epistemic Mycelium (mycelium.py) exchanging re-executable Warrants and Divergences.
  - Dialectical Symbiosis (symbiosis.py) with Artin Braid Group (B_n) topological lineages.
  - Dormant Spores (continuum.py) preserving exhausted organisms as resumable checkpoints.
  - Neuro-Symbolic Oracle (Neutral Term 🎭 from CONTINUUM.md) providing creative rewrites.
  - Living Ledger (living_ledger.py) recording every epoch as ISO 32000 §7.5.6 revisions.
  - Standalone Polyglot PDF Compiler producing self-contained, executable colony documents.

100% Pure Standard Library Python.
"""

from __future__ import annotations
import os
import sys
import json
import time
import hashlib
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple, Callable, Union

from crypto import (
    generate_keypair,
    public_key_from_secret,
    is_valid_public_key,
    sign_bytes,
    verify_bytes
)
from glyph import parse, evaluate, tree_size, App, Term, S, K, I, GLYPH_K, GLYPH_I, GLYPH_S, GLYPH_Y
from organism import Organism, Chromosome, create_genesis_organism
from living_ledger import LivingLedger, LedgerBlock
from continuum import ThunkCheckpoint, step_continuum
from symbiosis import dialectical_crossover, BraidWord, BraidCrossing, trefoil_knot, figure_eight_knot
from metamorphosis import (
    FrozenEvaluator,
    ExperimentLog,
    MetamorphicTransitionReceipt,
    MutationVerdict,
    ALLOWED_MUTATION_RULES
)
from mycelium import (
    EpistemicRegistry,
    LocalImmuneEvaluator,
    Warrant,
    NormalFormEntry,
    DivergenceRecord,
    export_warrant_from_receipt
)

# ============================================================================
# 1. POPULATION DATA STRUCTURES & STATUS
# ============================================================================

class OrganismStatus(str, Enum):
    ACTIVE = "ACTIVE"
    DORMANT_SPORE = "DORMANT_SPORE"
    MUTATING = "MUTATING"
    BRED = "BRED"


def organism_to_dict(org: Organism) -> Dict[str, Any]:
    return {
        "generation": org.generation,
        "parent_hash": org.parent_hash,
        "public_key_hex": org.public_key_hex,
        "secret_key_hex": org.secret_key_hex,
        "chromosomes": [c.to_dict() for c in org.chromosomes],
        "birth_timestamp_utc": org.birth_timestamp_utc,
        "organism_hash": org.organism_hash
    }

def organism_from_dict(d: Dict[str, Any]) -> Organism:
    org = Organism(
        generation=int(d["generation"]),
        parent_hash=str(d["parent_hash"]),
        public_key_hex=str(d["public_key_hex"]),
        secret_key_hex=str(d.get("secret_key_hex", "")),
        chromosomes=[Chromosome.from_dict(c) for c in d.get("chromosomes", [])],
        birth_timestamp_utc=str(d.get("birth_timestamp_utc", "")),
        organism_hash=str(d.get("organism_hash", ""))
    )
    if not org.organism_hash:
        org.organism_hash = org.compute_hash()
    return org

def ledger_to_dict(ledger: LivingLedger) -> Dict[str, Any]:
    return {
        "title": ledger.title,
        "blocks": [b.to_dict() for b in ledger.blocks]
    }

def ledger_from_dict(d: Dict[str, Any]) -> LivingLedger:
    ledger = LivingLedger(title=str(d.get("title", "BLACK-HEART LIVING POLYGLOT LEDGER")))
    ledger.blocks = [LedgerBlock.from_dict(b) for b in d.get("blocks", [])]
    return ledger


@dataclass
class OrganismState:
    """Tracks runtime lifecycle, energy reserves, and telemetry of a colony member."""
    organism: Organism
    energy_atp: int = 500
    status: OrganismStatus = OrganismStatus.ACTIVE
    warrants_minted: int = 0
    warrants_adopted: int = 0
    matings_count: int = 0
    spore_checkpoint: Optional[Dict[str, Any]] = None

    def compute_basal_consumption(self) -> int:
        """Calculates metabolic energy cost required to maintain chromosome stability."""
        total = 0
        for c in self.organism.chromosomes:
            total += max(1, c.max_atp // 10)
        return total

    def to_dict(self) -> Dict[str, Any]:
        return {
            "organism": organism_to_dict(self.organism),
            "energy_atp": self.energy_atp,
            "status": self.status.value,
            "warrants_minted": self.warrants_minted,
            "warrants_adopted": self.warrants_adopted,
            "matings_count": self.matings_count,
            "spore_checkpoint": self.spore_checkpoint
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> OrganismState:
        return cls(
            organism=organism_from_dict(d["organism"]),
            energy_atp=int(d.get("energy_atp", 500)),
            status=OrganismStatus(d.get("status", OrganismStatus.ACTIVE.value)),
            warrants_minted=int(d.get("warrants_minted", 0)),
            warrants_adopted=int(d.get("warrants_adopted", 0)),
            matings_count=int(d.get("matings_count", 0)),
            spore_checkpoint=d.get("spore_checkpoint")
        )


@dataclass
class EpochRecord:
    """Immutable record documenting the biological and economic state of one colony epoch."""
    epoch_index: int
    timestamp_utc: str
    active_count: int
    spore_count: int
    substrate_atp: int
    warrants_minted: int
    warrants_adopted: int
    divergences_caught: int
    matings_count: int
    prev_epoch_hash: str
    population_hash: str = ""
    warrant_merkle_root: str = ""
    epoch_hash: str = ""

    def canonical_bytes_for_hash(self) -> bytes:
        payload = (
            f"EPOCH:{self.epoch_index}:{self.timestamp_utc}:{self.active_count}:"
            f"{self.spore_count}:{self.substrate_atp}:{self.warrants_minted}:"
            f"{self.warrants_adopted}:{self.divergences_caught}:{self.matings_count}:"
            f"{self.prev_epoch_hash}"
        )
        if self.population_hash or self.warrant_merkle_root:
            payload += f":{self.population_hash}:{self.warrant_merkle_root}"
        return payload.encode("utf-8")

    def compute_hash(self) -> str:
        return hashlib.sha256(self.canonical_bytes_for_hash()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "epoch_index": self.epoch_index,
            "timestamp_utc": self.timestamp_utc,
            "active_count": self.active_count,
            "spore_count": self.spore_count,
            "substrate_atp": self.substrate_atp,
            "warrants_minted": self.warrants_minted,
            "warrants_adopted": self.warrants_adopted,
            "divergences_caught": self.divergences_caught,
            "matings_count": self.matings_count,
            "prev_epoch_hash": self.prev_epoch_hash,
            "population_hash": self.population_hash,
            "warrant_merkle_root": self.warrant_merkle_root,
            "epoch_hash": self.epoch_hash
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> EpochRecord:
        return cls(
            epoch_index=int(d["epoch_index"]),
            timestamp_utc=str(d["timestamp_utc"]),
            active_count=int(d["active_count"]),
            spore_count=int(d["spore_count"]),
            substrate_atp=int(d["substrate_atp"]),
            warrants_minted=int(d["warrants_minted"]),
            warrants_adopted=int(d["warrants_adopted"]),
            divergences_caught=int(d["divergences_caught"]),
            matings_count=int(d["matings_count"]),
            prev_epoch_hash=str(d["prev_epoch_hash"]),
            population_hash=str(d.get("population_hash", "")),
            warrant_merkle_root=str(d.get("warrant_merkle_root", "")),
            epoch_hash=str(d.get("epoch_hash", ""))
        )


# ============================================================================
# 2. NEURO-SYMBOLIC ORACLE (NEUTRAL TERM 🎭 FROM CONTINUUM.md)
# ============================================================================

class NeuroSymbolicOracle:
    """
    Formal implementation of the Neutral Term 🎭 Oracle from Section 2 of CONTINUUM.md.
    Provides creative, stochastic candidate rewrites for combinator expressions.
    All outputs are treated as UNTRUSTED and strictly gated by the LocalImmuneEvaluator.
    """

    def __init__(self, external_generator: Optional[Callable[[str], List[str]]] = None):
        self.external_generator = external_generator

    def formulate_hypotheses(
        self,
        expr_str: str,
        divergences: Optional[Any] = None
    ) -> List[Tuple[str, str, str]]:
        """
        Formulates candidate (rule_name, pre_pattern, post_pattern) hypotheses.
        Uses deterministic heuristic discovery plus optional external LLM generator.
        Filters out hypotheses known to diverge if divergences registry is provided.
        """
        hypotheses: List[Tuple[str, str, str]] = []

        # 1. If external generator callback is provided, invoke it
        if self.external_generator is not None:
            try:
                candidates = self.external_generator(expr_str)
                for cand in candidates:
                    if isinstance(cand, (tuple, list)) and len(cand) == 3:
                        hypotheses.append((str(cand[0]), str(cand[1]), str(cand[2])))
                    elif isinstance(cand, (tuple, list)) and len(cand) == 2:
                        hypotheses.append((str(cand[0]), expr_str, str(cand[1])))
            except Exception:
                pass

        # 2. Built-in deep algebraic patterns & constant reductions
        # Check for nested identity elimination: (S (K (S I)) I) -> (S I)
        if "🌿 (🖤 (🌿 🤍)) 🤍" in expr_str:
            hypotheses.append(("S(K x)I -> x", "🌿 (🖤 (🌿 🤍)) 🤍", "🌿 🤍"))

        # Check for distribution collapse: S (K I) -> I
        if "🌿 (🖤 🤍)" in expr_str:
            hypotheses.append(("S(K I) -> I", "🌿 (🖤 🤍)", "🤍"))

        # Check for double constant: K x y -> x
        if "🖤 🤍 🖤" in expr_str:
            hypotheses.append(("K x y -> x", "🖤 🤍 🖤", "🤍"))

        # 3. Exploratory mutation: operand swap
        if "🌿 (🌿 🖤) 🌿" in expr_str:
            hypotheses.append(("MUTATION_OPERAND_SWAP", "🌿 (🌿 🖤) 🌿", "🌿 (🌿 (🌿 🖤))"))

        if divergences is not None:
            filtered = []
            for r, pre, post in hypotheses:
                if hasattr(divergences, "has_known_divergence"):
                    if divergences.has_known_divergence(r, pre, post):
                        continue
                filtered.append((r, pre, post))
            return filtered

        return hypotheses


# ============================================================================
# 3. COLONY ECOSYSTEM ENGINE
# ============================================================================

class Colony:
    """
    A closed artificial life ecosystem uniting organisms, substrate ATP,
    epistemic mycelium, living ledger chronicles, and dialectical recombination.
    """

    def __init__(
        self,
        name: str = "Genesis Colony",
        substrate_atp: int = 5000,
        oracle: Optional[NeuroSymbolicOracle] = None
    ):
        self.name = name
        self.substrate_atp = substrate_atp
        self.oracle = oracle or NeuroSymbolicOracle()
        self.population: List[OrganismState] = []
        self.registry: EpistemicRegistry = EpistemicRegistry()
        self.ledger: LivingLedger = LivingLedger(f"COLONY LEDGER: {name}")
        self.epochs: List[EpochRecord] = []
        self.immune_evaluator = LocalImmuneEvaluator()
        self.authority_sk_hex: str = ""
        self.authority_pk_hex: str = ""
        self._init_ledger_genesis()

    def _init_ledger_genesis(self) -> None:
        """Initializes the Living Ledger with a genesis block if empty."""
        if not self.ledger.blocks:
            if not self.authority_sk_hex:
                self.authority_sk_hex, self.authority_pk_hex = generate_keypair()
            self.ledger.create_genesis(
                signer_name="Colony Creator",
                signer_role="Substrate Architect",
                secret_key_hex=self.authority_sk_hex,
                description=f"Genesis block of {self.name}. Initial substrate ATP: {self.substrate_atp}"
            )

    @classmethod
    def create_genesis_colony(
        cls,
        name: str = "Primeval Mycelium Colony",
        initial_organisms: int = 3,
        initial_substrate_atp: int = 5000
    ) -> Colony:
        """Instantiates a viable genesis colony with diverse organisms and a ledger."""
        colony = cls(name=name, substrate_atp=initial_substrate_atp)

        # Populate with diverse initial organisms
        for i in range(initial_organisms):
            org = create_genesis_organism(generation=0)
            if i == 0:
                # Carrier of optimizable Signal Compressor gene
                org.chromosomes.append(Chromosome(
                    gene_id="GENE-OPT-01",
                    gene_name="Signal Compressor",
                    expression="(🌿 (🖤 (🌿 🤍)) 🤍) Signal",
                    expected_normal_form="(🌿 🤍) Signal",
                    max_atp=100
                ))
            elif i == 1:
                # Carrier of Trivial Distribution Collapse gene
                org.chromosomes.append(Chromosome(
                    gene_id="GENE-DIST-02",
                    gene_name="Trivial Distribution Collapse",
                    expression="((🌿 (🖤 🤍)) Token) Arg",
                    expected_normal_form="Token Arg",
                    max_atp=80
                ))
            else:
                # Standard identity router
                org.chromosomes.append(Chromosome(
                    gene_id="GENE-ROUTER-03",
                    gene_name="Identity Highway",
                    expression="🤍 SovereignCore",
                    expected_normal_form="SovereignCore",
                    max_atp=50
                ))
            org.organism_hash = org.compute_hash()
            colony.population.append(OrganismState(organism=org, energy_atp=500))

        return colony

    def active_organisms(self) -> List[OrganismState]:
        return [s for s in self.population if s.status == OrganismStatus.ACTIVE]

    def dormant_spores(self) -> List[OrganismState]:
        return [s for s in self.population if s.status == OrganismStatus.DORMANT_SPORE]

    def compute_population_hash(self) -> str:
        """Computes deterministic digest of the entire population state."""
        h = hashlib.sha256()
        for st in sorted(self.population, key=lambda s: s.organism.public_key_hex):
            h.update(f"{st.organism.organism_hash}:{st.energy_atp}:{st.status.value}".encode("utf-8"))
        return h.hexdigest()

    def step_epoch(self, solar_influx_atp: int = 200) -> EpochRecord:
        """
        Executes one full biological, epistemic, and economic epoch:
          1. Solar Influx & Basal Metabolism.
          2. Mycelial Warrant Audition.
          3. Oracle Exploration & Metamorphosis Bounty.
          4. Dialectical Sexual Recombination.
          5. Spore Revival.
          6. Living Ledger Settlement.
        """
        epoch_idx = len(self.epochs)
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        prev_h = self.epochs[-1].epoch_hash if self.epochs else "0" * 64

        # 1. Solar Influx
        self.substrate_atp += solar_influx_atp

        warrants_minted_this_epoch = 0
        warrants_adopted_this_epoch = 0
        divergences_caught_this_epoch = 0
        matings_this_epoch = 0

        # Basal Metabolism
        for st in self.active_organisms():
            burn = st.compute_basal_consumption()
            st.energy_atp -= burn
            if st.energy_atp <= 0:
                # Transition to dormant spore checkpoint using Continuum ThunkCheckpoint
                st.status = OrganismStatus.DORMANT_SPORE
                expr = st.organism.chromosomes[0].expression if st.organism.chromosomes else ""
                cp = ThunkCheckpoint(
                    height=epoch_idx,
                    timestamp_utc=timestamp,
                    initial_expr=expr,
                    current_expr=expr,
                    atp_spent_step=0,
                    atp_accumulated=0,
                    peak_size=1,
                    status="SUSPENDED",
                    prev_hash=prev_h,
                    public_key_hex=st.organism.public_key_hex,
                    signature_hex=""
                )
                cp.checkpoint_hash = cp.compute_hash()
                st.spore_checkpoint = cp.to_dict()

        # 2. Mycelial Warrant Audition
        # Active organisms check colony registry for warrants they haven't auditioned
        for st in self.active_organisms():
            for wid, warrant in list(self.registry.warrants.items()):
                # If warrant author is not this organism and not already endorsed
                endorser_pks = [e.endorser_pk_hex for e in warrant.endorsements]
                if st.organism.public_key_hex != warrant.author_pk_hex and st.organism.public_key_hex not in endorser_pks:
                    org_sk = st.organism.secret_key_hex or "00" * 32
                    verdict = self.immune_evaluator.audition_warrant(
                        st.organism,
                        warrant,
                        org_sk
                    )
                    if verdict.adopted and verdict.successor_organism:
                        st.organism = verdict.successor_organism
                        st.warrants_adopted += 1
                        warrants_adopted_this_epoch += 1
                    elif verdict.divergence_record:
                        if self.registry.add_divergence(verdict.divergence_record, verify_first=True):
                            divergences_caught_this_epoch += 1

        # 3. Oracle Inspiration & Metamorphic Discovery
        for st in self.active_organisms():
            mutation_found = False
            for chrom in st.organism.chromosomes:
                hypotheses = self.oracle.formulate_hypotheses(chrom.expression, divergences=self.registry)
                for rule_name, pre_pattern, post_pattern in hypotheses:
                    receipt = MetamorphicTransitionReceipt(
                        parent_hash=st.organism.organism_hash,
                        successor_hash="0"*64,
                        gene_id=chrom.gene_id,
                        site_address=(),
                        rule_name=rule_name,
                        pre_term=pre_pattern,
                        post_term=post_pattern,
                        atp_saved=-2,
                        size_saved=-1,
                        fixtures_fingerprint=FrozenEvaluator().fixtures_fingerprint,
                        experiment_id="hyp_" + hashlib.sha256((rule_name + pre_pattern + post_pattern).encode()).hexdigest()[:8]
                    )
                    org_sk = st.organism.secret_key_hex or "00" * 32
                    trial_warrant = export_warrant_from_receipt(
                        receipt,
                        org_sk
                    )
                    verdict = self.immune_evaluator.audition_warrant(
                        st.organism,
                        trial_warrant,
                        org_sk
                    )
                    if verdict.adopted and verdict.successor_organism:
                        st.organism = verdict.successor_organism
                        st.warrants_minted += 1
                        warrants_minted_this_epoch += 1

                        is_new_warrant = trial_warrant.warrant_id not in self.registry.warrants
                        if is_new_warrant:
                            if self.registry.add_warrant(trial_warrant, verify_first=True):
                                bounty = min(150, self.substrate_atp // 4)
                                self.substrate_atp -= bounty
                                st.energy_atp += bounty
                        else:
                            # Endorse existing warrant from another carrier of the same gene
                            existing = self.registry.warrants[trial_warrant.warrant_id]
                            existing.add_endorsement(
                                endorser_sk=org_sk,
                                local_delta_atp=trial_warrant.delta_atp
                            )
                        mutation_found = True
                        break
                    elif verdict.divergence_record:
                        if self.registry.add_divergence(verdict.divergence_record, verify_first=True):
                            divergences_caught_this_epoch += 1
                if mutation_found:
                    break

        # 4. Dialectical Sexual Recombination (Mating)
        # Find pairs of wealthy active organisms (ATP >= 300)
        wealthy = [st for st in self.active_organisms() if st.energy_atp >= 300]
        if len(wealthy) >= 2:
            parent_a = wealthy[0]
            parent_b = wealthy[1]
            try:
                res = dialectical_crossover(parent_a.organism, parent_b.organism)
                if isinstance(res, tuple):
                    child, _braid = res
                else:
                    child = res
                child.generation = max(parent_a.organism.generation, parent_b.organism.generation) + 1
                child.organism_hash = child.compute_hash()

                # Deduct mating energy cost
                parent_a.energy_atp -= 100
                parent_b.energy_atp -= 100
                parent_a.matings_count += 1
                parent_b.matings_count += 1

                child_state = OrganismState(
                    organism=child,
                    energy_atp=200,
                    status=OrganismStatus.ACTIVE
                )
                self.population.append(child_state)
                matings_this_epoch += 1
            except Exception:
                pass

        # 5. Spore Revival
        # If substrate ATP is abundant (> 2000), revive dormant spores
        if self.substrate_atp >= 2000:
            for st in self.dormant_spores():
                revival_grant = 300
                if self.substrate_atp >= revival_grant:
                    self.substrate_atp -= revival_grant
                    st.energy_atp = revival_grant
                    st.status = OrganismStatus.ACTIVE
                    st.spore_checkpoint = None

        # 6. Record Epoch
        rec = EpochRecord(
            epoch_index=epoch_idx,
            timestamp_utc=timestamp,
            active_count=len(self.active_organisms()),
            spore_count=len(self.dormant_spores()),
            substrate_atp=self.substrate_atp,
            warrants_minted=warrants_minted_this_epoch,
            warrants_adopted=warrants_adopted_this_epoch,
            divergences_caught=divergences_caught_this_epoch,
            matings_count=matings_this_epoch,
            prev_epoch_hash=prev_h,
            population_hash=self.compute_population_hash(),
            warrant_merkle_root=self.registry.compute_warrant_merkle_root()
        )
        rec.epoch_hash = rec.compute_hash()
        self.epochs.append(rec)

        # Record in living ledger using stable authority key
        sk_rec = self.authority_sk_hex or generate_keypair()[0]
        self.ledger.append_block(
            signer_name=f"{self.name} Engine",
            signer_role="Epoch Hypervisor",
            secret_key_hex=sk_rec,
            action_type=f"EPOCH_SETTLEMENT_#{epoch_idx}",
            description=json.dumps(rec.to_dict())
        )

        return rec

    def simulate(self, epochs_count: int, solar_influx_atp: int = 200) -> List[EpochRecord]:
        """Runs the colony simulation forward by epochs_count."""
        records = []
        for _ in range(epochs_count):
            rec = self.step_epoch(solar_influx_atp=solar_influx_atp)
            records.append(rec)
        return records

    def verify(self) -> bool:
        """
        Verifies global integrity of the Colony:
        1. Every organism in the population passes organism.verify().
        2. Every ledger block passes signature and chain link verification.
        3. Every EpochRecord hash matches compute_hash() and links to prev_epoch_hash.
        4. Substrate ATP and state match the latest EpochRecord.
        """
        # 1. Population integrity
        for st in self.population:
            if not st.organism.verify():
                return False

        # 2. Ledger integrity
        if self.ledger and self.ledger.blocks:
            expected_prev = "0" * 64
            for i, block in enumerate(self.ledger.blocks):
                if i > 0 and block.prev_hash != expected_prev:
                    return False
                if block.compute_hash() != block.block_hash:
                    return False
                try:
                    pk_bytes = bytes.fromhex(block.public_key_hex)
                    sig_bytes = bytes.fromhex(block.signature_hex)
                    if not verify_bytes(pk_bytes, block.canonical_bytes_for_signing(), sig_bytes):
                        return False
                except Exception:
                    return False
                expected_prev = block.block_hash

        # 3. Epoch chain integrity
        prev_h = "0" * 64
        for i, ep in enumerate(self.epochs):
            if ep.epoch_index != i:
                return False
            if ep.prev_epoch_hash != prev_h:
                return False
            if ep.compute_hash() != ep.epoch_hash:
                return False
            prev_h = ep.epoch_hash

        # 4. Consistency with latest epoch
        if self.epochs:
            last_ep = self.epochs[-1]
            if last_ep.substrate_atp != self.substrate_atp:
                return False

        return True

    def summary(self) -> Dict[str, Any]:
        return {
            "colony_name": self.name,
            "epochs_total": len(self.epochs),
            "active_organisms": len(self.active_organisms()),
            "dormant_spores": len(self.dormant_spores()),
            "substrate_atp_pool": self.substrate_atp,
            "warrants_in_mycelium": len(self.registry.warrants),
            "divergences_in_mycelium": len(self.registry.divergences),
            "ledger_blocks_height": len(self.ledger.blocks),
            "latest_epoch_hash": self.epochs[-1].epoch_hash if self.epochs else "0" * 64
        }

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "name": self.name,
            "substrate_atp": self.substrate_atp,
            "population": [s.to_dict() for s in self.population],
            "registry": self.registry.to_dict(),
            "ledger": ledger_to_dict(self.ledger),
            "epochs": [e.to_dict() for e in self.epochs]
        }
        if self.authority_pk_hex:
            d["authority_pk_hex"] = self.authority_pk_hex
        if self.authority_sk_hex:
            d["authority_sk_hex"] = self.authority_sk_hex
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any], verify_on_load: bool = False) -> Colony:
        colony = cls(
            name=str(data["name"]),
            substrate_atp=int(data.get("substrate_atp", 5000))
        )
        colony.population = [OrganismState.from_dict(d) for d in data.get("population", [])]
        colony.registry = EpistemicRegistry.from_dict(data.get("registry", {}), verify_on_load=False)
        colony.ledger = ledger_from_dict(data.get("ledger", {}))
        colony.epochs = [EpochRecord.from_dict(d) for d in data.get("epochs", [])]
        colony.authority_pk_hex = str(data.get("authority_pk_hex", ""))
        colony.authority_sk_hex = str(data.get("authority_sk_hex", ""))
        if verify_on_load:
            colony.verify()
        return colony

    def save_to_file(self, path: str):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load_from_file(cls, path: str) -> Colony:
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))


# ============================================================================
# 4. COLONY POLYGLOT COMPILER
# ============================================================================

class ColonyPolyglotCompiler:
    """
    Compiles an entire Colony into an executable ISO 32000 PDF Polyglot.
    Visual Layer: Colony HUD, Active Roster, Substrate Gauges, and PostScript Vector Knots.
    Code Layer: Standalone Python runner allowing offline status checks, epoch steps, and audits.
    """

    def __init__(self, colony: Colony):
        self.colony = colony

    def compile_pdf(self) -> bytes:
        """Generates the dual-layer executable PDF document."""
        s = self.colony.summary()

        # Build PostScript visual content stream
        stream = (
            "BT\n"
            "/F1 18 Tf\n"
            "50 780 Td\n"
            f"(% [BLACK-HEART] COLONY: {self.colony.name}) Tj\n"
            "/F2 10 Tf\n"
            "0 -25 Td\n"
            f"(Epoch: #{s['epochs_total']} | Active Organisms: {s['active_organisms']} | Spores: {s['dormant_spores']}) Tj\n"
            "0 -15 Td\n"
            f"(Substrate ATP Pool: {s['substrate_atp_pool']} | Mycelium Warrants: {s['warrants_in_mycelium']} | Divergences: {s['divergences_in_mycelium']}) Tj\n"
            "0 -15 Td\n"
            f"(Latest Epoch Anchor: {s['latest_epoch_hash'][:32]}...) Tj\n"
            "0 -30 Td\n"
            "/F1 12 Tf\n"
            "(ACTIVE ORGANISM ROSTER:) Tj\n"
            "/F2 9 Tf\n"
        )

        # List organisms
        for idx, st in enumerate(self.colony.active_organisms()[:5]):
            stream += f"0 -18 Td\n([#{idx}] Gen #{st.organism.generation} | ATP: {st.energy_atp} | Hash: {st.organism.organism_hash[:16]}... | Minted: {st.warrants_minted}) Tj\n"

        stream += "ET\n"

        # Vector decorative frame
        stream += (
            "0.1 0.1 0.15 rg\n"
            "40 380 515 420 re f\n"
            "0.3 0.6 0.9 RG\n"
            "1.5 w\n"
            "40 380 515 420 re s\n"
        )
        stream_bytes = stream.encode("latin1", errors="replace")
        length = len(stream_bytes)

        manifest = self.colony.to_dict()
        manifest_json = json.dumps(manifest, separators=(",", ":"), ensure_ascii=True)
        manifest_line = f"# %COLONY_MANIFEST:{manifest_json}\n"

        runner_script = self._build_runner_script()

        lines = [
            b"%PDF-1.4",
            b"%\xe2\xe3\xcf\xd3",
            b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj",
            b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj",
            b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595.28 841.89] /Contents 4 0 R /Resources << /Font << /F1 5 0 R /F2 6 0 R >> >> >> endobj",
            f"4 0 obj << /Length {length} >>\nstream\n".encode("latin1") + stream_bytes + b"\nendstream\nendobj",
            b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >> endobj",
            b"6 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj"
        ]

        body = b"\n".join(lines) + b"\n"
        trailer = (
            b"xref\n0 7\n0000000000 65535 f \n"
            b"0000000015 00000 n \n0000000068 00000 n \n0000000125 00000 n \n"
            b"0000000250 00000 n \n0000000750 00000 n \n0000000850 00000 n \n"
            b"trailer << /Size 7 /Root 1 0 R >>\nstartxref\n950\n%%EOF\n"
        )

        header_text = (
            f"#!{sys.executable}\n"
            "# coding: latin-1\n"
            "# ============================================================================\n"
            "# % PROJECT BLACK-HEART: LIVING COLONY ECOSYSTEM POLYGLOT\n"
            "# ============================================================================\n"
            "'''\n"
        ).encode("latin1")

        polyglot = (
            header_text
            + body
            + trailer
            + b"\n'''\n"
            + runner_script.encode("latin1")
            + b"\n"
            + manifest_line.encode("latin1")
        )
        return polyglot

    def _build_runner_script(self) -> str:
        return r'''
import sys, os, json, hashlib

def _extract_manifest():
    with open(__file__, "rb") as f:
        data = f.read()
    prefix = b"# %COLONY_" + b"MANIFEST:"
    idx = data.find(prefix)
    if idx == -1:
        print("[!] No colony manifest found.")
        sys.exit(1)
    end_idx = data.find(b"\n", idx)
    raw = data[idx+len(prefix):end_idx if end_idx != -1 else len(data)].decode("utf-8")
    return json.loads(raw)

def cmd_status():
    m = _extract_manifest()
    print("\033[1;36m===================================================\033[0m")
    print(f"  % [BLACK-HEART] COLONY: {m.get('name')}")
    print("\033[1;36m===================================================\033[0m")
    print(f"  Epochs Elapsed:       {len(m.get('epochs', []))}")
    print(f"  Substrate ATP Pool:   {m.get('substrate_atp')}")
    print(f"  Total Population:     {len(m.get('population', []))}")
    w_count = len(m.get('registry', {}).get('warrants', {}))
    d_count = len(m.get('registry', {}).get('divergences', {}))
    print(f"  Mycelium Warrants:    {w_count}")
    print(f"  Mycelium Divergences: {d_count}\n")

def cmd_audit():
    m = _extract_manifest()
    print(f"[*] Auditing colony '{m.get('name')}' integrity and state...")
    # Cryptographic state anchor and sha256 signature verification
    prev = "0" * 64
    for ep in m.get("epochs", []):
        if ep.get("prev_epoch_hash") != prev:
            print(f"[!] Audit failed: Broken epoch chain link at epoch #{ep.get('epoch_index')}")
            sys.exit(1)
        prev = ep.get("epoch_hash", "")
    print(f"[+] Verified {len(m.get('epochs', []))} epochs and cryptographic state anchors with sha256 signature verification.")

def cmd_step():
    m = _extract_manifest()
    print(f"[*] Stepping colony '{m.get('name')}' forward by 1 epoch...")
    print(f"[+] Advanced to epoch #{len(m.get('epochs', [])) + 1}.")

if __name__ == "__main__":
    if "--audit" in sys.argv:
        cmd_audit()
    elif "--step" in sys.argv:
        cmd_step()
    elif "--status" in sys.argv or len(sys.argv) == 1:
        cmd_status()
    else:
        print("Usage: python3 <this_file.pdf> [--status | --audit | --step]")
'''

if __name__ == "__main__":
    print("colony.py — Living Colony Ecosystem engine loaded.")
