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

Review r1 on PR #24 (`~/Projects/.triad/reviews/black-heart-pr24-r1/`) found two
further gaps, fixed here:
  R1 — `test_all`'s origin check ran only before a suite's tests executed, so a
       module imported DURING a test's run (not at discovery time) escaped it,
       and the LAST suite had no check after it at all. `test_all.py` now also
       checks immediately after each suite's `run()` (A4/A5 below exercise this
       against the real runner, not a mock of it).
  R2 — this file's own all-engine import inventory (what is now A2) ran in the
       SAME process as the rest of the suite, preloading ~40 engines and so
       masking any later search-path defect by module caching. It now runs in
       a child process and leaves the parent's sys.modules untouched.
Also fixed: C2 compared `git status` TEXT (misses a file that was already
dirty and is mutated further without its status letter changing) and silently
dropped the child's return code; it now compares tracked-file content digests
and reports the child's return code. The sys.path fix itself was strengthened
to MOVE current_dir to the front rather than only insert it "if absent" (a
module already present elsewhere on sys.path was previously left there).

Sections:
  A  every engine resolves to this checkout (in a child process), the closure
     guard has teeth, and it holds against a runtime import in the last suite
  B  a distinguishable second checkout on cwd does not get injected
  C  running the sheaf demo does not modify the tracked example, and a full
     run changes no tracked byte
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from unittest.mock import patch

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path[:1]:
    sys.path.insert(0, _HERE)

import test_all  # noqa: E402

_POISONERS = ["anyon_glyph", "continuum", "goedel", "morpho_net", "zk_glyph"]


