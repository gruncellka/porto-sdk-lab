"""Tests for scripts/sync.py."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import sync  # type: ignore[import-untyped]


def _result(code: int = 0, stdout: str = "") -> MagicMock:
    result = MagicMock()
    result.returncode = code
    result.stdout = stdout
    return result


def test_get_submodule_status_parsing() -> None:
    """Parser should classify ok, uninitialized and modified statuses."""
    output = " 12345678 resources/porto-data (heads/main)\n-abcdef12 sdks/porto-sdk-python\n+feedbeef sdks/porto-sdk-typescript"
    with patch.object(sync.subprocess, "run", return_value=_result(0, output)):
        status_list = sync.get_submodule_status(Path("."))
    assert len(status_list) == 3
    assert status_list[0]["status"] == "ok"
    assert status_list[1]["status"] == "uninitialized"
    assert status_list[2]["status"] == "modified"


def test_get_submodule_status_on_git_error() -> None:
    """Git status errors should return empty list."""
    with patch.object(sync.subprocess, "run", return_value=_result(1, "")):
        assert sync.get_submodule_status(Path(".")) == []


def test_print_submodule_status_empty(capsys) -> None:
    """Printer should handle empty list."""
    sync.print_submodule_status([], "Title")
    captured = capsys.readouterr().out
    assert "(no submodules found)" in captured


def test_print_submodule_status_with_nested(capsys) -> None:
    """Printer should include nested subsection when nested paths exist."""
    sync.print_submodule_status(
        [
            {"path": "resources/porto-data", "commit": "11111111", "status": "ok"},
            {
                "path": "sdks/porto-sdk-python/resources/porto-data",
                "commit": "22222222",
                "status": "modified",
            },
        ],
        "Title",
    )
    captured = capsys.readouterr().out
    assert "Root-level submodules" in captured
    assert "Nested submodules (inside SDKs)" in captured
    assert "[!]" in captured


def test_main_no_gitmodules(tmp_path: Path) -> None:
    """main should no-op when .gitmodules is missing."""
    (tmp_path / ".git").mkdir()
    with (
        patch.object(sys, "argv", ["sync.py"]),
        patch.object(sync, "get_workspace_root", return_value=tmp_path),
    ):
        assert sync.main() == 0


def test_main_not_git_repo(tmp_path: Path) -> None:
    """main should no-op when .git is missing."""
    (tmp_path / ".gitmodules").write_text("")
    with (
        patch.object(sys, "argv", ["sync.py"]),
        patch.object(sync, "get_workspace_root", return_value=tmp_path),
    ):
        assert sync.main() == 0


def test_main_remote_mode_success_with_changes(tmp_path: Path) -> None:
    """Remote mode should run and return 0 on success."""
    (tmp_path / ".gitmodules").write_text("")
    (tmp_path / ".git").mkdir()

    with (
        patch.object(sys, "argv", ["sync.py", "--remote"]),
        patch.object(sync, "get_workspace_root", return_value=tmp_path),
        patch.object(sync, "submodules_in_gitmodules_but_not_in_index", return_value=[]),
        patch.object(
            sync,
            "get_submodule_status",
            side_effect=[
                [{"path": "a", "commit": "11111111", "status": "ok"}],
                [{"path": "a", "commit": "22222222", "status": "ok"}],
            ],
        ),
        patch.object(sync.subprocess, "run", return_value=_result(0, "")),
    ):
        assert sync.main() == 0


def test_main_update_error_path(tmp_path: Path) -> None:
    """If git submodule update fails, main should still complete with 0."""
    (tmp_path / ".gitmodules").write_text("")
    (tmp_path / ".git").mkdir()
    with (
        patch.object(sys, "argv", ["sync.py"]),
        patch.object(sync, "get_workspace_root", return_value=tmp_path),
        patch.object(
            sync,
            "submodules_in_gitmodules_but_not_in_index",
            return_value=[{"path": "x", "url": "u"}],
        ),
        patch.object(sync, "get_submodule_status", return_value=[]),
        patch.object(sync.subprocess, "run", return_value=_result(1, "")),
    ):
        assert sync.main() == 0


def test_get_submodule_paths_parsing() -> None:
    """Submodule path parser should extract path column."""
    output = " 12345678 resources/porto-data (heads/main)\n-abcdef12 sdks/porto-sdk-python"
    with patch.object(sync.subprocess, "run", return_value=_result(0, output)):
        paths = sync.get_submodule_paths(Path("."))
    assert paths == ["resources/porto-data", "sdks/porto-sdk-python"]


def test_get_submodule_paths_git_error() -> None:
    """Submodule path parser should return empty list on git error."""
    with patch.object(sync.subprocess, "run", return_value=_result(1, "")):
        assert sync.get_submodule_paths(Path(".")) == []


def test_is_submodule_dirty_handles_git_error_and_clean_output() -> None:
    """Dirty checker should handle git errors and clean output."""
    with patch.object(sync.subprocess, "run", return_value=_result(1, "")):
        assert sync.is_submodule_dirty(Path("."), "sdks/porto-sdk-python") is False
    with patch.object(sync.subprocess, "run", return_value=_result(0, "")):
        assert sync.is_submodule_dirty(Path("."), "sdks/porto-sdk-python") is False


def test_is_submodule_dirty_true_on_porcelain_output() -> None:
    """Dirty checker should report true when porcelain output is non-empty."""
    with patch.object(sync.subprocess, "run", return_value=_result(0, " M file.py\n")):
        assert sync.is_submodule_dirty(Path("."), "sdks/porto-sdk-python") is True


def test_stash_submodule_changes_create_failure_returns_none() -> None:
    """Stash helper should return None when stash push fails."""
    with patch.object(sync.subprocess, "run", return_value=_result(1, "")):
        assert sync.stash_submodule_changes(Path("."), "sdks/porto-sdk-python") is None


def test_stash_submodule_changes_list_failure_returns_none() -> None:
    """Stash helper should return None when stash list fails."""
    with patch.object(
        sync.subprocess,
        "run",
        side_effect=[_result(0, ""), _result(1, "")],
    ):
        assert sync.stash_submodule_changes(Path("."), "sdks/porto-sdk-python") is None


def test_stash_submodule_changes_returns_matching_ref() -> None:
    """Stash helper should find matching marker ref and skip malformed lines."""
    with (
        patch.object(sync.uuid, "uuid4", return_value="abc123"),
        patch.object(
            sync.subprocess,
            "run",
            side_effect=[
                _result(0, ""),
                _result(
                    0,
                    "stash@{2} no-tab-format\n"
                    "stash@{1}\tother-marker\n"
                    "stash@{0}\tOn main: porto-sdk-lab-autostash-abc123\n",
                ),
            ],
        ),
    ):
        ref = sync.stash_submodule_changes(Path("."), "sdks/porto-sdk-python")
    assert ref == "stash@{0}"


def test_restore_submodule_stash_apply_failure() -> None:
    """Restore helper should return false when apply fails."""
    with patch.object(sync.subprocess, "run", return_value=_result(1, "")) as run_mock:
        assert (
            sync.restore_submodule_stash(Path("."), "sdks/porto-sdk-python", "stash@{0}") is False
        )
        assert run_mock.call_count == 1


def test_restore_submodule_stash_success_drops_stash() -> None:
    """Restore helper should apply then drop stash on success."""
    with patch.object(
        sync.subprocess,
        "run",
        side_effect=[_result(0, ""), _result(0, "")],
    ) as run_mock:
        assert sync.restore_submodule_stash(Path("."), "sdks/porto-sdk-python", "stash@{0}") is True
        assert run_mock.call_count == 2


def test_main_autostash_stash_and_restore(tmp_path: Path) -> None:
    """Autostash should stash dirty submodules and restore afterwards."""
    (tmp_path / ".gitmodules").write_text("")
    (tmp_path / ".git").mkdir()
    with (
        patch.object(sys, "argv", ["sync.py", "--autostash"]),
        patch.object(sync, "get_workspace_root", return_value=tmp_path),
        patch.object(sync, "submodules_in_gitmodules_but_not_in_index", return_value=[]),
        patch.object(sync, "get_submodule_status", return_value=[]),
        patch.object(sync, "get_submodule_paths", return_value=["sdks/porto-sdk-python"]),
        patch.object(sync, "is_submodule_dirty", return_value=True),
        patch.object(sync, "stash_submodule_changes", return_value="stash@{0}"),
        patch.object(sync, "restore_submodule_stash", return_value=True) as restore_mock,
        patch.object(sync.subprocess, "run", return_value=_result(0, "")),
    ):
        assert sync.main() == 0
        restore_mock.assert_called_once_with(tmp_path, "sdks/porto-sdk-python", "stash@{0}")
