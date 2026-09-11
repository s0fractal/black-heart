#!/usr/bin/env python3
"""
Unit tests for glyph.py (SKIY Reduction Engine, Suspended Thunks, and SporeStore)
"""

import unittest
from glyph import (
    parse, evaluate, resume, tree_size, term_hash,
    K, I, S, Y, TRUE, FALSE, CHURCH_0, CHURCH_1,
    BudgetExceededError, EvalStatus, SporeStore, SporeReceipt, Var, App,
    term_address
)

class TestGlyphCombinators(unittest.TestCase):

    def test_identity(self):
        # 🤍 x -> x
        expr = parse("🤍 (VarA)")
        res = evaluate(expr)
        self.assertTrue(res.is_settled())
        self.assertEqual(str(res.normal_form), "VarA")
        self.assertEqual(res.atp_spent, 1)

    def test_k_drop(self):
        # 🖤 x y -> x
        expr = parse("🖤 First Second")
        res = evaluate(expr)
        self.assertTrue(res.is_settled())
        self.assertEqual(str(res.normal_form), "First")
        self.assertEqual(res.atp_spent, 1)

    def test_skk_is_identity(self):
        # 🌿 🖤 🖤 x -> (🖤 x) (🖤 x) -> x
        expr = parse("🌿 🖤 🖤 Target")
        res = evaluate(expr)
        self.assertTrue(res.is_settled())
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
            evaluate(omega, max_atp=50, raise_on_limit=True)

        # Non-raising returns SUSPENDED
        res = evaluate(omega, max_atp=50, raise_on_limit=False)
        self.assertTrue(res.is_suspended())
        self.assertEqual(res.atp_spent, 50)

    def test_deterministic_hash(self):
        expr1 = parse("🌿 🖤 🤍 Target")
        expr2 = parse("🤍 (🤍 Target)")
        res1 = evaluate(expr1)
        res2 = evaluate(expr2)
        # Both reduce to 'Target'
        self.assertEqual(str(res1.normal_form), str(res2.normal_form))
        self.assertEqual(res1.hash, res2.hash)

    def test_suspended_thunk_and_resume(self):
        # Complex term: SKK Target takes 2 steps.
        # Let us construct a 4-step reduction:
        # 🤍 (🤍 (🌿 🖤 🖤 Target))
        expr = parse("🤍 (🤍 (🌿 🖤 🖤 Target))")

        # 1. Run with 1 ATP -> pauses as SUSPENDED
        step1 = evaluate(expr, max_atp=1)
        self.assertTrue(step1.is_suspended())
        self.assertEqual(step1.atp_spent, 1)

        # 2. Resume with 1 more ATP -> still SUSPENDED
        step2 = resume(step1, additional_atp=1)
        self.assertTrue(step2.is_suspended())
        self.assertEqual(step2.atp_spent, 2)

        # 3. Resume with 5 more ATP -> reaches normal form!
        step3 = resume(step2, additional_atp=5)
        self.assertTrue(step3.is_settled())
        self.assertEqual(str(step3.normal_form), "Target")
        self.assertEqual(step3.atp_spent, 4)  # exactly 4 steps total!

        # Compare with 1-shot full evaluation
        full = evaluate(expr, max_atp=100)
        self.assertEqual(step3.hash, full.hash)
        self.assertEqual(step3.atp_spent, full.atp_spent)

    def test_spore_store_forward_cache(self):
        store = SporeStore()
        expr = parse("🌿 🖤 🖤 FastTarget")

        # First run: computed
        res1, was_cached1 = store.forward(expr, atp=100)
        self.assertFalse(was_cached1)
        self.assertTrue(res1.is_settled())
        self.assertEqual(str(res1.normal_form), "FastTarget")

        # Second run: instant cache hit O(1)
        res2, was_cached2 = store.forward(expr, atp=100)
        self.assertTrue(was_cached2)
        self.assertEqual(res1.hash, res2.hash)

    def test_spore_store_reverse_audit(self):
        store = SporeStore()
        expr = parse("🌿 🖤 🖤 AuditTarget")

        # 1. Forward run creates legitimate receipt
        res, _ = store.forward(expr, atp=100)
        # Keyed by the profile-qualified address; the legacy digest is not a key.
        receipt = store._receipts[term_address(expr)]

        # 2. Honest audit passes
        ok, msg = store.audit(expr, receipt)
        self.assertTrue(ok)
        self.assertEqual(msg, "AUDIT_VERIFIED_HONEST")

        # 3. Forged receipt (tampered output address) fails audit
        fake_receipt = SporeReceipt(
            input_hash=receipt.input_hash,
            output_hash="glyph.term.v2:" + "0" * 64,
            atp_spent=receipt.atp_spent,
            status=receipt.status
        )
        ok_fake, msg_fake = store.audit(expr, fake_receipt)
        self.assertFalse(ok_fake)
        self.assertIn("Output address mismatch", msg_fake)

        # 4. A receipt carrying a bare legacy digest is refused by PROFILE,
        #    before any comparison: the encoding it was written under cannot
        #    tell two terms apart, so it is re-derived, not reinterpreted.
        legacy_receipt = SporeReceipt(
            input_hash="0" * 64,
            output_hash="0" * 64,
            atp_spent=receipt.atp_spent,
            status=receipt.status
        )
        ok_legacy, msg_legacy = store.audit(expr, legacy_receipt)
        self.assertFalse(ok_legacy)
        self.assertIn("Unknown address profile", msg_legacy)

if __name__ == "__main__":
    unittest.main()
