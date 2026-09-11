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
import re
import sys
from dataclasses import dataclass
from typing import Union, List, Optional, Tuple, Any

# Support deep combinator reductions, Y-combinator chains, and deeply nested ASTs
sys.setrecursionlimit(max(sys.getrecursionlimit(), 50000))

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


def parse_application(head_expr: str, argument_expr: str) -> Term:
    """
    Build `head_expr applied to argument_expr` by parsing each side on its own
    and joining the two ASTs.

    Never compose the two into one string first. Source text concatenation lets
    an endpoint disappear into its neighbours: `f"{head} ({arg})"` with an empty
    head parses as just the argument, so a replay attributes the argument's own
    behaviour to a function that was never supplied. Each side must stand alone
    as a term, or this raises.
    """
    head = parse(head_expr)
    argument = parse(argument_expr)
    return App(head, argument)

def canonical_bytes(term: Term) -> bytes:
    """Deterministic content-addressed byte representation."""
    if isinstance(term, Comb):
        return term.symbol.encode("utf-8")
    elif isinstance(term, Var):
        return f"${term.name}".encode("utf-8")
    elif isinstance(term, App):
        return b"(" + canonical_bytes(term.left) + b" " + canonical_bytes(term.right) + b")"
    raise TypeError(f"Unknown term type: {type(term)}")

TERM_ADDRESS_PROFILE = "glyph.term.v2"
# The four characters that make `canonical_bytes` ambiguous, found by searching
# for colliding pairs rather than by reading the function:
#   `$`  a Comb symbol starting with it renders exactly like a Var: Comb("$a")
#        and Var("a") both give `$a`
#   ` `  a name or symbol containing one lets the split between siblings move:
#        App(Var("a"), Var(" $a")) and App(Var("a $"), Var("a")) agree
#   ( )  a Comb symbol containing them can imitate an application outright:
#        Comb("($a $b)") and App(Var("a"), Var("b")) agree — though that witness
#        also contains `$`, and a search over 7.4M terms whose leaves carry
#        parentheses but neither a space nor a `$` found NO collision. The
#        parenthesis exclusion is therefore retained as conservatism rather than
#        demonstrated need: the search is bounded, parentheses are structural in
#        this encoding, and the cost is only that a symbol like "(x)" is not
#        vouched for.
_LEGACY_UNSAFE_CHARS = frozenset(" $()")


def _encode_term_v2(term: Term) -> bytes:
    """Prefix-free encoding: distinct terms have distinct bytes, always.

    Each node carries a tag and each leaf carries the byte length of its
    payload, so no node's encoding is a prefix of another's and the split
    between siblings cannot move.
    """
    if isinstance(term, Comb):
        payload = term.symbol.encode("utf-8")
        return b"C" + str(len(payload)).encode("ascii") + b":" + payload
    if isinstance(term, Var):
        payload = term.name.encode("utf-8")
        return b"V" + str(len(payload)).encode("ascii") + b":" + payload
    if isinstance(term, App):
        return b"A" + _encode_term_v2(term.left) + _encode_term_v2(term.right)
    raise TypeError(f"not a term: {type(term).__name__}")


def term_address(term: Term) -> str:
    """The content address of a term, qualified by its profile.

    Returns `glyph.term.v2:<64 hex>`. The profile travels with the value so a
    consumer can tell what it is holding, and so a digest under one profile can
    never be mistaken for a digest under another.
    """
    digest = hashlib.sha256(
        TERM_ADDRESS_PROFILE.encode("ascii") + b"\x00" + _encode_term_v2(term)
    ).hexdigest()
    return f"{TERM_ADDRESS_PROFILE}:{digest}"


def is_term_address(value: Any) -> bool:
    """True for a well-formed address under the CURRENT profile, and nothing else.

    A bare 64-hex string is not one: that is what a legacy `term_hash` looks
    like, and treating it as an address is the silent reinterpretation this
    profile exists to prevent.
    """
    if not isinstance(value, str) or not value.startswith(TERM_ADDRESS_PROFILE + ":"):
        return False
    digest = value[len(TERM_ADDRESS_PROFILE) + 1:]
    return len(digest) == 64 and all(c in "0123456789abcdef" for c in digest)


def in_legacy_address_domain(term: Term) -> bool:
    """A SUFFICIENT condition for `term_hash` to be unambiguous. Not a recognizer.

    True establishes uniqueness only among terms inside this restricted domain.
    It does not establish uniqueness against unrestricted ASTs: Var("a") is
    accepted here but shares legacy bytes with the excluded Comb("$a"). Both
    sides of a legacy lookup must therefore come from an independently enforced
    domain; checking only the incoming term cannot validate an unrestricted cache.
    False means this sufficient condition gives no guarantee. `parse("$")`
    produces the excluded Var("$"), which collides with the also-excluded
    Comb("$$"). This does not show ambiguity within parser-produced terms.

    An earlier version of this helper was narrower still and rejected
    `parse("ї")` and `parse("!")`, which are ordinary parser outputs: it tested
    an ASCII identifier shape instead of the property that matters. The property
    that matters is the absence of the four characters listed above, and every
    other character — Unicode letters, punctuation, the glyph aliases — is
    admitted.

    Use it to justify leaving a call site on the legacy digest, never to reject
    input on its own: a false negative here is a term this function cannot
    vouch for, not a term that is unsafe.
    """
    if isinstance(term, Comb):
        return not (_LEGACY_UNSAFE_CHARS & set(term.symbol))
    if isinstance(term, Var):
        return not (_LEGACY_UNSAFE_CHARS & set(term.name))
    if isinstance(term, App):
        return in_legacy_address_domain(term.left) and in_legacy_address_domain(term.right)
    return False


