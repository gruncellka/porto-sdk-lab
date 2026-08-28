"""Submodule parsing and git index helpers."""

from __future__ import annotations

import subprocess
from pathlib import Path

from lib.workspace import get_workspace_root


def parse_gitmodules(workspace_root: Path) -> list[dict]:
    """Parse .gitmodules and return list of submodule path/url."""
    gitmodules = workspace_root / ".gitmodules"
    if not gitmodules.exists():
        return []

    entries: list[dict] = []
    current: dict[str, str] = {}

    for line in gitmodules.read_text().splitlines():
        line = line.strip()
        if line.startswith("[submodule "):
            if current and "path" in current:
                entries.append(current)
            current = {}
            continue
        if "=" in line and current is not None:
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"')
            if key == "path":
                current["path"] = value
            elif key == "url":
                current["url"] = value

    if current and "path" in current:
        entries.append(current)
    return entries


def get_submodule_paths_in_index(workspace_root: Path) -> set[str]:
    """Return paths registered as submodules in git index (mode 160000)."""
    result = subprocess.run(
        ["git", "ls-files", "-s"],
        cwd=workspace_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return set()

    paths: set[str] = set()
    for line in result.stdout.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        mode = parts[0].split()[0] if parts[0] else ""
        if mode == "160000":
            paths.add(parts[1].strip())
    return paths


def submodules_in_gitmodules_but_not_in_index(
    workspace_root: Path | None = None,
) -> list[dict]:
    """Find submodules listed in .gitmodules that are not in the git index."""
    if workspace_root is None:
        workspace_root = get_workspace_root()

    in_gitmodules = parse_gitmodules(workspace_root)
    in_index = get_submodule_paths_in_index(workspace_root)
    missing: list[dict] = []
    for sm in in_gitmodules:
        path = sm.get("path", "")
        if path and path not in in_index:
            missing.append(sm)
    return missing
