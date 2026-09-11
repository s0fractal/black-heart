#!/usr/bin/env python3
"""
Regression: a local section is glued only if its own computation holds.

Measured at 1aed5c9. `verify_descent` meant to check each section's term
against its declared normal form, but compared the evaluation status with
"NORMAL_FORM", which glyph never produces (it has SETTLED and SUSPENDED), inside
`except Exception: pass`. Every one of these glued, with the same section in two
overlapping charts so the cocycle check agreed:

    term settles to x, section declares y        GLUED
    malformed term "(S K"                        GLUED
    Y I, which never settles                     GLUED
    10 steps in a context whose budget is 5      GLUED  (the check also had a floor of 50)
    empty term / empty normal form               GLUED
    verified_steps 0 for a 2-step term           GLUED

Changing only the status name would have been wrong too: the branch compared
`str(result)` with the declared text, and `S K K (K I)` renders as `🖤 🤍`, so the
demo's own true sections (`K I`) would have been refused.

Sections:
  A  each false or uncheckable section is refused, with its reason
  B  true sections still glue: both spellings, free variables, exact budget
  C  the real callers: CLI glue and obstruct, the example demo
"""
from __future__ import annotations

import os
import subprocess
import sys
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

import sheaf_kernel as sh
from sheaf_kernel import (EpistemicContext, EpistemicSheafKernel, LocalSection,
                          SectionStatus, local_computation_failure)

if os.path.dirname(os.path.abspath(sh.__file__)) != _HERE:
    raise ImportError(f"sheaf_kernel resolved to {sh.__file__}, outside {_HERE}")

TEN_I = "I (" * 10 + "x" + ")" * 10   # reaches x in exactly 10 steps


def descent(term, nf, steps=1, budget=100, status=SectionStatus.LOCAL_THEOREM, second=None):
    """Two overlapping charts. By default both hold the same section, so only
    the local check can refuse; `second` replaces the second chart's (term, nf, steps)."""
    k = EpistemicSheafKernel()
    c1 = EpistemicContext.create("Alpha", ["d1", "d2"], budget)
    c2 = EpistemicContext.create("Beta", ["d2", "d3"], budget)
    k.register_context(c1)
    k.register_context(c2)
    k.register_section(LocalSection.create(c1, "claim", term, nf, steps, status))
    t2, n2, s2 = second or (term, nf, steps)
    k.register_section(LocalSection.create(c2, "claim", t2, n2, s2, status))
    return k.verify_descent("claim", [c1, c2])


class RefusedTest(unittest.TestCase):
    """Section A: each of these glued at 1aed5c9."""

    def assertRefused(self, report, *fragments):
        self.assertFalse(report.is_gluing_admissible)
        self.assertIsNone(report.global_section)
        for f in fragments:
            self.assertIn(f, report.rejection_reason)

    def test_A1_a_false_normal_form_is_refused(self):
        self.assertRefused(descent("S K K x", "y", 2),
                           "Computational divergence", "settles to 'x'", "declares 'y'")

    def test_A2_a_malformed_term_is_refused(self):
        self.assertRefused(descent("(S K", "x"), "its term", "does not parse")

    def test_A3_a_malformed_normal_form_is_refused(self):
        self.assertRefused(descent("I x", "(x"), "its normal form", "does not parse")

    def test_A4_a_term_that_never_settles_is_refused(self):
        self.assertRefused(descent("Y I", "x"), "does not settle")

    def test_A5_the_context_budget_is_the_limit_with_no_floor(self):
        """10 steps: budget 9 is refused, although 9 < 50."""
        self.assertRefused(descent(TEN_I, "x", steps=9, budget=9),
                           "does not settle within the context budget of 9 ATP")

    def test_A6_an_empty_term_or_normal_form_is_refused(self):
        self.assertRefused(descent("", "x"), "declares no term")
        self.assertRefused(descent("S K K x", "", 2), "declares no normal form")

    def test_A7_understated_steps_are_refused(self):
        self.assertRefused(descent("S K K x", "x", 1), "claims 1 verified steps; its term takes 2")
        self.assertRefused(descent("S K K x", "x", 0), "claims 0 verified steps")

    def test_A8_no_status_exempts_a_section(self):
        self.assertRefused(descent("S K K x", "y", 2, status=SectionStatus.LOCAL_AXIOM),
                           "Computational divergence")

    def test_A9_one_false_chart_among_true_ones_is_named(self):
        report = descent("S K K x", "x", 2, second=("I x", "y", 1))
        self.assertRefused(report, "context 'Beta'", "declares 'y'")

    def test_A10_the_predicate_function_agrees(self):
        ctx = EpistemicContext.create("C", ["d"], 100)
        ok = LocalSection.create(ctx, "c", "S K K x", "x", 2)
        bad = LocalSection.create(ctx, "c", "S K K x", "y", 2)
        self.assertIsNone(local_computation_failure(ok, ctx))
        self.assertIn("divergence", local_computation_failure(bad, ctx))


class HoldsTest(unittest.TestCase):
    """Section B: the check refuses false sections, not true ones."""

    def assertGlued(self, report):
        self.assertTrue(report.is_gluing_admissible, report.rejection_reason)
        self.assertEqual(report.h1_dimension, 0)
        self.assertIsNotNone(report.global_section)

    def test_B1_a_true_section_glues(self):
        self.assertGlued(descent("S K K x", "x", 2))

    def test_B2_the_normal_form_is_compared_as_a_term_not_as_text(self):
        """`S K K (K I)` renders as `🖤 🤍`; both spellings of it hold."""
        self.assertGlued(descent("S K K (K I)", "K I", 2))
        self.assertGlued(descent("S K K (K I)", "🖤 🤍", 2))
        self.assertGlued(descent("S K K (K I)", "(K) (I)", 2))

    def test_B3_free_variables_are_terms(self):
        self.assertGlued(descent("K True False", "True", 1))

    def test_B4_exactly_the_budget_is_enough(self):
        self.assertGlued(descent(TEN_I, "x", steps=10, budget=10))

    def test_B5_overstated_steps_are_allowed(self):
        """verified_steps is checked as an upper bound, and says so."""
        self.assertGlued(descent("S K K x", "x", 5))

    def test_B6_an_obstructed_section_is_still_refused_as_obstructed(self):
        report = descent("I", "K", 0, status=SectionStatus.OBSTRUCTED)
        self.assertFalse(report.is_gluing_admissible)
        self.assertIn("obstructed", report.rejection_reason.lower())


class CallerTest(unittest.TestCase):
    """Section C: the real callers still behave as they claim."""

    def run_cli(self, *args):
        return subprocess.run([sys.executable, "-B", os.path.join(_HERE, "cli.py"), *args],
                              cwd=_HERE, capture_output=True, text=True, timeout=300)

    def test_C1_cli_glue_is_admissible(self):
        r = self.run_cli("sheaf", "glue")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("SUCCESS (ADMISSIBLE)", r.stdout)

    def test_C2_cli_obstruct_is_refused_by_the_cocycle_not_the_local_check(self):
        r = self.run_cli("sheaf", "obstruct")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("does not hold", r.stdout)
        self.assertIn("H^1", r.stdout)

    def test_C3_the_example_demo_glues(self):
        r = subprocess.run([sys.executable, "-B", os.path.join(_HERE, "examples", "sheaf_demo.py")],
                           cwd=_HERE, capture_output=True, text=True, timeout=300,
                           env=dict(os.environ, PYTHONPATH=_HERE))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Gluing Admissible: \033[1;32mTrue", r.stdout)


if __name__ == "__main__":
    unittest.main()
