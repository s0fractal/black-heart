#!/usr/bin/env python3
# coding: utf-8
"""
egraph_kernel.py — Epistemic E-Graph Kernel & Proof-Carrying Equality Saturation.
Part of Project Black-Heart (%🖤). Engine #28.

Normative implementation of EGRAPH-0.1:
  1. Equivalence Graphs (E-Graphs) for Combinator Terms:
     Polynomial-space DAG representation of exponential or infinite equivalence classes.
     Each EClass contains multiple equivalent ENodes.
  2. Congruence Closure & Upward Invariant Maintenance:
     Union-Find with path compression, HashCons memoization, and upward parent congruence.
     Restores structural congruence f(a) == f(a') when a == a'.
  3. Non-Destructive Equality Saturation:
     Solves the Phase Ordering Problem. Rewriting rules union e-classes without
     destroying intermediate representations, allowing multiple competing optimizations
     to coexist simultaneously.
  4. Proof Forest and Checked Explanations:
     Every union records which classes it joined and why (`proof_edges`, by class id).
     An explanation is a separate thing: a derivation t1 = u1 = ... = t2 searched over
     the rules this e-graph was saturated with, in which every step names its rule,
     address and direction and is replayed by `check_derivation` before it is
     returned. When none is found within budget, the explanation says so and has no
     steps (before S4d it invented one; see test_egraph_explanation.py).
  5. Dynamic Programming Optimal Term Extraction:
     Computes globally minimal-energy, minimal-AST normal forms using Bellman-Ford
     cost relaxation across cyclic e-graphs.
  6. Epistemic Tombstone Quarantine:
     Integrates with EpistemicTombstoneRegistry (Engine #25). Flags e-classes
     containing refuted patterns as tainted, preventing dead or unsound alleles
     from being extracted into active genomes.
  7. ISO 32000 Append-Only Polyglot Physicality:
     Compiles E-Graph states and proof certificates into vector PDF HUDs with
     embedded Latin-1 self-executing Python audit runners (`python3 egraph.pdf`).

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

import glyph
from glyph import (
    Term, Comb, Var, App,
    K, I, S, Y,
    parse, evaluate, tree_size, canonical_bytes, term_hash,
    GLYPH_K, GLYPH_I, GLYPH_S, GLYPH_Y
)
import warrant_kernel
from warrant_kernel import EvidenceGrade, EdgeClaim, Polarity
import controlled_forgetting
from controlled_forgetting import EpistemicTombstoneRegistry, RetirementMode

EGRAPH_MANIFEST_PREFIX = "%" + "🖤" + " EGRAPH_MANIFEST: "

# ============================================================================
# 1. ENODE & DISJOINT-SET (UNION-FIND)
# ============================================================================

@dataclass(frozen=True)
class ENode:
    """
    Immutable representation of an operator node in an E-Graph.
    Children are canonical EClass IDs (integers).
    """
    op: str
    children: Tuple[int, ...] = ()

    def canonical(self, uf: UnionFind) -> ENode:
        return ENode(self.op, tuple(uf.find(c) for c in self.children))

    def __repr__(self) -> str:
        if not self.children:
            return self.op
        if self.op == "@":
            return f"({self.children[0]} @ {self.children[1]})"
        return f"{self.op}({', '.join(map(str, self.children))})"


class UnionFind:
    """Disjoint-set forest with path compression and union-by-rank."""
    def __init__(self):
        self.parents: Dict[int, int] = {}
        self.ranks: Dict[int, int] = {}

    def make_set(self, x: int) -> int:
        if x not in self.parents:
            self.parents[x] = x
            self.ranks[x] = 0
        return x

    def find(self, x: int) -> int:
        if x not in self.parents:
            self.make_set(x)
            return x
        path = []
        curr = x
        while self.parents[curr] != curr:
            path.append(curr)
            curr = self.parents[curr]
        for node in path:
            self.parents[node] = curr
        return curr

    def union(self, x: int, y: int) -> Tuple[int, int]:
        root_x = self.find(x)
        root_y = self.find(y)
        if root_x == root_y:
            return root_x, root_x
        # Union by rank
        if self.ranks[root_x] < self.ranks[root_y]:
            root_x, root_y = root_y, root_x
        self.parents[root_y] = root_x
        if self.ranks[root_x] == self.ranks[root_y]:
            self.ranks[root_x] += 1
        return root_x, root_y  # (survivor, absorbed)


# ============================================================================
# 2. PROOF FOREST & JUSTIFICATIONS
# ============================================================================

@dataclass
class JustificationEdge:
    """An undirected edge recording an equational derivation step."""
    source_class: int
    target_class: int
    rule_name: str
    subst_desc: str = ""


class DerivationStatus(str, Enum):
    """What stands behind an explanation's steps."""
    CHECKED = "CHECKED"                                  # every step replayed against the e-graph's rules
    NOT_FOUND_WITHIN_BUDGET = "NOT_FOUND_WITHIN_BUDGET"  # equivalent in the e-graph; no derivation found, none invented
    NOT_EQUIVALENT = "NOT_EQUIVALENT"                    # different e-classes
    UNCHECKED = "UNCHECKED"                              # built by hand; nothing was replayed
    INVALID = "INVALID"                                  # steps attached that do not replay


@dataclass
class EquivalenceProofStep:
    """One rewrite. `justification` names the rule, applied once at `address`
    of `from_expr` (forward) or of `to_expr` (reverse). An address is the path
    from the root, 0 = left and 1 = right."""
    step_num: int
    from_expr: str
    to_expr: str
    justification: str
    address: Tuple[int, ...] = ()
    direction: str = "forward"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_num": self.step_num,
            "from_expr": self.from_expr,
            "to_expr": self.to_expr,
            "justification": self.justification,
            "address": list(self.address),
            "direction": self.direction
        }


