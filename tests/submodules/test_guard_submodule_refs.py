"""Tests for scripts/hooks/guard_submodule_refs.py."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import hooks.guard_submodule_refs as guard  # type: ignore[import-untyped]


def _result(code: int = 0, stdout: str = "") -> MagicMock:
    result = MagicMock()
    result.returncode = code
    result.stdout = stdout
    return result


def test_staged_submodule_changes_returns_empty_on_git_error() -> None:
    """Git failures should not block commits."""
    with patch.object(guard.subprocess, "run", return_value=_result(1, "")):
        assert guard._staged_submodule_changes() == []


def test_staged_submodule_changes_parses_gitlink_and_deduplicates() -> None:
    """Parser should capture only gitlink paths and preserve first-seen order."""
    output = "\n".join(
        [
            ":100644 100644 a b M\tREADME.md",
            ":160000 160000 a b M\tresources/porto-data",
            ":160000 100644 a b D\tresources/porto-features",
            ":100644 160000 a b A\tsdks/porto-sdk-python",
            ":160000 160000 a b R100\told/path\tresources/porto-data",
            "not-a-raw-line",
            ":160000 160000 a b M without-tab",
        ]
    )
    with patch.object(guard.subprocess, "run", return_value=_result(0, output)):
        assert guard._staged_submodule_changes() == [
            "resources/porto-data",
            "resources/porto-features",
            "sdks/porto-sdk-python",
        ]


def test_main_allows_override_env_var() -> None:
    """Guard should be bypassed when explicit override is set."""
    with (
        patch.object(guard.os, "getenv", return_value="1"),
        patch.object(guard, "_staged_submodule_changes") as staged_changes,
    ):
        assert guard.main() == 0
        staged_changes.assert_not_called()


def test_main_returns_zero_when_no_staged_gitlinks() -> None:
    """No staged gitlinks should allow commit."""
    with (
        patch.object(guard.os, "getenv", return_value=None),
        patch.object(guard, "_staged_submodule_changes", return_value=[]),
    ):
        assert guard.main() == 0


def test_main_blocks_commit_and_prints_paths(capsys) -> None:
    """Staged gitlinks should block commit and print actionable guidance."""
    with (
        patch.object(guard.os, "getenv", return_value=None),
        patch.object(
            guard,
            "_staged_submodule_changes",
            return_value=["resources/porto-data", "sdks/porto-sdk-python"],
        ),
    ):
        assert guard.main() == 1

    output = capsys.readouterr().out
    assert "Commit blocked" in output
    assert "resources/porto-data" in output
    assert "sdks/porto-sdk-python" in output
    assert "ALLOW_SUBMODULE_POINTER_COMMIT=1 git commit" in output
