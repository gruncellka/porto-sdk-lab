"""Tests for scripts/status.py."""

import sys
from pathlib import Path
from unittest.mock import patch

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import status  # type: ignore[import-not-found]


def test_print_status_all_good(tmp_path: Path) -> None:
    """print_status should return 0 when all checks pass."""
    with (
        patch.object(status, "get_workspace_root", return_value=tmp_path),
        patch.object(status, "check_venv_exists", return_value=True),
        patch.object(
            status, "check_submodules_initialized", return_value={"sdks/porto-sdk-python": "ok"}
        ),
        patch.object(status, "check_sdks", return_value={"porto-sdk-python": True}),
        patch.object(status, "check_resources", return_value=["porto-data"]),
    ):
        assert status.print_status() == 0


def test_print_status_with_missing_components(tmp_path: Path) -> None:
    """print_status should return 1 when required pieces are missing."""
    with (
        patch.object(status, "get_workspace_root", return_value=tmp_path),
        patch.object(status, "check_venv_exists", return_value=False),
        patch.object(
            status,
            "check_submodules_initialized",
            return_value={"sdks/porto-sdk-python": "missing"},
        ),
        patch.object(status, "check_sdks", return_value={}),
        patch.object(status, "check_resources", return_value=[]),
    ):
        assert status.print_status() == 1


def test_print_status_submodule_error_and_modified(tmp_path: Path) -> None:
    """print_status should handle _error and modified/unknown submodule states."""
    with (
        patch.object(status, "get_workspace_root", return_value=tmp_path),
        patch.object(status, "check_venv_exists", return_value=True),
        patch.object(
            status,
            "check_submodules_initialized",
            return_value={
                "_error": "error",
                "resources/porto-data": "modified",
                "resources/porto-features": "unknown",
            },
        ),
        patch.object(status, "check_sdks", return_value={"porto-sdk-typescript": False}),
        patch.object(status, "check_resources", return_value=["porto-data", "porto-features"]),
    ):
        assert status.print_status() == 0


def test_status_main_returns_print_status_result() -> None:
    """main should delegate to print_status."""
    with patch.object(status, "print_status", return_value=1):
        assert status.main() == 1
