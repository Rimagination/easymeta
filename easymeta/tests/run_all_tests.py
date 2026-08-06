#!/usr/bin/env python3
"""Run contracts, P0/P1 regressions, ecology benchmarks, and source manifests."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


TEST_DIR = Path(__file__).resolve().parent


def main() -> int:
    for script in (
        "run_contract_tests.py",
        "run_tests.py",
        "run_p1_tests.py",
        "run_ecology_benchmarks.py",
    ):
        completed = subprocess.run(
            [sys.executable, str(TEST_DIR / script)],
            cwd=TEST_DIR.parent,
            check=False,
        )
        if completed.returncode != 0:
            return completed.returncode
    print(
        "PASS: complete contract, P0/P1, executable ecology benchmark, and "
        "source-reproduction manifest "
        "meta-analysis skill regression suite"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
