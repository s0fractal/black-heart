#!/usr/bin/env python3
"""
Regression: an e-graph explanation contains only steps that replay.

Measured at 1aed5c9. `explain_equivalence` looked for a path in the proof
forest starting from `add_term(term_a)`, but for two equivalent terms that call
returns the class ROOT for both, so the search "found" an empty path at once;
an empty list is falsy, and the fallback emitted one invented step,
"Congruence Closure (Structural Identity)", from term_a straight to term_b.
Over every term with at most four leaves over S K I x whose normal form the
e-graph unified with it, 884 of 884 explanations were that single invented step,
and identical terms got one too. The path branch never produced a step.

Now an explanation is a derivation searched over the rules the e-graph was
actually saturated with, every step carries its rule, address and direction,
and it is returned only after `check_derivation` replays it. When no derivation
is found within the budget, the status says so and there are no steps:
equivalence then rests on the e-graph's union-find alone, and is labelled so.

Sections:
  A  explanations: real, replayed, or absent with a status
  B  the checker refuses forged derivations
  C  the CLI and the PDF report the status, not an invented step
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest

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

import egraph_kernel as eg
from egraph_kernel import (DerivationStatus, EGraph, EquivalenceProofStep, EquivalenceProofTree,
                           RewriteRule, STANDARD_COMBINATOR_RULES, check_derivation,
                           generate_egraph_pdf, replay_explanation)
from glyph import App, I, K, S, Var, evaluate, parse

if os.path.dirname(os.path.abspath(eg.__file__)) != _HERE:
    raise ImportError(f"egraph_kernel resolved to {eg.__file__}, outside {_HERE}")

FAKE = "Congruence Closure (Structural Identity)"
RULES = {r.name: r for r in STANDARD_COMBINATOR_RULES}


def saturated(*terms, rules=STANDARD_COMBINATOR_RULES):
    g = EGraph()
    for t in terms:
        g.add_term(parse(t) if isinstance(t, str) else t)
    g.saturate(rules, max_iterations=6, fuel_atp=2000)
    return g


def step(n, a, b, rule, address=(), direction="forward"):
    return EquivalenceProofStep(step_num=n, from_expr=a, to_expr=b, justification=rule,
                                address=tuple(address), direction=direction)


def small_terms(max_leaves):
    by = {1: [S, K, I, Var("x")]}
    for n in range(2, max_leaves + 1):
        by[n] = [App(l, r) for k in range(1, n) for l in by[k] for r in by[n - k]]
    return [t for n in by for t in by[n]]


class ExplanationTest(unittest.TestCase):
    """Section A."""

    def assertChecked(self, g, a, b, proof):
        self.assertTrue(proof.is_equivalent)
        self.assertEqual(proof.derivation_status, DerivationStatus.CHECKED)
        self.assertIsNone(check_derivation(parse(a) if isinstance(a, str) else a,
                                           parse(b) if isinstance(b, str) else b,
                                           proof.proof_steps, g.theory))
        self.assertNotIn(FAKE, [s.justification for s in proof.proof_steps])

    def test_A1_the_audits_example_is_a_real_derivation(self):
        g = saturated("S K K x", "x")
        proof = g.explain_equivalence(parse("S K K x"), parse("x"))
        self.assertChecked(g, "S K K x", "x", proof)
        self.assertGreaterEqual(len(proof.proof_steps), 2)
        self.assertEqual(parse(proof.proof_steps[0].from_expr), parse("S K K x"))
        self.assertEqual(parse(proof.proof_steps[-1].to_expr), parse("x"))

    def test_A2_identical_terms_need_no_step(self):
        g = saturated("S K K x")
        proof = g.explain_equivalence(parse("S K K x"), parse("S K K x"))
        self.assertChecked(g, "S K K x", "S K K x", proof)
        self.assertEqual(proof.proof_steps, [])

    def test_A3_every_unified_term_in_a_generated_space_gets_a_checked_derivation(self):
        """At 1aed5c9 every one of these was the single invented step."""
        unified = 0
        for t in small_terms(3):
            r = evaluate(t, max_atp=200)
            if not r.is_settled() or r.term == t:
                continue
            g = saturated(t, r.term)
            proof = g.explain_equivalence(t, r.term)
            if not proof.is_equivalent:
                continue
            unified += 1
            with self.subTest(term=str(t)):
                self.assertChecked(g, t, r.term, proof)
        self.assertGreater(unified, 50)

    def test_A4_a_valley_goes_down_and_back_up(self):
        g = saturated("K x (S S)", "I x")
        proof = g.explain_equivalence(parse("K x (S S)"), parse("I x"))
        self.assertChecked(g, "K x (S S)", "I x", proof)
        self.assertIn("reverse", [s.direction for s in proof.proof_steps])

    def test_A5_not_equivalent_has_no_steps(self):
        g = saturated("K", "S")
        proof = g.explain_equivalence(parse("K"), parse("S"))
        self.assertFalse(proof.is_equivalent)
        self.assertEqual(proof.derivation_status, DerivationStatus.NOT_EQUIVALENT)
        self.assertEqual(proof.proof_steps, [])

    def test_A6_no_derivation_within_budget_is_said_not_invented(self):
        g = saturated("S K K x", "x")
        proof = g.explain_equivalence(parse("S K K x"), parse("x"), max_terms=1)
        self.assertTrue(proof.is_equivalent, "the e-graph did unify them")
        self.assertEqual(proof.derivation_status, DerivationStatus.NOT_FOUND_WITHIN_BUDGET)
        self.assertEqual(proof.proof_steps, [])

    def test_A7_a_custom_rule_the_egraph_used_can_justify_a_step(self):
        custom = STANDARD_COMBINATOR_RULES + [
            RewriteRule.from_strings("RULE-DISTRIB", "S (K (S I)) (K I) x", "I x")]
        g = saturated("S (K (S I)) (K I) x", "x", rules=custom)
        proof = g.explain_equivalence(parse("S (K (S I)) (K I) x"), parse("x"))
        self.assertChecked(g, "S (K (S I)) (K I) x", "x", proof)

    def test_A9_explain_never_returns_steps_its_checker_refuses(self):
        """If the search ever produced a bad derivation, it must not be shown."""
        from unittest import mock
        forged = [step(1, "🌿 🖤 🖤 x", "x", FAKE)]
        g = saturated("S K K x", "x")
        with mock.patch.object(eg, "find_derivation", return_value=forged):
            proof = g.explain_equivalence(parse("S K K x"), parse("x"))
        self.assertEqual(proof.derivation_status, DerivationStatus.NOT_FOUND_WITHIN_BUDGET)
        self.assertEqual(proof.proof_steps, [])

    def test_A8_to_dict_carries_the_status_and_each_steps_site(self):
        g = saturated("S K K x", "x")
        d = g.explain_equivalence(parse("S K K x"), parse("x")).to_dict()
        self.assertEqual(d["derivation_status"], "CHECKED")
        for s in d["steps"]:
            self.assertIn("address", s)
            self.assertIn(s["direction"], ("forward", "reverse"))


class CheckerTest(unittest.TestCase):
    """Section B: `check_derivation` is what an explanation must pass."""

    def refuse(self, a, b, steps, rules=RULES):
        reason = check_derivation(parse(a), parse(b), steps, rules)
        self.assertIsNotNone(reason, "a forged derivation was accepted")
        return reason

    def test_B0_a_genuine_derivation_is_accepted(self):
        steps = [step(1, "S K K x", "K x (K x)", "RULE-S"), step(2, "K x (K x)", "x", "RULE-K")]
        self.assertIsNone(check_derivation(parse("S K K x"), parse("x"), steps, RULES))

    def test_B1_the_old_invented_step_is_refused(self):
        self.assertIn("rule", self.refuse("S K K x", "x", [step(1, "S K K x", "x", FAKE)]))

    def test_B2_the_right_rule_at_the_wrong_address_is_refused(self):
        self.refuse("S K K x", "x", [step(1, "S K K x", "K x (K x)", "RULE-S", address=(0,)),
                                     step(2, "K x (K x)", "x", "RULE-K")])

    def test_B3_a_wrong_rule_name_is_refused(self):
        self.refuse("S K K x", "x", [step(1, "S K K x", "K x (K x)", "RULE-K"),
                                     step(2, "K x (K x)", "x", "RULE-K")])

    def test_B4_a_broken_chain_is_refused_even_when_it_ends_right(self):
        """Step 2 is a valid rewrite and ends at the target; only the link is wrong."""
        self.assertIn("starts at", self.refuse(
            "S K K x", "x", [step(1, "S K K x", "K x (K x)", "RULE-S"),
                             step(2, "K x x", "x", "RULE-K")]))

    def test_B5_a_derivation_ending_elsewhere_is_refused(self):
        self.refuse("S K K x", "x", [step(1, "S K K x", "K x (K x)", "RULE-S")])

    def test_B6_a_reverse_step_labelled_forward_is_refused(self):
        self.refuse("x", "I x", [step(1, "x", "I x", "RULE-I", direction="forward")])
        self.assertIsNone(check_derivation(parse("x"), parse("I x"),
                                           [step(1, "x", "I x", "RULE-I", direction="reverse")], RULES))

    def test_B7_a_rule_outside_the_theory_is_refused(self):
        rogue = {"RULE-ROGUE": RewriteRule.from_strings("RULE-ROGUE", "x", "K")}
        self.assertIsNone(check_derivation(parse("S"), parse("K"),
                                           [step(1, "S", "K", "RULE-ROGUE")], rogue))
        self.refuse("S", "K", [step(1, "S", "K", "RULE-ROGUE")])

    def test_B8_an_unknown_direction_and_an_empty_proof_of_a_difference_are_refused(self):
        self.refuse("I x", "x", [step(1, "I x", "x", "RULE-I", direction="sideways")])
        self.refuse("I x", "x", [])

    def test_B10_a_repeated_pattern_variable_must_bind_one_term(self):
        dup = {"RULE-DUP": RewriteRule.from_strings("RULE-DUP", "K x x", "x")}
        self.assertIsNone(check_derivation(parse("K a a"), parse("a"), [step(1, "K a a", "a", "RULE-DUP")], dup))
        self.refuse("K a b", "a", [step(1, "K a b", "a", "RULE-DUP")], rules=dup)

    def test_B9_one_name_cannot_mean_two_rules_in_one_egraph(self):
        g = saturated("I x")
        with self.assertRaises(ValueError):
            g.saturate([RewriteRule.from_strings("RULE-I", "x", "I x")], max_iterations=1)


class ConsumerTest(unittest.TestCase):
    """Section C."""

    def cli(self, *args):
        return subprocess.run([sys.executable, "-B", os.path.join(_HERE, "cli.py"), *args],
                              cwd=_HERE, capture_output=True, text=True, timeout=300)

    def test_C1_cli_explain_reports_a_checked_derivation(self):
        r = self.cli("egraph", "explain", "S K K x", "x")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Derivation:    CHECKED", r.stdout)
        self.assertNotIn("Structural Identity", r.stdout)

    def test_C2_cli_explain_of_different_terms(self):
        r = self.cli("egraph", "explain", "K", "S")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("NOT_EQUIVALENT", r.stdout)

    def test_C3_the_pdf_prints_the_status_not_an_invented_step(self):
        g = saturated("S K K x", "x")
        checked = g.explain_equivalence(parse("S K K x"), parse("x"))
        unexplained = g.explain_equivalence(parse("S K K x"), parse("x"), max_terms=1)
        with tempfile.TemporaryDirectory() as d:
            a = generate_egraph_pdf(g, os.path.join(d, "a.pdf"), sample_proof=checked)
            b = generate_egraph_pdf(g, os.path.join(d, "b.pdf"), sample_proof=unexplained)
        self.assertIn(b"CHECKED", a)
        self.assertNotIn(b"Structural Identity", a)
        self.assertIn(b"no checked derivation", b)
        self.assertNotIn(b"Derivation Path", b)


class ExportReplayTest(unittest.TestCase):
    """Section D: review E1 on PR #21. The exporter replays the explanation it
    is given; it does not read the explanation's status."""

    def pdf(self, g, proof):
        with tempfile.TemporaryDirectory() as d:
            return generate_egraph_pdf(g, os.path.join(d, "p.pdf"), sample_proof=proof)

    def test_D1_a_mutated_endpoint_and_last_step_is_not_credited(self):
        """The reviewer's probe: a genuine CHECKED proof of I x = x, retargeted to y."""
        g = saturated("I x", "x")
        proof = g.explain_equivalence(parse("I x"), parse("x"))
        self.assertEqual(proof.derivation_status, DerivationStatus.CHECKED)
        proof.term_b = "y"
        proof.proof_steps[-1].to_expr = "y"
        blob = self.pdf(g, proof)
        self.assertNotIn(b"Derivation: CHECKED", blob)
        self.assertNotIn(b"=== y", blob)
        self.assertIn(b"NOT credited", blob)
        self.assertEqual(replay_explanation(g, proof)[0], DerivationStatus.INVALID)

    def test_D2_a_mutated_middle_step_is_not_credited(self):
        g = saturated("S K K x", "x")
        proof = g.explain_equivalence(parse("S K K x"), parse("x"))
        proof.proof_steps[0].justification = "RULE-K"
        self.assertNotIn(b"Derivation: CHECKED", self.pdf(g, proof))
        self.assertEqual(replay_explanation(g, proof)[0], DerivationStatus.INVALID)

    def test_D3_a_hand_built_CHECKED_object_is_not_credited(self):
        g = saturated("K", "S")
        forged = EquivalenceProofTree(term_a="🖤", term_b="🌿", is_equivalent=True,
                                      proof_steps=[step(1, "🖤", "🌿", FAKE)],
                                      derivation_status=DerivationStatus.CHECKED)
        blob = self.pdf(g, forged)
        self.assertNotIn(b"Derivation: CHECKED", blob)
        self.assertIn(b"NOT credited", blob)

    def test_D4_a_forged_equivalence_without_steps_is_not_credited(self):
        g = saturated("K", "S")
        forged = EquivalenceProofTree(term_a="🖤", term_b="🌿", is_equivalent=True, proof_steps=[],
                                      derivation_status=DerivationStatus.NOT_FOUND_WITHIN_BUDGET)
        blob = self.pdf(g, forged)
        self.assertNotIn(b"Equivalent in the e-graph", blob)
        self.assertIn(b"NOT credited", blob)
        self.assertEqual(replay_explanation(g, forged)[0], DerivationStatus.NOT_EQUIVALENT)

    def test_D5_genuine_explanations_are_still_credited(self):
        for a, b in (("S K K x", "x"), ("K x (S S)", "I x"), ("S K K x", "S K K x")):
            with self.subTest(a=a, b=b):
                g = saturated(a, b)
                proof = g.explain_equivalence(parse(a), parse(b))
                self.assertEqual(replay_explanation(g, proof)[0], DerivationStatus.CHECKED)
                self.assertIn(b"Derivation: CHECKED", self.pdf(g, proof))

    def test_D6_replaying_adds_nothing_to_the_egraph(self):
        g = saturated("K", "S")
        before = (len(g.hashcons), len(g.classes))
        replay_explanation(g, EquivalenceProofTree(term_a="K I", term_b="S", is_equivalent=True))
        self.assertEqual((len(g.hashcons), len(g.classes)), before)


if __name__ == "__main__":
    unittest.main()
