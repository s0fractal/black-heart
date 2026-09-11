#!/usr/bin/env python3
"""
Regression: the test suite imports every module from THIS checkout, a second
checkout cannot substitute a dependency, and a run rewrites no tracked file.

Until S9 five engine modules (anyon_glyph, continuum, goedel, morpho_net,
zk_glyph) ran, on import, a block that inserted os.getcwd(), a parent directory,
and the literal "/Users/s0fractal/Projects/black-heart" onto sys.path. So once
one had been imported, a later import -- a test module or one of its
dependencies -- could resolve out of another clone. `test_all` guarded only the
names of the selected suite modules, not their dependency closure, and one test
(the sheaf demo) wrote a tracked example on every run.

Sections:
  A  every engine resolves to this checkout, and the closure guard has teeth
  B  a distinguishable second checkout on cwd does not get injected
  C  running the sheaf demo does not modify the tracked example
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import textwrap
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path[:1]:
    sys.path.insert(0, _HERE)

import test_all  # noqa: E402

_POISONERS = ["anyon_glyph", "continuum", "goedel", "morpho_net", "zk_glyph"]


class OriginTest(unittest.TestCase):
    """Section A."""

    def test_A1_no_engine_puts_a_foreign_path_ahead_of_this_checkout(self):
        """Behavioural: after importing every engine from a neutral cwd, the
        FIRST sys.path directory that holds a repo module (glyph.py) must be this
        checkout. A last-resort checkout appended AFTER it is allowed (the
        polyglot self-import needs it) but must never precede it."""
        import glob, json
        names = [os.path.splitext(os.path.basename(f))[0]
                 for f in sorted(glob.glob(os.path.join(_HERE, "*.py")))
                 if not os.path.basename(f).startswith("test_") and os.path.basename(f) != "conftest.py"]
        probe = textwrap.dedent(f"""
            import sys, os, json
            sys.path.insert(0, {_HERE!r})
            for m in {names!r}:
                try: __import__(m)
                except Exception: pass
            first = next((p for p in sys.path
                          if p and os.path.isfile(os.path.join(p, "glyph.py"))), None)
            print(json.dumps(os.path.abspath(first) if first else None))
        """)
        with tempfile.TemporaryDirectory() as neutral:
            env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
            r = subprocess.run([sys.executable, "-B", "-c", probe], cwd=neutral, env=env,
                               capture_output=True, text=True, timeout=180)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            first = json.loads(r.stdout.strip().splitlines()[-1])
            self.assertEqual(first, _HERE,
                             f"a foreign checkout precedes this one on sys.path: {first}")

    def test_A2_every_engine_imports_from_this_checkout(self):
        import importlib, glob
        for f in sorted(glob.glob(os.path.join(_HERE, "*.py"))):
            name = os.path.splitext(os.path.basename(f))[0]
            if name.startswith("test_") or name in ("conftest",):
                continue
            try:
                mod = importlib.import_module(name)
            except Exception:
                continue
            path = getattr(mod, "__file__", None)
            if path:
                self.assertEqual(os.path.dirname(os.path.abspath(path)), _HERE,
                                 f"{name} imported from outside this checkout: {path}")
        self.assertEqual(test_all._foreign_repo_modules(), [])

    def test_A3_the_closure_guard_fires_on_a_foreign_dependency(self):
        import types
        fake = types.ModuleType("glyph")
        fake.__file__ = "/some/other/checkout/glyph.py"
        real = sys.modules.get("glyph")
        sys.modules["glyph"] = fake
        try:
            self.assertIn("glyph <- /some/other/checkout/glyph.py",
                          "; ".join(test_all._foreign_repo_modules()))
            with self.assertRaises(ImportError):
                test_all._assert_local("test_suite_isolation")
        finally:
            if real is not None:
                sys.modules["glyph"] = real
            else:
                del sys.modules["glyph"]
        self.assertEqual(test_all._foreign_repo_modules(), [])


class SecondCheckoutTest(unittest.TestCase):
    """Section B: a second checkout discoverable via the cwd must not shadow."""

    def test_B1_importing_a_poisoner_does_not_inject_the_cwd(self):
        with tempfile.TemporaryDirectory() as d2:
            # A distinguishable second checkout: a marked glyph.py.
            with open(os.path.join(d2, "glyph.py"), "w") as f:
                f.write("MARK_SECOND_CHECKOUT = True\n")
            probe = textwrap.dedent(f"""
                import sys, os
                sys.path.insert(0, {_HERE!r})          # this checkout, as the suite arranges
                for m in {_POISONERS!r}:
                    __import__(m)
                # The cwd (a second checkout) must not have been injected at all.
                assert {d2!r} not in [os.path.abspath(p) for p in sys.path if p], "the cwd/second checkout was injected"
                import glyph
                assert os.path.dirname(os.path.abspath(glyph.__file__)) == {_HERE!r}, glyph.__file__
                assert not getattr(glyph, "MARK_SECOND_CHECKOUT", False), "glyph came from the second checkout"
                print("OK")
            """)
            env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
            r = subprocess.run([sys.executable, "-B", "-c", probe], cwd=d2, env=env,
                               capture_output=True, text=True, timeout=120)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("OK", r.stdout)

    def test_B2_a_second_checkout_on_pythonpath_after_here_does_not_win(self):
        with tempfile.TemporaryDirectory() as d2:
            with open(os.path.join(d2, "glyph.py"), "w") as f:
                f.write("MARK_SECOND_CHECKOUT = True\n")
            probe = textwrap.dedent(f"""
                import sys, os
                sys.path.insert(0, {_HERE!r})
                import continuum, glyph
                assert os.path.dirname(os.path.abspath(glyph.__file__)) == {_HERE!r}, glyph.__file__
                print("OK")
            """)
            env = dict(os.environ, PYTHONPATH=d2)
            r = subprocess.run([sys.executable, "-B", "-c", probe], env=env,
                               capture_output=True, text=True, timeout=120)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


class NoTrackedWriteTest(unittest.TestCase):
    """Section C: a run must not rewrite a tracked artifact."""

    def test_C1_the_sheaf_demo_can_be_redirected_off_the_tracked_example(self):
        tracked = os.path.join(_HERE, "examples", "sheaf_certificate.pdf")
        before = None
        if os.path.exists(tracked):
            with open(tracked, "rb") as fh:
                before = fh.read()
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "cert.pdf")
            env = dict(os.environ, PYTHONPATH=_HERE, BLACKHEART_SHEAF_DEMO_OUT=out)
            r = subprocess.run([sys.executable, "-B", os.path.join(_HERE, "examples", "sheaf_demo.py")],
                               cwd=_HERE, env=env, capture_output=True, text=True, timeout=300)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertTrue(os.path.exists(out))
        after = None
        if os.path.exists(tracked):
            with open(tracked, "rb") as fh:
                after = fh.read()
        self.assertEqual(before, after, "running the demo rewrote the tracked example")

    def test_C2_a_full_run_leaves_the_git_working_tree_clean(self):
        """A plain `python3 test_all.py` run modifies no tracked file. Guarded
        against recursion: the spawned run sets BLACKHEART_SUITE_CHILD, and when
        that is set this test skips instead of spawning again."""
        if os.environ.get("BLACKHEART_SUITE_CHILD"):
            self.skipTest("inside a spawned suite run (recursion guard)")
        if not os.path.exists(os.path.join(_HERE, ".git")):
            self.skipTest("not a git checkout")

        def dirty():
            r = subprocess.run(["git", "-C", _HERE, "status", "--porcelain", "--untracked-files=no"],
                               capture_output=True, text=True, timeout=60)
            return r.stdout.strip()

        before = dirty()
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", BLACKHEART_SUITE_CHILD="1")
        subprocess.run([sys.executable, "-B", os.path.join(_HERE, "test_all.py")],
                       cwd=_HERE, env=env, capture_output=True, text=True, timeout=1800)
        self.assertEqual(dirty(), before, "a full suite run modified tracked files")


if __name__ == "__main__":
    unittest.main()