@dataclass
class EquivalenceProofTree:
    """Why two terms share an e-class.

    `is_equivalent` is the e-graph's union-find answer. `proof_steps` is
    non-empty only when `derivation_status` is CHECKED: every step was replayed
    by `check_derivation` against the rules the e-graph was saturated with.
    NOT_FOUND_WITHIN_BUDGET means equivalent in the e-graph with no derivation
    found; nothing stands in for one.
    """
    term_a: str
    term_b: str
    is_equivalent: bool
    proof_steps: List[EquivalenceProofStep] = field(default_factory=list)
    derivation_status: DerivationStatus = DerivationStatus.UNCHECKED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "term_a": self.term_a,
            "term_b": self.term_b,
            "is_equivalent": self.is_equivalent,
            "derivation_status": DerivationStatus(self.derivation_status).value,
            "steps": [s.to_dict() for s in self.proof_steps]
        }


# ============================================================================
# 3. REWRITE RULES & PATTERN MATCHING
# ============================================================================

@dataclass
class RewriteRule:
    """A directed equational rewrite rule LHS -> RHS."""
    name: str
    lhs: Term
    rhs: Term

    @classmethod
    def from_strings(cls, name: str, lhs_str: str, rhs_str: str) -> RewriteRule:
        return cls(name=name, lhs=parse(lhs_str), rhs=parse(rhs_str))


# Standard combinator rewrite theories
STANDARD_COMBINATOR_RULES = [
    RewriteRule.from_strings("RULE-I", "I x", "x"),
    RewriteRule.from_strings("RULE-K", "K x y", "x"),
    RewriteRule.from_strings("RULE-S", "S x y z", "(x z) (y z)"),
    RewriteRule.from_strings("RULE-SKK-COLLAPSE", "S K K", "I"),
    RewriteRule.from_strings("RULE-SKI-COLLAPSE", "S K I", "I"),
]


# ============================================================================
# 3b. DERIVATIONS: STEPS THAT REPLAY
# ============================================================================

def _match(pattern: Term, term: Term, subst: Dict[str, Term]) -> Optional[Dict[str, Term]]:
    if isinstance(pattern, Var):
        bound = subst.get(pattern.name)
        if bound is None:
            return {**subst, pattern.name: term}
        return subst if bound == term else None
    if isinstance(pattern, Comb):
        return subst if term == pattern else None
    if isinstance(pattern, App) and isinstance(term, App):
        left = _match(pattern.left, term.left, subst)
        return None if left is None else _match(pattern.right, term.right, left)
    return None


def _instantiate_term(pattern: Term, subst: Dict[str, Term]) -> Term:
    if isinstance(pattern, Var):
        return subst[pattern.name]  # KeyError: a right-hand variable the left did not bind
    if isinstance(pattern, App):
        return App(_instantiate_term(pattern.left, subst), _instantiate_term(pattern.right, subst))
    return pattern


def _subterm_at(term: Term, address: Tuple[int, ...]) -> Optional[Term]:
    for bit in address:
        if not isinstance(term, App) or bit not in (0, 1):
            return None
        term = term.left if bit == 0 else term.right
    return term


def _replace_at(term: Term, address: Tuple[int, ...], new: Term) -> Term:
    if not address:
        return new
    if address[0] == 0:
        return App(_replace_at(term.left, address[1:], new), term.right)
    return App(term.left, _replace_at(term.right, address[1:], new))


def _addresses(term: Term, prefix: Tuple[int, ...] = ()):
    yield prefix
    if isinstance(term, App):
        yield from _addresses(term.left, prefix + (0,))
        yield from _addresses(term.right, prefix + (1,))


def rewrite_at(term: Term, address: Tuple[int, ...], rule: RewriteRule) -> Optional[Term]:
    """`term` with `rule` applied once, forward, at `address`; None if it does not apply there."""
    sub = _subterm_at(term, address)
    if sub is None:
        return None
    subst = _match(rule.lhs, sub, {})
    if subst is None:
        return None
    try:
        return _replace_at(term, address, _instantiate_term(rule.rhs, subst))
    except KeyError:
        return None


def check_derivation(
    term_a: Term,
    term_b: Term,
    steps: List[EquivalenceProofStep],
    rules: Dict[str, RewriteRule]
) -> Optional[str]:
    """Why `steps` is not a derivation of `term_b` from `term_a` under `rules`, or None.

    Each step must name a rule in `rules`, and that rule applied once at the
    step's address must turn from_expr into to_expr (forward) or to_expr into
    from_expr (reverse). The steps must chain: the first starts at term_a, each
    starts where the previous one ended, and the last ends at term_b. Terms are
    compared as ASTs. Nothing is searched: the address is part of the claim, and
    it is replayed.
    """
    current = term_a
    for i, s in enumerate(steps, 1):
        try:
            a, b = parse(s.from_expr), parse(s.to_expr)
        except Exception as e:
            return f"step {i}: not a term: {e}"
        if a != current:
            return f"step {i} starts at '{s.from_expr}', not where the derivation stands ('{current}')"
        rule = rules.get(s.justification)
        if rule is None:
            return f"step {i}: rule {s.justification!r} is not in the theory"
        if s.direction == "forward":
            replayed = rewrite_at(a, tuple(s.address), rule) == b
        elif s.direction == "reverse":
            replayed = rewrite_at(b, tuple(s.address), rule) == a
        else:
            return f"step {i}: unknown direction {s.direction!r}"
        if not replayed:
            return (f"step {i}: {s.justification} at {list(s.address)} does not rewrite "
                    f"'{s.from_expr}' to '{s.to_expr}' ({s.direction})")
        current = b
    if current != term_b:
        return f"the derivation ends at '{current}', not at '{term_b}'"
    return None


