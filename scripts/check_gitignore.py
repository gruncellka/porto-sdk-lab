#!/usr/bin/env python3
"""Fail when tracked files match generated-path deny patterns."""

from __future__ import annotations

import re
import subprocess
import sys

# (pattern, human label) — matched against repo-relative posix paths from git ls-files
DENY_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^labs/experiments/latest$"), "labs/experiments/latest (local symlink only)"),
    (
        re.compile(r"^labs/experiments/runs/.+"),
        "labs/experiments/runs/* (except .gitkeep)",
    ),
    (re.compile(r"^labs/.+/artifacts/.+"), "labs/**/artifacts/**"),
    (
        re.compile(r"^labs/experiments/.+\.(png|pdf|zip)$"),
        "labs/experiments stamp/media (local evidence only)",
    ),
    (
        re.compile(r"^surface/artifacts/.+"),
        "surface/artifacts/** (except .gitkeep) — generated extract/report/stubs",
    ),
    (
        re.compile(r"^surface/node_modules/"),
        "surface/node_modules/ (TypeDoc install — npm ci in CI)",
    ),
    (re.compile(r"(^|/)\.env$"), ".env (secrets — use .env.example only)"),
    (
        re.compile(r"(^|/)\.env\.(?!example$)"),
        ".env.* (secrets — use .env.example only)",
    ),
    (re.compile(r"(^|/)test_credentials\.env$"), "test_credentials.env"),
    (re.compile(r"^\.coverage(\.|$)"), ".coverage artifacts"),
    (re.compile(r"\.log$"), "*.log"),
]

ALLOWLIST = frozenset(
    {
        "labs/experiments/runs/.gitkeep",
        "surface/artifacts/.gitkeep",
        "artifacts/.gitkeep",
        ".env.example",
    }
)


def tracked_files() -> list[str]:
    proc = subprocess.run(
        ["git", "ls-files", "-z"],
        check=True,
        capture_output=True,
    )
    raw = proc.stdout.decode("utf-8")
    if not raw:
        return []
    return [part for part in raw.split("\0") if part]


def violations(paths: list[str]) -> list[str]:
    found: list[str] = []
    for path in paths:
        if path in ALLOWLIST or path.endswith("/.env.example"):
            continue
        for pattern, label in DENY_PATTERNS:
            if pattern.search(path):
                found.append(f"{path} ({label})")
                break
    return found


def main() -> int:
    paths = tracked_files()
    bad = violations(paths)
    if bad:
        print("Tracked files that should be gitignored:", file=sys.stderr)
        for item in bad:
            print(f"  - {item}", file=sys.stderr)
        return 1
    print("check-gitignore: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
