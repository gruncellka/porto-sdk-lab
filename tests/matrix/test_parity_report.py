"""Tests for scripts/parity-report.py."""

import importlib.util
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_PARITY_PATH = _REPO_ROOT / "scripts" / "parity-report.py"
_SPEC = importlib.util.spec_from_file_location("parity_report", _PARITY_PATH)
assert _SPEC and _SPEC.loader
parity_report = importlib.util.module_from_spec(_SPEC)
sys.modules["parity_report"] = parity_report
_SPEC.loader.exec_module(parity_report)


def test_normalize_step_replaces_placeholders() -> None:
    assert parity_report._normalize_step('Given provider is "deutschepost"') == "provider is *"


def test_collect_feature_steps_includes_sdk_features() -> None:
    features = parity_report._collect_feature_steps()
    assert any(path.endswith("resolution.feature") for path in features)


def test_build_report_has_summary() -> None:
    report, rows = parity_report.build_report()
    assert "# BDD step parity report" in report
    assert "## Summary" in report
    assert isinstance(rows, list)
