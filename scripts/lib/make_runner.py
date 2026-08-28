"""Helpers for invoking workspace Make targets."""

import subprocess
import sys


def run_make(target: str, *args: str, check: bool = True) -> int:
    """Run a make target with optional arguments."""
    cmd = ["make", target] + list(args)
    try:
        result = subprocess.run(cmd, check=False)
        if check and result.returncode != 0:
            sys.exit(result.returncode)
        return result.returncode
    except FileNotFoundError:
        print("❌ Error: 'make' command not found. Please install make.", file=sys.stderr)
        if check:
            sys.exit(1)
        return 1
