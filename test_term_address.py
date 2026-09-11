#!/usr/bin/env python3
"""
Regression: a term's address identifies the term, and says which profile it is in.

`canonical_bytes` renders a variable as `$name` and an application as
`(left right)`. The split between siblings is recoverable only while no name
contains a space or a `$`:

    App(Var('a'), Var('b $c'))   ->  ($a $b $c)
    App(Var('a $b'), Var('c'))   ->  ($a $b $c)

`Var` and `App` are public constructors, so a caller can build both. Measured on
the base commit, with those two terms:

    SporeStore.forward(B)                -> A's normal form, cached=True
    SporeStore.audit(B, receipt_for_A)   -> (True, 'AUDIT_VERIFIED_HONEST')

A cache served a wrong answer and a receipt certified a term it was not about.

What the sections pin:

  A  the collision, and that the new profile separates the pair
  B  the cache and the receipt, the two measured consequences
  C  profiles do not cross: a bare legacy digest is refused rather than read as
     an address, and neither profile's value satisfies the other
  D  the legacy domain is checkable, and text is inside it, so the sites that
     stayed on the legacy digest can say why

What is NOT claimed: that every consumer of `term_hash` was exploitable. The
ones that were are section B; the rest are listed in
`docs/TERM-ADDRESS-USE-SITES.md` as exposure, with the reason each was left.
"""
from __future__ import annotations

import os
import sys
import unittest

# Same import guard, and same reason, as test_retirement_binding.py.
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path[:1]:
    sys.path.insert(0, _HERE)
for _name, _mod in list(sys.modules.items()):
    _file = getattr(_mod, "__file__", None)
    if not _file:
        continue
    if os.path.dirname(os.path.abspath(_file)) != _HERE and \
            os.path.exists(os.path.join(_HERE, os.path.basename(_file))):
        del sys.modules[_name]

import glyph
from glyph import (
    App, Var, Comb, K, I, S, EvalStatus, SporeStore, SporeReceipt,
    canonical_bytes, term_hash, term_address, is_term_address,
    in_legacy_address_domain, parse, evaluate, TERM_ADDRESS_PROFILE,
)

if os.path.dirname(os.path.abspath(glyph.__file__)) != _HERE:
    raise ImportError(f"glyph resolved to {glyph.__file__}, outside {_HERE}")

A = App(Var("a"), Var("b $c"))
B = App(Var("a $b"), Var("c"))


class LegacyCollisionTest(unittest.TestCase):

    def test_A1_the_collision_is_real_and_recorded(self):
        self.assertNotEqual(A, B)
        self.assertEqual(canonical_bytes(A), canonical_bytes(B))
        self.assertEqual(term_hash(A), term_hash(B))

    def test_A2_the_profile_separates_them(self):
        self.assertNotEqual(term_address(A), term_address(B))
        self.assertTrue(is_term_address(term_address(A)))

    def test_A3_the_encoding_is_prefix_free(self):
        seen = {}
        for label, t in (
            ("var a", Var("a")),
            ("var ab", Var("ab")),
            ("comb with a var payload", Comb("ab")),
            ("a applied to b", App(Var("a"), Var("b"))),
            ("nested left", App(App(Var("a"), Var("b")), Var("c"))),
            ("nested right", App(Var("a"), App(Var("b"), Var("c")))),
            ("empty name", Var("")),
            ("colon in a name", Var("a:1")),
            ("digits that could read as a length", Var("2:x")),
            # Without the leaf length prefixes these two encode identically.
            ("tag inside the left name", App(Var("aV"), Var("b"))),
            ("tag inside the right name", App(Var("a"), Var("Vb"))),
            ("the collision pair, left", A),
            ("the collision pair, right", B),
        ):
            addr = term_address(t)
            self.assertNotIn(addr, seen, f"{label} collides with {seen.get(addr)}")
            seen[addr] = label


