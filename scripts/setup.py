#!/usr/bin/env python3
"""Lab setup operations - environment and submodules."""

import argparse
import subprocess
import sys
from pathlib import Path

from lib.submodules import submodules_in_gitmodules_but_not_in_index
from lib.workspace import get_workspace_root

# Keep in sync with `requires-python` in pyproject.toml.
MIN_PYTHON = (3, 13)


def _require_min_python() -> int:
    """Fail fast if the interpreter is older than the project requires."""
    if sys.version_info < MIN_PYTHON:
        required = ".".join(str(p) for p in MIN_PYTHON)
        current = ".".join(str(p) for p in sys.version_info[:3])
        print(
            f"❌ Python >= {required} is required to set up this workspace "
            f"(found {current} at {sys.executable}).",
            file=sys.stderr,
        )
        print(
            "   Install it (macOS):  brew install python@3.13\n"
            "   Then re-run:         make PYTHON=python3.13",
            file=sys.stderr,
        )
        return 1
    return 0


def setup_environment(workspace_root: Path) -> int:
    """Setup Python virtual environment and pre-commit hooks.

    Args:
        workspace_root: Workspace root directory.

    Returns:
        Exit code (0 = success, non-zero = failure).
    """
    print("🐍 Setting up Python environment...")
    print()

    venv_path = workspace_root / "venv"

    if not venv_path.exists():
        print(f"📦 Creating virtual environment with {sys.executable}...")
        # Use the *current* interpreter (the one running this script) so the
        # venv inherits its version. Hard-coding "python3" picks up whatever
        # is first on PATH (often /usr/bin/python3 on macOS, which is 3.9).
        result = subprocess.run(
            [sys.executable, "-m", "venv", "venv"],
            cwd=workspace_root,
            check=False,
        )
        if result.returncode != 0:
            print("❌ Failed to create virtual environment", file=sys.stderr)
            return 1
    else:
        print("📦 Virtual environment already exists")

    # Activate and install dependencies
    print("🔌 Installing dependencies...")
    activate_script = venv_path / "bin" / "activate"
    if not activate_script.exists():
        print("❌ Virtual environment activation script not found", file=sys.stderr)
        return 1

    # Install workspace dependencies
    pip_cmd = [
        str(venv_path / "bin" / "python"),
        "-m",
        "pip",
        "install",
        "--upgrade",
        "pip",
        "--quiet",
    ]
    result = subprocess.run(pip_cmd, cwd=workspace_root, check=False)
    if result.returncode != 0:
        print("⚠️  Failed to upgrade pip", file=sys.stderr)

    pip_install_cmd = [
        str(venv_path / "bin" / "python"),
        "-m",
        "pip",
        "install",
        "-e",
        ".[dev]",
        "--quiet",
    ]
    result = subprocess.run(pip_install_cmd, cwd=workspace_root, check=False)
    if result.returncode != 0:
        print("❌ Failed to install lab dependencies", file=sys.stderr)
        return 1

    # Install pre-commit hooks
    print("🔗 Installing pre-commit hooks...")
    precommit_cmd = [str(venv_path / "bin" / "pre-commit"), "install"]
    result = subprocess.run(precommit_cmd, cwd=workspace_root, check=False)
    if result.returncode != 0:
        print("⚠️  Failed to install pre-commit hooks", file=sys.stderr)

    print()
    print("✅ Python environment setup complete!")
    return 0


def setup_repos(workspace_root: Path) -> int:
    """Initialize git submodules.

    Args:
        workspace_root: Workspace root directory.

    Returns:
        Exit code (0 = success, non-zero = failure).
    """
    print("📦 Setting up git submodules...")
    print()

    gitmodules_path = workspace_root / ".gitmodules"
    if not gitmodules_path.exists():
        print("⚠️  .gitmodules not found, nothing to initialize")
        return 0

    if not (workspace_root / ".git").exists():
        print("⚠️  Not in a git repository, cannot initialize submodules")
        return 0

    # Initialize submodules (only clones/updates submodules that are in the git index)
    result = subprocess.run(
        ["git", "submodule", "update", "--init", "--recursive"],
        cwd=workspace_root,
        check=False,
    )

    if result.returncode != 0:
        print("❌ Failed to initialize submodules", file=sys.stderr)
        return 1

    # Warn if .gitmodules lists submodules that are not in the index — they will never be cloned
    unregistered = submodules_in_gitmodules_but_not_in_index(workspace_root)
    if unregistered:
        print()
        print("⚠️  Some submodules are in .gitmodules but not registered in the repo (no gitlink).")
        print("   Run the following once from the repo root, then commit:")
        for sm in unregistered:
            path = sm.get("path", "")
            url = sm.get("url", "")
            print(f"   git submodule add {url} {path}")
        print()

    print()
    print("✅ Submodules initialized successfully!")
    return 0


def main() -> int:
    """Main entry point for setup operations."""
    parser = argparse.ArgumentParser(
        description="Setup lab environment and/or repositories",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--repos-only",
        action="store_true",
        help="Initialize git submodules only",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Complete setup (repos + environment)",
    )

    args = parser.parse_args()
    workspace_root = get_workspace_root()

    if args.repos_only:
        return setup_repos(workspace_root)

    # Anything that touches the workspace venv needs the supported interpreter.
    py_check = _require_min_python()
    if py_check != 0:
        return py_check

    if args.all:
        repos_result = setup_repos(workspace_root)
        env_result = setup_environment(workspace_root)
        return repos_result or env_result
    else:
        return setup_environment(workspace_root)


if __name__ == "__main__":
    sys.exit(main())
