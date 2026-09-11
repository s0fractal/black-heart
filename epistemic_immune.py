#!/usr/bin/env python3
# coding: utf-8
"""
epistemic_immune.py — Autonomic Epistemic Immune System & Metabolic Self-Healing.
Part of Project Black-Heart (%🖤). Engine #26.

Normative implementation of EPISTEMIC-IMMUNE-0.1:
  1. Synthesis of Warrant Epistemic Kernel (Engine #24, WARRANT-0.2),
     Controlled Forgetting (Engine #25, CONTROLLED-FORGETTING-0.1),
     and Autopoietic Quine Organisms (Engines #22, #23).
  2. ResurrectionDefense Pre-Flight Gate:
     Blocks mutations and equational rewrites from being evaluated if the candidate
     rule or allele is tombstoned in the EpistemicTombstoneRegistry, preventing vanity
     ATP metabolic burn before trial reductions.
  3. Counterexample Metabolism & Gas Bounty Reclamation:
     When a candidate mutation diverges, the caller supplies the two EXECUTABLE terms
     and the input; this module constructs a Grade C CounterexampleWitness, mints an
     EdgeClaim(REFUTE) over those terms, and **audits that same claim**. Only a PASS
     buys anything: the claim is recorded, the Negative Space Coverage metric mu(C) is
     computed, a signed RetirementRecord (mode=REFUTED) with mandatory Invariant I4
     loss declaration is registered, and the gas bounty (+ATP) is credited. FAIL or
     UNVERIFIED returns the verdict and changes nothing.

     API compatibility: `metabolize_counterexample` now takes keyword-only arguments
     including the required `parent_term` and `candidate_term`, and returns a
     `MetabolismOutcome` rather than a `(claim, retirement, bounty)` tuple. No old
     call shape binds, by design: the previous one passed a gene id and a rule name
     where executable endpoints now go. Records emitted by the previous version stay
     as they are; nothing is re-signed or retrospectively validated, and a historical
     claim that fails today's audit is evidence about the producer, not a record to
     repair.
  4. Generational Hypothesis Elevation (E -> A):
     Periodically tests empirical hypotheses that survived multiple generations against
     closed Church-Rosser reduction rules; promotes sound rules to Grade A Axiomatic
     Identities, supersedes the empirical hypothesis (mode=SUPERSEDED), and integrates
     the proven axiom into the organism's active rewrite core.
  5. Horizontal Swarm Inoculation:
     Peer organisms exchange their tombstone registries (InoculationProtocol), absorbing
     counterexamples so peers avoid repeating each other's evolutionary failures.
  6. Starvation Autophagy & Metabolic Homeostasis:
     When an organism's ATP reserve drops below a critical threshold (starvation),
     autophagy prunes non-vital or bloated chromosomes to minimal normal forms,
     reclaiming gas and preserving organism viability.
  7. ISO 32000 Append-Only Polyglot Immune HUD:
     Renders an obsidian/emerald vector HUD with ATP gauges and negative space statistics,
     embedding a standalone Python verification runner.
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
from glyph import (
    Term, parse, evaluate, term_hash, tree_size,
    GLYPH_K, GLYPH_I, GLYPH_S, GLYPH_ANCHOR
)
from organism import Chromosome
import warrant_kernel
from warrant_kernel import (
    EvidenceGrade, VerificationStatus, Polarity,
    EdgeClaim, CounterexampleWitness, AxiomaticWitness, EmpiricalWitness,
    TrustConfig, WarrantVerifier, Verdict, promote_empirical_to_axiomatic
)
import controlled_forgetting
from controlled_forgetting import (
    RetirementMode, AdmissionStatus, NegativeSpaceMeter,
    RetirementRecord, ReAdoptionRecord, EpistemicTombstoneRegistry,
    ResurrectionGuard, EpistemicResurrectionError, append_retirement_tombstone_to_pdf
)

# ============================================================================
# 1. IMMUNE METABOLISM DATA STRUCTURES
# ============================================================================

class ImmuneHealthStatus(str, Enum):
    """Metabolic and immune homeostasis standing of an organism."""
    HOMEOSTASIS = "HOMEOSTASIS"               # Plentiful ATP reserves, normal mutation/evolution.
    METABOLIC_STRESS = "METABOLIC_STRESS"     # Low ATP, conservative mutational filtering active.
    STARVATION = "STARVATION"                 # Critical ATP deficiency, starvation autophagy triggered.


@dataclass
class EpistemicOrganism:
    """
    Autonomous computational organism with integrated epistemic immune metabolism.
    Maintains active chromosomes, ATP metabolic fuel reserve, empirical edge-claims,
    epistemic tombstone registry, and proven axiomatic identities.
    """
    organism_id: str
    generation: int
    chromosomes: List[Chromosome]
    public_key_hex: str
    atp_reserve: int = 500
    claims: List[EdgeClaim] = field(default_factory=list)
    tombstone_registry: EpistemicTombstoneRegistry = field(default_factory=EpistemicTombstoneRegistry)
    inoculated_tombstones_count: int = 0
    active_axioms: List[str] = field(default_factory=list)
    total_bounties_reclaimed: int = 0
    autophagy_events_count: int = 0

    def compute_genome_hash(self) -> str:
        tokens = []
        for c in sorted(self.chromosomes, key=lambda x: x.gene_id):
            tokens.append(f"{c.gene_id}:{c.expression}:{c.expected_normal_form}:{getattr(c, 'vital', True)}")
        return hashlib.sha256(";".join(tokens).encode("utf-8")).hexdigest()

    def get_health_status(self, starvation_threshold: int = 80, stress_threshold: int = 200) -> ImmuneHealthStatus:
        if self.atp_reserve <= starvation_threshold:
            return ImmuneHealthStatus.STARVATION
        elif self.atp_reserve <= stress_threshold:
            return ImmuneHealthStatus.METABOLIC_STRESS
        return ImmuneHealthStatus.HOMEOSTASIS

    def to_dict(self) -> Dict[str, Any]:
        return {
            "organism_id": self.organism_id,
            "generation": self.generation,
            "genome_hash": self.compute_genome_hash(),
            "chromosomes": [c.to_dict() for c in self.chromosomes],
            "public_key_hex": self.public_key_hex,
            "atp_reserve": self.atp_reserve,
            "claims": [c.to_dict() for c in self.claims],
            "tombstones": self.tombstone_registry.to_dict(),
            "inoculated_tombstones_count": self.inoculated_tombstones_count,
            "active_axioms": self.active_axioms,
            "total_bounties_reclaimed": self.total_bounties_reclaimed,
            "autophagy_events_count": self.autophagy_events_count
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> EpistemicOrganism:
        org = cls(
            organism_id=str(d["organism_id"]),
            generation=int(d["generation"]),
            chromosomes=[Chromosome.from_dict(c) for c in d["chromosomes"]],
            public_key_hex=str(d["public_key_hex"]),
            atp_reserve=int(d.get("atp_reserve", 500)),
            claims=[EdgeClaim.from_dict(c) for c in d.get("claims", [])],
            tombstone_registry=EpistemicTombstoneRegistry.from_dict(d.get("tombstones", {})),
            inoculated_tombstones_count=int(d.get("inoculated_tombstones_count", 0)),
            active_axioms=list(d.get("active_axioms", [])),
            total_bounties_reclaimed=int(d.get("total_bounties_reclaimed", 0)),
            autophagy_events_count=int(d.get("autophagy_events_count", 0))
        )
        return org


# ============================================================================
# 2. RESURRECTION DEFENSE (PRE-FLIGHT IMMUNE GATE)
# ============================================================================

class ResurrectionDefense:
    """
    Enforces Invariant I3 at the mutation proposal site.
    Intercepts candidate rewrite rules before trial reductions are executed,
    saving the organism from wasting precious ATP on previously refuted or retired alleles.
    """

    @staticmethod
    def preflight_check(
        registry: EpistemicTombstoneRegistry,
        candidate_rule_or_id: str,
        target_digest: str = ""
    ) -> Tuple[bool, str]:
        """
        Returns (is_permitted, refusal_reason).
        If False, mutation MUST be aborted before burning any ATP.
        """
        cid = candidate_rule_or_id.strip()
        # Direct check by subject ID
        if not registry.is_admitted(cid):
            tomb = registry.tombstones[cid]
            return False, (
                f"Resurrection Defense Refusal: candidate '{cid}' is tombstoned ({tomb.mode.value}). "
                f"Declared loss: '{tomb.loss_declaration}'. Invariant I3 prohibits implicit re-evaluation."
            )

        # Check by target digest if provided
        if target_digest:
            for tid, tomb in registry.tombstones.items():
                if tomb.target_digest == target_digest and not registry.is_admitted(tid):
                    return False, (
                        f"Resurrection Defense Refusal: target digest '{target_digest[:16]}...' matches "
                        f"tombstoned artifact '{tid}' ({tomb.mode.value})."
                    )

        # Heuristic check for known refuted structural patterns
        for tid, tomb in registry.tombstones.items():
            if tomb.mode == RetirementMode.REFUTED and tid == cid and not registry.is_admitted(tid):
                return False, f"Resurrection Defense Refusal: pattern '{cid}' was refuted by counterexample."

        return True, ""


# ============================================================================
# 3. COUNTEREXAMPLE METABOLISM & GAS BOUNTY RECLAMATION
# ============================================================================

class ObservationStatus(str, Enum):
    """
    Outcome of replaying one input through two terms.
    An observation records what the engine did. It grants nothing.
    """
    DIVERGES = "DIVERGES"                    # both settled, outputs differ
    COINCIDES = "COINCIDES"                  # both settled, outputs equal
    INCOMPLETE = "INCOMPLETE"                # one or both hit the ATP ceiling
    UNPARSEABLE = "UNPARSEABLE"              # an operand is not a term
    EVALUATION_FAILED = "EVALUATION_FAILED"  # the engine raised


@dataclass(frozen=True)
class DivergenceObservation:
    """
    A replay transcript, offered so a caller can state true operands instead of
    guessing them. It is deliberately NOT accepted by the metabolism: the claim
    carries the caller's own declarations and the audit re-derives everything.
    """
    status: ObservationStatus
    parent_term: str
    candidate_term: str
    input_fixture: str
    parent_output: Optional[str] = None
    candidate_output: Optional[str] = None
    atp_required: Optional[int] = None
    detail: str = ""

    def diverges(self) -> bool:
        return self.status == ObservationStatus.DIVERGES


def observe_divergence(
    parent_term: str,
    candidate_term: str,
    input_fixture: str,
    max_atp: int = 100_000
) -> DivergenceObservation:
    """
    Applies `input_fixture` as a single argument to each term and reports what
    the engine did. The application shape is exactly the one the Grade C audit
    replays: `<term> (<input_fixture>)`.
    """
    base = dict(parent_term=parent_term, candidate_term=candidate_term,
                input_fixture=input_fixture)
    try:
        p_term = parse(f"{parent_term} ({input_fixture})")
        c_term = parse(f"{candidate_term} ({input_fixture})")
    except Exception as e:
        return DivergenceObservation(status=ObservationStatus.UNPARSEABLE,
                                     detail=f"{type(e).__name__}: {e}", **base)
    try:
        res_p = evaluate(p_term, max_atp=max_atp)
        res_c = evaluate(c_term, max_atp=max_atp)
    except Exception as e:
        return DivergenceObservation(status=ObservationStatus.EVALUATION_FAILED,
                                     detail=f"{type(e).__name__}: {e}", **base)
    if not res_p.is_settled() or not res_c.is_settled():
        return DivergenceObservation(
            status=ObservationStatus.INCOMPLETE,
            detail=f"parent {res_p.status.value}, candidate {res_c.status.value} at {max_atp} ATP",
            **base)
    out_p, out_c = str(res_p.term), str(res_c.term)
    required = max(res_p.atp_spent, res_c.atp_spent)
    if glyph.canonical_bytes(res_p.term) == glyph.canonical_bytes(res_c.term):
        return DivergenceObservation(
            status=ObservationStatus.COINCIDES, parent_output=out_p,
            candidate_output=out_c, atp_required=required,
            detail="outputs coincide: no counterexample here", **base)
    return DivergenceObservation(
        status=ObservationStatus.DIVERGES, parent_output=out_p,
        candidate_output=out_c, atp_required=required, **base)


class MetabolismStatus(str, Enum):
    """
    Whether a proposed counterexample was metabolized.
    REFUSED and UNVERIFIED are not observationally equivalent to each other, and
    neither leaves any trace in the organism.
    """
    METABOLIZED = "METABOLIZED"   # the claim passed an independent audit; effects applied
    REFUSED = "REFUSED"           # the audit contradicted the claim; nothing applied
    UNVERIFIED = "UNVERIFIED"     # the audit reached no verdict; nothing applied


@dataclass
class MetabolismOutcome:
    """
    The result of one metabolism attempt.

    This is a local return value, not a grant that travels. It carries no
    success flag that another consumer could spend: `verdict` is a record of
    what this call measured, and anyone holding the claim must audit it again.
    Effects, when they happen, happen inside the call that did the audit.
    """
    status: MetabolismStatus
    claim: EdgeClaim
    verdict: Verdict
    retirement: Optional[RetirementRecord] = None
    gas_bounty: int = 0

    def granted(self) -> bool:
        return self.status == MetabolismStatus.METABOLIZED


class CounterexampleMetabolism:
    """
    Transforms experimental failures and divergences into metabolic fuel:
      - Synthesizes Grade C CounterexampleWitness over CALLER-SUPPLIED terms.
      - Mints EdgeClaim(Polarity.REFUTE) and audits it independently.
      - Only on PASS: records the claim, retires the candidate rule in the
        EpistemicTombstoneRegistry with Invariant I4 loss, credits the bounty.

    Identifiers are provenance, never code. A gene id names a chromosome and a
    rule name names a retirement subject; neither is an executable endpoint, and
    both parse as ordinary terms (`"GENESIS_K"` is a free variable, `"x y -> y x"`
    is an application of six of them), so a producer that put them in the claim
    minted evidence that replays something no one intended.
    """

    @staticmethod
    def metabolize_counterexample(
        organism: EpistemicOrganism,
        *,
        gene_id: str,
        rule_name: str,
        parent_term: str,
        candidate_term: str,
        input_fixture: str,
        expected_norm: str,
        actual_norm: str,
        atp_cost: int,
        secret_key_hex: str,
        public_key_hex: str,
        verifier: Optional[WarrantVerifier] = None
    ) -> MetabolismOutcome:
        """
        Executes the counterexample conversion protocol:
          1. Constructs a CounterexampleWitness over the declared operands.
          2. Mints a signed Grade C EdgeClaim whose endpoints are the executable
             terms `parent_term` and `candidate_term`.
          3. **Audits that same claim** with an independent verifier.
          4. On PASS only: records the claim, computes mu(C), registers a signed
             RetirementRecord(mode=REFUTED) naming the audited evidence, and
             credits the gas bounty.
          5. On FAIL or UNVERIFIED: returns the claim and the verdict, and leaves
             the organism's claims, tombstones and ATP exactly as they were.

        Parameters are keyword-only: the previous signature took `gene_id` and
        `rule_name` in the positions that now hold executable terms, and a
        positional call that silently kept working would rebuild the defect.

        `gene_id` and `rule_name` stay as provenance and as the retirement
        subject. Whether a label denotes the term supplied beside it remains the
        caller's assertion; what is no longer assumed is that a label can be run.
        """
        # 1. Construct Counterexample Witness over the declared operands.
        witness = CounterexampleWitness(
            input_expr=input_fixture,
            expected_normal_form=expected_norm,
            actual_divergence=actual_norm,
            atp_to_diverge=atp_cost
        )

        # 2. Mint Grade C Claim over the executable endpoints.
        successor_hash = hashlib.sha256(actual_norm.encode("utf-8")).hexdigest()
        claim = EdgeClaim.create_and_sign(
            parent_hash=organism.compute_genome_hash(),
            tau=candidate_term,
            omega=parent_term,
            successor_hash=successor_hash,
            polarity=Polarity.REFUTE,
            witness=witness,
            secret_key_hex=secret_key_hex,
            public_key_hex=public_key_hex
        )

        # 3. Audit this claim, before it is recorded and before anything is spent.
        audit = verifier or WarrantVerifier(TrustConfig())
        verdict = audit.audit_claim(claim)
        if verdict.status != VerificationStatus.PASS:
            return MetabolismOutcome(
                status=(MetabolismStatus.REFUSED
                        if verdict.status == VerificationStatus.FAIL
                        else MetabolismStatus.UNVERIFIED),
                claim=claim, verdict=verdict, retirement=None, gas_bounty=0)

        # 4. Effects. Everything below this line rests on the verdict above.
        organism.claims.append(claim)

        coverage = NegativeSpaceMeter.calculate_coverage(rule_name)
        gas_bounty = NegativeSpaceMeter.compute_gas_reclamation(coverage)

        loss_desc = (
            f"Pruned candidate rewrite '{rule_name}' on gene '{gene_id}': divergence "
            f"reproduced on input '{input_fixture}' between parent '{parent_term}' and "
            f"candidate '{candidate_term}' (parent -> '{expected_norm}', candidate -> "
            f"'{actual_norm}', {atp_cost} ATP declared). Audited as claim {claim.claim_id}."
        )
        rule_digest = hashlib.sha256(rule_name.encode("utf-8")).hexdigest()

        ret_record = organism.tombstone_registry.retire(
            target_id=rule_name,
            target_digest=rule_digest,
            mode=RetirementMode.REFUTED,
            loss_declaration=loss_desc,
            author_sk_hex=secret_key_hex,
            author_pk_hex=public_key_hex,
            rule_or_pattern=rule_name
        )

        # 5. Credit metabolic fuel.
        organism.atp_reserve += gas_bounty
        organism.total_bounties_reclaimed += gas_bounty

        return MetabolismOutcome(
            status=MetabolismStatus.METABOLIZED, claim=claim, verdict=verdict,
            retirement=ret_record, gas_bounty=gas_bounty)


# ============================================================================
# 4. GENERATIONAL HYPOTHESIS ELEVATION (E -> A)
# ============================================================================

class HypothesisElevationCycle:
    """
    Automates promotion from Empirical Hypothesis (Grade E) to Axiomatic Identity (Grade A).
    Resolves Open Question 2 of WARRANT.md in the living organism.
    """

    @staticmethod
    def evaluate_and_elevate(
        organism: EpistemicOrganism,
        secret_key_hex: str,
        public_key_hex: str
    ) -> Optional[Tuple[EdgeClaim, RetirementRecord]]:
        """
        Scans organism's empirical claims. If an empirical claim is proven confluent
        under Church-Rosser reduction for symbolic variables, it promotes the claim to Grade A,
        retires the Grade E claim with mode=SUPERSEDED, and adds the axiom to active_axioms.
        """
        for claim in list(organism.claims):
            if claim.grade == EvidenceGrade.EMPIRICAL and claim.polarity == Polarity.AFFIRM:
                # Attempt formal elevation
                promoted = promote_empirical_to_axiomatic(claim, secret_key_hex, public_key_hex)
                if promoted:
                    # Register the new Axiomatic claim
                    organism.claims.append(promoted)
                    if promoted.tau not in organism.active_axioms:
                        organism.active_axioms.append(promoted.tau)

                    # Supersede the empirical claim
                    loss_msg = (
                        f"Empirical hypothesis '{claim.claim_id[:16]}...' on rule '{claim.tau}' "
                        f"superseded by proved axiomatic identity '{promoted.claim_id[:16]}...'."
                    )
                    emp_digest = hashlib.sha256(claim.claim_id.encode("utf-8")).hexdigest()
                    ret_rec = organism.tombstone_registry.retire(
                        target_id=claim.claim_id,
                        target_digest=emp_digest,
                        mode=RetirementMode.SUPERSEDED,
                        loss_declaration=loss_msg,
                        author_sk_hex=secret_key_hex,
                        author_pk_hex=public_key_hex,
                        replacement_id=promoted.claim_id,
                        rule_or_pattern=claim.tau
                    )
                    return promoted, ret_rec
        return None


# ============================================================================
# 5. HORIZONTAL SWARM INOCULATION
# ============================================================================

@dataclass
class InoculationReport:
    absorbed_tombstones_count: int
    # Records refused at the gate. The name is historical: refusal covers a
    # signature that does not cover the body, a record filed under a subject it
    # does not name, and a re-adoption that names no retirement held here.
    rejected_signatures_count: int
    pruned_search_space_volume: float
    total_active_tombstones: int


class HorizontalInoculation:
    """
    Transfers epistemic immune defenses across peer organisms.
    When organisms meet or sync over P2P mesh, they exchange tombstones so peers
    inherit negative knowledge without repeating failed trials.
    """

    @staticmethod
    def inoculate(
        recipient: EpistemicOrganism,
        donor_registry: EpistemicTombstoneRegistry
    ) -> InoculationReport:
        absorbed = 0
        rejected = 0
        added_volume = 0.0

        for tid, tomb in donor_registry.tombstones.items():
            # One complete check before absorption: the body names the subject
            # it is filed under, the numbers it declares are inside their
            # domains, and the signature covers that body. A correctly signed
            # record can still carry a coverage figure that is not a ratio, so
            # refusal precedes both the write and the coverage arithmetic.
            if not tomb.is_admissible_for(tid):
                rejected += 1
                continue

            # Ingest if not already present or if newly updated
            if tid not in recipient.tombstone_registry.tombstones:
                recipient.tombstone_registry.tombstones[tid] = tomb
                absorbed += 1
                added_volume += tomb.negative_space_coverage

        # Re-adoptions re-open the active surface, so they are held to the same
        # binding plus the link to the retirement the recipient actually holds.
        # A re-adoption naming some other retirement of the same subject, or
        # naming none the recipient knows, is refused rather than stored.
        for rid, ro in donor_registry.readoptions.items():
            # The incoming re-adoption alone is not enough: the retirement it
            # would clear is the recipient's own, so that record is put through
            # the same complete check before this one can cite it.
            local_tomb = recipient.tombstone_registry.tombstones.get(rid)
            if local_tomb is None or not ro.is_admissible_for(rid, local_tomb):
                rejected += 1
                continue
            recipient.tombstone_registry.readoptions[rid] = ro

        recipient.inoculated_tombstones_count += absorbed

        return InoculationReport(
            absorbed_tombstones_count=absorbed,
            rejected_signatures_count=rejected,
            pruned_search_space_volume=round(added_volume, 4),
            total_active_tombstones=len(recipient.tombstone_registry.tombstones)
        )


# ============================================================================
# 6. STARVATION AUTOPHAGY & METABOLIC HOMEOSTASIS
# ============================================================================

@dataclass
class AutophagyReport:
    triggered: bool
    initial_atp: int
    final_atp: int
    pruned_chromosomes: List[str]
    reclaimed_fuel: int
    status_after: ImmuneHealthStatus


class StarvationAutophagy:
    """
    Emergency self-healing engine triggered when metabolic ATP drops to critical levels.
    Identifies non-vital or bloated chromosomes, archives them to the historical substrate,
    reduces expressions to minimal normal forms, and reclaims emergency metabolic fuel.
    """

    @staticmethod
    def trigger_autophagy(
        organism: EpistemicOrganism,
        secret_key_hex: str,
        public_key_hex: str,
        starvation_threshold: int = 80,
        recovery_target_atp: int = 200
    ) -> AutophagyReport:
        initial_atp = organism.atp_reserve
        if initial_atp > starvation_threshold:
            return AutophagyReport(
                triggered=False,
                initial_atp=initial_atp,
                final_atp=initial_atp,
                pruned_chromosomes=[],
                reclaimed_fuel=0,
                status_after=organism.get_health_status()
            )

        pruned = []
        reclaimed_total = 0

        # Scan chromosomes in reverse priority (non-vital first, then largest expression)
        candidates = [c for c in organism.chromosomes if not getattr(c, "vital", True)]
        # If all are marked vital, allow non-core chromosomes to be autophagized
        if not candidates and len(organism.chromosomes) > 1:
            candidates = [c for c in organism.chromosomes if not c.gene_id.startswith("GENESIS") and not c.gene_id.startswith("CORE")]

        # Sort by largest tree size to maximize fuel reclamation
        candidates.sort(key=lambda x: glyph.tree_size(glyph.parse(x.expression)), reverse=True)

        for c in candidates:
            if organism.atp_reserve >= recovery_target_atp:
                break

            # Calculate fuel reclaimed from this chromosome
            try:
                t = glyph.parse(c.expression)
                size = glyph.tree_size(t)
            except Exception:
                size = 5
            fuel = 40 + size * 4

            # Archive the chromosome in the tombstone registry
            loss_msg = (
                f"Emergency Autophagy: archived non-vital chromosome '{c.gene_id}' "
                f"(size {size}) to restore metabolic fuel homeostasis (+{fuel} ATP)."
            )
            c_digest = hashlib.sha256(c.expression.encode("utf-8")).hexdigest()
            organism.tombstone_registry.retire(
                target_id=c.gene_id,
                target_digest=c_digest,
                mode=RetirementMode.ARCHIVED,
                loss_declaration=loss_msg,
                author_sk_hex=secret_key_hex,
                author_pk_hex=public_key_hex,
                rule_or_pattern=c.expression
            )

            # Remove chromosome from active genome
            organism.chromosomes = [x for x in organism.chromosomes if x.gene_id != c.gene_id]
            organism.atp_reserve += fuel
            reclaimed_total += fuel
            pruned.append(c.gene_id)

        organism.autophagy_events_count += 1

        return AutophagyReport(
            triggered=True,
            initial_atp=initial_atp,
            final_atp=organism.atp_reserve,
            pruned_chromosomes=pruned,
            reclaimed_fuel=reclaimed_total,
            status_after=organism.get_health_status()
        )


# ============================================================================
# 7. ISO 32000 PDF POLYGLOT IMMUNE HUD VISUALIZER
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


def generate_immune_organism_pdf(
    organism: EpistemicOrganism,
    output_path: str
) -> bytes:
    """
    Creates an ISO 32000 compliant vector PDF polyglot document containing:
      - Visual Epistemic Immune HUD & Metabolic Status.
      - Health status badge (Emerald: Homeostasis, Amber: Stress, Crimson: Starvation).
      - ATP metabolic fuel gauge.
      - Embedded JCS-canonical JSON immune manifest.
      - Embedded self-executing Python auditor (`python3 doc.pdf`).
    """
    status = organism.get_health_status()
    if status == ImmuneHealthStatus.HOMEOSTASIS:
        health_col = "0.20 0.85 0.40"     # Emerald
        health_bg = "0.05 0.14 0.08"
    elif status == ImmuneHealthStatus.METABOLIC_STRESS:
        health_col = "0.90 0.65 0.15"     # Amber
        health_bg = "0.14 0.10 0.04"
    else:
        health_col = "0.95 0.25 0.25"     # Crimson
        health_bg = "0.15 0.05 0.06"

    total_neg_space = sum(t.negative_space_coverage for t in organism.tombstone_registry.tombstones.values())
    total_tombstones = len(organism.tombstone_registry.tombstones)
    refuted_count = sum(1 for t in organism.tombstone_registry.tombstones.values() if t.mode == RetirementMode.REFUTED)

    # Calculate gauge width
    max_gauge_w = 200
    gauge_pct = min(1.0, max(0.05, organism.atp_reserve / 1000.0))
    gauge_w = int(max_gauge_w * gauge_pct)

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
        "(%# BLACK-HEART: EPISTEMIC IMMUNE METABOLISM) Tj",
        "/F1 10 Tf",
        "0.6 0.7 0.85 rg",
        "0 -20 Td",
        "(EPISTEMIC-IMMUNE-0.1 | Autonomic Homeostasis & Inoculation HUD) Tj",
        "ET",
        # Health & Metabolic Card
        f"{health_bg} rg",
        "30 540 552 150 re f",
        f"{health_col} RG 2 w",
        "30 540 552 150 re S",
        "BT",
        "/F1 14 Tf",
        "1.0 1.0 1.0 rg",
        "45 660 Td",
        f"(ORGANISM HEALTH: [{status.value}]) Tj",
        "/F1 9 Tf",
        "0.80 0.85 0.90 rg",
        "0 -24 Td",
        f"(Organism ID:       {organism.organism_id[:32]}...) Tj",
        "0 -16 Td",
        f"(Generation:        #{organism.generation} | Active Chromosomes: {len(organism.chromosomes)}) Tj",
        "0 -16 Td",
        f"(ATP Fuel Reserve:  {organism.atp_reserve} ATP) Tj",
        "0 -16 Td",
        f"(Swarm Inoculations: {organism.inoculated_tombstones_count} external defenses absorbed) Tj",
        "0 -16 Td",
        f"(Negative Space:    {total_neg_space:.2f} AST search volume pruned | Reclaimed: +{organism.total_bounties_reclaimed} ATP) Tj",
        "ET",
        # Fuel Gauge Background & Fill
        "0.10 0.12 0.15 rg",
        "320 595 200 12 re f",
        f"{health_col} rg",
        f"320 595 {gauge_w} 12 re f",
        "0.3 0.35 0.45 RG 1 w",
        "320 595 200 12 re S",
        # Defense & Axiom Card
        "0.07 0.08 0.11 rg",
        "30 360 552 165 re f",
        "0.30 0.35 0.45 RG 1.5 w",
        "30 360 552 165 re S",
        "BT",
        "/F1 12 Tf",
        "0.90 0.95 1.0 rg",
        "45 500 Td",
        f"(IMMUNE MEMORY & ACTIVE AXIOMATIC CORE) Tj",
        "/F1 8 Tf",
        "0.75 0.80 0.85 rg",
        "0 -20 Td",
        f"(Tombstone Defenses: {total_tombstones} registered (Refuted: {refuted_count}, Superseded: {total_tombstones - refuted_count})) Tj",
        "0 -14 Td",
        f"(Active Axiom Bank:  {len(organism.active_axioms)} proven algebraic identities in genome) Tj",
        "0 -14 Td",
        f"(Autophagy Events:   {organism.autophagy_events_count} metabolic rescue sequences triggered) Tj",
        "0 -14 Td",
        f"(ResurrectionGuard:  INVARIANT I3 ACTIVE - Implicit resurrection fail-closed) Tj",
        "0 -14 Td",
        f"(Author Key:         {organism.public_key_hex[:32]}...) Tj",
        "ET",
        # Footer notice
        "BT",
        "/F1 8 Tf",
        "0.40 0.45 0.55 rg",
        "30 25 Td",
        "(Self-Executing Polyglot: Run 'python3 <file>.pdf' for trustless cryptographic audit) Tj",
        "ET",
        "Q"
    ]
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

    manifest_json = json.dumps(organism.to_dict(), sort_keys=True)
    manifest_line = (
        b"# %" + bytes([0xf0, 0x9f, 0x96, 0xa4])
        + b" IMMUNE_METABOLISM_MANIFEST: " + manifest_json.encode("utf-8") + b"\n"
    )

    py_runner = f"""