class MeasuredConsequencesTest(unittest.TestCase):
    """The two places the collision actually produced a wrong answer."""

    def setUp(self):
        self.store = SporeStore()

    def test_B1_the_cache_no_longer_answers_for_another_term(self):
        first, cached_first = self.store.forward(A, 1000)
        second, cached_second = self.store.forward(B, 1000)
        self.assertFalse(cached_first)
        self.assertFalse(cached_second, "B was served from A's cache entry")
        self.assertEqual(str(first.term), str(A))
        self.assertEqual(str(second.term), str(B))

    def test_B2_the_cache_still_caches(self):
        """A fix that simply never caches would pass B1 and fail the point."""
        expr = parse("🌿 🖤 🖤 Target")
        first, cached_first = self.store.forward(expr, 100)
        again, cached_again = self.store.forward(expr, 100)
        self.assertFalse(cached_first)
        self.assertTrue(cached_again)
        self.assertEqual(first.hash, again.hash)

    def test_B3_a_receipt_does_not_certify_another_term(self):
        self.store.forward(A, 1000)
        receipt = self.store._receipts[term_address(A)]
        ok, why = self.store.audit(B, receipt)
        self.assertFalse(ok, "a receipt for A verified against B")
        self.assertIn("mismatch", why)

    def test_B4_an_honest_receipt_still_audits(self):
        self.store.forward(A, 1000)
        receipt = self.store._receipts[term_address(A)]
        self.assertEqual(self.store.audit(A, receipt), (True, "AUDIT_VERIFIED_HONEST"))


class ProfilesDoNotCrossTest(unittest.TestCase):

    def setUp(self):
        self.store = SporeStore()
        self.store.forward(A, 1000)
        self.receipt = self.store._receipts[term_address(A)]

    def test_C1_a_legacy_digest_is_not_an_address(self):
        self.assertFalse(is_term_address(term_hash(A)))
        self.assertFalse(is_term_address("0" * 64))
        self.assertFalse(is_term_address("some.other.profile:" + "0" * 64))
        self.assertFalse(is_term_address(None))

    def test_C2_a_legacy_receipt_is_refused_by_profile(self):
        legacy = SporeReceipt(input_hash=term_hash(A), output_hash=term_hash(A),
                              atp_spent=self.receipt.atp_spent, status=EvalStatus.SETTLED)
        ok, why = self.store.audit(A, legacy)
        self.assertFalse(ok)
        self.assertIn("Unknown address profile", why)
        self.assertIn("re-derive", why)

    def test_C3_an_unknown_profile_is_refused_not_guessed(self):
        import dataclasses
        foreign = dataclasses.replace(
            self.receipt, input_hash="glyph.term.v3:" + "a" * 64)
        ok, why = self.store.audit(A, foreign)
        self.assertFalse(ok)
        self.assertIn("Unknown address profile", why)

    def test_C4_a_cache_keyed_under_one_profile_does_not_serve_another(self):
        """A legacy-keyed entry cannot satisfy a request under the new profile."""
        poisoned = SporeStore()
        poisoned._cache[term_hash(A)] = evaluate(A, max_atp=100)
        result, cached = poisoned.forward(A, 100)
        self.assertFalse(cached, "a legacy cache key satisfied a v2 lookup")

    def test_C5_the_address_carries_its_profile(self):
        self.assertTrue(term_address(A).startswith(TERM_ADDRESS_PROFILE + ":"))
        self.assertEqual(self.receipt.input_hash, term_address(A))


class LegacyDomainTest(unittest.TestCase):
    """The sites that stayed on the legacy digest can state why."""

    def test_D1_text_is_inside_the_domain(self):
        for text in ("🌿 🖤 🖤 Target", "🤍 x", "🖤 Truth Mirage", "a b $c", "a$b c"):
            with self.subTest(text=text):
                self.assertTrue(in_legacy_address_domain(parse(text)))

    def test_D2_the_collision_pair_is_outside_it(self):
        self.assertFalse(in_legacy_address_domain(A))
        self.assertFalse(in_legacy_address_domain(B))

    def test_D3_parse_cannot_build_the_collision(self):
        """`$` is tokenized on its own, so a name never absorbs one."""
        self.assertNotEqual(term_hash(parse("a b $c")), term_hash(parse("a$b c")))

    def test_D4_combinators_are_inside_the_domain(self):
        for t in (K, I, S, App(App(S, K), K), parse("🌿 🖤 🤍")):
            self.assertTrue(in_legacy_address_domain(t))

    def test_D5_a_name_with_a_space_or_a_dollar_is_outside(self):
        for name in ("b $c", "a b", "$x", "a$"):
            with self.subTest(name=name):
                self.assertFalse(in_legacy_address_domain(Var(name)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
