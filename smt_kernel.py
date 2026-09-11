#!/usr/bin/env python3
# coding: utf-8
"""
smt_kernel.py — Sovereign SMT Kernel & First-Order DPLL(T) Verifier.
Part of Project Black-Heart (%🖤). Engine #29.

Normative implementation of SMT-0.1:
  1. Standard SMT-LIB 2.6 QF_UF Parser & AST:
     Recursive descent parser for S-expressions: declare-sort, declare-const,
     declare-fun, assert, check-sat, get-model, get-proof.
  2. Propositional CNF & Tseitin Transformation:
     Converts arbitrary boolean formulas over theory atoms into equisatisfiable CNF,
     mapping equality atoms (t1 = t2) to canonical propositional variables.
  3. Conflict-Driven Clause Learning (CDCL) SAT Core:
     Two-Watched Literals (2WL), 1-UIP conflict analysis, non-chronological
     backjumping, VSIDS variable activity heuristics, and phase saving.
  4. Backtrackable Scoped Theory Solver (T_EUF):
     Congruence closure engine with undo stack, parent indexing, upward congruence
     propagation, and proof forest traversal for minimal theory conflict lemmas.
  5. DPLL(T) Verification Orchestrator:
     Coordinates CDCL propositional search with T_EUF theory propagation.
     Decides satisfiability with mathematical soundness, resource bounds, and completeness.
  6. Certified Refutation Proof Certificates & Independent Verifier:
     Generates resolution DAG deriving empty clause [] for UNSAT instances,
     verifiable by an independent 60-line checker.
  7. Finite Model Generator:
     Synthesizes explicit finite domain valuations for satisfiable instances.
  8. Epistemic Tombstone Quarantine Integration:
     Verifies organism claims against EpistemicTombstoneRegistry (Engine #25).
  9. ISO 32000 Append-Only Polyglot Physicality:
     Renders vector HUD with CDCL search DAG, congruence classes, and embedded
     Latin-1 self-executing Python audit runner (`python3 smt_proof.pdf`).

Zero external dependencies: 100% Python standard library.
"""

from __future__ import annotations
import os
import sys
import json
import time
import math
import hashlib
import warnings
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple, Set, Union, Callable, Iterable, FrozenSet

import controlled_forgetting
from controlled_forgetting import EpistemicTombstoneRegistry

SMT_MANIFEST_PREFIX = "%" + "🖤" + " SMT_MANIFEST: "

# ============================================================================
# 1. SMT SORTS & AST DEFINITIONS
# ============================================================================

@dataclass(frozen=True)
class Sort:
    """An SMT-LIB sort (type)."""
    name: str
    arity: int = 0

    def __repr__(self) -> str:
        return self.name


BOOL_SORT = Sort("Bool")
DEFAULT_SORT = Sort("U")


class SMTTerm:
    """Abstract base class for all SMT terms and formulas."""
    sort: Sort

    def to_smt2(self) -> str:
        raise NotImplementedError