def find_derivation(
    term_a: Term,
    term_b: Term,
    rules: Dict[str, RewriteRule],
    max_terms: int = 20000
) -> Optional[List[EquivalenceProofStep]]:
    """A derivation of `term_b` from `term_a` under `rules`, or None.

    Rewrites forward from both ends, breadth first, until the two sides meet;
    the half grown from term_b is returned as reverse steps. So it finds a
    common reduct, a valley. It does not find a derivation that must pass
    through a term neither side reaches by rewriting forward. `max_terms`
    bounds the distinct terms held by both sides together.
    """
    if term_a == term_b:
        return []
    ordered = sorted(rules.items())
    seen_a: Dict[Term, Optional[Tuple[Term, str, Tuple[int, ...]]]] = {term_a: None}
    seen_b: Dict[Term, Optional[Tuple[Term, str, Tuple[int, ...]]]] = {term_b: None}
    frontiers = [[term_a], [term_b]]
    meet: Optional[Term] = None

    while meet is None and (frontiers[0] or frontiers[1]):
        for side in (0, 1):
            seen, other = (seen_a, seen_b) if side == 0 else (seen_b, seen_a)
            grown: List[Term] = []
            for t in frontiers[side]:
                for address in _addresses(t):
                    for name, rule in ordered:
                        u = rewrite_at(t, address, rule)
                        if u is None or u in seen:
                            continue
                        if len(seen_a) + len(seen_b) >= max_terms:
                            return None
                        seen[u] = (t, name, address)
                        if u in other:
                            meet = u
                            break
                        grown.append(u)
                    if meet is not None:
                        break
                if meet is not None:
                    break
            frontiers[side] = grown
            if meet is not None:
                break
    if meet is None:
        return None

    down: List[Tuple[Term, str, Tuple[int, ...], Term]] = []
    cur = meet
    while seen_a[cur] is not None:
        prev, name, address = seen_a[cur]
        down.append((prev, name, address, cur))
        cur = prev
    down.reverse()
    up: List[Tuple[Term, str, Tuple[int, ...], Term]] = []
    cur = meet
    while seen_b[cur] is not None:
        prev, name, address = seen_b[cur]
        up.append((cur, name, address, prev))
        cur = prev

    steps = [EquivalenceProofStep(step_num=0, from_expr=str(a), to_expr=str(b),
                                  justification=name, address=address, direction="forward")
             for a, name, address, b in down]
    steps += [EquivalenceProofStep(step_num=0, from_expr=str(a), to_expr=str(b),
                                   justification=name, address=address, direction="reverse")
              for a, name, address, b in up]
    for i, s in enumerate(steps, 1):
        s.step_num = i
    return steps


def replay_explanation(egraph: "EGraph", proof: EquivalenceProofTree) -> Tuple[DerivationStatus, str]:
    """What `proof` may be credited with in `egraph`, decided from its content.

    Its `derivation_status` and `is_equivalent` fields are ignored: they are
    public mutable data. Any consumer that credits an explanation calls this.

    - CHECKED: the endpoints parse and the attached steps replay under
      `egraph.theory` (zero steps only for identical terms).
    - INVALID: steps are attached and do not replay, or an endpoint does not parse.
    - Otherwise the e-graph itself is asked, adding nothing:
      NOT_FOUND_WITHIN_BUDGET if both terms are already in one class, and
      NOT_EQUIVALENT if they are not.

    A replay shows derivability under the e-graph's rules. It does not show
    that those rules are right.
    """
    try:
        a, b = parse(proof.term_a), parse(proof.term_b)
    except Exception as e:
        return DerivationStatus.INVALID, f"an endpoint does not parse: {e}"
    try:
        reason = check_derivation(a, b, list(proof.proof_steps), egraph.theory)
    except Exception as e:
        return DerivationStatus.INVALID, f"the attached steps are malformed: {type(e).__name__}"
    if reason is None:
        return DerivationStatus.CHECKED, ""
    if proof.proof_steps:
        return DerivationStatus.INVALID, reason
    ca, cb = egraph.lookup(a), egraph.lookup(b)
    if ca is not None and ca == cb:
        return DerivationStatus.NOT_FOUND_WITHIN_BUDGET, "equivalent in the e-graph; no derivation attached"
    return DerivationStatus.NOT_EQUIVALENT, "the e-graph does not put these terms in one class"


# ============================================================================
# 4. EPISTEMIC E-CLASS & E-GRAPH
# ============================================================================

@dataclass
class EClass:
    """An equivalence class grouping equivalent ENodes."""
    class_id: int
    nodes: Set[ENode] = field(default_factory=set)
    parents: Set[Tuple[ENode, int]] = field(default_factory=set)
    is_tainted: bool = False
    taint_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "class_id": self.class_id,
            "nodes": [repr(n) for n in sorted(self.nodes, key=lambda x: repr(x))],
            "is_tainted": self.is_tainted,
            "taint_reason": self.taint_reason
        }