def term_hash(term: Term) -> str:
    """LEGACY content digest. Unambiguous only inside `in_legacy_address_domain`.

    Kept because it is what historical artifacts were addressed with, and
    rewriting those would destroy the evidence they are. It is not the address
    for new work: use `term_address`.
    """
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
    # Leftmost-outermost unfolding semantics. In tree substitution, eager recursion
    # can inflate AST size (tracked deterministically via peak_size and ATP budget).
    # For asymptotically optimal recursion with graph sharing (Lévy optimality)
    # that prevents exponential term blowup, see interaction.py (Lafont Interaction Combinators).
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
    """A memoized reduction, addressed under a named profile.

    `input_hash` and `output_hash` keep their names and now carry PROFILE-
    QUALIFIED addresses (`glyph.term.v2:<hex>`). A receipt written before this
    change carries bare digests under the ambiguous legacy encoding; `audit`
    refuses those by profile rather than reinterpreting them, so a legacy
    receipt is not silently accepted as a v2 one.
    """
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
        h_in = term_address(term)
        if h_in in self._cache:
            cached = self._cache[h_in]
            if cached.status == EvalStatus.SETTLED:
                return cached, True

        res = evaluate(term, max_atp=atp)
        if res.status == EvalStatus.SETTLED:
            self._cache[h_in] = res
            self._receipts[h_in] = SporeReceipt(
                input_hash=h_in,
                output_hash=term_address(res.term),
                atp_spent=res.atp_spent,
                status=res.status
            )
        return res, False

    def audit(self, term: Term, claimed_receipt: SporeReceipt) -> Tuple[bool, str]:
        """
        Reverse audit: Recompute term from scratch and check whether the receipt was honest.
        Returns (is_valid: bool, reason: str).

        Addresses are compared under the current profile. A receipt whose
        addresses are not of this profile is REFUSED, not reinterpreted: a bare
        digest was written under an encoding that cannot tell two terms apart,
        and accepting it here would carry that ambiguity forward. Such receipts
        have to be re-derived from their term.
        """
        for field, value in (("input", claimed_receipt.input_hash),
                             ("output", claimed_receipt.output_hash)):
            if not is_term_address(value):
                return False, (
                    f"Unknown address profile for {field}: {value[:24]!r} is not a "
                    f"{TERM_ADDRESS_PROFILE} address. A receipt written under the "
                    "legacy digest cannot be verified here; re-derive it.")

        actual_in_hash = term_address(term)
        if actual_in_hash != claimed_receipt.input_hash:
            return False, f"Input address mismatch: expected {claimed_receipt.input_hash}, got {actual_in_hash}"

        recomputed = evaluate(term, max_atp=claimed_receipt.atp_spent + 10)
        if term_address(recomputed.term) != claimed_receipt.output_hash:
            return False, (f"Output address mismatch: claimed {claimed_receipt.output_hash}, "
                           f"got {term_address(recomputed.term)}")
        if recomputed.atp_spent != claimed_receipt.atp_spent:
            return False, f"ATP mismatch: claimed {claimed_receipt.atp_spent}, recomputed {recomputed.atp_spent}"
        if recomputed.status != claimed_receipt.status:
            return False, f"Status mismatch: claimed {claimed_receipt.status}, recomputed {recomputed.status}"

        return True, "AUDIT_VERIFIED_HONEST"

# --- Church Encoding Helpers ---

# Church successor in pure SKI: succ = S (S (K S) K).
#
#   succ n f x
#     = S (S (K S) K) n f x
#     = ((S (K S) K) f) ((n) f) x        [S a b c -> (a c) (b c)]
#     = (((K S) f) ((K) f)) (n f) x      [S (K S) K f -> ((K S) f) (K f)]
#     = (S (K f)) (n f) x
#     = ((K f) x) ((n f) x)              [S a b c again]
#     = f (n f x)
#
# The previous definition applied this term to I before use, i.e. it built
# `S (S (K S) K) I`, which is not the successor and collapses every numeral to
# x. The reducer was never at fault; only this construction was.
CHURCH_SUCC = App(S, App(App(S, App(K, S)), K))


def church_numeral(n: int) -> Term:
    """Construct Church numeral n: the term that applies f exactly n times to x.

    `church_numeral(n) f x` reduces to `f (f (... (f x)))` with n applications,
    so `church_numeral(0) f x` is `x` and `church_numeral(3) f x` is
    `f (f (f x))`.

    The index is a non-negative int and nothing else. `bool` is refused rather
    than read as 0 or 1, since `church_numeral(True)` reads like a request no
    caller means to make; a negative index has no numeral and is refused rather
    than silently yielding zero, which is what an empty `range` used to do.
    """
    if isinstance(n, bool) or not isinstance(n, int):
        raise TypeError(
            f"church_numeral() index must be a non-negative int, not {type(n).__name__}."
        )
    if n < 0:
        raise ValueError(f"church_numeral() has no numeral for a negative index: {n}.")
    res = CHURCH_0
    for _ in range(n):
        res = App(CHURCH_SUCC, res)
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
