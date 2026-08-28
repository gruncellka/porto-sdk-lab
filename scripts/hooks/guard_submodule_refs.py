#!/usr/bin/env python3
"""Block accidental submodule ref commits in the lab root repository.

This guard checks staged changes and fails if any gitlink (mode 160000)
is part of the commit. That means a submodule ref update/removal was staged.
"""

from __future__ import annotations

import os
import subprocess
import sys


def _staged_submodule_changes() -> list[str]:
    """Return staged paths where old/new mode indicates a gitlink (160000)."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--raw", "--no-abbrev"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        # Do not hard-fail on git command issues; let commit proceed.
        return []

    paths: list[str] = []
    for line in result.stdout.splitlines():
        if not line.startswith(":"):
            continue

        if "\t" not in line:
            continue

        meta, path_part = line.split("\t", 1)
        meta_parts = meta.split()
        if len(meta_parts) < 2:
            continue

        old_mode = meta_parts[0][1:]  # strip leading ':'
        new_mode = meta_parts[1]
        if old_mode != "160000" and new_mode != "160000":
            continue

        # For renames/copies path_part may include more than one tab-separated path.
        path = path_part.split("\t")[-1]
        paths.append(path)

    # Preserve order while deduplicating.
    unique_paths: list[str] = []
    seen = set()
    for path in paths:
        if path in seen:
            continue
        seen.add(path)
        unique_paths.append(path)
    return unique_paths


def main() -> int:
    if os.getenv("ALLOW_SUBMODULE_POINTER_COMMIT") == "1":
        return 0

    staged_paths = _staged_submodule_changes()
    if not staged_paths:
        return 0

    print("❌ Commit blocked: staged submodule ref changes detected.")
    print("")
    print("These paths are git submodules (gitlinks):")
    for path in staged_paths:
        print(f"  - {path}")
    print("")
    print("If this update is intentional:")
    print("  1) Commit/push inside submodule first")
    print("  2) Commit ref from lab root intentionally")
    print("")
    print("💡 Hint: if this is intentional, bypass once with:")
    print("  ALLOW_SUBMODULE_POINTER_COMMIT=1 git commit ...")

    return 1


if __name__ == "__main__":
    sys.exit(main())
