#!/usr/bin/env python3
"""Run every branch-cleanup test (unit, end-to-end on scratch repositories, workflow static checks).

Exit code 0 only if all pass. Used by .github/workflows/cleanup.yml (self-test before any cleanup) and meant to be
wired into tools/check_all.py by the Supervisor (one line, see docs/evaluation/process/T-048/README.md).
"""

from __future__ import annotations

import os
import sys

# select.py in this directory shadows the stdlib ``select`` module: never keep this directory on sys.path.
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:] = [p for p in sys.path if os.path.abspath(p or os.curdir) != _HERE]

import unittest  # noqa: E402


def main() -> int:
    tests = os.path.join(_HERE, "tests")
    suite = unittest.defaultTestLoader.discover(start_dir=tests, pattern="test_*.py", top_level_dir=tests)
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    print(f"cleanup tests: {result.testsRun} run, {len(result.failures)} failures, {len(result.errors)} errors, "
          f"{len(result.skipped)} skipped")
    return 0 if result.wasSuccessful() and result.testsRun > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