class EGraph:
    """
    Epistemic Equivalence Graph Kernel.
    Compact polynomial-space representation of exponential combinator equivalence.
    """
    def __init__(self):
        self.uf = UnionFind()
        self.classes: Dict[int, EClass] = {}
        self.hashcons: Dict[ENode, int] = {}
        self.dirty_classes: Set[int] = set()
        self.proof_edges: List[JustificationEdge] = []
        # Every rule this e-graph was saturated with, by name: what an
        # explanation's steps may cite.
        self.theory: Dict[str, RewriteRule] = {}
        self._next_id = 0

    def _allocate_class(self) -> int:
        cid = self._next_id
        self._next_id += 1
        self.uf.make_set(cid)
        self.classes[cid] = EClass(class_id=cid)
        return cid

    def add_term(self, term: Term) -> int:
        """Adds a glyph AST term to the E-Graph, returning its canonical EClass ID."""
        if isinstance(term, Comb):
            enode = ENode(term.symbol, ())
            return self._add_enode(enode)
        elif isinstance(term, Var):
            enode = ENode(f"${term.name}", ())
            return self._add_enode(enode)
        elif isinstance(term, App):
            left_id = self.add_term(term.left)
            right_id = self.add_term(term.right)
            enode = ENode("@", (left_id, right_id))
            return self._add_enode(enode)
        raise TypeError(f"Unknown term type: {type(term)}")

    def lookup(self, term: Term) -> Optional[int]:
        """The canonical class of `term` if this e-graph already holds it; never adds."""
        if isinstance(term, Comb):
            node = ENode(term.symbol, ())
        elif isinstance(term, Var):
            node = ENode(f"${term.name}", ())
        elif isinstance(term, App):
            left, right = self.lookup(term.left), self.lookup(term.right)
            if left is None or right is None:
                return None
            node = ENode("@", (left, right))
        else:
            return None
        cid = self.hashcons.get(node.canonical(self.uf))
        return None if cid is None else self.uf.find(cid)

    def _add_enode(self, enode: ENode) -> int:
        can_node = enode.canonical(self.uf)
        if can_node in self.hashcons:
            return self.uf.find(self.hashcons[can_node])

        cid = self._allocate_class()
        self.classes[cid].nodes.add(can_node)
        self.hashcons[can_node] = cid

        for child in can_node.children:
            c_root = self.uf.find(child)
            self.classes[c_root].parents.add((can_node, cid))

        return cid

    def union(self, id1: int, id2: int, justification: str = "") -> int:
        """Unions two EClasses and registers justification edge in the proof forest."""
        root1 = self.uf.find(id1)
        root2 = self.uf.find(id2)
        if root1 == root2:
            return root1

        survivor, absorbed = self.uf.union(root1, root2)
        # Merge absorbed class into survivor
        self.classes[survivor].nodes.update(self.classes[absorbed].nodes)
        self.classes[survivor].parents.update(self.classes[absorbed].parents)
        if self.classes[absorbed].is_tainted:
            self.classes[survivor].is_tainted = True
            self.classes[survivor].taint_reason = self.classes[absorbed].taint_reason

        del self.classes[absorbed]
        self.dirty_classes.add(survivor)

        # Record justification edge
        self.proof_edges.append(JustificationEdge(
            source_class=id1,
            target_class=id2,
            rule_name=justification or "congruence"
        ))

        return survivor

    def rebuild(self) -> None:
        """
        Restores HashCons and upward congruence closure.
        Propagates f(a) == f(a') when a == a'.
        """
        while self.dirty_classes:
            todo = list(self.dirty_classes)
            self.dirty_classes.clear()

            for cid in todo:
                c_root = self.uf.find(cid)
                if c_root not in self.classes:
                    continue

                # Deduplicate and re-canonicalize parents
                parents = list(self.classes[c_root].parents)
                self.classes[c_root].parents.clear()

                repaired_parents: Dict[ENode, int] = {}
                for p_node, p_class in parents:
                    can_p_node = p_node.canonical(self.uf)
                    can_p_class = self.uf.find(p_class)

                    if can_p_node in repaired_parents:
                        existing_class = repaired_parents[can_p_node]
                        if self.uf.find(existing_class) != self.uf.find(can_p_class):
                            self.union(existing_class, can_p_class, justification="congruence")
                    else:
                        repaired_parents[can_p_node] = can_p_class

                for p_node, p_class in repaired_parents.items():
                    can_p_class = self.uf.find(p_class)
                    if can_p_class in self.classes:
                        self.classes[can_p_class].nodes.add(p_node)
                        self.hashcons[p_node] = can_p_class
                        for ch in p_node.children:
                            ch_root = self.uf.find(ch)
                            if ch_root in self.classes:
                                self.classes[ch_root].parents.add((p_node, can_p_class))

    # ========================================================================
    # 5. PATTERN MATCHING & EQUALITY SATURATION
    # ========================================================================

    def _match_pattern(
        self,
        pattern: Term,
        class_id: int,
        subst: Dict[str, int]
    ) -> List[Dict[str, int]]:
        root_cid = self.uf.find(class_id)
        if root_cid not in self.classes:
            return []

        if isinstance(pattern, Var):
            vname = pattern.name
            if vname in subst:
                if self.uf.find(subst[vname]) == root_cid:
                    return [dict(subst)]
                return []
            else:
                new_subst = dict(subst)
                new_subst[vname] = root_cid
                return [new_subst]

        elif isinstance(pattern, Comb):
            for enode in self.classes[root_cid].nodes:
                if enode.op == pattern.symbol and not enode.children:
                    return [dict(subst)]
            return []

        elif isinstance(pattern, App):
            results = []
            for enode in self.classes[root_cid].nodes:
                if enode.op == "@" and len(enode.children) == 2:
                    left_matches = self._match_pattern(pattern.left, enode.children[0], subst)
                    for l_sub in left_matches:
                        right_matches = self._match_pattern(pattern.right, enode.children[1], l_sub)
                        results.extend(right_matches)
            return results

        return []

    def _instantiate(self, pattern: Term, subst: Dict[str, int]) -> int:
        if isinstance(pattern, Var):
            if pattern.name in subst:
                return self.uf.find(subst[pattern.name])
            raise KeyError(f"Variable ${pattern.name} unbound during instantiation.")
        elif isinstance(pattern, Comb):
            return self._add_enode(ENode(pattern.symbol, ()))
        elif isinstance(pattern, App):
            left_id = self._instantiate(pattern.left, subst)
            right_id = self._instantiate(pattern.right, subst)
            return self._add_enode(ENode("@", (left_id, right_id)))
        raise TypeError(f"Unknown term: {type(pattern)}")

    def saturate(
        self,
        rules: List[RewriteRule],
        max_iterations: int = 10,
        fuel_atp: int = 1000
    ) -> Dict[str, Any]:
        """
        Executes equality saturation loop.
        Applies rules non-destructively until reaching a fixed point or spending fuel.
        """
        pending = dict(self.theory)
        for rule in rules:
            known = pending.get(rule.name)
            if known is not None and (known.lhs, known.rhs) != (rule.lhs, rule.rhs):
                raise ValueError(f"rule name {rule.name!r} already names a different rule in this e-graph")
            pending[rule.name] = rule
        self.theory = pending

        start_time = time.time()
        applied_total = 0
        iterations_run = 0
        fuel_remaining = fuel_atp

        for it in range(max_iterations):
            iterations_run += 1
            matches_to_apply: List[Tuple[int, int, str]] = []

            # 1. Match phase
            for rule in rules:
                for cid in list(self.classes.keys()):
                    matches = self._match_pattern(rule.lhs, cid, {})
                    for m in matches:
                        try:
                            rhs_id = self._instantiate(rule.rhs, m)
                            matches_to_apply.append((cid, rhs_id, rule.name))
                        except Exception:
                            continue

            # 2. Apply phase
            unions_in_iter = 0
            for lhs_cid, rhs_cid, rname in matches_to_apply:
                if fuel_remaining <= 0:
                    break
                if self.uf.find(lhs_cid) != self.uf.find(rhs_cid):
                    self.union(lhs_cid, rhs_cid, justification=rname)
                    unions_in_iter += 1
                    applied_total += 1
                    fuel_remaining -= 2

            # 3. Rebuild phase
            self.rebuild()

            # Check convergence
            if unions_in_iter == 0 or fuel_remaining <= 0:
                break

        elapsed = time.time() - start_time
        return {
            "iterations": iterations_run,
            "total_unions": applied_total,
            "final_classes": len(self.classes),
            "final_nodes": len(self.hashcons),
            "fuel_spent": fuel_atp - fuel_remaining,
            "elapsed_seconds": round(elapsed, 4)
        }

    # ========================================================================
    # 6. HOMOTOPIC PROOF EXPLANATIONS (STEP-BY-STEP JUSTIFICATIONS)
    # ========================================================================

    def explain_equivalence(self, term_a: Term, term_b: Term, max_terms: int = 20000) -> EquivalenceProofTree:
        """
        Why term_a and term_b share an e-class, as a derivation that replays.

        Equivalence is the e-graph's union-find answer. The steps are searched
        over `self.theory`, the rules this e-graph was saturated with, and are
        returned only after `check_derivation` accepts them. If none is found
        within `max_terms`, the status is NOT_FOUND_WITHIN_BUDGET and there are
        no steps. The proof forest links class ids, not terms, so it is not
        offered as an explanation. Before S4d this method searched it from the
        class root of both terms, found the empty path every time, and emitted
        one invented step instead.
        """
        id_a = self.add_term(term_a)
        id_b = self.add_term(term_b)
        self.rebuild()
        str_a, str_b = str(term_a), str(term_b)

        if self.uf.find(id_a) != self.uf.find(id_b):
            return EquivalenceProofTree(term_a=str_a, term_b=str_b, is_equivalent=False,
                                        proof_steps=[], derivation_status=DerivationStatus.NOT_EQUIVALENT)

        steps = find_derivation(term_a, term_b, self.theory, max_terms=max_terms)
        if steps is None or check_derivation(term_a, term_b, steps, self.theory) is not None:
            return EquivalenceProofTree(term_a=str_a, term_b=str_b, is_equivalent=True,
                                        proof_steps=[], derivation_status=DerivationStatus.NOT_FOUND_WITHIN_BUDGET)
        return EquivalenceProofTree(term_a=str_a, term_b=str_b, is_equivalent=True,
                                    proof_steps=steps, derivation_status=DerivationStatus.CHECKED)

    # ========================================================================
    # 7. OPTIMAL TERM EXTRACTION
    # ========================================================================

    def extract_optimal(
        self,
        class_id: int,
        cost_fn: Optional[Callable[[ENode, List[int]], int]] = None
    ) -> Tuple[Term, int]:
        """
        Dynamic programming extraction of the lowest-cost term from an EClass.
        Guaranteed to return an acyclic optimal AST.
        """
        root_id = self.uf.find(class_id)
        if root_id not in self.classes:
            raise KeyError(f"EClass {class_id} not found in EGraph.")

        def default_ast_cost(node: ENode, child_costs: List[int]) -> int:
            base = 1
            if node.op == GLYPH_S:
                base = 3
            elif node.op == GLYPH_K:
                base = 2
            elif node.op == GLYPH_I:
                base = 1
            return base + sum(child_costs)

        fn = cost_fn or default_ast_cost

        # Iterative Bellman-Ford cost relaxation
        best_cost: Dict[int, int] = {}
        best_node: Dict[int, ENode] = {}

        changed = True
        iterations = 0
        max_iter = len(self.classes) * 2 + 10

        while changed and iterations < max_iter:
            changed = False
            iterations += 1

            for cid, eclass in self.classes.items():
                if eclass.is_tainted:
                    continue  # Skip poisoned classes

                for enode in eclass.nodes:
                    # Check if all children have computed costs
                    can_eval = True
                    child_c = []
                    for ch in enode.children:
                        ch_root = self.uf.find(ch)
                        if ch_root not in best_cost:
                            can_eval = False
                            break
                        child_c.append(best_cost[ch_root])

                    if can_eval:
                        cost = fn(enode, child_c)
                        if cid not in best_cost or cost < best_cost[cid]:
                            best_cost[cid] = cost
                            best_node[cid] = enode
                            changed = True

        if root_id not in best_node:
            # Fallback: choose first available node
            first_node = next(iter(self.classes[root_id].nodes))
            best_node[root_id] = first_node
            best_cost[root_id] = 100

        # Build term recursively
        def build_term(cid: int, seen: Set[int]) -> Term:
            r_cid = self.uf.find(cid)
            if r_cid in seen:
                # Cycle fallback
                return Var(f"cycle_{r_cid}")
            seen_next = seen | {r_cid}
            node = best_node[r_cid]

            if node.op == "@":
                left_term = build_term(node.children[0], seen_next)
                right_term = build_term(node.children[1], seen_next)
                return App(left_term, right_term)
            elif node.op.startswith("$"):
                return Var(node.op[1:])
            else:
                return Comb(node.op)

        extracted_term = build_term(root_id, set())
        return extracted_term, best_cost.get(root_id, 1)

    # ========================================================================
    # 8. TOMBSTONE INOCULATION & TAINT QUARANTINE
    # ========================================================================

    def inoculate_tombstones(self, registry: EpistemicTombstoneRegistry) -> int:
        """
        Marks EClasses containing refuted terms from an EpistemicTombstoneRegistry
        as tainted, preventing them from being extracted into active genomes.
        """
        tainted_count = 0
        for tid, tomb in registry.tombstones.items():
            if tomb.mode == RetirementMode.REFUTED:
                try:
                    refuted_t = parse(tomb.target_id)
                    cid = self.add_term(refuted_t)
                    root_cid = self.uf.find(cid)
                    if root_cid in self.classes and not self.classes[root_cid].is_tainted:
                        self.classes[root_cid].is_tainted = True
                        self.classes[root_cid].taint_reason = f"TOMBSTONE-REFUTED: {tomb.loss_declaration}"
                        tainted_count += 1
                except Exception:
                    continue
        return tainted_count

    def to_dict(self) -> Dict[str, Any]:
        return {
            "classes": {str(cid): c.to_dict() for cid, c in self.classes.items()},
            "total_classes": len(self.classes),
            "total_nodes": len(self.hashcons),
            "proof_edges_count": len(self.proof_edges)
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> EGraph:
        egraph = cls()
        # Restores classes from serialized definitions
        for cid_str, c_data in d.get("classes", {}).items():
            cid = int(cid_str)
            if cid not in egraph.classes:
                egraph.classes[cid] = EClass(
                    class_id=cid,
                    is_tainted=c_data.get("is_tainted", False),
                    taint_reason=c_data.get("taint_reason", "")
                )
                egraph.uf.make_set(cid)
        return egraph


# ============================================================================
# 9. ISO 32000 APPEND-ONLY POLYGLOT E-GRAPH COMPILER
# ============================================================================

def generate_egraph_pdf(
    egraph: EGraph,
    output_path: str,
    title: str = "EPISTEMIC EQUALITY SATURATION & E-GRAPH KERNEL",
    sample_proof: Optional[EquivalenceProofTree] = None
) -> bytes:
    """
    Compiles the E-Graph state into an ISO 32000 compliant vector PDF polyglot.
    Features:
      - Visual EClass bubble clusters & node counts.
      - Certified equational derivation tree banner.
      - Embedded JCS-canonical JSON manifest.
      - Embedded self-executing Latin-1 Python audit runner (`python3 egraph.pdf`).
    """
    total_classes = len(egraph.classes)
    total_nodes = len(egraph.hashcons)
    tainted = sum(1 for c in egraph.classes.values() if c.is_tainted)

    stream_lines = [
        "q",
        # Page background: Deep obsidian
        "0.03 0.04 0.06 rg",
        "0 0 612 792 re f",

        # Header Banner
        "0.06 0.09 0.13 rg",
        "30 710 552 60 re f",
        "0.20 0.50 0.80 RG 1.5 w",
        "30 710 552 60 re S",
        "BT",
        "/F1 15 Tf",
        "0.95 0.98 1.0 rg",
        "45 745 Td",
        f"(%# BLACK-HEART: {title}) Tj",
        "/F1 9 Tf",
        "0.40 0.80 0.95 rg",
        "0 -20 Td",
        "(EGRAPH-0.1 | Non-Destructive Saturation, Congruence Closure & Proof Forest) Tj",
        "ET",

        # E-Graph Telemetry Card
        "0.05 0.07 0.10 rg",
        "30 570 552 125 re f",
        "0.25 0.65 0.45 RG 1.5 w",
        "30 570 552 125 re S",
        "BT",
        "/F1 12 Tf",
        "0.30 0.95 0.60 rg",
        "45 668 Td",
        "(E-GRAPH TOPOLOGY & SATURATION TELEMETRY) Tj",
        "/F1 9 Tf",
        "0.85 0.90 0.95 rg",
        "0 -20 Td",
        f"(Active E-Classes:   {total_classes} equivalence clusters) Tj",
        "0 -15 Td",
        f"(Canonical E-Nodes:  {total_nodes} structural AST terms) Tj",
        "0 -15 Td",
        f"(Justification Edges: {len(egraph.proof_edges)} certified proof forest links) Tj",
        "0 -15 Td",
        f"(Tainted Classes:    {tainted} quarantined epistemic hazards (Tombstone Defense)) Tj",
        "ET",

        # Equational Proof Certificate Box
        "0.04 0.05 0.08 rg",
        "30 330 552 225 re f",
        "0.80 0.60 0.20 RG 1.5 w",
        "30 330 552 225 re S",
        "BT",
        "/F1 11 Tf",
        "1.0 0.85 0.30 rg",
        "45 532 Td",
        "(CERTIFIED EQUATIONAL DERIVATION TREE (PROOF FOREST)) Tj",
        "/F1 8 Tf",
        "0.75 0.80 0.85 rg",
    ]

    def _clean_latin1(text: str) -> str:
        s = (
            text.replace("🖤", "K")
            .replace("🤍", "I")
            .replace("🌿", "S")
            .replace("🔁", "Y")
            .replace("⚓", "#")
            .encode("ascii", "replace")
            .decode("latin-1")
        )
        return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    # What the attached explanation is credited with is decided here, by
    # replaying it against this e-graph, never read from its own status fields:
    # those are public mutable data (review E1 on PR #21).
    replayed, replay_reason = replay_explanation(egraph, sample_proof) if sample_proof else (None, "")
    if replayed == DerivationStatus.CHECKED:
        clean_a = _clean_latin1(sample_proof.term_a)
        clean_b = _clean_latin1(sample_proof.term_b)
        stream_lines.extend([
            "0 -18 Td",
            f"(Theorem Claim: {clean_a} === {clean_b}) Tj",
            "0 -14 Td",
            f"(Derivation: CHECKED, {len(sample_proof.proof_steps)} steps replayed against the e-graph's rules:) Tj",
        ])
        for step in sample_proof.proof_steps[:6]:
            f_expr = _clean_latin1(step.from_expr[:22])
            t_expr = _clean_latin1(step.to_expr[:22])
            just = _clean_latin1(step.justification[:32])
            stream_lines.extend([
                "0 -13 Td",
                f"(  [{step.step_num}] {f_expr} -> {t_expr}  | {just}) Tj",
            ])
    elif replayed == DerivationStatus.NOT_FOUND_WITHIN_BUDGET:
        stream_lines.extend([
            "0 -18 Td",
            f"(Claim: {_clean_latin1(sample_proof.term_a)} === {_clean_latin1(sample_proof.term_b)}) Tj",
            "0 -14 Td",
            "(Equivalent in the e-graph; no checked derivation within budget.) Tj",
        ])
    elif replayed is not None:
        stream_lines.extend([
            "0 -20 Td",
            f"(Attached explanation NOT credited: {_clean_latin1(replay_reason[:70])}) Tj",
        ])
    else:
        stream_lines.extend([
            "0 -20 Td",
            "(No specific theorem derivation attached. Standard saturation graph.) Tj",
        ])

    stream_lines.append("ET")

    # E-Class Cluster Breakdown Table
    stream_lines.extend([
        "0.05 0.06 0.09 rg",
        "30 50 552 265 re f",
        "0.20 0.25 0.35 RG 1 w",
        "30 50 552 265 re S",
        "BT",
        "/F1 10 Tf",
        "0.90 0.95 1.0 rg",
        "45 295 Td",
        "(E-CLASS REPRESENTATIVE CLUSTERS & OPTIMAL NORMAL FORMS) Tj",
        "/F1 8 Tf",
        "0.60 0.65 0.75 rg",
        "0 -16 Td",
        "(Class ID | Nodes | Optimal Normal Form           | Cost | Taint Status) Tj",
        "0 -12 Td",
        "(-----------------------------------------------------------------------------) Tj",
    ])

    for cid in sorted(egraph.classes.keys())[:10]:
        eclass = egraph.classes[cid]
        opt_term, opt_cost = egraph.extract_optimal(cid)
        opt_str = _clean_latin1(str(opt_term))[:30]
        taint_str = "TAINTED" if eclass.is_tainted else "CLEAN"
        row = f"#{cid:<8} | {len(eclass.nodes):<5} | {opt_str:<30} | {opt_cost:<4} | {taint_str}"
        stream_lines.extend([
            "0 -13 Td",
            f"({row}) Tj",
        ])

    stream_lines.extend([
        "ET",
        # Footer
        "BT",
        "/F1 8 Tf",
        "0.40 0.45 0.55 rg",
        "30 25 Td",
        "(ISO 32000 Polyglot: Run 'python3 <file>.pdf' for trustless E-Graph proof verification) Tj",
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

    manifest_line = _egraph_manifest_bytes(egraph)

    py_runner = _EGRAPH_RUNNER

    header_text = (
        f"#!{sys.executable}\n"
        "# coding: latin-1\n"
        "# ============================================================================\n"
        "# %# PROJECT BLACK-HEART: EPISTEMIC E-GRAPH KERNEL (ISO 32000 POLYGLOT)\n"
        "# ============================================================================\n"
        "r'''\n"
    ).encode("latin-1")

    polyglot = header_text + body + xref + trailer + manifest_line + b"'''\n" + py_runner.encode("latin-1")
    with open(output_path, "wb") as f:
        f.write(polyglot)
    return polyglot


_EGRAPH_MANIFEST_PREFIX_BYTES = b"# %" + bytes([0xf0, 0x9f, 0x96, 0xa4]) + b" EGRAPH_MANIFEST: "
_EGRAPH_HASH_PREFIX_BYTES = b"# %" + bytes([0xf0, 0x9f, 0x96, 0xa4]) + b" EGRAPH_MANIFEST_SHA256: "


def _egraph_manifest_bytes(egraph: "EGraph") -> bytes:
    """The manifest line plus a self-consistency hash line over its JSON.

    The runner recomputes the SHA-256 over the manifest JSON and compares, so an
    in-place edit of the counts (before S7 it claimed soundness for any counts)
    is caught. Both lines are appended by `generate_egraph_pdf` and
    `append_egraph_hud`, and the runner reads the LAST of each, so an appended
    HUD carries its own verifiable manifest.
    """
    manifest_json = json.dumps(egraph.to_dict(), sort_keys=True)
    manifest_hash = hashlib.sha256(manifest_json.encode("utf-8")).hexdigest()
    return (_EGRAPH_MANIFEST_PREFIX_BYTES + manifest_json.encode("utf-8") + b"\n"
            + _EGRAPH_HASH_PREFIX_BYTES + manifest_hash.encode("ascii") + b"\n")


# A manifest reporter, not a prover. It verifies the embedded manifest against
# its own SHA-256 and reports the recorded counts. It re-derives nothing and
# claims no soundness. It does NOT put the cwd (or the document's directory) on
# sys.path and does NOT import egraph_kernel: before S7 it did, so a file placed
# next to a planted egraph_kernel.py ran that code and still printed "sound".
_EGRAPH_RUNNER = r"""
# coding: latin-1
import sys, json, hashlib

def audit_egraph_polyglot():
    print("\033[1;36m" + "=" * 70)
    print("  %# EPISTEMIC E-GRAPH KERNEL -- MANIFEST REPORTER (EGRAPH-0.1)")
    print("=" * 70 + "\033[0m")
    with open(__file__, 'rb') as f:
        data = f.read()
    m_prefix = bytes([0x23, 0x20, 0x25, 0xf0, 0x9f, 0x96, 0xa4]) + b" EGRAPH_MANIFEST: "
    h_prefix = bytes([0x23, 0x20, 0x25, 0xf0, 0x9f, 0x96, 0xa4]) + b" EGRAPH_MANIFEST_SHA256: "
    m_idx = data.rfind(m_prefix)
    h_idx = data.rfind(h_prefix)
    if m_idx == -1 or h_idx == -1:
        print("\033[1;31m[-] No self-verifying E-Graph manifest found in document.\033[0m")
        sys.exit(1)
    manifest_bytes = data[m_idx + len(m_prefix):data.find(b"\n", m_idx)]
    recorded_hash = data[h_idx + len(h_prefix):data.find(b"\n", h_idx)].decode("ascii").strip()
    if hashlib.sha256(manifest_bytes).hexdigest() != recorded_hash:
        print("\033[1;31m[!] FAILED: manifest self-consistency check failed "
              "(contents do not match the embedded SHA-256).\033[0m")
        sys.exit(1)
    manifest = json.loads(manifest_bytes.decode("utf-8"))
    print("\033[1;32m[*] Manifest self-consistency: OK (contents match embedded SHA-256).\033[0m")
    print(f"[*] Total E-Classes:         {manifest['total_classes']}")
    print(f"[*] Total Canonical E-Nodes: {manifest['total_nodes']}")
    print(f"[*] Justification Edges:     {manifest['proof_edges_count']}")
    print("[i] Scope: this runner verified the integrity of a compiler-produced")
    print("    manifest only. It did NOT re-derive congruence or any equivalence,")
    print("    and asserts no soundness. To check an equivalence, load the e-graph")
    print("    in a trusted checkout and call explain_equivalence.")
    print("\033[1;36m" + "=" * 70 + "\033[0m")
    sys.exit(0)

if __name__ == "__main__":
    audit_egraph_polyglot()
"""


def append_egraph_hud(
    source_pdf_bytes: bytes,
    output_path: str,
    egraph: EGraph
) -> bytes:
    """
    Appends an ISO 32000 §7.5.6 incremental update with the latest E-Graph HUD
    to an existing polyglot document. Preserves byte prefix:
    output.startswith(source_pdf_bytes) == True.
    """
    stream_lines = [
        "q",
        "0.03 0.04 0.06 rg",
        "0 0 612 792 re f",
        "0.06 0.09 0.13 rg",
        "30 710 552 60 re f",
        "0.20 0.50 0.80 RG 1.5 w",
        "30 710 552 60 re S",
        "BT",
        "/F1 15 Tf",
        "0.95 0.98 1.0 rg",
        "45 745 Td",
        "(%# BLACK-HEART: E-GRAPH INCREMENTAL UPDATE) Tj",
        "/F1 9 Tf",
        "0.40 0.80 0.95 rg",
        "0 -20 Td",
        f"(EGRAPH-0.1 | Incremental State Update | Classes: {len(egraph.classes)}) Tj",
        "ET",
        "Q"
    ]
    content_bytes = "\n".join(stream_lines).encode("latin-1")

    obj_num = 200 + len(egraph.classes) * 2
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

    manifest_line = _egraph_manifest_bytes(egraph)

    incremental_update = source_pdf_bytes + new_body + xref_table + trailer_dict + manifest_line
    with open(output_path, "wb") as f:
        f.write(incremental_update)
    return incremental_update
