"""Workspace path helpers."""

from pathlib import Path


def get_workspace_root() -> Path:
    """Get the lab root directory (parent of scripts/)."""
    script_dir = Path(__file__).resolve().parent.parent
    return script_dir.parent
