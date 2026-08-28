#!/usr/bin/env python3
"""Lab orchestrator: run make registry in both SDK checkouts."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

LAB_ROOT = Path(__file__).resolve().parent.parent
SDKS = (
    LAB_ROOT / "sdks" / "porto-sdk-python",
    LAB_ROOT / "sdks" / "porto-sdk-typescript",
)


def main() -> int:
    failed = 0
    for sdk in SDKS:
        if not sdk.is_dir():
            print(f"skip missing {sdk}", file=sys.stderr)
            continue
        print(f"=== {sdk.name}: make registry ===")
        r = subprocess.run(["make", "registry"], cwd=sdk, check=False)
        if r.returncode != 0:
            failed = 1
    return failed


if __name__ == "__main__":
    raise SystemExit(main())