def _tracked_digest(repo_dir: str) -> str:
    """One digest over every tracked file's path and current bytes.

    Stronger than comparing `git status` TEXT (review R1's additional
    correction): a file already dirty before a run keeps the same status
    letter if the run mutates it further, so a status-text comparison misses
    that. This hashes actual content, so any byte-level change is caught
    regardless of the file's status before the run.
    """
    r = subprocess.run(["git", "-C", repo_dir, "ls-files", "-z"],
                       capture_output=True, timeout=60)
    paths = sorted(p for p in r.stdout.split(b"\0") if p)
    h = hashlib.sha256()
    for p in paths:
        h.update(p)
        h.update(b"\0")
        try:
            with open(os.path.join(repo_dir, p.decode()), "rb") as fh:
                h.update(fh.read())
        except FileNotFoundError:
            h.update(b"<deleted>")
        h.update(b"\0")
    return h.hexdigest()


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
        """Runs the all-engine import inventory in a CHILD process (review R1's
        R2 finding: doing this in-process preloaded ~40 engines into the very
        process that then runs the rest of test_all's suites, so a later
        search-path defect would be masked by the cached modules -- import is a
        no-op once a name is in sys.modules, regardless of what search order
        would otherwise have found). The parent's sys.modules is asserted
        unchanged by this test itself."""
        import glob
        before = set(sys.modules)
        names = [os.path.splitext(os.path.basename(f))[0]
                 for f in sorted(glob.glob(os.path.join(_HERE, "*.py")))
                 if not os.path.basename(f).startswith("test_") and os.path.basename(f) != "conftest.py"]
        probe = textwrap.dedent(f"""
            import sys, os, json, importlib
            sys.path.insert(0, {_HERE!r})
            results = {{}}
            for m in {names!r}:
                try:
                    mod = importlib.import_module(m)
                except Exception as e:
                    results[m] = {{"status": "error", "detail": f"{{type(e).__name__}}: {{e}}"}}
                    continue
                path = getattr(mod, "__file__", None)
                if path is None:
                    results[m] = {{"status": "no_file"}}
                    continue
                origin = os.path.dirname(os.path.abspath(path))
                results[m] = {{"status": "ok" if origin == {_HERE!r} else "foreign", "origin": origin}}
            print(json.dumps(results))
        """)
        with tempfile.TemporaryDirectory() as neutral:
            env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
            r = subprocess.run([sys.executable, "-B", "-c", probe], cwd=neutral, env=env,
                               capture_output=True, text=True, timeout=180)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            results = json.loads(r.stdout.strip().splitlines()[-1])

        foreign = {m: v for m, v in results.items() if v["status"] == "foreign"}
        errors = {m: v for m, v in results.items() if v["status"] == "error"}
        self.assertEqual(foreign, {}, f"engine(s) imported from outside this checkout: {foreign}")
        # A skipped/failed import narrows coverage; report it rather than
        # letting it pass silently (review R1's explicit request), without
        # failing the test over it -- some modules are not standalone-importable
        # (e.g. missing optional runtime deps) and that is not a path defect.
        if errors:
            names_only = ", ".join(sorted(errors))
            print(f"\n  [i] {len(errors)} engine module(s) not importable standalone "
                 f"(not counted as origin failures): {names_only}", file=sys.stderr)

        # This inventory ran entirely in the child process: the parent's own
        # sys.modules must be exactly as it was before this test.
        self.assertEqual(set(sys.modules) - before, set(),
                         "the all-engine inventory leaked imports into the parent process")

    def test_A4_a_runtime_import_in_the_last_suite_fails_the_run(self):
        """Negative (review R1). Uses the REAL test_all.run_all_tests() and the
        REAL origin guard; only the discovered suite is substituted, exactly as
        the reviewer's probe does, so this is not a check against a mock of our
        own making. The one patched suite's OWN test performs a genuine runtime
        import of a foreign glyph.py -- discovery time is clean; the import
        happens only while the test runs, and this is deliberately the ONLY
        (hence last) suite, reproducing 'the last suite has no check after it'.
        """
        import importlib.util

        with tempfile.TemporaryDirectory() as td:
            foreign_path = os.path.join(td, "glyph.py")
            with open(foreign_path, "w") as f:
                f.write("SECOND_CHECKOUT = True\n")

            class LateImport(unittest.TestCase):
                def runTest(self):
                    spec = importlib.util.spec_from_file_location("glyph", foreign_path)
                    mod = importlib.util.module_from_spec(spec)
                    sys.modules["glyph"] = mod
                    spec.loader.exec_module(mod)
                    self.assertTrue(mod.SECOND_CHECKOUT)

            real_glyph = sys.modules.get("glyph")
            try:
                with patch.object(test_all, "SUITES", [("late import", "test_suite_isolation")]), \
                     patch.object(unittest.TestLoader, "loadTestsFromName",
                                  return_value=unittest.TestSuite([LateImport()])), \
                     contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    success = test_all.run_all_tests()
            finally:
                if real_glyph is not None:
                    sys.modules["glyph"] = real_glyph
                else:
                    sys.modules.pop("glyph", None)
            self.assertFalse(success,
                             "a foreign module imported during the last suite's own test "
                             "run was not caught: run_all_tests() reported success")
            self.assertEqual(test_all._foreign_repo_modules(), [],
                             "the foreign module was not cleaned up after the run")

    def test_A5_an_ordinary_local_import_still_reports_success(self):
        """Positive (review R1): the post-run checkpoint added for A4 must not
        make an ordinary suite that imports only local repo modules fail."""
        class LocalImport(unittest.TestCase):
            def runTest(self):
                import glyph  # already resident from this checkout
                self.assertEqual(os.path.dirname(os.path.abspath(glyph.__file__)), _HERE)

        with patch.object(test_all, "SUITES", [("local import", "test_suite_isolation")]), \
             patch.object(unittest.TestLoader, "loadTestsFromName",
                          return_value=unittest.TestSuite([LocalImport()])), \
             contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            success = test_all.run_all_tests()
        self.assertTrue(success, "an ordinary local import was wrongly reported as foreign")

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
                # A fallback may append the cwd (a second checkout) AFTER this
                # checkout, but it must never precede it: the first sys.path dir
                # holding a repo module must be this checkout, and glyph must
                # resolve here, unmarked -- no substitution.
                first = next((p for p in sys.path
                              if p and os.path.isfile(os.path.join(p, "glyph.py"))), None)
                assert os.path.abspath(first) == {_HERE!r}, first
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

    def test_C2_a_full_run_leaves_tracked_file_bytes_unchanged(self):
        """A plain `python3 test_all.py` run changes no tracked byte. Compares
        content digests (review R1's additional correction), not `git status`
        text: a file already dirty before the run keeps the same status letter
        even if the run mutates it further, so a status-text comparison would
        miss that. Checked regardless of the child's own pass/fail -- a failing
        child run must not rewrite tracked bytes either -- and the child's
        return code is reported, not silently discarded, so a crash or timeout
        is visible in the failure message rather than read as "nothing to
        compare". Guarded against recursion: the spawned run sets
        BLACKHEART_SUITE_CHILD, and when that is set this test skips -- the
        check is performed once, by the outer/parent invocation that spawned it,
        not by the child itself."""
        if os.environ.get("BLACKHEART_SUITE_CHILD"):
            self.skipTest("recursion guard: this process is the spawned child; "
                          "the outer invocation that launched it performs this check")
        if not os.path.exists(os.path.join(_HERE, ".git")):
            self.skipTest("not a git checkout")

        before = _tracked_digest(_HERE)
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", BLACKHEART_SUITE_CHILD="1")
        r = subprocess.run([sys.executable, "-B", os.path.join(_HERE, "test_all.py")],
                           cwd=_HERE, env=env, capture_output=True, text=True, timeout=1800)
        after = _tracked_digest(_HERE)
        # Unconditional: even a failed or incomplete child run must not have
        # rewritten tracked bytes.
        self.assertEqual(before, after,
                         f"a full suite run modified tracked file bytes "
                         f"(child returncode={r.returncode})")
        # Independent of the byte check (review R3): unchanged bytes from a
        # child that crashed, timed out, or was otherwise cut short is not
        # evidence that the intended FULL run passed -- it may simply not have
        # reached the point where it would have written anything. Measured by
        # the reviewer with a synthetic returncode=1 child whose bytes never
        # moved: the byte assertion alone reported this test as passing.
        self.assertEqual(r.returncode, 0,
                         f"the spawned test_all.py did not complete successfully "
                         f"(returncode={r.returncode})\n--- stdout ---\n{r.stdout}\n"
                         f"--- stderr ---\n{r.stderr}")


