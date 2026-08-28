"""Tests for scripts/lib modules."""

import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from lib import lab_state, make_runner, submodules, workspace  # type: ignore[import-untyped]


def test_get_workspace_root() -> None:
    """Test that get_workspace_root returns correct path."""
    root = workspace.get_workspace_root()
    assert root.exists()
    assert root.is_dir()
    assert (root / "scripts").exists()
    assert (root / "pyproject.toml").exists()


def test_check_venv_exists() -> None:
    """Test check_venv_exists function."""
    root = workspace.get_workspace_root()

    # Test with actual lab root
    result = lab_state.check_venv_exists(root)
    # May or may not exist, but should not crash
    assert isinstance(result, bool)

    # Test with None (auto-detect)
    result = lab_state.check_venv_exists()
    assert isinstance(result, bool)

    # Test with non-existent path
    fake_path = Path("/nonexistent/path")
    result = lab_state.check_venv_exists(fake_path)
    assert result is False


def test_check_submodules_initialized() -> None:
    """Test check_submodules_initialized function."""
    root = workspace.get_workspace_root()

    # Test with actual lab root
    result = lab_state.check_submodules_initialized(root)
    assert isinstance(result, dict)

    # Test with None (auto-detect)
    result = lab_state.check_submodules_initialized()
    assert isinstance(result, dict)

    # Test with temp directory (no .gitmodules)
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        result = lab_state.check_submodules_initialized(tmp_path)
        assert result == {}


def test_check_sdks() -> None:
    """Test check_sdks function."""
    root = workspace.get_workspace_root()

    # Test with actual lab root
    result = lab_state.check_sdks(root)
    assert isinstance(result, dict)

    # Test with None (auto-detect)
    result = lab_state.check_sdks()
    assert isinstance(result, dict)

    # Test with temp directory (no sdks/)
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        result = lab_state.check_sdks(tmp_path)
        assert result == {}


def test_check_resources() -> None:
    """Test check_resources function."""
    root = workspace.get_workspace_root()

    # Test with actual lab root
    result = lab_state.check_resources(root)
    assert isinstance(result, list)

    # Test with None (auto-detect)
    result = lab_state.check_resources()
    assert isinstance(result, list)

    # Test with temp directory (no resources/)
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        result = lab_state.check_resources(tmp_path)
        assert result == []


def test_run_make() -> None:
    """Test run_make function."""
    # Test with help target (should succeed)
    result = make_runner.run_make("help", check=False)
    assert result == 0

    # Test with invalid target (should fail)
    result = make_runner.run_make("nonexistent-target-xyz", check=False)
    assert result != 0


def test_run_make_missing_binary() -> None:
    """run_make should return 1 when make binary is missing."""
    with patch.object(make_runner.subprocess, "run", side_effect=FileNotFoundError):
        assert make_runner.run_make("help", check=False) == 1


def test_parse_gitmodules() -> None:
    """Test parse_gitmodules returns path and url for each submodule."""
    root = workspace.get_workspace_root()
    entries = submodules.parse_gitmodules(root)
    # We have at least porto-data, porto-features, and SDKs
    assert isinstance(entries, list)
    paths = [e.get("path") for e in entries if e.get("path")]
    assert "resources/porto-data" in paths
    assert "resources/porto-features" in paths


def test_parse_gitmodules_empty() -> None:
    """Test parse_gitmodules with no .gitmodules returns []."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = submodules.parse_gitmodules(Path(tmpdir))
        assert result == []


def test_submodules_in_gitmodules_but_not_in_index() -> None:
    """Test detection of submodules in .gitmodules but not in index."""
    root = workspace.get_workspace_root()
    unregistered = submodules.submodules_in_gitmodules_but_not_in_index(root)
    assert isinstance(unregistered, list)
    for u in unregistered:
        assert "path" in u
        assert "url" in u


def test_check_submodules_initialized_git_error(tmp_path: Path) -> None:
    """check_submodules_initialized should return error marker on git failure."""
    (tmp_path / ".gitmodules").write_text("")
    with patch.object(lab_state.subprocess, "run", return_value=MagicMock(returncode=1)):
        result = lab_state.check_submodules_initialized(tmp_path)
    assert result.get("_error") == "error"


def test_get_submodule_paths_in_index_parsing_and_failure(tmp_path: Path) -> None:
    """Parser should read 160000 entries and handle command failure."""
    good = MagicMock(
        returncode=0, stdout="160000 abc\tresources/porto-data\n100644 def\tREADME.md\n"
    )
    with patch.object(submodules.subprocess, "run", return_value=good):
        paths = submodules.get_submodule_paths_in_index(tmp_path)
    assert "resources/porto-data" in paths

    bad = MagicMock(returncode=1, stdout="")
    with patch.object(submodules.subprocess, "run", return_value=bad):
        assert submodules.get_submodule_paths_in_index(tmp_path) == set()
