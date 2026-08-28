"""
CLI examples with provider support.

Demonstrates SDK CLI commands:
  porto config check [--provider ...]
  porto ident --country DE --weight 20 [--provider ...]
  porto restrict --country DE [--provider ...]
  porto calc --type letter_standard --country DE --weight 20 [--provider ...]
"""

from __future__ import annotations

import json
import subprocess
import sys
from typing import Any


def run_porto(args: list[str]) -> Any:
    full = ["porto", *args]
    print(f"Running: {' '.join(full)}")
    out = subprocess.check_output(full, text=True)
    return json.loads(out)


def main() -> int:
    try:
        print("\n--- porto config check ---")
        print(json.dumps(run_porto(["config", "check", "--json"]), indent=2))

        print("\n--- porto config check --provider swisspost ---")
        print(
            json.dumps(
                run_porto(["config", "check", "--provider", "swisspost", "--json"]),
                indent=2,
            )
        )

        print("\n--- porto restrict ---")
        print(json.dumps(run_porto(["restrict", "--country", "DE", "--json"]), indent=2))

        print("\n--- porto restrict --provider swisspost ---")
        print(
            json.dumps(
                run_porto(
                    [
                        "restrict",
                        "--country",
                        "CH",
                        "--provider",
                        "swisspost",
                        "--json",
                    ]
                ),
                indent=2,
            )
        )

        print("\n✅ All CLI commands OK")
        return 0
    except Exception as exc:  # pragma: no cover - lab script
        print("CLI command failed")
        print(str(exc))
        return 1


if __name__ == "__main__":
    sys.exit(main())
