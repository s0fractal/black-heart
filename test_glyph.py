#!/usr/bin/env python3
"""
Unit tests for glyph.py (SKIY Reduction Engine)
"""

import unittest
from glyph import (
    parse, evaluate, tree_size, term_hash,
    K, I, S, Y, TRUE, FALSE, CHURCH_0, CHURCH_1,
    BudgetExceededError, Var, App
)

class TestGlyphCombinators(unittest.TestCase):

    def test_identity(self):
        # 🤍 x -> x
        expr = parse("🤍 (VarA)")
        res = evaluate(expr)
        self.assertEqual(str(res.normal_form), "VarA")
        self.assertEqual(res.atp_spent, 1)

    def test_k_drop(self):
        # 🖤 x y -> x
        expr = parse("🖤 First Second")
        res = evaluate(expr)
        self.assertEqual(str(res.normal_form), "First")
        self.assertEqual(res.atp_spent, 1)

    def test_skk_is_identity(self):
        # 🌿 🖤 🖤 x -> (🖤 x) (🖤 x) -> x
        expr = parse("🌿 🖤 🖤 Target")
        res = evaluate(expr)
        self.assertEqual(str(res.normal_form), "Target")
        self.assertEqual(res.atp_spent, 2)

    def test_church_booleans(self):
        # TRUE a b -> a
        expr_true = parse("🖤 Left Right")
        res_true = evaluate(expr_true)
        self.assertEqual(str(res_true.normal_form), "Left")

        # FALSE a b -> b  (FALSE = 🖤 🤍)
        expr_false = parse("(🖤 🤍) Left Right")
        res_false = evaluate(expr_false)
        self.assertEqual(str(res_false.normal_form), "Right")

    def test_omega_combinator_bounded(self):
        # Omega: (S I I) (S I I) diverges infinitely!
        # In glyphs: (🌿 🤍 🤍) (🌿 🤍 🤍)
        omega = parse("(🌿 🤍 🤍) (🌿 🤍 🤍)")
        with self.assertRaises(BudgetExceededError):
            evaluate(omega, max_atp=50)

    def test_deterministic_hash(self):
        expr1 = parse("🌿 🖤 🤍 Target")
        expr2 = parse("🤍 (🤍 Target)")
        res1 = evaluate(expr1)
        res2 = evaluate(expr2)
        # Both reduce to 'Target'
        self.assertEqual(str(res1.normal_form), str(res2.normal_form))
        self.assertEqual(res1.hash, res2.hash)

if __name__ == "__main__":
    unittest.main()
