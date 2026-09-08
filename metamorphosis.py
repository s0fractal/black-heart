#!/usr/bin/env python3
# coding: utf-8
"""
metamorphosis.py — Autonomous Form Metamorphosis & Program Self-Contemplation Engine.
Part of Project Black-Heart (%🖤).

Implements:
  1. Addressable Program Representation:
     Zipper-style AST path addressing (tuple of 'L'/'R' branch directions) over
     pure combinator terms (SKIY).
  2. Algebraic Equational Rewriting & Mutation Proposals:
     Locates candidate rewrite sites and applies sound combinatory optimization rules:
       - S(K x)(K y) -> K(x y)  [Constant distribution optimization]
       - S(K x)I     -> x       [Identity distribution elimination]
       - S(K I)      -> I       [Trivial distribution collapse]
       - I x         -> x       [Static identity reduction]
       - K x y       -> x       [Static constant reduction]
     as well as exploratory structural mutations.
  3. External Invariant Evaluator (FrozenEvaluator):
     Decoupled test harness with frozen input fixtures that measures:
       - Semantic invariance across all test inputs (f_new(x) == f_old(x))
       - Execution cost differential: Delta ATP = ATP_cand - ATP_orig
       - Syntactic size differential: Delta Size = Size_cand - Size_orig
  4. Scientific Experiment Ledger (ExperimentLog):
     Chronicles every evaluated mutation. Crucially preserves REJECTED mutations
     (semantic divergence or lack of efficiency gain) as permanent empirical records.
  5. Successor Organism Minting & Independent Transition Replay:
     Successor organism embeds an immutable MetamorphicTransitionReceipt.
     An independent auditor re-executes the rewrite from the parent payload,
     re-evaluates on frozen inputs, and verifies functional invariance and ATP savings.
  6. Standalone Executable Polyglot PDF Compiler:
     Generates valid ISO 32000 PDF documents with embedded metamorphic manifest
     and standalone Python execution ('python3 metamorphic.pdf --audit').
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

from glyph import (
    Term, Comb, Var, App,
    K, I, S, Y,
    parse, evaluate, tree_size, canonical_bytes, term_hash,
    GLYPH_K, GLYPH_I, GLYPH_S, GLYPH_Y, GLYPH_ANCHOR
)
from organism import Organism, Chromosome, create_genesis_organism
import vault as V

# Type alias for AST tree address: sequence of 'L' (left) and 'R' (right) branches
Address = Tuple[str, ...]

METAMORPHOSIS_MANIFEST_PREFIX = "# %METAMORPHOSIS"

# ============================================================================
# 1. AST PATH ADDRESSING & LOCAL SUBTERM MANIPULATION
# ============================================================================

def get_subterm_at(term: Term, address: Address) -> Term:
    """Navigates to the subterm at the given binary branch address."""
    curr = term
    for step in address:
        if not isinstance(curr, App):
            raise IndexError(f"Cannot traverse '{step}' into non-App leaf: {curr}")
        if step == "L":
            curr = curr.left
        elif step == "R":
            curr = curr.right
        else:
            raise ValueError(f"Invalid address direction '{step}', expected 'L' or 'R'")
    return curr


def replace_subterm_at(term: Term, address: Address, replacement: Term) -> Term:
    """Replaces the subterm at the given address, returning a new immutable Term."""
    if not address:
        return replacement
    if not isinstance(term, App):
        raise IndexError(f"Cannot traverse into non-App leaf: {term}")
    step = address[0]
    rest = address[1:]
    if step == "L":
        return App(replace_subterm_at(term.left, rest, replacement), term.right)
    elif step == "R":
        return App(term.left, replace_subterm_at(term.right, rest, replacement))
    else:
        raise ValueError(f"Invalid address direction '{step}', expected 'L' or 'R'")


def enumerate_subterm_addresses(term: Term, prefix: Address = ()) -> List[Tuple[Address, Term]]:
    """Recursively lists all subterm addresses in prefix order."""
    items = [(prefix, term)]
    if isinstance(term, App):
        items.extend(enumerate_subterm_addresses(term.left, prefix + ("L",)))
        items.extend(enumerate_subterm_addresses(term.right, prefix + ("R",)))
    return items


# ============================================================================
# 2. EQUATIONAL REWRITE ENGINE & MUTATION PROPOSALS
# ============================================================================

@dataclass(frozen=True)
class RewriteRule:
    name: str
    description: str


RULE_S_K_K = RewriteRule("S(K x)(K y) -> K(x y)", "Distribution of constant functions elimination")
RULE_S_K_I = RewriteRule("S(K x)I -> x", "Identity distribution elimination")
RULE_S_K_I_COLLAPSE = RewriteRule("S(K I) -> I", "Trivial distribution collapse")
RULE_STATIC_I = RewriteRule("I x -> x", "Static identity reduction")
RULE_STATIC_K = RewriteRule("K x y -> x", "Static constant reduction")
RULE_EXPLORATORY_MUTATION = RewriteRule("MUTATION", "Exploratory structural mutation")


def match_and_rewrite(subterm: Term) -> List[Tuple[RewriteRule, Term]]:
    """
    Checks if a subterm matches any algebraic simplification rule.
    Returns a list of (Rule, ReplacementTerm).
    """
    proposals: List[Tuple[RewriteRule, Term]] = []

    # Rule 1: S (K x) (K y) -> K (x y)
    # subterm is App(App(S, App(K, x)), App(K, y))
    if (isinstance(subterm, App) and
        isinstance(subterm.left, App) and
        subterm.left.left == S and
        isinstance(subterm.left.right, App) and
        subterm.left.right.left == K and
        isinstance(subterm.right, App) and
        subterm.right.left == K):
        x = subterm.left.right.right
        y = subterm.right.right
        proposals.append((RULE_S_K_K, App(K, App(x, y))))

    # Rule 2: S (K x) I -> x
    # subterm is App(App(S, App(K, x)), I)
    if (isinstance(subterm, App) and
        isinstance(subterm.left, App) and
        subterm.left.left == S and
        isinstance(subterm.left.right, App) and
        subterm.left.right.left == K and
        subterm.right == I):
        x = subterm.left.right.right
        proposals.append((RULE_S_K_I, x))

    # Rule 3: S (K I) -> I
    # subterm is App(S, App(K, I))
    if (isinstance(subterm, App) and
        subterm.left == S and
        isinstance(subterm.right, App) and
        subterm.right.left == K and
        subterm.right.right == I):
        proposals.append((RULE_S_K_I_COLLAPSE, I))

    # Rule 4: I x -> x
    # subterm is App(I, x)
    if isinstance(subterm, App) and subterm.left == I:
        x = subterm.right
        proposals.append((RULE_STATIC_I, x))

    # Rule 5: K x y -> x
    # subterm is App(App(K, x), y)
    if (isinstance(subterm, App) and
        isinstance(subterm.left, App) and
        subterm.left.left == K):
        x = subterm.left.right
        proposals.append((RULE_STATIC_K, x))

    return proposals


@dataclass
class MutationProposal:
    gene_id: str
    site_address: Address
    rule: RewriteRule
    original_subterm: Term
    proposed_subterm: Term
    original_term: Term
    candidate_term: Term


def propose_form_metamorphoses(
    chromosome: Chromosome,
    include_exploratory: bool = True
) -> List[MutationProposal]:
    """
    Inspects the chromosome's combinator expression AST and discovers
    all addressable candidate rewrite sites.
    """
    root = parse(chromosome.expression)
    proposals: List[MutationProposal] = []

    for addr, sub in enumerate_subterm_addresses(root):
        # 1. Standard algebraic simplification rules
        for rule, repl in match_and_rewrite(sub):
            new_root = replace_subterm_at(root, addr, repl)
            if new_root != root:
                proposals.append(MutationProposal(
                    gene_id=chromosome.gene_id,
                    site_address=addr,
                    rule=rule,
                    original_subterm=sub,
                    proposed_subterm=repl,
                    original_term=root,
                    candidate_term=new_root
                ))

        # 2. Exploratory mutations (to test hypothesis rejection and evolutionary exploration)
        if include_exploratory and isinstance(sub, App):
            # Candidate exploratory mutation A: Swap left and right operands (often semantically invalid)
            swap_repl = App(sub.right, sub.left)
            new_root_swap = replace_subterm_at(root, addr, swap_repl)
            if new_root_swap != root:
                proposals.append(MutationProposal(
                    gene_id=chromosome.gene_id,
                    site_address=addr,
                    rule=RewriteRule("MUTATION_OPERAND_SWAP", "Exploratory operand transposition"),
                    original_subterm=sub,
                    proposed_subterm=swap_repl,
                    original_term=root,
                    candidate_term=new_root_swap
                ))

            # Candidate exploratory mutation B: Replace subterm with K (often drops arguments)
            k_repl = K
            new_root_k = replace_subterm_at(root, addr, k_repl)
            if new_root_k != root:
                proposals.append(MutationProposal(
                    gene_id=chromosome.gene_id,
                    site_address=addr,
                    rule=RewriteRule("MUTATION_CONSTANT_COLLAPSE", "Exploratory collapse to constant K"),
                    original_subterm=sub,
                    proposed_subterm=k_repl,
                    original_term=root,
                    candidate_term=new_root_k
                ))

    return proposals


# ============================================================================
# 3. EXTERNAL INVARIANT EVALUATOR & FROZEN TEST VECTORS
# ============================================================================

class MutationVerdict(str, Enum):
    ACCEPTED_MORE_EFFICIENT = "ACCEPTED_MORE_EFFICIENT"
    REJECTED_SEMANTIC_MISMATCH = "REJECTED_SEMANTIC_MISMATCH"
    REJECTED_NO_EFFICIENCY_GAIN = "REJECTED_NO_EFFICIENCY_GAIN"
    REJECTED_BUDGET_EXCEEDED = "REJECTED_BUDGET_EXCEEDED"
    REJECTED_UNTESTED = "REJECTED_UNTESTED"


@dataclass
class EvaluationReceipt:
    verdict: MutationVerdict
    semantic_preserved: bool
    atp_original: int
    atp_candidate: int
    atp_delta: int
    size_original: int
    size_candidate: int
    size_delta: int
    test_inputs_count: int
    discrepancy_input: Optional[str] = None
    discrepancy_expected: Optional[str] = None
    discrepancy_actual: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "semantic_preserved": self.semantic_preserved,
            "atp_original": self.atp_original,
            "atp_candidate": self.atp_candidate,
            "atp_delta": self.atp_delta,
            "size_original": self.size_original,
            "size_candidate": self.size_candidate,
            "size_delta": self.size_delta,
            "test_inputs_count": self.test_inputs_count,
            "discrepancy_input": self.discrepancy_input,
            "discrepancy_expected": self.discrepancy_expected,
            "discrepancy_actual": self.discrepancy_actual
        }


class FrozenEvaluator:
    """
    External invariant evaluator that verifies semantic invariance across a frozen
    set of test input fixtures and precisely measures computational cost.
    """
    def __init__(self, frozen_inputs: Optional[List[Term]] = None, atp_budget_per_test: int = 500):
        if frozen_inputs is None:
            # Canonical standard fixtures: Booleans, Church numerals, and variables
            self.frozen_inputs: List[Term] = [
                K,                 # TRUE
                App(K, I),         # FALSE / CHURCH_0
                I,                 # CHURCH_1
                Var("alpha"),      # Abstract parameter alpha
                Var("beta")        # Abstract parameter beta
            ]
        else:
            self.frozen_inputs = list(frozen_inputs)
        self.atp_budget_per_test = atp_budget_per_test

    @property
    def fixtures_fingerprint(self) -> str:
        """SHA-256 fingerprint of the frozen test fixtures and evaluator profile."""
        fixtures_bytes = b":".join(canonical_bytes(t) for t in self.frozen_inputs)
        profile_bytes = f"PROFILE:v1:atp_budget={self.atp_budget_per_test}:count={len(self.frozen_inputs)}:".encode("utf-8")
        return hashlib.sha256(profile_bytes + fixtures_bytes).hexdigest()

    def evaluate_transformation(
        self,
        original_term: Term,
        candidate_term: Term
    ) -> EvaluationReceipt:
        """
        Executes both original and candidate terms against all frozen inputs.
        Verifies functional equivalence and measures execution cost deltas.
        """
        orig_size = tree_size(original_term)
        cand_size = tree_size(candidate_term)
        size_delta = cand_size - orig_size

        # K5: Empty fixtures cannot verify semantic preservation
        if len(self.frozen_inputs) == 0:
            return EvaluationReceipt(
                verdict=MutationVerdict.REJECTED_UNTESTED,
                semantic_preserved=False,
                atp_original=0,
                atp_candidate=0,
                atp_delta=0,
                size_original=orig_size,
                size_candidate=cand_size,
                size_delta=size_delta,
                test_inputs_count=0,
                discrepancy_actual="Empty test fixtures provided; cannot certify semantic invariance"
            )

        total_orig_atp = 0
        total_cand_atp = 0

        # Test both terms on each frozen input
        for test_in in self.frozen_inputs:
            test_orig_app = App(original_term, test_in)
            test_cand_app = App(candidate_term, test_in)

            try:
                res_orig = evaluate(test_orig_app, max_atp=self.atp_budget_per_test)
            except Exception as e:
                return EvaluationReceipt(
                    verdict=MutationVerdict.REJECTED_BUDGET_EXCEEDED,
                    semantic_preserved=False,
                    atp_original=total_orig_atp,
                    atp_candidate=total_cand_atp,
                    atp_delta=0,
                    size_original=orig_size,
                    size_candidate=cand_size,
                    size_delta=size_delta,
                    test_inputs_count=len(self.frozen_inputs),
                    discrepancy_input=str(test_in),
                    discrepancy_expected=None,
                    discrepancy_actual=f"Original failed evaluation: {e}"
                )

            try:
                res_cand = evaluate(test_cand_app, max_atp=self.atp_budget_per_test)
            except Exception as e:
                return EvaluationReceipt(
                    verdict=MutationVerdict.REJECTED_BUDGET_EXCEEDED,
                    semantic_preserved=False,
                    atp_original=total_orig_atp,
                    atp_candidate=total_cand_atp,
                    atp_delta=0,
                    size_original=orig_size,
                    size_candidate=cand_size,
                    size_delta=size_delta,
                    test_inputs_count=len(self.frozen_inputs),
                    discrepancy_input=str(test_in),
                    discrepancy_expected=None,
                    discrepancy_actual=f"Candidate exceeded budget or errored: {e}"
                )

            # K3: Settled Execution Gate — both original and candidate MUST be settled.
            # If either or both are suspended (out of ATP budget), semantic equivalence is unproven.
            if not res_orig.is_settled() or not res_cand.is_settled():
                return EvaluationReceipt(
                    verdict=MutationVerdict.REJECTED_BUDGET_EXCEEDED,
                    semantic_preserved=False,
                    atp_original=total_orig_atp + res_orig.atp_spent,
                    atp_candidate=total_cand_atp + res_cand.atp_spent,
                    atp_delta=(total_cand_atp + res_cand.atp_spent) - (total_orig_atp + res_orig.atp_spent),
                    size_original=orig_size,
                    size_candidate=cand_size,
                    size_delta=size_delta,
                    test_inputs_count=len(self.frozen_inputs),
                    discrepancy_input=str(test_in),
                    discrepancy_expected=f"SETTLED (got {res_orig.status.value})",
                    discrepancy_actual=f"SETTLED (got {res_cand.status.value})"
                )

            total_orig_atp += res_orig.atp_spent
            total_cand_atp += res_cand.atp_spent

            # Semantic equivalence check
            if res_orig.normal_form != res_cand.normal_form:
                return EvaluationReceipt(
                    verdict=MutationVerdict.REJECTED_SEMANTIC_MISMATCH,
                    semantic_preserved=False,
                    atp_original=total_orig_atp,
                    atp_candidate=total_cand_atp,
                    atp_delta=total_cand_atp - total_orig_atp,
                    size_original=orig_size,
                    size_candidate=cand_size,
                    size_delta=size_delta,
                    test_inputs_count=len(self.frozen_inputs),
                    discrepancy_input=str(test_in),
                    discrepancy_expected=str(res_orig.normal_form),
                    discrepancy_actual=str(res_cand.normal_form)
                )

        atp_delta = total_cand_atp - total_orig_atp

        # Measurable benefit criterion:
        # Candidate strictly saves ATP, or preserves ATP while reducing syntactic AST size
        if atp_delta < 0 or (atp_delta == 0 and size_delta < 0):
            verdict = MutationVerdict.ACCEPTED_MORE_EFFICIENT
        else:
            verdict = MutationVerdict.REJECTED_NO_EFFICIENCY_GAIN

        return EvaluationReceipt(
            verdict=verdict,
            semantic_preserved=True,
            atp_original=total_orig_atp,
            atp_candidate=total_cand_atp,
            atp_delta=atp_delta,
            size_original=orig_size,
            size_candidate=cand_size,
            size_delta=size_delta,
            test_inputs_count=len(self.frozen_inputs)
        )


# ============================================================================
# 4. SCIENTIFIC EXPERIMENT LEDGER (POSITIVE & NEGATIVE KNOWLEDGE)
# ============================================================================

@dataclass
class ExperimentRecord:
    experiment_id: str
    timestamp_utc: str
    gene_id: str
    rule_name: str
    site_address: Address
    original_subterm: str
    proposed_subterm: str
    original_term: str
    candidate_term: str
    verdict: MutationVerdict
    atp_original: int
    atp_candidate: int
    atp_delta: int
    size_original: int
    size_candidate: int
    size_delta: int
    test_inputs_count: int
    discrepancy_detail: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "timestamp_utc": self.timestamp_utc,
            "gene_id": self.gene_id,
            "rule_name": self.rule_name,
            "site_address": list(self.site_address),
            "original_subterm": self.original_subterm,
            "proposed_subterm": self.proposed_subterm,
            "original_term": self.original_term,
            "candidate_term": self.candidate_term,
            "verdict": self.verdict.value,
            "atp_original": self.atp_original,
            "atp_candidate": self.atp_candidate,
            "atp_delta": self.atp_delta,
            "size_original": self.size_original,
            "size_candidate": self.size_candidate,
            "size_delta": self.size_delta,
            "test_inputs_count": self.test_inputs_count,
            "discrepancy_detail": self.discrepancy_detail
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> ExperimentRecord:
        return cls(
            experiment_id=d["experiment_id"],
            timestamp_utc=d["timestamp_utc"],
            gene_id=d["gene_id"],
            rule_name=d["rule_name"],
            site_address=tuple(d["site_address"]),
            original_subterm=d["original_subterm"],
            proposed_subterm=d["proposed_subterm"],
            original_term=d["original_term"],
            candidate_term=d["candidate_term"],
            verdict=MutationVerdict(d["verdict"]),
            atp_original=d["atp_original"],
            atp_candidate=d["atp_candidate"],
            atp_delta=d["atp_delta"],
            size_original=d["size_original"],
            size_candidate=d["size_candidate"],
            size_delta=d["size_delta"],
            test_inputs_count=d["test_inputs_count"],
            discrepancy_detail=d.get("discrepancy_detail")
        )


def derive_experiment_id(
    gene_id: str,
    site_address: Address,
    rule_name: str,
    original_term: str,
    candidate_term: str
) -> str:
    """Computes a deterministic content-addressed experiment ID."""
    seed = f"EXP:{gene_id}:{list(site_address)}:{rule_name}:{original_term}:{candidate_term}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]


@dataclass
class ExperimentLog:
    records: List[ExperimentRecord] = field(default_factory=list)

    def record_experiment(
        self,
        proposal: MutationProposal,
        receipt: EvaluationReceipt
    ) -> ExperimentRecord:
        eid = derive_experiment_id(
            proposal.gene_id,
            proposal.site_address,
            proposal.rule.name,
            str(proposal.original_term),
            str(proposal.candidate_term)
        )
        detail = None
        if receipt.verdict == MutationVerdict.REJECTED_SEMANTIC_MISMATCH:
            detail = f"Input '{receipt.discrepancy_input}' diverged: expected '{receipt.discrepancy_expected}', got '{receipt.discrepancy_actual}'"
        elif receipt.verdict == MutationVerdict.REJECTED_NO_EFFICIENCY_GAIN:
            detail = f"Preserved semantics, but no gain (Delta ATP={receipt.atp_delta:+d}, Delta Size={receipt.size_delta:+d})"

        rec = ExperimentRecord(
            experiment_id=eid,
            timestamp_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            gene_id=proposal.gene_id,
            rule_name=proposal.rule.name,
            site_address=proposal.site_address,
            original_subterm=str(proposal.original_subterm),
            proposed_subterm=str(proposal.proposed_subterm),
            original_term=str(proposal.original_term),
            candidate_term=str(proposal.candidate_term),
            verdict=receipt.verdict,
            atp_original=receipt.atp_original,
            atp_candidate=receipt.atp_candidate,
            atp_delta=receipt.atp_delta,
            size_original=receipt.size_original,
            size_candidate=receipt.size_candidate,
            size_delta=receipt.size_delta,
            test_inputs_count=receipt.test_inputs_count,
            discrepancy_detail=detail
        )
        self.records.append(rec)
        return rec

    def accepted_records(self) -> List[ExperimentRecord]:
        return [r for r in self.records if r.verdict == MutationVerdict.ACCEPTED_MORE_EFFICIENT]

    def rejected_records(self) -> List[ExperimentRecord]:
        return [r for r in self.records if r.verdict != MutationVerdict.ACCEPTED_MORE_EFFICIENT]

    def to_list(self) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in self.records]

    @classmethod
    def from_list(cls, l: List[Dict[str, Any]]) -> ExperimentLog:
        return cls([ExperimentRecord.from_dict(d) for d in l])


# ============================================================================
# 5. METAMORPHIC TRANSITION RECEIPT & SUCCESSOR MINTING
# ============================================================================

@dataclass
class MetamorphicTransitionReceipt:
    parent_hash: str
    successor_hash: str
    gene_id: str
    rule_name: str
    site_address: Address
    pre_term: str
    post_term: str
    atp_saved: int
    size_saved: int
    fixtures_fingerprint: str
    experiment_id: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "parent_hash": self.parent_hash,
            "successor_hash": self.successor_hash,
            "gene_id": self.gene_id,
            "rule_name": self.rule_name,
            "site_address": list(self.site_address),
            "pre_term": self.pre_term,
            "post_term": self.post_term,
            "atp_saved": self.atp_saved,
            "size_saved": self.size_saved,
            "fixtures_fingerprint": self.fixtures_fingerprint,
            "experiment_id": self.experiment_id
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> MetamorphicTransitionReceipt:
        return cls(
            parent_hash=d["parent_hash"],
            successor_hash=d["successor_hash"],
            gene_id=d["gene_id"],
            rule_name=d["rule_name"],
            site_address=tuple(d["site_address"]),
            pre_term=d["pre_term"],
            post_term=d["post_term"],
            atp_saved=d["atp_saved"],
            size_saved=d["size_saved"],
            fixtures_fingerprint=d["fixtures_fingerprint"],
            experiment_id=d["experiment_id"]
        )


ALLOWED_MUTATION_RULES: set[str] = {
    "S(K x)(K y) -> K(x y)",
    "S(K x)I -> x",
    "S(K I) -> I",
    "I x -> x",
    "K x y -> x",
    "MUTATION_CHILD_SWAP",
    "MUTATION_CONSTANT_COLLAPSE",
}


class MetamorphicProvenanceError(ValueError):
    """Raised when an alleged metamorphic transition fails independent replay or verification."""
    pass


def contemplate_and_evolve(
    organism: Organism,
    evaluator: Optional[FrozenEvaluator] = None
) -> Tuple[Optional[Organism], ExperimentLog, Optional[MetamorphicTransitionReceipt]]:
    """
    Autonomous self-contemplation engine:
    1. Organism reads the addressable AST representation of its own chromosomes.
    2. Proposes local form changes (algebraic simplifications and exploratory mutations).
    3. External invariant evaluator tests each candidate against frozen inputs.
    4. All experiments (accepted and rejected) are recorded in the scientific experiment log.
    5. The best accepted candidate is minted into a successor organism carrying the transition receipt.
    """
    if evaluator is None:
        evaluator = FrozenEvaluator()

    log = ExperimentLog()
    best_candidate: Optional[Tuple[MutationProposal, EvaluationReceipt, Chromosome, ExperimentRecord]] = None
    best_savings = -1

    for chrom in organism.chromosomes:
        proposals = propose_form_metamorphoses(chrom, include_exploratory=True)
        for prop in proposals:
            orig_term = parse(chrom.expression)
            receipt = evaluator.evaluate_transformation(orig_term, prop.candidate_term)
            rec = log.record_experiment(prop, receipt)

            if receipt.verdict == MutationVerdict.ACCEPTED_MORE_EFFICIENT:
                savings = -receipt.atp_delta
                if savings > best_savings:
                    best_savings = savings
                    best_candidate = (prop, receipt, chrom, rec)

    if best_candidate is None:
        return None, log, None

    prop, receipt, target_chrom, best_rec = best_candidate

    # Mint successor organism
    new_chromosomes = []
    for c in organism.chromosomes:
        if c.gene_id == prop.gene_id:
            # Update expression to optimized form
            new_chrom = Chromosome(
                gene_id=c.gene_id,
                gene_name=c.gene_name,
                expression=str(prop.candidate_term),
                expected_normal_form=c.expected_normal_form,
                max_atp=c.max_atp,
                atp_burned=0,
                vital=c.vital
            )
            new_chromosomes.append(new_chrom)
        else:
            new_chromosomes.append(Chromosome.from_dict(c.to_dict()))

    successor = Organism(
        generation=organism.generation + 1,
        parent_hash=organism.organism_hash or organism.compute_hash(),
        public_key_hex=organism.public_key_hex,
        secret_key_hex=organism.secret_key_hex,
        chromosomes=new_chromosomes
    )
    successor.organism_hash = successor.compute_hash()

    trans_receipt = MetamorphicTransitionReceipt(
        parent_hash=organism.organism_hash or organism.compute_hash(),
        successor_hash=successor.organism_hash,
        gene_id=prop.gene_id,
        rule_name=prop.rule.name,
        site_address=prop.site_address,
        pre_term=target_chrom.expression,
        post_term=str(prop.candidate_term),
        atp_saved=-receipt.atp_delta,
        size_saved=-receipt.size_delta,
        fixtures_fingerprint=evaluator.fixtures_fingerprint,
        experiment_id=best_rec.experiment_id
    )

    return successor, log, trans_receipt


def audit_metamorphic_transition(
    parent: Organism,
    successor: Organism,
    receipt: MetamorphicTransitionReceipt,
    evaluator: Optional[FrozenEvaluator] = None,
    experiment_log: Optional[ExperimentLog] = None
) -> Tuple[bool, str]:
    """
    Independent replay auditor:
    1. Verifies cryptographic parent/child hash linkage.
    2. Verifies operation rule validity against closed rule set.
    3. Verifies pre_term, post_term, and size_saved claims against parent.
    4. Reconstructs and verifies that non-target chromosomes are strictly unmodified.
    5. Confirms successor metabolic viability and verification.
    6. Re-runs external frozen evaluator to confirm semantic equivalence and ATP conservation.
    7. Verifies experiment ID derivation and provenance ledger linkage.
    Fails closed on any inconsistency.
    """
    if evaluator is None:
        evaluator = FrozenEvaluator()

    # 1. Closed rule set check (K2)
    if receipt.rule_name not in ALLOWED_MUTATION_RULES:
        raise MetamorphicProvenanceError(
            f"Unrecognized or unauthorized mutation rule: '{receipt.rule_name}'"
        )

    # 2. Verify parent hash
    parent_actual_hash = parent.compute_hash()
    if receipt.parent_hash != parent_actual_hash:
        raise MetamorphicProvenanceError(
            f"Parent hash mismatch: claimed '{receipt.parent_hash}', actual '{parent_actual_hash}'"
        )
    if successor.parent_hash != parent_actual_hash:
        raise MetamorphicProvenanceError(
            f"Successor parent pointer mismatch: claimed '{successor.parent_hash}', actual '{parent_actual_hash}'"
        )

    # 3. Verify successor hash
    succ_actual_hash = successor.compute_hash()
    if receipt.successor_hash != succ_actual_hash:
        raise MetamorphicProvenanceError(
            f"Successor hash mismatch: claimed '{receipt.successor_hash}', actual '{succ_actual_hash}'"
        )

    # 4. Successor lifecycle and generation check
    if successor.generation != parent.generation + 1:
        raise MetamorphicProvenanceError(
            f"Successor generation mismatch: parent gen #{parent.generation}, successor gen #{successor.generation}"
        )

    # 5. Check chromosome collection uniqueness and count (K1)
    p_gene_ids = [c.gene_id for c in parent.chromosomes]
    s_gene_ids = [c.gene_id for c in successor.chromosomes]
    if len(p_gene_ids) != len(set(p_gene_ids)):
        raise MetamorphicProvenanceError("Parent organism contains duplicate gene_ids")
    if len(s_gene_ids) != len(set(s_gene_ids)):
        raise MetamorphicProvenanceError("Successor organism contains duplicate gene_ids")
    if len(p_gene_ids) != len(s_gene_ids):
        raise MetamorphicProvenanceError(
            f"Genome size mismatch: parent has {len(p_gene_ids)} chromosomes, successor has {len(s_gene_ids)}"
        )
    if receipt.gene_id not in p_gene_ids:
        raise MetamorphicProvenanceError(f"Target gene '{receipt.gene_id}' not found in parent organism")
    if receipt.gene_id not in s_gene_ids:
        raise MetamorphicProvenanceError(f"Target gene '{receipt.gene_id}' not found in successor organism")

    # 6. Locate target chromosome in parent
    parent_chrom = next(c for c in parent.chromosomes if c.gene_id == receipt.gene_id)
    parent_term = parse(parent_chrom.expression)

    # 7. Check pre_term claim (K2)
    if receipt.pre_term != parent_chrom.expression:
        raise MetamorphicProvenanceError(
            f"Claimed pre_term '{receipt.pre_term}' does not match parent gene expression '{parent_chrom.expression}'"
        )

    # 8. Replay local substitution from parent payload
    try:
        subterm = get_subterm_at(parent_term, receipt.site_address)
        rewrites = match_and_rewrite(subterm)
        matching_rewrite = next((r for r in rewrites if r[0].name == receipt.rule_name), None)

        if matching_rewrite is not None:
            replayed_term = replace_subterm_at(parent_term, receipt.site_address, matching_rewrite[1])
        elif receipt.rule_name == "MUTATION_CHILD_SWAP" and isinstance(subterm, App):
            replayed_term = replace_subterm_at(parent_term, receipt.site_address, App(subterm.right, subterm.left))
        elif receipt.rule_name == "MUTATION_CONSTANT_COLLAPSE":
            replayed_term = replace_subterm_at(parent_term, receipt.site_address, K)
        else:
            raise MetamorphicProvenanceError(
                f"Rule '{receipt.rule_name}' does not apply to subterm '{subterm}' at {receipt.site_address}"
            )
    except Exception as e:
        raise MetamorphicProvenanceError(f"Failed to replay transition from parent: {e}")

    # 9. Verify post_term claim against replayed term (K2)
    if receipt.post_term != str(replayed_term):
        raise MetamorphicProvenanceError(
            f"Claimed post_term '{receipt.post_term}' does not match replayed term '{replayed_term}'"
        )

    # 10. Verify size_saved claim (K2)
    expected_size_saved = tree_size(parent_term) - tree_size(replayed_term)
    if receipt.size_saved != expected_size_saved:
        raise MetamorphicProvenanceError(
            f"Claimed size_saved {receipt.size_saved} does not match actual difference {expected_size_saved}"
        )

    # 11. Whole-genome invariance verification (K1)
    for p_c, s_c in zip(parent.chromosomes, successor.chromosomes):
        if p_c.gene_id != receipt.gene_id:
            # Off-target chromosome MUST be strictly unmodified
            if (s_c.gene_id != p_c.gene_id or
                s_c.gene_name != p_c.gene_name or
                s_c.expression != p_c.expression or
                s_c.expected_normal_form != p_c.expected_normal_form or
                s_c.max_atp != p_c.max_atp or
                s_c.vital != p_c.vital):
                raise MetamorphicProvenanceError(
                    f"Off-target chromosome '{p_c.gene_id}' was altered in successor organism without authorization"
                )
        else:
            # Target chromosome MUST have the exact replayed expression
            if (s_c.gene_id != p_c.gene_id or
                s_c.gene_name != p_c.gene_name or
                s_c.expression != str(replayed_term) or
                s_c.max_atp != p_c.max_atp or
                s_c.vital != p_c.vital):
                raise MetamorphicProvenanceError(
                    f"Target chromosome '{p_c.gene_id}' in successor does not match replayed transition"
                )

    # 12. Check successor cryptographic key validity and provenance
    from crypto import is_valid_public_key
    if not is_valid_public_key(successor.public_key_hex):
        raise MetamorphicProvenanceError("Successor public key is invalid or malformed")
    if successor.public_key_hex != parent.public_key_hex:
        raise MetamorphicProvenanceError("Successor public key diverges from parent public key")

    # 13. Re-evaluate on frozen fixtures
    if evaluator.fixtures_fingerprint != receipt.fixtures_fingerprint:
        raise MetamorphicProvenanceError(
            f"Test fixtures fingerprint mismatch: claimed '{receipt.fixtures_fingerprint}', actual '{evaluator.fixtures_fingerprint}'"
        )

    succ_term = parse(successor.chromosomes[p_gene_ids.index(receipt.gene_id)].expression)
    eval_receipt = evaluator.evaluate_transformation(parent_term, succ_term)
    if not eval_receipt.semantic_preserved:
        raise MetamorphicProvenanceError(
            f"Semantic preservation failure: candidate diverged on input '{eval_receipt.discrepancy_input}'"
        )

    atp_saved_actual = -eval_receipt.atp_delta
    if atp_saved_actual != receipt.atp_saved:
        raise MetamorphicProvenanceError(
            f"Claimed ATP savings mismatch: claimed {receipt.atp_saved}, actual {atp_saved_actual}"
        )

    if eval_receipt.verdict != MutationVerdict.ACCEPTED_MORE_EFFICIENT:
        raise MetamorphicProvenanceError(
            f"Transition did not achieve measurable efficiency gain: {eval_receipt.verdict}"
        )

    # 14. Verify experiment ID derivation and provenance (K2, K4)
    expected_exp_id = derive_experiment_id(
        receipt.gene_id,
        receipt.site_address,
        receipt.rule_name,
        receipt.pre_term,
        receipt.post_term
    )
    if receipt.experiment_id != expected_exp_id:
        raise MetamorphicProvenanceError(
            f"Experiment ID derivation mismatch: claimed '{receipt.experiment_id}', expected '{expected_exp_id}'"
        )

    if experiment_log is not None:
        rec = next((r for r in experiment_log.records if r.experiment_id == receipt.experiment_id), None)
        if rec is None:
            raise MetamorphicProvenanceError(
                f"Claimed experiment_id '{receipt.experiment_id}' not found in provided experiment ledger"
            )
        if (rec.gene_id != receipt.gene_id or
            rec.candidate_term != receipt.post_term or
            rec.site_address != receipt.site_address or
            rec.rule_name != receipt.rule_name or
            rec.verdict != MutationVerdict.ACCEPTED_MORE_EFFICIENT):
            raise MetamorphicProvenanceError(
                "Experiment ledger record attributes diverge from transition receipt"
            )

    return True, f"TRANSITION VERIFIED: {receipt.rule_name} on gene '{receipt.gene_id}' saved {atp_saved_actual} ATP (Q.E.D.)"


# ============================================================================
# 6. STANDALONE EXECUTABLE POLYGLOT COMPILER
# ============================================================================

class MetamorphicPolyglotCompiler:
    """
    Compiles an ISO 32000 PDF document carrying both the visual proof of form
    metamorphosis and an executable Python autonomous audit engine.
    """
    def __init__(
        self,
        parent: Organism,
        successor: Organism,
        transition: MetamorphicTransitionReceipt,
        log: ExperimentLog
    ):
        self.parent = parent
        self.successor = successor
        self.transition = transition
        self.log = log

    def _build_pdf_stream(self) -> bytes:
        def _clean(s: Any) -> str:
            if s is None:
                return ""
            txt = str(s)
            txt = txt.replace(GLYPH_K, "K").replace(GLYPH_I, "I").replace(GLYPH_S, "S").replace(GLYPH_Y, "Y").replace(GLYPH_ANCHOR, "#")
            txt = txt.replace("\U0001f5a4", "K").replace("\U0001f90d", "I").replace("\U0001f33f", "S").replace("\U0001f501", "Y").replace("\u2693", "#")
            res = []
            for ch in txt:
                if 32 <= ord(ch) < 127:
                    if ch in "()\\":
                        res.append("\\\\" + ch)
                    else:
                        res.append(ch)
                elif ord(ch) == 10 or ord(ch) == 13:
                    res.append(" ")
                else:
                    res.append("?")
            return "".join(res)

        ops = []
        # Background: Deep Obsidian to Slate Gradient Simulation
        ops.append("q")
        ops.append("0.04 0.05 0.08 rg 0 0 595.28 841.89 re f")

        # Header Title
        ops.append("BT /F1 18 Tf 0.95 0.75 0.2 rg 40 800 Td (% BLACK-HEART AUTONOMOUS FORM METAMORPHOSIS) Tj ET")
        ops.append("BT /F2 9.5 Tf 0.6 0.7 0.8 rg 40 782 Td (Program Self-Contemplation & Invariant-Preserving Form Evolution) Tj ET")

        # Lineage Card
        ops.append("0.08 0.12 0.18 rg 40 685 515.28 80 re f")
        ops.append("0.2 0.35 0.5 RG 1 w 40 685 515.28 80 re S")
        ops.append("BT /F1 10.5 Tf 0.4 0.85 0.95 rg 55 745 Td (GENERATIONAL TRANSITION & PEDIGREE) Tj ET")
        ops.append(f"BT /F2 8.5 Tf 0.8 0.85 0.9 rg 55 728 Td (Parent Generation: #{self.parent.generation}  [Hash: {self.parent.organism_hash[:16]}...]) Tj ET")
        ops.append(f"BT /F2 8.5 Tf 0.8 0.85 0.9 rg 55 712 Td (Successor Gen:     #{self.successor.generation}  [Hash: {self.successor.organism_hash[:16]}...]) Tj ET")
        gene_c = _clean(self.transition.gene_id)
        rule_c = _clean(self.transition.rule_name)
        ops.append(f"BT /F1 9 Tf 0.3 0.95 0.5 rg 55 696 Td ([*] Target Gene: '{gene_c}' | Rule: '{rule_c}') Tj ET")

        # Efficiency Card
        ops.append("0.08 0.12 0.18 rg 40 590 515.28 80 re f")
        ops.append("0.2 0.35 0.5 RG 1 w 40 590 515.28 80 re S")
        ops.append("BT /F1 10.5 Tf 0.95 0.7 0.2 rg 55 650 Td (MEASURED COMPUTATIONAL BENEFIT (INDEPENDENT ORACLE)) Tj ET")
        ops.append(f"BT /F2 9 Tf 0.85 0.9 0.95 rg 55 632 Td (Energy Saved: Delta ATP = -{self.transition.atp_saved} fuel quanta  |  Syntactic Delta: {self.transition.size_saved:+d} AST nodes) Tj ET")
        pre_c = _clean(self.transition.pre_term[:50])
        post_c = _clean(self.transition.post_term[:50])
        ops.append(f"BT /F2 8.5 Tf 0.7 0.75 0.8 rg 55 616 Td (Pre-form:  {pre_c}) Tj ET")
        ops.append(f"BT /F2 8.5 Tf 0.4 0.95 0.5 rg 55 600 Td (Post-form: {post_c}) Tj ET")

        # Empirical Experiment Table Card
        ops.append("0.08 0.12 0.18 rg 40 280 515.28 295 re f")
        ops.append("0.2 0.35 0.5 RG 1 w 40 280 515.28 295 re S")
        ops.append("BT /F1 10.5 Tf 0.95 0.4 0.6 rg 55 555 Td (EMPIRICAL SCIENTIFIC LEDGER (ACCEPTED & REJECTED EXPERIMENTS)) Tj ET")
        ops.append("BT /F2 7.5 Tf 0.55 0.65 0.75 rg 55 538 Td (ID          VERDICT                     RULE                        DELTA ATP   DETAILS) Tj ET")
        ops.append("0.2 0.3 0.4 RG 0.5 w 55 532 m 540 532 l S")

        y = 518
        for r in self.log.records[:12]:
            if r.verdict == MutationVerdict.ACCEPTED_MORE_EFFICIENT:
                c_str = "0.3 0.95 0.4"
                v_badge = "ACCEPTED (SOUND)"
            elif r.verdict == MutationVerdict.REJECTED_SEMANTIC_MISMATCH:
                c_str = "0.95 0.35 0.35"
                v_badge = "REJECTED (DIVERGED)"
            else:
                c_str = "0.95 0.7 0.3"
                v_badge = "REJECTED (NO GAIN)"

            rule_abbr = _clean(r.rule_name[:22])
            det_abbr = _clean((r.discrepancy_detail or "Equivalence verified")[:26])
            eid_c = _clean(r.experiment_id[:10])
            ops.append(f"BT /F2 7.5 Tf {c_str} rg 55 {y} Td ({eid_c:10s}  {v_badge:26s}  {rule_abbr:24s}  {r.atp_delta:+4d} ATP    {det_abbr}) Tj ET")
            y -= 18

        # Footer Passport Stamp
        ops.append("0.1 0.25 0.4 RG 1 w 40 180 515.28 85 re S")
        ops.append("BT /F1 9 Tf 0.5 0.8 1.0 rg 55 245 Td (CRYPTOGRAPHIC AUTONOMY & REPLAY PROVENANCE) Tj ET")
        ops.append(f"BT /F2 7.5 Tf 0.7 0.8 0.85 rg 55 230 Td (Parent Public Key:   {self.parent.public_key_hex}) Tj ET")
        ops.append(f"BT /F2 7.5 Tf 0.7 0.8 0.85 rg 55 215 Td (Fixtures Fingerprint: {self.transition.fixtures_fingerprint}) Tj ET")
        ops.append(f"BT /F2 7.5 Tf 0.7 0.8 0.85 rg 55 200 Td (Transition Stamp:     sha256:{self.transition.successor_hash[:32]}...) Tj ET")
        ops.append("BT /F1 8.5 Tf 0.3 0.95 0.5 rg 55 186 Td ([*] Standalone executable: 'python3 <this_file.pdf> --audit' to verify proof) Tj ET")
        ops.append("Q")

        return "\n".join(ops).encode("latin1")

    def _build_runner_script(self) -> str:
        return r'''#!/usr/bin/env python3
# coding: latin-1
import os, sys, json, hashlib

MANIFEST_PREFIX = "# %METAMORPHOSIS"

def load_manifest():
    with open(__file__, "rb") as f:
        content = f.read()
    p = MANIFEST_PREFIX.encode("latin1")
    start = content.rfind(p)
    if start == -1:
        print("[FAIL] Missing Metamorphosis manifest in polyglot.")
        sys.exit(1)
    end = content.find(b"\n", start)
    if end == -1:
        end = len(content)
    line = content[start + len(p):end].decode("utf-8")
    return json.loads(line)

def cmd_info():
    data = load_manifest()
    print("=================================================================")
    print("  %[BH] BLACK-HEART AUTONOMOUS FORM METAMORPHOSIS PASSPORT")
    print("=================================================================\n")
    print(f"[*] Parent Hash:        [#] {data['parent']['organism_hash']}")
    print(f"[*] Successor Hash:     [#] {data['successor']['organism_hash']}")
    print(f"[*] Transition Rule:    {data['transition']['rule_name']}")
    print(f"[*] Target Gene ID:     {data['transition']['gene_id']}")
    print(f"[*] Energy Conserved:   +{data['transition']['atp_saved']} ATP")
    print(f"[*] Size Differential:  {data['transition']['size_saved']:+d} AST nodes\n")
    print(f"Pre-metamorphosis Form:  {data['transition']['pre_term']}")
    print(f"Post-metamorphosis Form: {data['transition']['post_term']}\n")

def cmd_experiments():
    data = load_manifest()
    print("=================================================================")
    print("  %[BH] SCIENTIFIC EXPERIMENT LEDGER (POSITIVE & NEGATIVE KNOWLEDGE)")
    print("=================================================================\n")
    print(f"{'ID':12s} {'VERDICT':28s} {'RULE':26s} {'DELTA ATP':10s}")
    print("-" * 75)
    for r in data["experiments"]:
        v = r["verdict"]
        print(f"{r['experiment_id']:12s} {v:28s} {r['rule_name'][:24]:26s} {r['atp_delta']:+6d} ATP")
        if r.get("discrepancy_detail"):
            print(f"    --> Details: {r['discrepancy_detail']}")
    print("-" * 75)
    total = len(data["experiments"])
    acc = sum(1 for r in data["experiments"] if r["verdict"] == "ACCEPTED_MORE_EFFICIENT")
    print(f"Total Experiments: {total} | Accepted Transitions: {acc} | Preserved Failures: {total - acc}\n")

def cmd_audit():
    data = load_manifest()
    src_dir = data.get("source_dir")
    if src_dir and src_dir not in sys.path:
        sys.path.insert(0, src_dir)
    from metamorphosis import Organism, MetamorphicTransitionReceipt, FrozenEvaluator, ExperimentLog, audit_metamorphic_transition

    parent = Organism(
        generation=data['parent']['generation'],
        parent_hash=data['parent']['parent_hash'],
        public_key_hex=data['parent']['public_key_hex'],
        secret_key_hex=data['parent'].get('secret_key_hex', ''),
        chromosomes=[Organism.__dataclass_fields__['chromosomes'].default_factory() for _ in [0]][0]
    )
    # Reconstruct chromosomes
    from organism import Chromosome
    parent.chromosomes = [Chromosome.from_dict(c) for c in data['parent']['chromosomes']]
    parent.birth_timestamp_utc = data['parent']['birth_timestamp_utc']
    parent.organism_hash = data['parent']['organism_hash']

    successor = Organism(
        generation=data['successor']['generation'],
        parent_hash=data['successor']['parent_hash'],
        public_key_hex=data['successor']['public_key_hex'],
        secret_key_hex=data['successor'].get('secret_key_hex', ''),
        chromosomes=[Chromosome.from_dict(c) for c in data['successor']['chromosomes']],
        birth_timestamp_utc=data['successor']['birth_timestamp_utc'],
        organism_hash=data['successor']['organism_hash']
    )

    receipt = MetamorphicTransitionReceipt.from_dict(data['transition'])
    evaluator = FrozenEvaluator()
    exp_log = ExperimentLog.from_list(data.get('experiments', [])) if 'experiments' in data else None

    try:
        ok, msg = audit_metamorphic_transition(parent, successor, receipt, evaluator, experiment_log=exp_log)
        print("=================================================================")
        print("  %[BH] METAMORPHIC PROVENANCE & ORACLE AUDITOR")
        print("=================================================================\n")
        print(f"[*] Parent Hash:      \033[1;32m[OK] SOUND\033[0m (Hash: {parent.organism_hash[:16]}...)")
        print(f"[*] Successor Hash:   \033[1;32m[OK] SOUND\033[0m (Hash: {successor.organism_hash[:16]}...)")
        print(f"[*] Transition Replay:\033[1;32m[OK] SOUND\033[0m (Rule: {receipt.rule_name})")
        print(f"[*] Semantic Check:   \033[1;32m[OK] SOUND\033[0m (5 frozen fixtures invariant)")
        print(f"[*] Energy Reduction: \033[1;32m[OK] SOUND\033[0m (-{receipt.atp_saved} ATP saved)\n")
        print(f"\033[1;32m[OK] {msg}\033[0m\n")
    except Exception as e:
        print("=================================================================")
        print("  %[BH] METAMORPHIC PROVENANCE & ORACLE AUDITOR")
        print("=================================================================\n")
        print(f"\033[1;31m[FAIL] METAMORPHIC AUDIT FAILED: {e}\033[0m\n")
        sys.exit(1)

if __name__ == "__main__":
    if "--experiments" in sys.argv:
        cmd_experiments()
    elif "--audit" in sys.argv or "--audit-transition" in sys.argv:
        cmd_audit()
    else:
        cmd_info()
'''

    def compile_pdf(self, vault_bytes: Optional[bytes] = None) -> bytes:
        stream_bytes = self._build_pdf_stream()
        length = len(stream_bytes)

        manifest_data = {
            "source_dir": os.path.dirname(os.path.abspath(__file__)),
            "parent": {
                "generation": self.parent.generation,
                "parent_hash": self.parent.parent_hash,
                "organism_hash": self.parent.organism_hash or self.parent.compute_hash(),
                "public_key_hex": self.parent.public_key_hex,
                "birth_timestamp_utc": self.parent.birth_timestamp_utc,
                "chromosomes": [c.to_dict() for c in self.parent.chromosomes]
            },
            "successor": {
                "generation": self.successor.generation,
                "parent_hash": self.successor.parent_hash,
                "organism_hash": self.successor.organism_hash or self.successor.compute_hash(),
                "public_key_hex": self.successor.public_key_hex,
                "birth_timestamp_utc": self.successor.birth_timestamp_utc,
                "chromosomes": [c.to_dict() for c in self.successor.chromosomes]
            },
            "transition": self.transition.to_dict(),
            "experiments": self.log.to_list()
        }

        manifest_line = METAMORPHOSIS_MANIFEST_PREFIX + json.dumps(manifest_data, separators=(",", ":"), ensure_ascii=True) + "\n"
        runner_script = self._build_runner_script()

        # Build ISO 32000 PDF
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
            "# % PROJECT BLACK-HEART: AUTONOMOUS FORM METAMORPHOSIS POLYGLOT\n"
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