# coding: latin-1
import sys, json, os

cwd = os.getcwd()
if cwd not in sys.path:
    sys.path.insert(0, cwd)

def audit_immune_organism():
    print("\\033[1;36m" + "=" * 70)
    print("  %# EPISTEMIC IMMUNE METABOLISM AUDITOR (EPISTEMIC-IMMUNE-0.1)")
    print("=" * 70 + "\\033[0m")
    with open(__file__, 'rb') as f:
        data = f.read()
    prefix = bytes([0x23, 0x20, 0x25, 0xf0, 0x9f, 0x96, 0xa4]) + b" IMMUNE_METABOLISM_MANIFEST: "
    idx = data.rfind(prefix)
    if idx == -1:
        print("\\033[1;31m[-] No immune metabolism manifest found.\\033[0m")
        sys.exit(1)
    end = data.find(b"\\n", idx)
    org_json = json.loads(data[idx + len(prefix):end].decode('utf-8'))
    import epistemic_immune
    org = epistemic_immune.EpistemicOrganism.from_dict(org_json)
    status = org.get_health_status().value
    print(f"[*] Organism ID: {{org.organism_id}} (Gen #{{org.generation}})")
    print(f"[*] Metabolic Status: {{status}} | ATP Reserve: {{org.atp_reserve}} ATP")
    print(f"[*] Active Chromosomes: {{len(org.chromosomes)}} | Active Axioms: {{len(org.active_axioms)}}")
    print(f"[*] Tombstones: {{len(org.tombstone_registry.tombstones)}} (Inoculated from Swarm: {{org.inoculated_tombstones_count}})\\n")

    all_valid = True
    for tid, t in org.tombstone_registry.tombstones.items():
        if not t.verify_signature():
            print(f"\\033[1;31m[!] Signature INVALID for tombstone '{{tid}}'\\033[0m")
            all_valid = False
        else:
            print(f"  [TOMBSTONE] '{{tid}}' -> {{t.mode.value}} | Loss: '{{t.loss_declaration[:40]}}...'")

    print("\\033[1;36m" + "=" * 70 + "\\033[0m")
    if all_valid:
        print("\\033[1;32m[+] Immune metabolism and tombstone defenses fully verified.\\033[0m")
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    audit_immune_organism()
"""

    header_text = (
        f"#!{sys.executable}\n"
        "# coding: latin-1\n"
        "# ============================================================================\n"
        "# %# PROJECT BLACK-HEART: EPISTEMIC IMMUNE METABOLISM (ISO 32000 POLYGLOT)\n"
        "# ============================================================================\n"
        "r'''\n"
    ).encode("latin-1")

    polyglot = header_text + body + xref + trailer + manifest_line + b"'''\n" + py_runner.encode("latin-1")
    with open(output_path, "wb") as f:
        f.write(polyglot)
    return polyglot


def append_immune_hud_to_pdf(
    source_pdf_bytes: bytes,
    output_path: str,
    organism: EpistemicOrganism
) -> bytes:
    """
    Appends an ISO 32000 §7.5.6 incremental document update containing the visual
    Epistemic Immune HUD to an existing polyglot document.
    Preserves byte prefix: output.startswith(source_pdf_bytes) == True.
    """
    status = organism.get_health_status()
    if status == ImmuneHealthStatus.HOMEOSTASIS:
        health_col = "0.20 0.85 0.40"
        health_bg = "0.05 0.14 0.08"
    elif status == ImmuneHealthStatus.METABOLIC_STRESS:
        health_col = "0.90 0.65 0.15"
        health_bg = "0.14 0.10 0.04"
    else:
        health_col = "0.95 0.25 0.25"
        health_bg = "0.15 0.05 0.06"

    total_neg_space = sum(t.negative_space_coverage for t in organism.tombstone_registry.tombstones.values())
    total_tombstones = len(organism.tombstone_registry.tombstones)
    refuted_count = sum(1 for t in organism.tombstone_registry.tombstones.values() if t.mode == RetirementMode.REFUTED)

    max_gauge_w = 200
    gauge_pct = min(1.0, max(0.05, organism.atp_reserve / 1000.0))
    gauge_w = int(max_gauge_w * gauge_pct)

    stream_lines = [
        "q",
        "0.04 0.05 0.07 rg",
        "0 0 612 792 re f",
        "0.08 0.10 0.14 rg",
        "30 710 552 60 re f",
        "0.20 0.25 0.35 RG 1 w",
        "30 710 552 60 re S",
        "BT",
        "/F1 16 Tf",
        "1.0 1.0 1.0 rg",
        "45 745 Td",
        "(%# BLACK-HEART: EPISTEMIC IMMUNE METABOLISM) Tj",
        "/F1 10 Tf",
        "0.6 0.7 0.85 rg",
        "0 -20 Td",
        "(EPISTEMIC-IMMUNE-0.1 | Autonomic Homeostasis & Inoculation HUD) Tj",
        "ET",
        f"{health_bg} rg",
        "30 540 552 150 re f",
        f"{health_col} RG 2 w",
        "30 540 552 150 re S",
        "BT",
        "/F1 14 Tf",
        "1.0 1.0 1.0 rg",
        "45 660 Td",
        f"(ORGANISM HEALTH: [{status.value}]) Tj",
        "/F1 9 Tf",
        "0.80 0.85 0.90 rg",
        "0 -24 Td",
        f"(Organism ID:       {organism.organism_id[:32]}...) Tj",
        "0 -16 Td",
        f"(Generation:        #{organism.generation} | Active Chromosomes: {len(organism.chromosomes)}) Tj",
        "0 -16 Td",
        f"(ATP Fuel Reserve:  {organism.atp_reserve} ATP) Tj",
        "0 -16 Td",
        f"(Swarm Inoculations: {organism.inoculated_tombstones_count} external defenses absorbed) Tj",
        "0 -16 Td",
        f"(Negative Space:    {total_neg_space:.2f} AST search volume pruned | Reclaimed: +{organism.total_bounties_reclaimed} ATP) Tj",
        "ET",
        "0.10 0.12 0.15 rg",
        "320 595 200 12 re f",
        f"{health_col} rg",
        f"320 595 {gauge_w} 12 re f",
        "0.3 0.35 0.45 RG 1 w",
        "320 595 200 12 re S",
        "0.07 0.08 0.11 rg",
        "30 360 552 165 re f",
        "0.30 0.35 0.45 RG 1.5 w",
        "30 360 552 165 re S",
        "BT",
        "/F1 12 Tf",
        "0.90 0.95 1.0 rg",
        "45 500 Td",
        f"(IMMUNE MEMORY & ACTIVE AXIOMATIC CORE) Tj",
        "/F1 8 Tf",
        "0.75 0.80 0.85 rg",
        "0 -20 Td",
        f"(Tombstone Defenses: {total_tombstones} registered (Refuted: {refuted_count}, Superseded: {total_tombstones - refuted_count})) Tj",
        "0 -14 Td",
        f"(Active Axiom Bank:  {len(organism.active_axioms)} proven algebraic identities in genome) Tj",
        "0 -14 Td",
        f"(Autophagy Events:   {organism.autophagy_events_count} metabolic rescue sequences triggered) Tj",
        "0 -14 Td",
        f"(ResurrectionGuard:  INVARIANT I3 ACTIVE - Implicit resurrection fail-closed) Tj",
        "0 -14 Td",
        f"(Author Key:         {organism.public_key_hex[:32]}...) Tj",
        "ET",
        "BT",
        "/F1 8 Tf",
        "0.40 0.45 0.55 rg",
        "30 25 Td",
        "(Self-Executing Polyglot: Run 'python3 <file>.pdf' for trustless cryptographic audit) Tj",
        "ET",
        "Q"
    ]
    content_bytes = "\n".join(stream_lines).encode("latin-1")

    import re
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

    update_body = pages_update_obj + content_obj + font_obj + page_obj

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

    manifest_json = json.dumps(organism.to_dict(), sort_keys=True)
    manifest_line = (
        b"# %" + bytes([0xf0, 0x9f, 0x96, 0xa4])
        + b" IMMUNE_METABOLISM_MANIFEST: " + manifest_json.encode("utf-8") + b"\n"
    )

    py_runner = f"""
