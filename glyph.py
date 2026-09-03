#!/usr/bin/env python3
"""
glyph.py — Pure Combinator Reduction Engine on Glyphs (SKIY)
Part of Project Black-Heart (%🖤).

Glyphs:
  🖤 = K combinator (Black Cone: Constant / Drop: K x y -> x)
  🤍 = I combinator (White Cone: Identity / Flow: I x -> x)
  🌿 = S combinator (Spore: Branching / Distribution: S x y z -> (x z)(y z))
  🔁 = Y combinator (Fixpoint / Recurrent Time: Y f -> f (Y f))
  ⚓ = Settlement Marker: [hash: ATP_cost]
"""

from __future__ import annotations
import hashlib
import sys
from dataclasses import dataclass
from typing import Union, List, Optional, Tuple

# Core Glyphs
GLYPH_K = "🖤"
GLYPH_I = "🤍"
GLYPH_S = "🌿"
GLYPH_Y = "🔁"
GLYPH_ANCHOR = "⚓"

@dataclass(frozen=True)
class Comb:
    symbol: str

    def __repr__(self) -> str:
        return self.symbol

@dataclass(frozen=True)
class Var:
    name: str

    def __repr__(self) -> str:
        return self.name

@dataclass(frozen=True)
class App:
    left: Term
    right: Term

    def __repr__(self) -> str:
        # Avoid redundant outer parentheses
        l_str = str(self.left)
        r_str = f"({self.right})" if isinstance(self.right, App) else str(self.right)
        return f"{l_str} {r_str}"

Term = Union[Comb, Var, App]

# Constants
K = Comb(GLYPH_K)
I = Comb(GLYPH_I)
S = Comb(GLYPH_S)
Y = Comb(GLYPH_Y)

# Standard Combinations
# TRUE = K
TRUE = K
# FALSE = K I
FALSE = App(K, I)

# Church Numeral 0 = FALSE = K I
CHURCH_0 = FALSE
# Church Numeral 1 = I = 🤍
CHURCH_1 = I

class ExecutionError(Exception):
    pass

class BudgetExceededError(ExecutionError):
    pass

def parse(text: str) -> Term:
    """Parse a glyph combinator string with whitespace and parentheses."""
    tokens = []
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c.isspace():
            i += 1
        elif c in "()":
            tokens.append(c)
            i += 1
        elif c in (GLYPH_K, GLYPH_I, GLYPH_S, GLYPH_Y):
            tokens.append(c)
            i += 1
        elif c.isalnum() or c in "_-":
            j = i
            while j < n and (text[j].isalnum() or text[j] in "_-"):
                j += 1
            word = text[i:j]
            # If standalone single-letter alias
            if word == "K":
                tokens.append(GLYPH_K)
            elif word == "I":
                tokens.append(GLYPH_I)
            elif word == "S":
                tokens.append(GLYPH_S)
            elif word == "Y":
                tokens.append(GLYPH_Y)
            else:
                tokens.append(word)
            i = j
        else:
            # other unicode characters
            tokens.append(c)
            i += 1

    pos = 0

    def parse_primary() -> Term:
        nonlocal pos
        if pos >= len(tokens):
            raise ValueError("Unexpected end of input")
        tok = tokens[pos]
        pos += 1
        if tok == "(":
            res = parse_expr()
            if pos >= len(tokens) or tokens[pos] != ")":
                raise ValueError("Unmatched open parenthesis")
            pos += 1  # consume ')'
            return res
        elif tok == GLYPH_K:
            return K
        elif tok == GLYPH_I:
            return I
        elif tok == GLYPH_S:
            return S
        elif tok == GLYPH_Y:
            return Y
        else:
            return Var(tok)

    def parse_expr() -> Term:
        nonlocal pos
        terms = []
        while pos < len(tokens) and tokens[pos] != ")":
            terms.append(parse_primary())
        if not terms:
            raise ValueError("Empty expression in parentheses")
        res = terms[0]
        for t in terms[1:]:
            res = App(res, t)
        return res

    result = parse_expr()
    if pos < len(tokens):
        raise ValueError(f"Trailing tokens starting at {tokens[pos]}")
    return result

def tree_size(term: Term) -> int:
    """Calculate the number of nodes in the term AST."""
    if isinstance(term, App):
        return 1 + tree_size(term.left) + tree_size(term.right)
    return 1

