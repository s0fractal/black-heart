#!/usr/bin/env python3
"""
Regression for two small, unrelated defects that share one shape: a value was
described by its label rather than by what it actually is.

S2a — `glyph.church_numeral(n)` returned a term that reduces to `x` for every
n. The builder pre-applied the SKI successor to `I`, so no numeral ever counted
anything. Nothing consumed it, and no test applied a numeral to arguments; the
suite only ever checked that a term came back.

S2b — the `cli.py` REPL unpacked `evaluate()` into three values, but the
library has returned an `EvalResult` object since the first commit. Every
expression printed `cannot unpack non-iterable EvalResult object`, so the REPL
had never evaluated anything.

S2b (same shape, runner side) — the embedded polyglot runner carries its OWN
engine whose `evaluate` returns a tuple. `579150f` applied the host-side fix
(`.term`) to that template, so every generated document's self-audit raised
`'tuple' object has no attribute 'term'` and reported its claims as failed.

The tests below therefore refuse to accept "a term came back", "the process
exited", or "the runner printed something" as evidence:

  A  numerals are applied to fresh symbols and compared to f^n(x) as terms
  B  the REPL is driven as a real process over stdin/stdout
  C  a generated document is executed, and both a true and a false claim are
     checked, so GREEN cannot come from a broken evaluator

Keys, temporary files and generated documents are per-test and removed.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

# Import hygiene: generated runners prepend a hard-coded absolute checkout path
# to sys.path, so a suite that ran earlier can leave project modules resolved
# against another clone. Same guard, and same reason, as in
# `test_retirement_binding.py`; the underlying defect stays open.
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
from glyph import App, Var, EvalStatus, evaluate, church_numeral

if os.path.dirname(os.path.abspath(glyph.__file__)) != _HERE:
    raise ImportError(f"glyph resolved to {glyph.__file__}, outside {_HERE}")

ANSI = re.compile(r"\x1b\[[0-9;]*m")


def plain(text: str) -> str:
    return ANSI.sub("", text)


def applied(n: int, f: Var, x: Var):
    """The term f^n(x), built directly, with no help from the module under test."""
    term = x
    for _ in range(n):
        term = App(f, term)
    return term


class ChurchNumeralTest(unittest.TestCase):
    """A Church numeral is a counting function, so it is tested by counting."""

    def setUp(self):
        self.f, self.x = Var("f"), Var("x")

    def reduce_applied(self, numeral):
        return evaluate(App(App(numeral, self.f), self.x), max_atp=20_000)

    def test_A1_numerals_zero_to_five_count(self):
        for n in range(6):
            with self.subTest(n=n):
                res = self.reduce_applied(church_numeral(n))
                self.assertEqual(res.status, EvalStatus.SETTLED)
                self.assertEqual(res.term, applied(n, self.f, self.x),
                                 f"church_numeral({n}) f x reduced to {res.term}")

    def test_A2_numerals_are_distinct_as_functions(self):
        """Distinct terms are not enough: they must differ where it is observed."""
        seen = {}
        for n in range(6):
            form = str(self.reduce_applied(church_numeral(n)).term)
            self.assertNotIn(form, seen, f"n={n} and n={seen.get(form)} agree on f x")
            seen[form] = n

    def test_A3_successor_advances_by_one(self):
        for n in range(5):
            with self.subTest(n=n):
                succ_n = App(glyph.CHURCH_SUCC, church_numeral(n))
                res = evaluate(App(App(succ_n, self.f), self.x), max_atp=20_000)
                self.assertEqual(res.status, EvalStatus.SETTLED)
                self.assertEqual(res.term, applied(n + 1, self.f, self.x))

    def test_A4_zero_and_one_keep_their_documented_forms(self):
        """The two forms the module states outright, unchanged by this repair."""
        self.assertEqual(church_numeral(0), glyph.CHURCH_0)
        self.assertEqual(church_numeral(0), App(glyph.K, glyph.I))
        self.assertEqual(self.reduce_applied(glyph.CHURCH_1).term, App(self.f, self.x))
        self.assertIs(glyph.is_church_boolean(glyph.K), True)
        self.assertIs(glyph.is_church_boolean(App(glyph.K, glyph.I)), False)

    def test_A5_index_contract_is_stated_not_guessed(self):
        for bad, exc in ((-1, ValueError), (-42, ValueError),
                         (True, TypeError), (False, TypeError),
                         (1.0, TypeError), ("3", TypeError), (None, TypeError)):
            with self.subTest(value=bad):
                with self.assertRaises(exc):
                    church_numeral(bad)

    def test_A6_numerals_stay_within_a_bounded_budget(self):
        """Guards the repair against a builder that terminates only by luck."""
        for n in range(6):
            with self.subTest(n=n):
                self.assertLess(self.reduce_applied(church_numeral(n)).atp_spent, 2_000)


class ReplProcessTest(unittest.TestCase):
    """Driven as a process: nothing here can be satisfied by an import."""

    def repl(self, *lines, timeout=60):
        proc = subprocess.run(
            [sys.executable, "-B", os.path.join(_HERE, "cli.py"), "repl"],
            input="\n".join(lines) + "\n", capture_output=True, text=True,
            timeout=timeout, cwd=_HERE)
        return plain(proc.stdout), plain(proc.stderr), proc.returncode

    def test_B1_identity_reduces_and_reports_a_settlement(self):
        out, err, code = self.repl("🤍 Signal", ":q")
        self.assertEqual(code, 0)
        self.assertNotIn("Error", out)
        self.assertIn("Normal Form: Signal", out)
        self.assertIn("Settlement", out)

    def test_B2_constant_and_distribution_reduce(self):
        out, _, _ = self.repl("🖤 Truth Mirage", "🌿 🖤 🖤 Signal", ":q")
        self.assertIn("Normal Form: Truth", out)
        self.assertIn("Normal Form: Signal", out)
        self.assertNotIn("Error", out)

    def test_B3_exhausted_budget_is_not_called_a_normal_form(self):
        out, _, code = self.repl(":atp 20", "🔁 🤍", ":q")
        self.assertEqual(code, 0)
        self.assertNotIn("Error", out)
        tail = out.split("ATP budget updated", 1)[1]
        self.assertNotIn("Normal Form", tail)
        self.assertNotIn("Settlement", tail)
        self.assertIn("SUSPENDED", tail.upper())

    def test_B4_parse_error_is_reported_and_the_session_survives(self):
        out, _, code = self.repl("((", "🤍 Recovered", ":q")
        self.assertEqual(code, 0)
        self.assertIn("Syntax error", out)
        self.assertIn("Normal Form: Recovered", out)
        self.assertLess(out.index("Syntax error"), out.index("Normal Form: Recovered"))

    def test_B5_an_engine_failure_would_not_look_like_a_user_error(self):
        """The defect this pins printed the same shape for both.

        A parse error is the user's; anything else is the tool's, and the two
        must not be reported identically.
        """
        out, _, _ = self.repl("((", ":q")
        self.assertIn("Syntax", out)
        self.assertNotIn("EvalResult", out)


class PolyglotRunnerTest(unittest.TestCase):
    """A generated document, executed. Both verdicts are exercised."""

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="s2-polyglot-")
        self.addCleanup(shutil.rmtree, self.dir, True)

    def build(self, expr: str, expected: str) -> str:
        from polyglot import PolyglotDocument
        doc = PolyglotDocument("S2 runner regression")
        doc.add_claim("c1", "identity claim", expr, expected)
        path = os.path.join(self.dir, "claim.pdf")
        doc.compile(path)
        return path

    def run_document(self, path: str):
        proc = subprocess.run([sys.executable, "-B", path], capture_output=True,
                              text=True, timeout=120, cwd=self.dir)
        return plain(proc.stdout), proc.returncode

    def test_C1_a_true_claim_settles(self):
        out, code = self.run_document(self.build("🤍 a", "a"))
        self.assertNotIn("ERROR", out)
        self.assertIn("SETTLED", out)
        self.assertEqual(code, 0)

    def test_C2_a_false_claim_is_refuted_and_not_by_an_exception(self):
        out, code = self.run_document(self.build("🤍 a", "b"))
        self.assertEqual(code, 1)
        self.assertIn("REFUTED", out)
        self.assertNotIn("ERROR", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