def _fake_child_run(returncode, stdout="", stderr=""):
    """A `subprocess.run` side_effect that intercepts only the call whose argv
    ends in test_all.py (C2's spawned child) and answers with `returncode`
    WITHOUT actually running the suite; every other call (in particular
    `_tracked_digest`'s own `git ls-files`) is delegated to the real
    `subprocess.run`, exactly as the reviewer's probe does it."""
    real_run = subprocess.run

    def side_effect(cmd, *args, **kwargs):
        if isinstance(cmd, list) and any(str(x).endswith("test_all.py") for x in cmd):
            return subprocess.CompletedProcess(cmd, returncode, stdout=stdout, stderr=stderr)
        return real_run(cmd, *args, **kwargs)
    return side_effect


class C2HarnessTest(unittest.TestCase):
    """Controls on C2 itself (review R3): it must fail on a byte change and on
    a failed child, independently of each other, not only when both coincide."""

    def setUp(self):
        if not os.path.exists(os.path.join(_HERE, ".git")):
            self.skipTest("not a git checkout")

    def _run_c2(self, returncode, digest_pair=None):
        """`digest_pair`, if given, replaces `_tracked_digest`'s two calls
        (before/after) with fixed values instead of reading git; otherwise the
        real digest is read twice (and so is identical both times, since
        nothing in this harness touches the working tree)."""
        case = NoTrackedWriteTest("test_C2_a_full_run_leaves_tracked_file_bytes_unchanged")
        result = unittest.TestResult()
        with contextlib.ExitStack() as stack:
            # Clear BLACKHEART_SUITE_CHILD for the duration of this call. C2's
            # own recursion guard (against a REAL spawn recursing into ANOTHER
            # real spawn) would otherwise also skip THIS fully-mocked
            # invocation whenever this harness itself happens to run nested
            # inside an already-spawned child (e.g. a real full-suite run that
            # reaches test_suite_isolation a second time) -- the guard belongs
            # to test_C2's real subprocess call, not to this mocked one.
            stack.enter_context(patch.dict(os.environ, {}, clear=False))
            os.environ.pop("BLACKHEART_SUITE_CHILD", None)
            # subprocess.run is the actual module attribute both C2 and
            # _tracked_digest call through; the side_effect delegates every
            # non-test_all.py invocation to the real subprocess.run.
            stack.enter_context(patch.object(subprocess, "run", side_effect=_fake_child_run(returncode)))
            if digest_pair is not None:
                stack.enter_context(patch.object(sys.modules[__name__], "_tracked_digest",
                                                 side_effect=list(digest_pair)))
            case.run(result)
        return result

    def test_H1_a_failed_child_with_unchanged_bytes_still_fails_C2(self):
        """The reviewer's own control: real digests (nothing actually changes
        the tree), a synthetic returncode=1 child. Before the R3 fix this
        reported success."""
        result = self._run_c2(returncode=1, digest_pair=("same", "same"))
        self.assertFalse(result.wasSuccessful())
        self.assertEqual(len(result.errors) + len(result.failures), 1)

    def test_H2_a_successful_child_with_unchanged_bytes_passes_C2(self):
        result = self._run_c2(returncode=0, digest_pair=("same", "same"))
        self.assertTrue(result.wasSuccessful())

    def test_H3_changed_bytes_fail_C2_even_when_the_child_succeeds(self):
        result = self._run_c2(returncode=0, digest_pair=("before", "after"))
        self.assertFalse(result.wasSuccessful())

    def test_H4_changed_bytes_fail_C2_even_when_the_child_fails(self):
        result = self._run_c2(returncode=1, digest_pair=("before", "after"))
        self.assertFalse(result.wasSuccessful())


if __name__ == "__main__":
    unittest.main()