def canonical_bytes(term: Term) -> bytes:
    """Deterministic content-addressed byte representation."""
    if isinstance(term, Comb):
        return term.symbol.encode("utf-8")
    elif isinstance(term, Var):
        return f"${term.name}".encode("utf-8")
    elif isinstance(term, App):
        return b"(" + canonical_bytes(term.left) + b" " + canonical_bytes(term.right) + b")"
    raise TypeError(f"Unknown term type: {type(term)}")

def term_hash(term: Term) -> str:
    """SHA-256 digest of canonical normal form."""
    return hashlib.sha256(canonical_bytes(term)).hexdigest()

from enum import Enum

class EvalStatus(str, Enum):
    SETTLED = "SETTLED"       # Normal form reached (Black Cone closure)
    SUSPENDED = "SUSPENDED"   # Paused at ATP limit (intermediate thunk)

@dataclass
class EvalResult:
    term: Term
    steps: int
    atp_spent: int
    peak_size: int
    hash: str
    status: EvalStatus = EvalStatus.SETTLED

    @property
    def normal_form(self) -> Term:
        """Backward-compatible alias for settled or intermediate term."""
        return self.term

    def is_settled(self) -> bool:
        return self.status == EvalStatus.SETTLED

    def is_suspended(self) -> bool:
        return self.status == EvalStatus.SUSPENDED

    def short_hash(self) -> str:
        return self.hash[:12]

    def badge(self) -> str:
        tag = "⚓" if self.status == EvalStatus.SETTLED else "⏳"
        return f"{tag}⟨status:{self.status.value}, atp:{self.atp_spent}, size:{tree_size(self.term)}, hash:{self.short_hash()}⟩"

def reduce_step(term: Term) -> Tuple[Optional[Term], bool]:
    """
    Perform a single leftmost-outermost reduction step.
    Returns (next_term, did_reduce).
    """
    # 1. Check if the root is a redex:
    # Rule I: I x -> x
    if isinstance(term, App) and term.left == I:
        return (term.right, True)

    # Rule K: (K x) y -> x
    if (isinstance(term, App) and 
        isinstance(term.left, App) and 
        term.left.left == K):
        x = term.left.right
        return (x, True)

    # Rule S: ((S x) y) z -> (x z) (y z)
    if (isinstance(term, App) and 
        isinstance(term.left, App) and 
        isinstance(term.left.left, App) and 
        term.left.left.left == S):
        x = term.left.left.right
        y = term.left.right
        z = term.right
        return (App(App(x, z), App(y, z)), True)

    # Rule Y: Y f -> f (Y f)
    if isinstance(term, App) and term.left == Y:
        f = term.right
        return (App(f, App(Y, f)), True)

    # If root is not a redex, reduce left spine first (leftmost-outermost)
    if isinstance(term, App):
        new_left, reduced_left = reduce_step(term.left)
        if reduced_left:
            return (App(new_left, term.right), True)
        new_right, reduced_right = reduce_step(term.right)
        if reduced_right:
            return (App(term.left, new_right), True)

    return (term, False)

def evaluate(term: Term, max_atp: int = 100_000, raise_on_limit: bool = False) -> EvalResult:
    """
    Evaluate term to normal form using leftmost-outermost order with ATP budget.
    If max_atp is reached before normal form:
      - if raise_on_limit is True: raises BudgetExceededError
      - if raise_on_limit is False: returns EvalResult with status=SUSPENDED (Suspended Thunk)
    """
    curr = term
    steps = 0
    peak_sz = tree_size(curr)

    while steps < max_atp:
        curr_sz = tree_size(curr)
        if curr_sz > peak_sz:
            peak_sz = curr_sz

        next_term, did_reduce = reduce_step(curr)
        if not did_reduce:
            # Normal form reached!
            return EvalResult(
                term=curr,
                steps=steps,
                atp_spent=steps,
                peak_size=peak_sz,
                hash=term_hash(curr),
                status=EvalStatus.SETTLED
            )

        steps += 1
        curr = next_term

    # Checked boundary: can current term reduce further?
    curr_sz = tree_size(curr)
    if curr_sz > peak_sz:
        peak_sz = curr_sz

    _, can_reduce = reduce_step(curr)
    if not can_reduce:
        return EvalResult(
            term=curr,
            steps=steps,
            atp_spent=steps,
            peak_size=peak_sz,
            hash=term_hash(curr),
            status=EvalStatus.SETTLED
        )

    if raise_on_limit:
        raise BudgetExceededError(f"Evaluation exceeded ATP budget ({max_atp} ATP)")

    # Suspended Thunk!
    return EvalResult(
        term=curr,
        steps=steps,
        atp_spent=steps,
        peak_size=peak_sz,
        hash=term_hash(curr),
        status=EvalStatus.SUSPENDED
    )