# coding: latin-1
import sys, json, os

cwd = os.getcwd()
if cwd not in sys.path:
    sys.path.insert(0, cwd)

def audit_immune_organism():
    print("\\033[1;36m" + "=" * 70)
    print("  %# EPISTEMIC IMMUNE METABOLISM AUDITOR (EPISTEMIC-IMMUNE-0.1)")
    print("=" * 70 + "\\033[0m")
    with open(__file__, 'rb') as f:
        data = f.read()
    prefix = bytes([0x23, 0x20, 0x25, 0xf0, 0x9f, 0x96, 0xa4]) + b" IMMUNE_METABOLISM_MANIFEST: "
    idx = data.rfind(prefix)
    if idx == -1:
        print("\\033[1;31m[-] No immune metabolism manifest found.\\033[0m")
        sys.exit(1)
    end = data.find(b"\\n", idx)
    org_json = json.loads(data[idx + len(prefix):end].decode('utf-8'))
    import epistemic_immune
    org = epistemic_immune.EpistemicOrganism.from_dict(org_json)
    status = org.get_health_status().value
    print(f"[*] Organism ID: {{org.organism_id}} (Gen #{{org.generation}})")
    print(f"[*] Metabolic Status: {{status}} | ATP Reserve: {{org.atp_reserve}} ATP")
    print(f"[*] Active Chromosomes: {{len(org.chromosomes)}} | Active Axioms: {{len(org.active_axioms)}}")
    print(f"[*] Tombstones: {{len(org.tombstone_registry.tombstones)}} (Inoculated from Swarm: {{org.inoculated_tombstones_count}})\\n")

    all_valid = True
    for tid, t in org.tombstone_registry.tombstones.items():
        if not t.verify_signature():
            print(f"\\033[1;31m[!] Signature INVALID for tombstone '{{tid}}'\\033[0m")
            all_valid = False
        else:
            print(f"  [TOMBSTONE] '{{tid}}' -> {{t.mode.value}} | Loss: '{{t.loss_declaration[:40]}}...'")

    print("\\033[1;36m" + "=" * 70 + "\\033[0m")
    if all_valid:
        print("\\033[1;32m[+] Immune metabolism and tombstone defenses fully verified.\\033[0m")
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    audit_immune_organism()
"""

    incremental_pdf = base_bytes + update_body + xref + trailer + manifest_line + b"'''\n" + py_runner.encode("latin-1")
    with open(output_path, "wb") as f:
        f.write(incremental_pdf)
    return incremental_pdf
