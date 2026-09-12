#!/usr/bin/env python3
"""CI gate for the R2 external-anchor reader.

Runs the R2 reader tests and FAILS if any were skipped -- in the OpenTimestamps
CI job the OTS-backed state tests must actually run, so a missing dependency can
never pass as green. (The zero-dependency main job legitimately skips them; this
job is where they must execute.) Run from the repo root.
"""
import os
import sys
import unittest

# Run the repo-root test module regardless of CWD: this file's directory is
# sys.path[0], so add the repo root (two levels up) for `import test_exp_lib_001`.
_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)
os.chdir(_REPO)

NAMES = [
    "test_exp_lib_001.ExternalAnchorR2Test",
    "test_exp_lib_001.ExternalAnchorNoLibTest",
]


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromNames(NAMES)
    res = unittest.TextTestRunner(verbosity=2).run(suite)
    print(f"ran={res.testsRun} skipped={len(res.skipped)} "
          f"failures={len(res.failures)} errors={len(res.errors)}")
    if res.skipped:
        print("FAIL: R2 tests skipped in the OpenTimestamps job:",
              [str(t) for t, _ in res.skipped])
        return 1
    if res.testsRun == 0:
        print("FAIL: no R2 tests were collected")
        return 1
    return 0 if res.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
