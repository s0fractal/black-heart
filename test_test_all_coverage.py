#!/usr/bin/env python3
# coding: utf-8
"""
test_test_all_coverage.py — test_all.py runs every root test_*.py module, or refuses.

During black-heart PR #99 a new root suite was not in test_all.SUITES, so every green CI
run on that PR executed none of its regressions. The runner's docstring promised "every
test_*.py in the repository root except this runner"; nothing enforced it. Now the set of
root test_*.py modules minus the explicit exclusions must equal the modules in SUITES,
checked before any suite runs.
"""

from __future__ import annotations
import os
import tempfile
import unittest
from unittest import mock

import test_all


class Coverage(unittest.TestCase):
    def test_the_repository_is_covered_today(self):
        # Green before and after: today's list happens to be complete.
        self.assertEqual(test_all.suite_coverage(test_all.root_test_modules(),
                                                 [m for _, m in test_all.SUITES]), ([], []))

    def test_an_unlisted_root_suite_is_named(self):
        with tempfile.TemporaryDirectory() as directory:
            for name in ("test_all.py", "test_a.py", "test_b.py", "helper.py"):
                open(os.path.join(directory, name), "w").close()
            unlisted, missing = test_all.suite_coverage(test_all.root_test_modules(directory), ["test_a"])
        self.assertEqual((unlisted, missing), (["test_b"], []))

    def test_a_listed_module_without_a_file_is_named(self):
        self.assertEqual(test_all.suite_coverage({"test_all", "test_a"}, ["test_a", "test_gone"]),
                         ([], ["test_gone"]))

    def test_the_runner_refuses_before_running_any_suite(self):
        loaded = []

        def load(self_loader, name, module=None):
            loaded.append(name)
            return unittest.TestSuite()
        dropped = [entry for entry in test_all.SUITES if entry[1] != "test_mycelium"]
        with mock.patch.object(test_all, "SUITES", dropped), \
                mock.patch.object(unittest.TestLoader, "loadTestsFromName", load), \
                mock.patch("builtins.print"):
            ok = test_all.run_all_tests()
        self.assertEqual((ok, loaded), (False, []))


if __name__ == "__main__":
    unittest.main()
