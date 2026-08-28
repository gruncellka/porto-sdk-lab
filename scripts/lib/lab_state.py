"""Workspace state checks used by status command."""

from __future__ import annotations

import subprocess
from pathlib import Path

from lib.workspace import get_workspace_root


def check_venv_exists(workspace_root: Path | None = None) -> bool:
    """Check if Python virtual environment exists."""
    if workspace_root is None:
        workspace_root = get_workspace_root()
    venv_path = workspace_root / "venv"
    return venv_path.exists() and venv_path.is_dir()


def check_submodules_initialized(workspace_root: Path | None = None) -> dict[str, str]:
    """Check git submodule status."""
    if workspace_root is None:
        workspace_root = get_workspace_root()

    gitmodules_path = workspace_root / ".gitmodules"
    if not gitmodules_path.exists():
        return {}

    status_map: dict[str, str] = {}

    try:
        result = subprocess.run(
            ["git", "submodule", "status"],
            cwd=workspace_root,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            for line in lines:
                if not line.strip():
                    continue

                parts = line.split()
                if len(parts) >= 2:
                    status_char = line[0]
                    submodule_path = parts[1]

                    if status_char == " ":
                        status_map[submodule_path] = "ok"
                    elif status_char == "-":
                        status_map[submodule_path] = "missing"
                    elif status_char == "+":
                        status_map[submodule_path] = "modified"
                    else:
                        status_map[submodule_path] = "unknown"
        else:
            status_map["_error"] = "error"
    except FileNotFoundError:
        status_map["_error"] = "error"

    return status_map


def check_sdks(workspace_root: Path | None = None) -> dict[str, bool]:
    """Check SDK directories and their completeness."""
    if workspace_root is None:
        workspace_root = get_workspace_root()

    sdks_dir = workspace_root / "sdks"
    sdks: dict[str, bool] = {}

    if not sdks_dir.exists():
        return sdks

    for sdk_dir in sdks_dir.iterdir():
        if not sdk_dir.is_dir():
            continue

        pyproject = sdk_dir / "pyproject.toml"
        package_json = sdk_dir / "package.json"
        is_complete = pyproject.exists() or package_json.exists()

        sdks[sdk_dir.name] = is_complete

    return sdks


def check_resources(workspace_root: Path | None = None) -> list[str]:
    """Check resource directories."""
    if workspace_root is None:
        workspace_root = get_workspace_root()

    resources_dir = workspace_root / "resources"
    resources: list[str] = []

    if not resources_dir.exists():
        return resources

    for resource_dir in resources_dir.iterdir():
        if resource_dir.is_dir():
            resources.append(resource_dir.name)

    return resources
