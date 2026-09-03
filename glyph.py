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

@dataclass
class EvalResult:
    normal_form: Term
    steps: int
    atp_spent: int
    peak_size: int
    hash: str

    def short_hash(self) -> str:
        return self.hash[:12]

    def badge(self) -> str:
        return f"⚓⟨atp:{self.atp_spent}, size:{tree_size(self.normal_form)}, hash:{self.short_hash()}⟩"

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

def evaluate(term: Term, max_atp: int = 100_000) -> EvalResult:
    """
    Evaluate term to normal form using leftmost-outermost order with ATP budget.
    """
    curr = term
    steps = 0
    peak_sz = tree_size(curr)

    while True:
        curr_sz = tree_size(curr)
        if curr_sz > peak_sz:
            peak_sz = curr_sz

        next_term, did_reduce = reduce_step(curr)
        if not did_reduce:
            # Normal form reached!
            h = term_hash(curr)
            return EvalResult(
                normal_form=curr,
                steps=steps,
                atp_spent=steps,
                peak_size=peak_sz,
                hash=h
            )

        steps += 1
        if steps > max_atp:
            raise BudgetExceededError(f"Evaluation exceeded ATP budget ({max_atp} ATP)")

        curr = next_term

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
