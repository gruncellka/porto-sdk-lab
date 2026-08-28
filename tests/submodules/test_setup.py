"""Tests for scripts/setup.py."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import setup  # type: ignore[import-not-found]


def _ok_result(code: int = 0) -> MagicMock:
    result = MagicMock()
    result.returncode = code
    return result


def test_setup_environment_success_existing_venv(tmp_path: Path) -> None:
    """setup_environment should install deps when venv exists."""
    venv_bin = tmp_path / "venv" / "bin"
    venv_bin.mkdir(parents=True)
    (venv_bin / "activate").write_text("#!/bin/sh\n")
    (venv_bin / "python").write_text("")

    with patch.object(
        setup.subprocess, "run", side_effect=[_ok_result(), _ok_result(), _ok_result()]
    ):
        assert setup.setup_environment(tmp_path) == 0


def test_setup_environment_create_venv_failure(tmp_path: Path) -> None:
    """setup_environment should fail when venv creation fails."""
    with patch.object(setup.subprocess, "run", return_value=_ok_result(1)):
        assert setup.setup_environment(tmp_path) == 1


def test_setup_environment_missing_activate_script(tmp_path: Path) -> None:
    """setup_environment should fail when activation script is missing."""
    (tmp_path / "venv").mkdir(parents=True)
    assert setup.setup_environment(tmp_path) == 1


def test_setup_environment_pip_install_failure(tmp_path: Path) -> None:
    """setup_environment should fail when editable install fails."""
    venv_bin = tmp_path / "venv" / "bin"
    venv_bin.mkdir(parents=True)
    (venv_bin / "activate").write_text("#!/bin/sh\n")
    (venv_bin / "python").write_text("")

    # upgrade pip ok, pip install fails
    with patch.object(setup.subprocess, "run", side_effect=[_ok_result(), _ok_result(1)]):
        assert setup.setup_environment(tmp_path) == 1


def test_setup_repos_no_gitmodules(tmp_path: Path) -> None:
    """setup_repos should no-op when .gitmodules is missing."""
    assert setup.setup_repos(tmp_path) == 0


def test_setup_repos_not_git_repo(tmp_path: Path) -> None:
    """setup_repos should no-op when .git folder is missing."""
    (tmp_path / ".gitmodules").write_text("")
    assert setup.setup_repos(tmp_path) == 0


def test_setup_repos_git_update_failure(tmp_path: Path) -> None:
    """setup_repos should fail when git submodule update fails."""
    (tmp_path / ".gitmodules").write_text("")
    (tmp_path / ".git").mkdir()
    with patch.object(setup.subprocess, "run", return_value=_ok_result(1)):
        assert setup.setup_repos(tmp_path) == 1


def test_setup_repos_success_with_unregistered_warning(tmp_path: Path) -> None:
    """setup_repos should still succeed and print warning for unregistered submodules."""
    (tmp_path / ".gitmodules").write_text("")
    (tmp_path / ".git").mkdir()
    with (
        patch.object(setup.subprocess, "run", return_value=_ok_result(0)),
        patch.object(
            setup,
            "submodules_in_gitmodules_but_not_in_index",
            return_value=[{"path": "x", "url": "u"}],
        ),
    ):
        assert setup.setup_repos(tmp_path) == 0


def test_setup_main_repos_only_branch(tmp_path: Path) -> None:
    """main() should use repos-only branch."""
    with (
        patch.object(sys, "argv", ["setup.py", "--repos-only"]),
        patch.object(setup, "get_workspace_root", return_value=tmp_path),
        patch.object(setup, "setup_repos", return_value=0),
    ):
        assert setup.main() == 0


def test_setup_main_all_branch(tmp_path: Path) -> None:
    """main() should execute both repos and env setup for --all."""
    with (
        patch.object(sys, "argv", ["setup.py", "--all"]),
        patch.object(setup, "get_workspace_root", return_value=tmp_path),
        patch.object(setup, "setup_repos", return_value=0),
        patch.object(setup, "setup_environment", return_value=0),
    ):
        assert setup.main() == 0


def test_setup_main_default_branch(tmp_path: Path) -> None:
    """main() default branch should only call setup_environment."""
    with (
        patch.object(sys, "argv", ["setup.py"]),
        patch.object(setup, "get_workspace_root", return_value=tmp_path),
        patch.object(setup, "setup_environment", return_value=0),
    ):
        assert setup.main() == 0