def resume(result: EvalResult, additional_atp: int, raise_on_limit: bool = False) -> EvalResult:
    """
    Resume reduction of a SUSPENDED thunk with additional ATP quota.
    """
    if result.status == EvalStatus.SETTLED:
        return result

    next_res = evaluate(result.term, max_atp=additional_atp, raise_on_limit=raise_on_limit)
    return EvalResult(
        term=next_res.term,
        steps=result.steps + next_res.steps,
        atp_spent=result.atp_spent + next_res.atp_spent,
        peak_size=max(result.peak_size, next_res.peak_size),
        hash=next_res.hash,
        status=next_res.status
    )

@dataclass(frozen=True)
class SporeReceipt:
    input_hash: str
    output_hash: str
    atp_spent: int
    status: EvalStatus

    def badge(self) -> str:
        return f"📜SporeReceipt⟨in:{self.input_hash[:8]}, out:{self.output_hash[:8]}, atp:{self.atp_spent}, status:{self.status.value}⟩"

class SporeStore:
    """
    SporeStore: Two-way memoization engine (Claude & Gemini Spore protocol).
    - Forward (Cache): Compute once, share infinitely. (Input Hash -> Normal Form)
    - Reverse (Audit): Re-evaluate from origin and verify receipt authenticity.
    """
    def __init__(self):
        self._cache: dict[str, EvalResult] = {}
        self._receipts: dict[str, SporeReceipt] = {}

    def forward(self, term: Term, atp: int) -> Tuple[EvalResult, bool]:
        """
        Forward evaluation with O(1) cache lookup.
        Returns (EvalResult, was_cached: bool).
        """
        h_in = term_hash(term)
        if h_in in self._cache:
            cached = self._cache[h_in]
            if cached.status == EvalStatus.SETTLED:
                return cached, True

        res = evaluate(term, max_atp=atp)
        if res.status == EvalStatus.SETTLED:
            self._cache[h_in] = res
            self._receipts[h_in] = SporeReceipt(
                input_hash=h_in,
                output_hash=res.hash,
                atp_spent=res.atp_spent,
                status=res.status
            )
        return res, False

    def audit(self, term: Term, claimed_receipt: SporeReceipt) -> Tuple[bool, str]:
        """
        Reverse audit: Recompute term from scratch and check whether the receipt was honest.
        Returns (is_valid: bool, reason: str).
        """
        actual_in_hash = term_hash(term)
        if actual_in_hash != claimed_receipt.input_hash:
            return False, f"Input hash mismatch: expected {claimed_receipt.input_hash}, got {actual_in_hash}"

        recomputed = evaluate(term, max_atp=claimed_receipt.atp_spent + 10)
        if recomputed.hash != claimed_receipt.output_hash:
            return False, f"Output hash mismatch: claimed {claimed_receipt.output_hash}, got {recomputed.hash}"
        if recomputed.atp_spent != claimed_receipt.atp_spent:
            return False, f"ATP mismatch: claimed {claimed_receipt.atp_spent}, recomputed {recomputed.atp_spent}"
        if recomputed.status != claimed_receipt.status:
            return False, f"Status mismatch: claimed {claimed_receipt.status}, recomputed {recomputed.status}"

        return True, "AUDIT_VERIFIED_HONEST"

# --- Church Encoding Helpers ---

def church_numeral(n: int) -> Term:
    """Construct Church numeral n in SKI."""
    # 0 = K I
    if n == 0:
        return App(K, I)
    # 1 = I
    # In SKI: succ = S (S (K S) K)
    # But for cleaner expansion, Church n = \f.\x. f^n(x)
    # In pure SKI:
    # 0 = K I
    # n+1 = S (S (K S) K) n
    succ = App(App(S, App(App(S, App(K, S)), K)), I)  # standard successor
    res = CHURCH_0
    for _ in range(n):
        res = App(succ, res)
    return res

def is_church_boolean(term: Term) -> Optional[bool]:
    """Check if normal form is Church TRUE (K) or FALSE (K I)."""
    if term == K:
        return True
    if isinstance(term, App) and term.left == K and term.right == I:
        return False
    return None

if __name__ == "__main__":
    test_expr = "🌿 🖤 🤍 (🖤 🤍)"
    print(f"Expression: {test_expr}")
    t = parse(test_expr)
    print(f"Parsed AST: {t}")
    res = evaluate(t)
    print(f"Normal form: {res.normal_form}")
    print(f"Settlement badge: {res.badge()}")
