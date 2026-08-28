"""Tests for scripts/cli.py."""

import argparse
import sys
from pathlib import Path
from unittest.mock import patch

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import cli


def test_setup_wrapper_repos_only_preserves_argv() -> None:
    """Wrapper should pass --repos-only and restore argv."""
    original = ["pytest", "-k", "x"]
    with (
        patch.object(sys, "argv", original.copy()),
        patch.object(cli.setup, "main", return_value=7),
    ):
        result = cli._setup_wrapper(argparse.Namespace(repos_only=True, all=False))
        assert sys.argv == original
    assert result == 7


def test_setup_wrapper_all_mode() -> None:
    """Wrapper should pass --all mode."""
    with patch.object(cli.setup, "main", return_value=3):
        assert cli._setup_wrapper(argparse.Namespace(repos_only=False, all=True)) == 3


def test_cli_main_no_args() -> None:
    """No command should print help and return 1."""
    with patch.object(sys, "argv", ["cli.py"]):
        assert cli.main() == 1


def test_cli_main_status_dispatch() -> None:
    """Status command dispatches to status.main."""
    with (
        patch.object(sys, "argv", ["cli.py", "status"]),
        patch.object(cli.status, "main", return_value=0),
    ):
        assert cli.main() == 0


def test_cli_main_sync_dispatch() -> None:
    """Sync command dispatches to sync.main."""
    with (
        patch.object(sys, "argv", ["cli.py", "sync"]),
        patch.object(cli.sync, "main", return_value=0),
    ):
        assert cli.main() == 0


def test_cli_main_test_target_resolution() -> None:
    """Test command should choose matching make targets."""
    with patch.object(cli, "run_make", return_value=0):
        with patch.object(sys, "argv", ["cli.py", "test", "--python"]):
            assert cli.main() == 0
        with patch.object(sys, "argv", ["cli.py", "test", "--typescript"]):
            assert cli.main() == 0
        with patch.object(sys, "argv", ["cli.py", "test", "--bdd"]):
            assert cli.main() == 0
        with patch.object(sys, "argv", ["cli.py", "test", "--all"]):
            assert cli.main() == 0
        with patch.object(sys, "argv", ["cli.py", "test"]):
            assert cli.main() == 0


def test_cli_main_clean_target_resolution() -> None:
    """Clean command should choose matching make targets."""
    with patch.object(cli, "run_make", return_value=0):
        with patch.object(sys, "argv", ["cli.py", "clean", "--all"]):
            assert cli.main() == 0
        with patch.object(sys, "argv", ["cli.py", "clean", "--deps"]):
            assert cli.main() == 0
        with patch.object(sys, "argv", ["cli.py", "clean", "--repos"]):
            assert cli.main() == 0
        with patch.object(sys, "argv", ["cli.py", "clean"]):
            assert cli.main() == 0


def test_cli_main_help_raises_system_exit() -> None:
    """Argparse help should raise SystemExit."""
    with patch.object(sys, "argv", ["cli.py", "--help"]):
        try:
            cli.main()
        except SystemExit as exc:
            assert exc.code == 0