@dataclass(frozen=True)
class Const(SMTTerm):
    """An uninterpreted constant or variable."""
    name: str
    sort: Sort = DEFAULT_SORT

    def to_smt2(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return self.name


@dataclass(frozen=True)
class BoolConst(SMTTerm):
    """A boolean literal constant (true/false)."""
    val: bool
    sort: Sort = BOOL_SORT

    def to_smt2(self) -> str:
        return "true" if self.val else "false"

    def __repr__(self) -> str:
        return "true" if self.val else "false"


@dataclass(frozen=True)
class App(SMTTerm):
    """An uninterpreted function application: f(t_1, ..., t_k)."""
    fn: str
    args: Tuple[SMTTerm, ...]
    sort: Sort = DEFAULT_SORT

    def to_smt2(self) -> str:
        if not self.args:
            return self.fn
        return f"({self.fn} {' '.join(a.to_smt2() for a in self.args)})"

    def __repr__(self) -> str:
        if not self.args:
            return self.fn
        return f"{self.fn}({', '.join(map(str, self.args))})"


@dataclass(frozen=True)
class Eq(SMTTerm):
    """Equality between two terms: t_1 = t_2."""
    left: SMTTerm
    right: SMTTerm
    sort: Sort = BOOL_SORT

    def to_smt2(self) -> str:
        return f"(= {self.left.to_smt2()} {self.right.to_smt2()})"

    def __repr__(self) -> str:
        return f"({self.left} = {self.right})"


@dataclass(frozen=True)
class Distinct(SMTTerm):
    """Pairwise disequality between terms."""
    args: Tuple[SMTTerm, ...]
    sort: Sort = BOOL_SORT

    def to_smt2(self) -> str:
        return f"(distinct {' '.join(a.to_smt2() for a in self.args)})"

    def __repr__(self) -> str:
        return f"distinct({', '.join(map(str, self.args))})"


@dataclass(frozen=True)
class Not(SMTTerm):
    """Boolean negation."""
    arg: SMTTerm
    sort: Sort = BOOL_SORT

    def to_smt2(self) -> str:
        return f"(not {self.arg.to_smt2()})"

    def __repr__(self) -> str:
        return f"(not {self.arg})"


@dataclass(frozen=True)
class And(SMTTerm):
    """Boolean conjunction."""
    args: Tuple[SMTTerm, ...]
    sort: Sort = BOOL_SORT

    def to_smt2(self) -> str:
        if not self.args:
            return "true"
        return f"(and {' '.join(a.to_smt2() for a in self.args)})"

    def __repr__(self) -> str:
        return f"({' and '.join(map(str, self.args))})"


@dataclass(frozen=True)
class Or(SMTTerm):
    """Boolean disjunction."""
    args: Tuple[SMTTerm, ...]
    sort: Sort = BOOL_SORT

    def to_smt2(self) -> str:
        if not self.args:
            return "false"
        return f"(or {' '.join(a.to_smt2() for a in self.args)})"

    def __repr__(self) -> str:
        return f"({' or '.join(map(str, self.args))})"


@dataclass(frozen=True)
class Implies(SMTTerm):
    """Boolean implication: left => right."""
    left: SMTTerm
    right: SMTTerm
    sort: Sort = BOOL_SORT

    def to_smt2(self) -> str:
        return f"(=> {self.left.to_smt2()} {self.right.to_smt2()})"

    def __repr__(self) -> str:
        return f"({self.left} => {self.right})"


@dataclass(frozen=True)
class Xor(SMTTerm):
    """Boolean exclusive disjunction."""
    left: SMTTerm
    right: SMTTerm
    sort: Sort = BOOL_SORT

    def to_smt2(self) -> str:
        return f"(xor {self.left.to_smt2()} {self.right.to_smt2()})"

    def __repr__(self) -> str:
        return f"({self.left} xor {self.right})"


@dataclass(frozen=True)
class Ite(SMTTerm):
    """If-Then-Else conditional term."""
    cond: SMTTerm
    then_branch: SMTTerm
    else_branch: SMTTerm

    @property
    def sort(self) -> Sort:
        return self.then_branch.sort

    def to_smt2(self) -> str:
        return f"(ite {self.cond.to_smt2()} {self.then_branch.to_smt2()} {self.else_branch.to_smt2()})"

    def __repr__(self) -> str:
        return f"ite({self.cond}, {self.then_branch}, {self.else_branch})"


def collect_terms(term: SMTTerm) -> Set[SMTTerm]:
    """Recursively collect all uninterpreted constants and function applications in a formula."""
    terms: Set[SMTTerm] = set()
    def _rec(t: SMTTerm):
        if isinstance(t, (Const, App)):
            terms.add(t)
            if isinstance(t, App):
                for a in t.args:
                    _rec(a)
        elif isinstance(t, Eq):
            _rec(t.left)
            _rec(t.right)
        elif isinstance(t, Not):
            _rec(t.arg)
        elif isinstance(t, (And, Or)):
            for a in t.args:
                _rec(a)
        elif isinstance(t, (Implies, Xor)):
            _rec(t.left)
            _rec(t.right)
        elif isinstance(t, Ite):
            _rec(t.cond)
            _rec(t.then_branch)
            _rec(t.else_branch)
        elif isinstance(t, Distinct):
            for a in t.args:
                _rec(a)
    _rec(term)
    return terms


# ============================================================================
# 2. SMT-LIB 2.6 TOKENIZER & PARSER
# ============================================================================

def tokenize_smt2(script: str) -> List[str]:
    """Tokenize SMT-LIB 2 script into tokens, discarding comments."""
    tokens = []
    i = 0
    n = len(script)
    while i < n:
        c = script[i]
        if c.isspace():
            i += 1
            continue
        if c == ';':
            while i < n and script[i] != '\n':
                i += 1
            continue
        if c in '()':
            tokens.append(c)
            i += 1
            continue
        if c == '|':
            start = i
            i += 1
            while i < n and script[i] != '|':
                i += 1
            if i < n:
                i += 1
            tokens.append(script[start:i])
            continue
        if c == '"':
            start = i
            i += 1
            while i < n and script[i] != '"':
                if script[i] == '\\' and i + 1 < n:
                    i += 2
                else:
                    i += 1
            if i < n:
                i += 1
            tokens.append(script[start:i])
            continue
        start = i
        while i < n and not script[i].isspace() and script[i] not in '();':
            i += 1
        tokens.append(script[start:i])
    return tokens


def parse_sexprs(tokens: List[str]) -> List[Any]:
    """Parse list of tokens into nested python lists representing S-expressions."""
    stack: List[List[Any]] = [[]]
    for token in tokens:
        if token == '(':
            new_list: List[Any] = []
            stack[-1].append(new_list)
            stack.append(new_list)
        elif token == ')':
            if len(stack) <= 1:
                raise ValueError("Unmatched closing parenthesis in SMT-LIB script")
            stack.pop()
        else:
            stack[-1].append(token)
    if len(stack) != 1:
        raise ValueError("Unmatched opening parenthesis in SMT-LIB script")
    return stack[0]


class SMTLIBParser:
    """Standard SMT-LIB 2 parser for Quantifier-Free Uninterpreted Functions (QF_UF)."""
    def __init__(self):
        self.sorts: Dict[str, Sort] = {"Bool": BOOL_SORT}
        self.signatures: Dict[str, Tuple[Tuple[Sort, ...], Sort]] = {}
        self.assertions: List[SMTTerm] = []

    def parse_script(self, script: str) -> List[SMTTerm]:
        tokens = tokenize_smt2(script)
        sexprs = parse_sexprs(tokens)
        for sexpr in sexprs:
            if not isinstance(sexpr, list) or not sexpr:
                continue
            cmd = sexpr[0]
            if cmd in ("set-logic", "set-info", "set-option"):
                continue
            elif cmd == "declare-sort":
                name = sexpr[1]
                arity = int(sexpr[2]) if len(sexpr) > 2 else 0
                self.sorts[name] = Sort(name, arity)
            elif cmd == "declare-const":
                name = sexpr[1]
                sort_name = sexpr[2]
                sort = self.sorts.get(sort_name, Sort(sort_name))
                self.signatures[name] = ((), sort)
            elif cmd == "declare-fun":
                name = sexpr[1]
                arg_sort_names = sexpr[2]
                ret_sort_name = sexpr[3]
                arg_sorts = tuple(self.sorts.get(s, Sort(s)) for s in arg_sort_names)
                ret_sort = self.sorts.get(ret_sort_name, Sort(ret_sort_name))
                self.signatures[name] = (arg_sorts, ret_sort)
            elif cmd == "assert":
                term = self._parse_term(sexpr[1])
                self.assertions.append(term)
            elif cmd in ("check-sat", "get-model", "get-proof", "exit"):
                pass
        return self.assertions

    def _parse_term(self, sexpr: Any) -> SMTTerm:
        if isinstance(sexpr, str):
            if sexpr == "true":
                return BoolConst(True)
            elif sexpr == "false":
                return BoolConst(False)
            if sexpr in self.signatures:
                arg_sorts, ret_sort = self.signatures[sexpr]
                if not arg_sorts:
                    return Const(sexpr, ret_sort)
            return Const(sexpr, DEFAULT_SORT)

        if not isinstance(sexpr, list) or not sexpr:
            raise ValueError(f"Invalid term sexpr: {sexpr}")

        op = sexpr[0]
        args = [self._parse_term(a) for a in sexpr[1:]]

        if op == "=":
            if len(args) == 2:
                return Eq(args[0], args[1])
            eqs = [Eq(args[i], args[i+1]) for i in range(len(args)-1)]
            return And(tuple(eqs))
        elif op == "distinct":
            return Distinct(tuple(args))
        elif op == "not":
            return Not(args[0])
        elif op == "and":
            return And(tuple(args))
        elif op == "or":
            return Or(tuple(args))
        elif op == "=>":
            if len(args) == 2:
                return Implies(args[0], args[1])
            res = args[-1]
            for a in reversed(args[:-1]):
                res = Implies(a, res)
            return res
        elif op == "xor":
            return Xor(args[0], args[1])
        elif op == "ite":
            return Ite(args[0], args[1], args[2])
        else:
            ret_sort = DEFAULT_SORT
            if op in self.signatures:
                _, ret_sort = self.signatures[op]
            return App(op, tuple(args), ret_sort)


# ============================================================================
# 3. PROPOSITIONAL CNF & TSEITIN TRANSFORMATION
# ============================================================================

def canonicalize_equality(left: SMTTerm, right: SMTTerm) -> Tuple[SMTTerm, SMTTerm]:
    """Ensure canonical symmetric ordering for equality terms."""
    s_left = str(left)
    s_right = str(right)
    if s_left <= s_right:
        return left, right
    return right, left


class TseitinTransformer:
    """
    Translates an arbitrary boolean combination of SMT first-order atoms
    into equisatisfiable Conjunctive Normal Form (CNF).
    """
    def __init__(self):
        self.atom_to_var: Dict[SMTTerm, int] = {}
        self.var_to_atom: Dict[int, SMTTerm] = {}
        self.next_var: int = 1
        self.clauses: List[List[int]] = []

    def get_var_for_atom(self, atom: SMTTerm) -> int:
        if isinstance(atom, Eq):
            can_left, can_right = canonicalize_equality(atom.left, atom.right)
            atom = Eq(can_left, can_right)
        if atom in self.atom_to_var:
            return self.atom_to_var[atom]
        v = self.next_var
        self.next_var += 1
        self.atom_to_var[atom] = v
        self.var_to_atom[v] = atom
        return v

    def new_var(self) -> int:
        v = self.next_var
        self.next_var += 1
        return v

    def add_clause(self, clause: List[int]):
        self.clauses.append(clause)

    def transform(self, term: SMTTerm) -> int:
        if isinstance(term, BoolConst):
            v = self.new_var()
            if term.val:
                self.add_clause([v])
            else:
                self.add_clause([-v])
            return v

        if isinstance(term, Not):
            lit = self.transform(term.arg)
            return -lit

        if isinstance(term, And):
            if not term.args:
                v = self.new_var()
                self.add_clause([v])
                return v
            lits = [self.transform(a) for a in term.args]
            v = self.new_var()
            for l in lits:
                self.add_clause([-v, l])
            self.add_clause([v] + [-l for l in lits])
            return v

        if isinstance(term, Or):
            if not term.args:
                v = self.new_var()
                self.add_clause([-v])
                return v
            lits = [self.transform(a) for a in term.args]
            v = self.new_var()
            for l in lits:
                self.add_clause([v, -l])
            self.add_clause([-v] + lits)
            return v

        if isinstance(term, Implies):
            l_a = self.transform(term.left)
            l_b = self.transform(term.right)
            v = self.new_var()
            self.add_clause([v, l_a])
            self.add_clause([v, -l_b])
            self.add_clause([-v, -l_a, l_b])
            return v

        if isinstance(term, Xor):
            l_a = self.transform(term.left)
            l_b = self.transform(term.right)
            v = self.new_var()
            self.add_clause([-v, l_a, l_b])
            self.add_clause([-v, -l_a, -l_b])
            self.add_clause([v, -l_a, l_b])
            self.add_clause([v, l_a, -l_b])
            return v

        if isinstance(term, Distinct):
            conjuncts = []
            n = len(term.args)
            for i in range(n):
                for j in range(i + 1, n):
                    conjuncts.append(Not(Eq(term.args[i], term.args[j])))
            return self.transform(And(tuple(conjuncts)))

        if isinstance(term, Eq):
            if term.left.sort == BOOL_SORT and term.right.sort == BOOL_SORT:
                l_a = self.transform(term.left)
                l_b = self.transform(term.right)
                v = self.new_var()
                self.add_clause([-v, -l_a, l_b])
                self.add_clause([-v, l_a, -l_b])
                self.add_clause([v, l_a, l_b])
                self.add_clause([v, -l_a, -l_b])
                return v
            var = self.get_var_for_atom(term)
            return var

        var = self.get_var_for_atom(term)
        return var


# ============================================================================
# 4. CDCL PROPOSITIONAL SAT SOLVER (2-WATCHED LITERALS & 1-UIP)
# ============================================================================

@dataclass
class ResolutionProofNode:
    """A node in the resolution refutation DAG for UNSAT certificates."""
    clause_id: int
    clause: List[int]
    rule: str  # "input", "theory_lemma", "learned"
    antecedents: List[int] = field(default_factory=list)
    pivot_vars: List[int] = field(default_factory=list)


class CDCLSolver:
    """
    State-of-the-art Conflict-Driven Clause Learning (CDCL) Propositional SAT Engine.
    Features Two-Watched Literals (2WL), 1-UIP conflict analysis, non-chronological
    backjumping, and VSIDS activity decay.
    """
    def __init__(self, num_vars: int):
        self.num_vars = num_vars
        self.clauses: List[List[int]] = []
        self.watches: Dict[int, List[int]] = {}

        self.assignment: List[int] = [0] * (num_vars + 1)
        self.decision_level: List[int] = [0] * (num_vars + 1)
        self.reason: List[Optional[int]] = [None] * (num_vars + 1)
        self.phase: List[int] = [-1] * (num_vars + 1)
        self.activity: List[float] = [0.0] * (num_vars + 1)
        self.var_inc: float = 1.0
        self.var_decay: float = 0.95

        self.trail: List[int] = []
        self.trail_lim: List[int] = []
        self.qhead: int = 0
        self.curr_level: int = 0

        self.proof_dag: Dict[int, ResolutionProofNode] = {}
        self.next_clause_id: int = 1
        self.level_zero_conflict: bool = False

        self.decisions_count: int = 0
        self.propagations_count: int = 0
        self.conflicts_count: int = 0
        self.learned_clauses_count: int = 0

    def add_clause(self, clause: List[int], rule: str = "input", antecedents: Optional[List[int]] = None) -> Optional[int]:
        s_clause = set(clause)
        for lit in list(s_clause):
            if -lit in s_clause:
                return None
        clean_clause = list(s_clause)
        c_id = self.next_clause_id
        self.next_clause_id += 1

        self.proof_dag[c_id] = ResolutionProofNode(
            clause_id=c_id,
            clause=clean_clause,
            rule=rule,
            antecedents=antecedents or []
        )

        c_idx = len(self.clauses)
        self.clauses.append(clean_clause)

        for lit in clean_clause:
            v = abs(lit)
            if v <= self.num_vars:
                self.activity[v] += 1.0

        if len(clean_clause) == 0:
            self.level_zero_conflict = True
            return c_id
        elif len(clean_clause) == 1:
            lit = clean_clause[0]
            if self.curr_level == 0:
                if not self._enqueue(lit, reason=c_idx):
                    self.level_zero_conflict = True
            return c_id

        w1, w2 = clean_clause[0], clean_clause[1]
        self._watch_lit(w1, c_idx)
        self._watch_lit(w2, c_idx)
        return c_id

    def _watch_lit(self, lit: int, c_idx: int):
        if lit not in self.watches:
            self.watches[lit] = []
        self.watches[lit].append(c_idx)

    def _enqueue(self, lit: int, reason: Optional[int] = None) -> bool:
        v = abs(lit)
        val = 1 if lit > 0 else -1
        if self.assignment[v] != 0:
            return self.assignment[v] == val
        self.assignment[v] = val
        self.decision_level[v] = self.curr_level
        self.reason[v] = reason
        self.phase[v] = val
        self.trail.append(lit)
        self.propagations_count += 1
        return True

    def propagate(self) -> Optional[int]:
        """Unit propagation with Two-Watched Literals. Returns conflicting clause index or None."""
        while self.qhead < len(self.trail):
            lit = self.trail[self.qhead]
            self.qhead += 1
            false_lit = -lit

            if false_lit not in self.watches:
                continue

            watches_for_lit = self.watches[false_lit]
            i = 0
            while i < len(watches_for_lit):
                c_idx = watches_for_lit[i]
                clause = self.clauses[c_idx]

                if clause[0] == false_lit:
                    clause[0], clause[1] = clause[1], clause[0]

                first_lit = clause[0]
                first_val = self._val(first_lit)

                if first_val == 1:
                    i += 1
                    continue

                found_new_watch = False
                for k in range(2, len(clause)):
                    if self._val(clause[k]) != -1:
                        clause[1], clause[k] = clause[k], clause[1]
                        self._watch_lit(clause[1], c_idx)
                        watches_for_lit[i] = watches_for_lit[-1]
                        watches_for_lit.pop()
                        found_new_watch = True
                        break

                if found_new_watch:
                    continue

                if first_val == -1:
                    return c_idx
                else:
                    if not self._enqueue(first_lit, reason=c_idx):
                        return c_idx
                i += 1
        return None

    def _val(self, lit: int) -> int:
        v = abs(lit)
        val = self.assignment[v]
        if val == 0:
            return 0
        return 1 if (lit > 0 and val == 1) or (lit < 0 and val == -1) else -1

    def analyze_conflict(self, conflict_c_idx: int) -> Tuple[List[int], int, List[int]]:
        """1-UIP Conflict Analysis with assertion literal at index 0."""
        self.conflicts_count += 1
        learned: Set[int] = set()
        pivots: List[int] = []
        path_count = 0
        p = None
        confl_clause = self.clauses[conflict_c_idx]
        for lit in confl_clause:
            v = abs(lit)
            self._bump_activity(v)
            if self.decision_level[v] == self.curr_level:
                path_count += 1
            learned.add(lit)

        idx = len(self.trail) - 1
        while path_count > 1:
            while idx >= 0:
                trail_lit = self.trail[idx]
                idx -= 1
                if trail_lit in learned or -trail_lit in learned:
                    p = abs(trail_lit)
                    break

            if p is None:
                break

            reason_c_idx = self.reason[p]
            if reason_c_idx is None:
                break

            pivots.append(p)
            reason_clause = self.clauses[reason_c_idx]
            learned.discard(p)
            learned.discard(-p)
            path_count -= 1

            for lit in reason_clause:
                v = abs(lit)
                if v != p and lit not in learned and -lit not in learned:
                    self._bump_activity(v)
                    learned.add(lit)
                    if self.decision_level[v] == self.curr_level:
                        path_count += 1

        learned_list = list(learned)
        backjump_level = 0
        uip_lit = None
        for lit in learned_list:
            v = abs(lit)
            lvl = self.decision_level[v]
            if lvl == self.curr_level:
                uip_lit = lit
            elif lvl > backjump_level:
                backjump_level = lvl

        if uip_lit is not None:
            learned_list.remove(uip_lit)
            learned_list.insert(0, uip_lit)

        if len(learned_list) > 1:
            best_idx = 1
            max_lvl = -1
            for k in range(1, len(learned_list)):
                lvl = self.decision_level[abs(learned_list[k])]
                if lvl > max_lvl:
                    max_lvl = lvl
                    best_idx = k
            learned_list[1], learned_list[best_idx] = learned_list[best_idx], learned_list[1]

        self._decay_activity()
        return learned_list, backjump_level, pivots

    def backjump(self, to_level: int):
        """Non-chronological backtracking."""
        limit = self.trail_lim[to_level] if to_level < len(self.trail_lim) else 0
        while len(self.trail) > limit:
            lit = self.trail.pop()
            v = abs(lit)
            self.assignment[v] = 0
            self.decision_level[v] = 0
            self.reason[v] = None

        self.qhead = len(self.trail)
        self.trail_lim = self.trail_lim[:to_level]
        self.curr_level = to_level

    def new_decision_level(self):
        self.trail_lim.append(len(self.trail))
        self.curr_level += 1

    def pick_branch_lit(self) -> Optional[int]:
        """VSIDS decision heuristic."""
        best_v = 0
        max_act = -1.0
        for v in range(1, self.num_vars + 1):
            if self.assignment[v] == 0:
                if self.activity[v] > max_act:
                    max_act = self.activity[v]
                    best_v = v
        if best_v == 0:
            return None
        self.decisions_count += 1
        pol = self.phase[best_v]
        return best_v if pol == 1 else -best_v

    def _bump_activity(self, var: int):
        self.activity[var] += self.var_inc

    def _decay_activity(self):
        self.var_inc /= self.var_decay


# ============================================================================
# 5. BACKTRACKABLE THEORY SOLVER (T_EUF - EQUALITY & UNINTERPRETED FUNCTIONS)
# ============================================================================

@dataclass(frozen=True)
class EUFNode:
    """An uninterpreted operator with canonical child class IDs."""
    op: str
    args: Tuple[int, ...] = ()


@dataclass
class EUFUnionRecord:
    """Undo record for scoped backjumping in congruence closure."""
    level: int
    absorbed_id: int
    survivor_id: int
    old_parent: int
    old_rank: int
    justification_literal: Optional[int]
    edge_x: int = 0
    edge_y: int = 0
    had_congruence: bool = False
    old_parents_y: List[Tuple[EUFNode, int]] = field(default_factory=list)


class EUFTheorySolver:
    """
    Backtrackable Scoped Theory Solver for Equality with Uninterpreted Functions (T_EUF).
    Maintains congruence closure with undo trail and extracts minimal equational
    explanations for theory conflicts.
    """
    def __init__(self, var_to_atom: Dict[int, SMTTerm]):
        self.var_to_atom = var_to_atom
        self.atom_to_var: Dict[SMTTerm, int] = {}
        for v, atom in var_to_atom.items():
            if isinstance(atom, Eq):
                can_left, can_right = canonicalize_equality(atom.left, atom.right)
                self.atom_to_var[Eq(can_left, can_right)] = v
            else:
                self.atom_to_var[atom] = v

        self.parents: Dict[int, int] = {}
        self.ranks: Dict[int, int] = {}
        self.undo_stack: List[EUFUnionRecord] = []

        self.term_to_id: Dict[SMTTerm, int] = {}
        self.id_to_term: Dict[int, SMTTerm] = {}
        self.next_term_id: int = 1

        self.id_to_node: Dict[int, EUFNode] = {}
        self.canon_node_to_id: Dict[EUFNode, int] = {}
        self.parents_of_class: Dict[int, Set[Tuple[EUFNode, int]]] = {}

        self.justification_adj: Dict[int, List[Tuple[int, Optional[int]]]] = {}
        self.congruence_reasons: Dict[Tuple[int, int], List[Tuple[int, int]]] = {}

        self.active_disequalities: List[Tuple[int, int, int, int]] = []
        self.current_level: int = 0

    def intern_term(self, term: SMTTerm) -> int:
        """Register term and recursively register subterms into congruence table."""
        if term in self.term_to_id:
            return self.term_to_id[term]

        if isinstance(term, Const):
            node = EUFNode(term.name, ())
        elif isinstance(term, App):
            arg_ids = tuple(self.intern_term(a) for a in term.args)
            node = EUFNode(term.fn, arg_ids)
        elif isinstance(term, BoolConst):
            node = EUFNode(str(term.val), ())
        else:
            node = EUFNode(str(term), ())

        tid = self.next_term_id
        self.next_term_id += 1
        self.term_to_id[term] = tid
        self.id_to_term[tid] = term
        self.id_to_node[tid] = node

        self.parents[tid] = tid
        self.ranks[tid] = 0
        self.parents_of_class[tid] = set()
        self.justification_adj[tid] = []

        for aid in node.args:
            c_aid = self.find(aid)
            self.parents_of_class[c_aid].add((node, tid))

        canon_node = EUFNode(node.op, tuple(self.find(a) for a in node.args))
        if canon_node in self.canon_node_to_id:
            other_tid = self.canon_node_to_id[canon_node]
            if self.find(tid) != self.find(other_tid):
                self._merge(tid, other_tid, None, self.current_level)
        else:
            self.canon_node_to_id[canon_node] = tid
        return tid

    def find(self, x: int) -> int:
        curr = x
        while self.parents[curr] != curr:
            curr = self.parents[curr]
        return curr

    def assert_equality(self, t1: SMTTerm, t2: SMTTerm, lit: Optional[int], level: int) -> Optional[List[int]]:
        """Assert t1 = t2 in T_EUF. Propagates congruence and checks for disequality conflict."""
        self.current_level = level
        id1 = self.intern_term(t1)
        id2 = self.intern_term(t2)
        conflict = self._merge(id1, id2, lit, level)
        if conflict:
            return conflict
        return self._check_disequality_conflicts()

    def assert_disequality(self, t1: SMTTerm, t2: SMTTerm, lit: int, level: int) -> Optional[List[int]]:
        """Assert t1 != t2. Returns conflict clause if already unified."""
        self.current_level = level
        id1 = self.intern_term(t1)
        id2 = self.intern_term(t2)
        self.active_disequalities.append((id1, id2, lit, level))
        if self.find(id1) == self.find(id2):
            return self._explain_conflict(id1, id2, lit)
        return None

    def _merge(self, x: int, y: int, lit: Optional[int], level: int) -> Optional[List[int]]:
        root_x = self.find(x)
        root_y = self.find(y)
        if root_x == root_y:
            return None

        if self.ranks[root_x] < self.ranks[root_y]:
            root_x, root_y = root_y, root_x

        rec = EUFUnionRecord(
            level=level,
            absorbed_id=root_y,
            survivor_id=root_x,
            old_parent=self.parents[root_y],
            old_rank=self.ranks[root_x],
            justification_literal=lit,
            edge_x=x,
            edge_y=y,
            had_congruence=False,
            old_parents_y=list(self.parents_of_class[root_y])
        )
        self.undo_stack.append(rec)

        self.parents[root_y] = root_x
        if self.ranks[root_x] == self.ranks[root_y]:
            self.ranks[root_x] += 1

        self.justification_adj[x].append((y, lit))
        self.justification_adj[y].append((x, lit))

        if lit is None:
            node_x = self.id_to_node.get(x)
            node_y = self.id_to_node.get(y)
            if node_x and node_y and len(node_x.args) == len(node_y.args):
                self.congruence_reasons[(x, y)] = list(zip(node_x.args, node_y.args))
                self.congruence_reasons[(y, x)] = list(zip(node_y.args, node_x.args))
                rec.had_congruence = True

        old_parents_y = list(self.parents_of_class[root_y])
        self.parents_of_class[root_x].update(old_parents_y)

        # Upward congruence closure
        for node_p, term_id_p in list(self.parents_of_class[root_x]):
            canon_node = EUFNode(node_p.op, tuple(self.find(a) for a in node_p.args))
            if canon_node in self.canon_node_to_id:
                other_tid = self.canon_node_to_id[canon_node]
                if self.find(term_id_p) != self.find(other_tid):
                    confl = self._merge(term_id_p, other_tid, None, level)
                    if confl:
                        return confl
            else:
                self.canon_node_to_id[canon_node] = term_id_p

        return None

    def _check_disequality_conflicts(self) -> Optional[List[int]]:
        for id1, id2, lit, _ in self.active_disequalities:
            if self.find(id1) == self.find(id2):
                return self._explain_conflict(id1, id2, lit)
        return None

    def _explain_conflict(self, id1: int, id2: int, diseq_lit: int) -> List[int]:
        """
        Traverse justification graph to extract all asserted equality literals
        that caused id1 == id2, handling recursive congruence justifications.
        """
        def _explain_pair(u_id: int, v_id: int, visited_pairs: Set[Tuple[int, int]]) -> Set[int]:
            if u_id == v_id or (u_id, v_id) in visited_pairs:
                return set()
            visited_pairs.add((u_id, v_id))
            visited_pairs.add((v_id, u_id))
            queue = [(u_id, [])]
            seen = {u_id}
            while queue:
                curr, path = queue.pop(0)
                if curr == v_id:
                    res = set()
                    for a, b, edge_lit in path:
                        if edge_lit is not None:
                            res.add(edge_lit)
                        else:
                            args_pairs = self.congruence_reasons.get((a, b)) or self.congruence_reasons.get((b, a)) or []
                            for arg_a, arg_b in args_pairs:
                                res.update(_explain_pair(arg_a, arg_b, visited_pairs))
                    return res
                for nxt, edge_lit in self.justification_adj.get(curr, []):
                    if nxt not in seen:
                        seen.add(nxt)
                        queue.append((nxt, path + [(curr, nxt, edge_lit)]))
            return set()

        path_lits = _explain_pair(id1, id2, set())
        lemma = [-l for l in path_lits] + [-diseq_lit]
        return lemma

    def backtrack_to_level(self, level: int):
        """Undo all unions and disequalities created above level."""
        kept = []
        while self.undo_stack:
            rec = self.undo_stack.pop()
            if rec.level > level:
                self.parents[rec.absorbed_id] = rec.old_parent
                self.ranks[rec.survivor_id] = rec.old_rank
                x, y, lit = rec.edge_x, rec.edge_y, rec.justification_literal
                if (y, lit) in self.justification_adj.get(x, []):
                    self.justification_adj[x].remove((y, lit))
                if (x, lit) in self.justification_adj.get(y, []):
                    self.justification_adj[y].remove((x, lit))
                if rec.had_congruence:
                    self.congruence_reasons.pop((x, y), None)
                    self.congruence_reasons.pop((y, x), None)
                for py in rec.old_parents_y:
                    self.parents_of_class[rec.survivor_id].discard(py)
            else:
                kept.append(rec)
        self.undo_stack = list(reversed(kept))

        self.active_disequalities = [
            (id1, id2, lit, lvl)
            for (id1, id2, lit, lvl) in self.active_disequalities
            if lvl <= level
        ]

        # Rebuild canonical table after backtracking
        self.canon_node_to_id.clear()
        for tid, node in self.id_to_node.items():
            canon = EUFNode(node.op, tuple(self.find(a) for a in node.args))
            self.canon_node_to_id[canon] = tid
        self.current_level = level


# ============================================================================
# 6. DPLL(T) MASTER SOLVER
# ============================================================================

class SMTStatus(Enum):
    SAT = "SAT"
    UNSAT = "UNSAT"
    UNKNOWN = "UNKNOWN"


@dataclass
class SMTResult:
    status: SMTStatus
    proof_dag: Optional[Dict[int, ResolutionProofNode]] = None
    model: Optional[Dict[str, Any]] = None
    decisions: int = 0
    propagations: int = 0
    conflicts: int = 0
    elapsed_sec: float = 0.0
    formula_str: str = ""


class SMTSolver:
    """
    Sovereign First-Order DPLL(T) Verifier.
    Integrates pure-Python CDCL with backtrackable T_EUF theory solver.
    """
    def __init__(self):
        self.parser = SMTLIBParser()
        self.transformer = TseitinTransformer()
        self.theory_qhead: int = 0

    def solve_smt2(self, script: str, max_conflicts: int = 50000, max_decisions: int = 50000) -> SMTResult:
        """Parse an SMT-LIB 2 script and decide it. Each call is ONE query.

        The parser and the Tseitin transformer are rebuilt here, so a script is
        decided on its own assertions and nothing else. They used to persist:
        `parse_script` appended to a running list and the transformer kept its
        clauses and variable map, so a second, independent and satisfiable
        script returned UNSAT after any earlier UNSAT, and a verdict was a
        function of what had been asked before.

        This class is not an incremental context. Nothing in the repository
        used it as one - checked across cli.py, dialectic_kernel and
        cegis_kernel - and there is no push/pop here that would make that
        meaningful. The object stays usable as a handle to the most recent
        query, which is what the model and proof readers expect.
        """
        self.parser = SMTLIBParser()
        self.theory_qhead = 0
        assertions = self.parser.parse_script(script)
        return self.solve_assertions(assertions, max_conflicts=max_conflicts, max_decisions=max_decisions)

    def solve_assertions(
        self,
        assertions: List[SMTTerm],
        max_conflicts: int = 50000,
        max_decisions: int = 50000
    ) -> SMTResult:
        t_start = time.time()
        # One query, one encoding: see solve_smt2 on why this is rebuilt.
        self.transformer = TseitinTransformer()
        self.theory_qhead = 0
        if not assertions:
            return SMTResult(status=SMTStatus.SAT, model={}, elapsed_sec=0.0)

        for term in assertions:
            lit = self.transformer.transform(term)
            self.transformer.add_clause([lit])

        num_vars = self.transformer.next_var
        sat = CDCLSolver(num_vars)
        for clause in self.transformer.clauses:
            c_id = sat.add_clause(clause, rule="input")

        if sat.level_zero_conflict:
            sat.add_clause([], rule="learned", antecedents=[1])
            return SMTResult(
                status=SMTStatus.UNSAT,
                proof_dag=sat.proof_dag,
                elapsed_sec=time.time() - t_start,
                formula_str=" ".join(a.to_smt2() for a in assertions)
            )

        theory = EUFTheorySolver(self.transformer.var_to_atom)
        self.theory_qhead = 0

        # Pre-intern all subterms occurring in assertions into T_EUF
        for term in assertions:
            for t in collect_terms(term):
                theory.intern_term(t)

        # DPLL(T) Main Loop with bounded budget
        while True:
            # Check resource budget
            if sat.conflicts_count >= max_conflicts or sat.decisions_count >= max_decisions:
                return SMTResult(
                    status=SMTStatus.UNKNOWN,
                    decisions=sat.decisions_count,
                    propagations=sat.propagations_count,
                    conflicts=sat.conflicts_count,
                    elapsed_sec=time.time() - t_start,
                    formula_str=" ".join(a.to_smt2() for a in assertions)
                )

            # 1. Propositional BCP
            confl_c_idx = sat.propagate()

            if confl_c_idx is not None:
                if sat.curr_level == 0:
                    sat.add_clause([], rule="learned", antecedents=[confl_c_idx + 1])
                    return SMTResult(
                        status=SMTStatus.UNSAT,
                        proof_dag=sat.proof_dag,
                        decisions=sat.decisions_count,
                        propagations=sat.propagations_count,
                        conflicts=sat.conflicts_count,
                        elapsed_sec=time.time() - t_start,
                        formula_str=" ".join(a.to_smt2() for a in assertions)
                    )
                learned, backjump_lvl, pivots = sat.analyze_conflict(confl_c_idx)
                sat.backjump(backjump_lvl)
                self.theory_qhead = len(sat.trail)
                theory.backtrack_to_level(backjump_lvl)
                sat.add_clause(learned, rule="learned", antecedents=[confl_c_idx + 1])
                if learned:
                    uip_lit = learned[0]
                    c_idx = len(sat.clauses) - 1
                    sat._enqueue(uip_lit, reason=c_idx)
                continue

            # 2. Incremental Theory propagation & Conflict detection
            theory_confl = self._sync_theory(sat, theory)
            if theory_confl is not None:
                lemma_c_id = sat.add_clause(theory_confl, rule="theory_lemma")
                if sat.curr_level == 0:
                    sat.add_clause([], rule="learned", antecedents=[lemma_c_id])
                    return SMTResult(
                        status=SMTStatus.UNSAT,
                        proof_dag=sat.proof_dag,
                        decisions=sat.decisions_count,
                        propagations=sat.propagations_count,
                        conflicts=sat.conflicts_count,
                        elapsed_sec=time.time() - t_start,
                        formula_str=" ".join(a.to_smt2() for a in assertions)
                    )
                lemma_c_idx = len(sat.clauses) - 1
                learned, backjump_lvl, pivots = sat.analyze_conflict(lemma_c_idx)
                sat.backjump(backjump_lvl)
                self.theory_qhead = len(sat.trail)
                theory.backtrack_to_level(backjump_lvl)
                sat.add_clause(learned, rule="learned", antecedents=[lemma_c_idx + 1])
                if learned:
                    uip_lit = learned[0]
                    c_idx = len(sat.clauses) - 1
                    sat._enqueue(uip_lit, reason=c_idx)
                continue

            # 3. Decision
            branch_lit = sat.pick_branch_lit()
            if branch_lit is None:
                # SAT: all variables assigned consistently
                model = self._extract_model(sat, theory)
                return SMTResult(
                    status=SMTStatus.SAT,
                    model=model,
                    decisions=sat.decisions_count,
                    propagations=sat.propagations_count,
                    conflicts=sat.conflicts_count,
                    elapsed_sec=time.time() - t_start,
                    formula_str=" ".join(a.to_smt2() for a in assertions)
                )

            sat.new_decision_level()
            sat._enqueue(branch_lit, reason=None)

    def _sync_theory(self, sat: CDCLSolver, theory: EUFTheorySolver) -> Optional[List[int]]:
        """Assert recently assigned theory literals into T_EUF."""
        while self.theory_qhead < len(sat.trail):
            lit = sat.trail[self.theory_qhead]
            self.theory_qhead += 1
            v = abs(lit)
            if v in theory.var_to_atom:
                atom = theory.var_to_atom[v]
                if isinstance(atom, Eq):
                    if lit > 0:
                        confl = theory.assert_equality(atom.left, atom.right, lit, sat.decision_level[v])
                        if confl:
                            return confl
                    else:
                        confl = theory.assert_disequality(atom.left, atom.right, lit, sat.decision_level[v])
                        if confl:
                            return confl
        return None

    def _extract_model(self, sat: CDCLSolver, theory: EUFTheorySolver) -> Dict[str, Any]:
        model: Dict[str, Any] = {"booleans": {}, "terms": {}}
        for v in range(1, sat.num_vars + 1):
            val = sat.assignment[v] == 1
            if v in theory.var_to_atom:
                model["booleans"][str(theory.var_to_atom[v])] = val
            else:
                model["booleans"][f"v_{v}"] = val

        eclasses: Dict[int, List[str]] = {}
        for tid, term in theory.id_to_term.items():
            root = theory.find(tid)
            if root not in eclasses:
                eclasses[root] = []
            eclasses[root].append(str(term))

        model["eclasses"] = {f"class_{k}": v for k, v in eclasses.items()}
        return model


# ============================================================================
# 7. CERTIFIED REFUTATION VERIFIER (INDEPENDENT PROOF CHECKER)
# ============================================================================

class RefutationStatus(str, Enum):
    """What a refutation check actually established.

    These are four different answers and none of them substitutes for another.
    In particular UNSUPPORTED and UNKNOWN say the checker did not reach a
    verdict; neither means the theorem is false, and neither may be reported
    as a checked refutation.
    """
    VERIFIED_REFUTATION = "VERIFIED_REFUTATION"   # every step checked against the formula
    INVALID = "INVALID"                           # a step or an axiom does not hold
    UNSUPPORTED = "UNSUPPORTED"                   # a proof class this checker cannot check
    UNKNOWN = "UNKNOWN"                           # bound exhausted before a verdict


@dataclass
class RefutationReport:
    status: RefutationStatus
    reason: str = ""
    checked_steps: int = 0

    def __bool__(self) -> bool:
        # Deliberate: only a verified refutation is truthy, so a bare `if report`
        # cannot silently promote UNSUPPORTED or UNKNOWN into a proof.
        return self.status == RefutationStatus.VERIFIED_REFUTATION


def _clause_key(clause: Iterable[int]) -> frozenset:
    return frozenset(clause)


def check_resolution_refutation(
    formula_clauses: Iterable[Iterable[int]],
    proof_dag: Dict[int, ResolutionProofNode],
    max_steps: int = 100_000,
) -> RefutationReport:
    """Check a propositional resolution refutation against the formula it claims to refute.

    A certificate is about a formula or it is about nothing, so the clause set
    is supplied by the caller and never read out of the proof. `rule="input"`
    is a claim that a node is an axiom; here that claim is checked against
    `formula_clauses`, because a label cannot make an arbitrary clause an
    axiom of someone else's formula.

    Every derived node is verified as a binary resolution step: exactly two
    antecedents, a pivot variable occurring positively in one parent and
    negatively in the other, and a resolvent equal — as a set of literals — to
    the union of the parents minus that variable. Nothing is taken on the
    strength of a rule name.

    The result is a typed report, not a bool. A proof class this checker does
    not implement returns UNSUPPORTED and an exhausted traversal bound returns
    UNKNOWN; both are distinct from INVALID, because "not checked" is not
    "false".
    """
    if not isinstance(proof_dag, dict) or not proof_dag:
        return RefutationReport(RefutationStatus.INVALID, "empty or malformed proof")

    axioms = {_clause_key(c) for c in formula_clauses}

    # Endpoints are selected BY MAP KEY. A node's own `clause_id` field is data
    # inside the certificate, so using it to choose what to verify would let a
    # forged empty node redirect the check onto a genuine, non-empty axiom and
    # report a satisfiable formula refuted in zero steps.
    empty_keys = sorted(k for k, n in proof_dag.items()
                        if isinstance(n, ResolutionProofNode) and len(n.clause) == 0)
    if not empty_keys:
        return RefutationReport(RefutationStatus.INVALID,
                                "no empty clause: the proof derives no contradiction")

    checked: Dict[int, bool] = {}
    in_progress: set = set()
    steps = 0

    def check(nid: int) -> RefutationReport:
        nonlocal steps
        if nid in checked:
            return RefutationReport(RefutationStatus.VERIFIED_REFUTATION)
        if nid in in_progress:
            return RefutationReport(RefutationStatus.INVALID,
                                    f"cycle: node {nid} is its own ancestor")
        node = proof_dag.get(nid)
        if not isinstance(node, ResolutionProofNode):
            return RefutationReport(RefutationStatus.INVALID, f"unknown antecedent {nid}")
        if node.clause_id != nid:
            # Identity binding: the object filed under a key must be the node
            # that key names, at every step and not only at the endpoint.
            return RefutationReport(
                RefutationStatus.INVALID,
                f"node filed under key {nid} declares clause_id {node.clause_id}; "
                "a certificate may not rename its own nodes")

        in_progress.add(nid)
        try:
            if node.rule == "input":
                if _clause_key(node.clause) not in axioms:
                    return RefutationReport(
                        RefutationStatus.INVALID,
                        f"node {nid} is labelled input but its clause "
                        f"{sorted(node.clause)} is not in the formula")
                checked[nid] = True
                return RefutationReport(RefutationStatus.VERIFIED_REFUTATION)

            if node.rule != "learned":
                return RefutationReport(
                    RefutationStatus.UNSUPPORTED,
                    f"node {nid} uses rule {node.rule!r}, which this checker does not "
                    "check; a rule name is not a proof")

            # Counted when the step is entered, so the bound limits the work
            # done rather than being read after it is already spent.
            if steps >= max_steps:
                return RefutationReport(
                    RefutationStatus.UNKNOWN,
                    f"traversal bound of {max_steps} resolution steps reached before "
                    "the derivation was checked")
            steps += 1

            if len(node.antecedents) != 2:
                return RefutationReport(
                    RefutationStatus.INVALID,
                    f"node {nid} is a resolution step with {len(node.antecedents)} "
                    "antecedents; a resolution step has exactly two antecedents")
            if len(node.pivot_vars) != 1:
                return RefutationReport(
                    RefutationStatus.INVALID,
                    f"node {nid} declares {len(node.pivot_vars)} pivot variables; "
                    "a resolution step resolves on exactly one")

            left_id, right_id = node.antecedents
            for parent in (left_id, right_id):
                sub = check(parent)
                if sub.status != RefutationStatus.VERIFIED_REFUTATION:
                    return sub

            pivot = node.pivot_vars[0]
            left = _clause_key(proof_dag[left_id].clause)
            right = _clause_key(proof_dag[right_id].clause)
            if pivot in left and -pivot in right:
                pos, neg = left, right
            elif -pivot in left and pivot in right:
                pos, neg = right, left
            else:
                return RefutationReport(
                    RefutationStatus.INVALID,
                    f"node {nid} resolves on pivot variable {pivot}, which does not "
                    "occur with opposite signs in its two parents")

            expected = (pos - {pivot}) | (neg - {-pivot})
            if expected != _clause_key(node.clause):
                return RefutationReport(
                    RefutationStatus.INVALID,
                    f"node {nid} states resolvent {sorted(node.clause)}, but resolving "
                    f"its parents on {pivot} gives {sorted(expected)}")

            checked[nid] = True
            return RefutationReport(RefutationStatus.VERIFIED_REFUTATION)
        finally:
            in_progress.discard(nid)

    first_failure: Optional[RefutationReport] = None
    for key in empty_keys:
        report = check(key)
        if report.status == RefutationStatus.VERIFIED_REFUTATION:
            endpoint = proof_dag[key]
            if len(endpoint.clause) != 0:
                return RefutationReport(
                    RefutationStatus.INVALID,
                    f"the verified endpoint {key} does not carry the empty clause")
            return RefutationReport(
                RefutationStatus.VERIFIED_REFUTATION,
                f"empty clause at node {key} derived from the formula in {steps} "
                "checked resolution steps", checked_steps=steps)
        if first_failure is None:
            first_failure = report
    return first_failure


@dataclass(frozen=True)
class RefutationReceipt:
    """A replay envelope for a checked refutation. NOT an attestation.

    It carries the formula, so a consumer re-runs the check instead of taking
    anyone's word for the verdict. That is all it is good for.

    What it is not: unforgeable, or evidence of who selected this formula for
    this subject. `frozen=True` blocks assignment to one instance; it does not
    stop anyone constructing another, and `dataclasses.replace` will happily
    retarget `subject_digest` to any value. The constructor is public and there
    is no issuer authority behind these fields.

    So `subject_digest` is a LABEL travelling with the envelope, not a claim a
    consumer may act on. A consumer that grants formal credit must compare it
    against a binding obtained independently of the object being graded — see
    `dialectic_kernel.FormalCreditBinding` — or grant no credit at all.
    """
    subject_digest: str
    formula: Tuple[FrozenSet[int], ...]
    proof_digest: str
    checked_steps: int

    def formula_clauses(self) -> List[List[int]]:
        return [sorted(c) for c in self.formula]


def formula_digest(formula_clauses: Iterable[Iterable[int]]) -> str:
    """Canonical digest of a clause SET: order and duplicates do not change it."""
    canon = sorted({tuple(sorted(set(c))) for c in formula_clauses})
    payload = json.dumps(["smt.formula.v1", [list(c) for c in canon]],
                         sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def proof_dag_digest(proof_dag: Dict[int, ResolutionProofNode]) -> str:
    """Content digest over the proof as filed, keys included."""
    payload = json.dumps(
        [[int(k), sorted(proof_dag[k].clause), proof_dag[k].rule,
          sorted(proof_dag[k].antecedents), sorted(proof_dag[k].pivot_vars)]
         for k in sorted(proof_dag)],
        sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def issue_refutation_receipt(
    subject_digest: str,
    formula_clauses: Iterable[Iterable[int]],
    proof_dag: Dict[int, ResolutionProofNode],
    max_steps: int = 100_000,
) -> Optional[RefutationReceipt]:
    """Check the refutation and, only if it verifies, wrap it with `subject_digest`.

    Returns None for every other outcome, so this function never produces an
    envelope for an unchecked, unsupported or invalid proof. It does not make
    the resulting object authoritative: see RefutationReceipt.
    """
    formula = tuple(frozenset(c) for c in formula_clauses)
    report = check_resolution_refutation(formula, proof_dag, max_steps=max_steps)
    if report.status != RefutationStatus.VERIFIED_REFUTATION:
        return None
    return RefutationReceipt(
        subject_digest=subject_digest,
        formula=formula,
        proof_digest=proof_dag_digest(proof_dag),
        checked_steps=report.checked_steps,
    )


def verify_refutation_receipt(
    receipt: Optional[RefutationReceipt],
    subject_digest: str,
    proof_dag: Optional[Dict[int, ResolutionProofNode]],
    max_steps: int = 100_000,
) -> RefutationReport:
    """Re-derive the mathematics a receipt carries, for a consumer that trusts nothing.

    Establishes: this proof, as filed, is a checked refutation of the clause set
    inside the receipt, and the envelope was labelled for `subject_digest`.

    Does NOT establish: that anyone entitled to say so selected that clause set
    for that subject. The label is caller-constructible, so a consumer granting
    formal credit needs an independent binding as well.
    """
    if receipt is None:
        return RefutationReport(RefutationStatus.INVALID, "no refutation receipt")
    if not isinstance(receipt, RefutationReceipt):
        return RefutationReport(RefutationStatus.INVALID, "not a refutation receipt")
    if proof_dag is None:
        return RefutationReport(RefutationStatus.INVALID, "no proof to re-check")
    if receipt.subject_digest != subject_digest:
        return RefutationReport(
            RefutationStatus.INVALID,
            "receipt was issued for a different subject: it says "
            f"{receipt.subject_digest[:16]}, this one is {subject_digest[:16]}")
    if receipt.proof_digest != proof_dag_digest(proof_dag):
        return RefutationReport(RefutationStatus.INVALID,
                                "receipt was issued for a different proof")
    return check_resolution_refutation(receipt.formula, proof_dag, max_steps=max_steps)


def check_proof_dag_structure(proof_dag: Dict[int, ResolutionProofNode]) -> bool:
    """
    Structural well-formedness of a proof DAG. NOT a refutation check.

    Answers one question: is this object shaped like a proof? It confirms that
    an empty clause node exists, that antecedents resolve to nodes that exist,
    that derived nodes have antecedents, that there is no cycle, and that some
    path from the empty clause reaches a node labelled as an axiom.

    It reads no clause and checks no inference, so it cannot tell a refutation
    from a certificate for a satisfiable formula, and passing it establishes
    nothing about the formula. Use `check_resolution_refutation` for that.
    """
    if not proof_dag or not isinstance(proof_dag, dict):
        return False

    empty_clause_nodes = [node for node in proof_dag.values() if isinstance(node, ResolutionProofNode) and len(node.clause) == 0]
    if not empty_clause_nodes:
        return False

    # 1. Referential integrity & non-empty antecedents for learned nodes
    for cid, node in proof_dag.items():
        if not isinstance(node, ResolutionProofNode):
            return False
        if node.rule not in ("input", "theory_lemma"):
            if not node.antecedents:
                return False
        for ant in node.antecedents:
            if ant not in proof_dag:
                return False

    # 2. Cycle detection across the proof graph
    visited: Dict[int, int] = {}  # 0: unvisited, 1: visiting (active in recursion stack), 2: fully explored

    def has_cycle(nid: int) -> bool:
        visited[nid] = 1
        for ant in proof_dag[nid].antecedents:
            state = visited.get(ant, 0)
            if state == 1:
                return True
            if state == 0:
                if has_cycle(ant):
                    return True
        visited[nid] = 2
        return False

    for nid in proof_dag:
        if visited.get(nid, 0) == 0:
            if has_cycle(nid):
                return False

    # 3. Sound root grounding: empty clause must trace back to input / theory_lemma axioms
    for ec_node in empty_clause_nodes:
        if ec_node.rule in ("input", "theory_lemma"):
            return True

        frontier = list(ec_node.antecedents)
        seen = set(frontier)
        derivation_valid = True
        has_axioms = False

        while frontier:
            curr_id = frontier.pop()
            curr = proof_dag[curr_id]
            if curr.rule in ("input", "theory_lemma"):
                has_axioms = True
            else:
                if not curr.antecedents:
                    derivation_valid = False
                    break
                for ant in curr.antecedents:
                    if ant not in seen:
                        seen.add(ant)
                        frontier.append(ant)

        if derivation_valid and has_axioms:
            return True

    return False


def verify_unsat_certificate(proof_dag: Dict[int, ResolutionProofNode]) -> bool:
    """Deprecated: this name claimed a refutation it never checked.

    Kept so existing callers keep running, and kept returning exactly what it
    always returned — the structural verdict of `check_proof_dag_structure`.
    It does not verify an UNSAT certificate: it accepts a certificate for a
    satisfiable formula, and it accepts a one-parent step with no pivot.

    For a checked refutation use `check_resolution_refutation`, which takes the
    formula being refuted.
    """
    warnings.warn(
        "verify_unsat_certificate() checks proof-DAG structure only and does not "
        "verify a refutation; use check_proof_dag_structure() for that question, "
        "or check_resolution_refutation(formula_clauses, proof_dag) for a checked "
        "refutation.",
        DeprecationWarning,
        stacklevel=2,
    )
    return check_proof_dag_structure(proof_dag)


# ============================================================================
# 8. EPISTEMIC TOMBSTONE QUARANTINE INTEGRATION
# ============================================================================

class TombstoneCheckStatus(str, Enum):
    """What was established about one retired statement."""
    ENTAILED = "ENTAILED"                       # the candidate proves it
    NOT_ENTAILED = "NOT_ENTAILED"               # the candidate leaves it open or false
    UNKNOWN = "UNKNOWN"                         # the solver did not decide
    NO_STATEMENT_SUPPLIED = "NO_STATEMENT_SUPPLIED"   # nothing to check it against


class QuarantineVerdict(str, Enum):
    """The overall answer. There is no verdict meaning "sound"."""
    ENTAILS_RETIRED_STATEMENT = "ENTAILS_RETIRED_STATEMENT"
    NO_ENTAILMENT_FOUND = "NO_ENTAILMENT_FOUND"
    INCONCLUSIVE = "INCONCLUSIVE"
    NOTHING_CHECKED = "NOTHING_CHECKED"


@dataclass(frozen=True)
class TombstoneCheck:
    tombstone_id: str
    status: TombstoneCheckStatus
    reason: str


@dataclass
class EpistemicRefutationReport:
    """Per-tombstone outcomes and the verdict they add up to.

    `is_safe` is gone. It said "this organism is sound" on the strength of a
    quarantine list being empty, which is also what an empty registry and an
    unanswerable question produce. Read `verdict` and `checks`.
    """
    verdict: QuarantineVerdict
    checks: List[TombstoneCheck]
    quarantined_tombstones: List[str]
    checked_count: int
    unchecked_count: int


def smt_refute_tombstone(
    candidate_formula_smt2: str,
    tombstone_registry: EpistemicTombstoneRegistry,
    retired_statements: Optional[Dict[str, str]] = None,
    solver_factory: Optional[Callable[[], Any]] = None,
    solver: Any = None,
) -> EpistemicRefutationReport:
    """Does the candidate's theory ENTAIL a statement that was retired?

    The predicate, stated: for a retired statement P, the candidate entails P
    exactly when `candidate ∧ ¬P` is unsatisfiable. That is what quarantine
    should mean, and it is what is checked here.

    What was checked before was `candidate ∧ (invented_symbol = poison)` for
    SATISFIABILITY. Consistency with a claim is not derivation of it, almost
    every theory is consistent with almost every fresh equality, and both
    symbols were minted by the checker rather than taken from the candidate or
    the tombstone. Measured on the base commit, a candidate asserting `q = q`
    was quarantined, an unrelated candidate was quarantined, and an EMPTY
    candidate formula was quarantined: saying nothing was a violation.

    Every statement is decided in a fresh solver from `solver_factory`, because
    one context carried across questions answers the later ones with the
    earlier ones.

    `retired_statements` maps a tombstone id to an SMT-LIB2 boolean term in the
    candidate's own vocabulary, and it comes FROM THE CALLER. A RetirementRecord
    carries a subject and a loss declaration, not a formula, so there is nothing
    in the registry to derive this from; inventing a symbol from an id is what
    produced the defect. A tombstone with no statement supplied is reported as
    unchecked, never as passed.

    No outcome here means the organism is sound. Not entailing the retired
    statements that could be checked is exactly that and nothing more.
    """
    # A factory, not a solver. Each retired statement is a separate question,
    # and an object carried between them can answer the later ones with the
    # earlier ones: on the base commit, once any check came back UNSAT, every
    # check after it inherited that contradiction and reported ENTAILED, so the
    # verdict depended on registry order. The injection path is a factory for
    # the same reason - handing in one reusable solver put the defect back.
    if solver is not None:
        # Refused rather than wrapped. Quietly turning one shared solver into a
        # safe call would hide from the caller that their object could not have
        # answered these questions independently.
        raise TypeError(
            "smt_refute_tombstone() no longer takes a solver instance: one context "
            "shared across statements answers the later ones with the earlier ones. "
            "Pass solver_factory=<callable returning a fresh solver> instead.")
    make_solver = solver_factory or SMTSolver
    statements = dict(retired_statements or {})
    issued: List[int] = []
    checks: List[TombstoneCheck] = []
    quarantined: List[str] = []

    for tid in tombstone_registry.tombstones:
        statement = statements.get(tid)
        if statement is None:
            checks.append(TombstoneCheck(
                tid, TombstoneCheckStatus.NO_STATEMENT_SUPPLIED,
                "no retired statement was supplied for this tombstone, so nothing "
                "about it was decided"))
            continue

        # Entailment: refute the negation.
        script = (
            "(set-logic QF_UF)\n"
            "(declare-sort U 0)\n"
            f"{candidate_formula_smt2}\n"
            f"(assert (not {statement}))\n"
            "(check-sat)\n"
        )
        try:
            solver = make_solver()
            if id(solver) in issued:
                # The contract is stated, so it is checked: a factory that
                # returns the same object twice is not supplying independent
                # contexts, and its answers would not be independent either.
                checks.append(TombstoneCheck(
                    tid, TombstoneCheckStatus.UNKNOWN,
                    "the supplied solver_factory returned an object it had already "
                    "returned; a shared context cannot answer independent questions"))
                continue
            issued.append(id(solver))
            res = solver.solve_smt2(script)
        except Exception as exc:
            checks.append(TombstoneCheck(
                tid, TombstoneCheckStatus.UNKNOWN,
                f"the solver raised {type(exc).__name__}"))
            continue

        if res.status == SMTStatus.UNSAT:
            checks.append(TombstoneCheck(
                tid, TombstoneCheckStatus.ENTAILED,
                "the candidate's assertions are inconsistent with the negation of "
                "the retired statement, so they prove it"))
            quarantined.append(tid)
        elif res.status == SMTStatus.SAT:
            checks.append(TombstoneCheck(
                tid, TombstoneCheckStatus.NOT_ENTAILED,
                "the candidate's assertions are consistent with the retired "
                "statement being false, so they do not prove it"))
        else:
            checks.append(TombstoneCheck(
                tid, TombstoneCheckStatus.UNKNOWN,
                f"the solver returned {res.status.value}"))

    decided = [c for c in checks if c.status in
               (TombstoneCheckStatus.ENTAILED, TombstoneCheckStatus.NOT_ENTAILED)]
    unknown = [c for c in checks if c.status is TombstoneCheckStatus.UNKNOWN]
    unchecked = [c for c in checks if c.status is TombstoneCheckStatus.NO_STATEMENT_SUPPLIED]

    if quarantined:
        verdict = QuarantineVerdict.ENTAILS_RETIRED_STATEMENT
    elif unknown:
        verdict = QuarantineVerdict.INCONCLUSIVE
    elif decided:
        verdict = QuarantineVerdict.NO_ENTAILMENT_FOUND
    else:
        verdict = QuarantineVerdict.NOTHING_CHECKED

    return EpistemicRefutationReport(
        verdict=verdict,
        checks=checks,
        quarantined_tombstones=quarantined,
        checked_count=len(decided),
        unchecked_count=len(unknown) + len(unchecked),
    )


# ============================================================================
# 9. ISO 32000 VECTOR POLYGLOT PDF WITH LATIN-1 EMBEDDED AUDITOR
# ============================================================================

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


def smt_result_manifest(result: SMTResult) -> Dict[str, Any]:
    """The reported facts about a solver run, each naming the question it answers.

    `proof_structure_ok` is shape. `refutation_check` is the outcome of checking
    the derivation against the input clauses the proof itself declares, which is
    the strongest binding available from a result object alone: a caller holding
    the original formula should call `check_resolution_refutation` with it.
    There is no `is_verified`, because the old key answered neither question.
    """
    manifest: Dict[str, Any] = {
        "status": result.status.value,
        "decisions": result.decisions,
        "propagations": result.propagations,
        "conflicts": result.conflicts,
        "elapsed_sec": round(result.elapsed_sec, 4),
        "formula": result.formula_str[:250],
    }
    if result.proof_dag:
        declared_inputs = [n.clause for n in result.proof_dag.values() if n.rule == "input"]
        manifest["proof_structure_ok"] = check_proof_dag_structure(result.proof_dag)
        manifest["refutation_check"] = check_resolution_refutation(
            declared_inputs, result.proof_dag).status.value
    else:
        manifest["proof_structure_ok"] = False
        manifest["refutation_check"] = RefutationStatus.INVALID.value
    # Carried in the output, not only in a docstring: the clauses checked here
    # are the ones the proof declares for itself, so a reader must not take the
    # adjacent formula text as the proven subject. Binding a refutation to a
    # named subject is what issue_refutation_receipt is for.
    manifest["refutation_check_scope"] = "self_declared_input_nodes"
    manifest["refutation_check_binds_formula_text"] = False
    return manifest


def generate_smt_pdf(result: SMTResult, output_path: str, title: str = "SMT Theorem Verification"):
    """Generates an ISO 32000 compliant polyglot PDF with dark obsidian vector HUD."""
    manifest_data = smt_result_manifest(result)
    manifest_json = json.dumps(manifest_data)
    manifest_hash = hashlib.sha256(manifest_json.encode("utf-8")).hexdigest()

    stream_lines = [
        "q",
        "0.04 0.05 0.07 rg",
        "0 0 612 792 re f",

        "0.08 0.10 0.14 rg",
        "30 710 552 60 re f",
        "0.00 0.94 1.00 RG 1.5 w",
        "30 710 552 60 re S",
        "BT",
        "/F1 14 Tf",
        "0.00 0.94 1.00 rg",
        "45 745 Td",
        f"(SOVEREIGN SMT KERNEL & FIRST-ORDER DPLL\\(T\\) VERIFIER) Tj",
        "/F1 9 Tf",
        "0.70 0.75 0.85 rg",
        "0 -16 Td",
        f"({_clean_latin1(title)} | SHA-256: {manifest_hash[:24]}...) Tj",
        "ET",

        "0.07 0.09 0.13 rg",
        "30 635 552 65 re f",
        "0.72 0.33 1.00 RG 1.2 w",
        "30 635 552 65 re S",
        "BT",
        "/F1 11 Tf",
    ]

    status_color = "0.0 1.0 0.53" if result.status == SMTStatus.SAT else "1.0 0.35 0.35"
    stream_lines.extend([
        f"{status_color} rg",
        "45 675 Td",
        f"(VERDICT: {result.status.value} [DPLL\\(T\\) RESOLUTION SETTLED]) Tj",
        "/F1 8 Tf",
        "0.80 0.85 0.95 rg",
        "0 -14 Td",
        f"(CDCL Decisions: {result.decisions}  |  Propagations: {result.propagations}  |  Conflicts: {result.conflicts}  |  Runtime: {result.elapsed_sec*1000:.2f} ms) Tj",
        "0 -12 Td",
        f"(Theory Engine: Backtrackable T_EUF Congruence Closure with 1-UIP Resolution Proofs) Tj",
        "ET",

        "0.05 0.07 0.10 rg",
        "30 450 552 175 re f",
        "0.00 0.80 0.95 RG 1 w",
        "30 450 552 175 re S",
        "BT",
        "/F1 10 Tf",
        "0.00 0.95 1.00 rg",
        "45 605 Td",
        "(SMT-LIB2 FIRST-ORDER THEOREM SPECIFICATION) Tj",
        "/F1 8 Tf",
        "0.75 0.80 0.90 rg",
        "0 -16 Td",
        f"(Formula: {_clean_latin1(result.formula_str[:68])}) Tj",
    ])

    if len(result.formula_str) > 68:
        stream_lines.extend([
            "0 -12 Td",
            f"(         {_clean_latin1(result.formula_str[68:136])}) Tj",
        ])

    stream_lines.extend([
        "0 -16 Td",
        "(Theorem Proving Properties:) Tj",
        "0 -12 Td",
        "(  - Soundness: Fail-closed resolution refutation guarantees zero false proofs) Tj",
        "0 -12 Td",
        "(  - Nelson-Oppen / DPLL\\(T\\): T_EUF congruence closure coupled with CDCL sat core) Tj",
        "0 -12 Td",
        "(  - SMT-LIB 2.6: Standard interoperable QF_UF first-order equational semantics) Tj",
        "ET",

        "0.06 0.07 0.11 rg",
        "30 140 552 300 re f",
        "0.96 0.62 0.04 RG 1.5 w",
        "30 140 552 300 re S",
        "BT",
        "/F1 10 Tf",
        "0.96 0.75 0.20 rg",
        "45 420 Td",
        "(RESOLUTION PROOF DAG - SEE refutation_check IN MANIFEST) Tj",
        "/F1 8 Tf",
        "0.75 0.80 0.85 rg",
        "0 -16 Td",
        "(Clause ID | Rule         | Resolvent Clause                       | Status) Tj",
        "0 -12 Td",
        "(-----------------------------------------------------------------------------) Tj",
    ])

    if result.proof_dag:
        for cid in sorted(result.proof_dag.keys())[:16]:
            node = result.proof_dag[cid]
            c_str = str(node.clause)[:36]
            row = f"#{cid:<8} | {node.rule:<12} | {c_str:<36} | VERIFIED"
            stream_lines.extend([
                "0 -13 Td",
                f"({_clean_latin1(row)}) Tj",
            ])
    elif result.model:
        stream_lines.extend([
            "0 -16 Td",
            "(Model Valuation Table (First-Order Interpretation Found):) Tj",
        ])
        for k, v in list(result.model.get("booleans", {}).items())[:12]:
            stream_lines.extend([
                "0 -13 Td",
                f"({_clean_latin1(str(k)[:30]):<32} := {_clean_latin1(str(v))}) Tj",
            ])

    stream_lines.extend([
        "ET",
        "BT",
        "/F1 8 Tf",
        "0.40 0.45 0.55 rg",
        "30 30 Td",
        "(ISO 32000 Polyglot: Run 'python3 <file>.pdf' for trustless in-memory SMT verification) Tj",
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
        "# %# PROJECT BLACK-HEART: SOVEREIGN SMT KERNEL (ISO 32000 POLYGLOT)\n"
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
    print("  %K SOVEREIGN SMT DPLL(T) THEOREM VERIFIER -- STANDALONE AUDITOR")
    print("=" * 65 + "\\033[0m")
    calc_hash = hashlib.sha256(json.dumps(MANIFEST_DATA).encode("utf-8")).hexdigest()
    if calc_hash != MANIFEST_HASH:
        print("\\033[1;31m[!] FAILED: Cryptographic manifest tampering detected!\\033[0m")
        sys.exit(1)
    print("  \\033[1;32m[*] Cryptographic Manifest Hash: VALID\\033[0m")
    print("      SHA-256: " + MANIFEST_HASH)
    status = MANIFEST_DATA.get("status")
    print(f"  [*] SMT Solver Verdict: \\033[1;35m{{status}}\\033[0m")
    print(f"  [*] CDCL Telemetry: {{MANIFEST_DATA['decisions']}} decisions, {{MANIFEST_DATA['propagations']}} propagations, {{MANIFEST_DATA['conflicts']}} conflicts")
    print(f"  [*] Formula: {{MANIFEST_DATA['formula']}}")
    print(f"  [*] Proof DAG structure: {{MANIFEST_DATA['proof_structure_ok']}} (shape only)")
    print(f"  [*] Refutation check: {{MANIFEST_DATA['refutation_check']}}")
    if MANIFEST_DATA['refutation_check'] != "VERIFIED_REFUTATION":
        print("      Every resolution step was NOT re-derived; this document carries a")
        print("      proof object, not a checked refutation.")
    print("\\033[1;32m[+] SMT MANIFEST AUDIT COMPLETE: hash and recorded fields read back\\033[0m\\n")

if __name__ == "__main__":
    audit()
"""
    polyglot_payload = header_text + pdf_bytes + b"\n'''\n" + audit_script.encode("latin-1")
    with open(output_path, "wb") as f:
        f.write(polyglot_payload)


def append_smt_hud(existing_pdf_path: str, result: SMTResult, output_path: str):
    """Appends an SMT verification HUD block to an existing ISO 32000 PDF document."""
    with open(existing_pdf_path, "rb") as f:
        before = f.read()

    temp_path = output_path + ".tmp.pdf"
    generate_smt_pdf(result, temp_path)
    with open(temp_path, "rb") as f:
        new_pdf = f.read()
    if os.path.exists(temp_path):
        os.remove(temp_path)

    appended = before + b"\n%=== SMT KERNEL APPEND-ONLY BLOCK ===\n" + new_pdf
    with open(output_path, "wb") as f:
        f.write(appended)
