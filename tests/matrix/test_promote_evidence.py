"""Tests for scripts/labs/promote-evidence.py."""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_PROMOTE_PATH = _REPO_ROOT / "scripts" / "labs" / "promote-evidence.py"
_SPEC = importlib.util.spec_from_file_location("promote_evidence", _PROMOTE_PATH)
assert _SPEC and _SPEC.loader
promote_evidence = importlib.util.module_from_spec(_SPEC)
sys.modules["promote_evidence"] = promote_evidence
_SPEC.loader.exec_module(promote_evidence)


def test_resolve_case_id_from_legacy_sdk_input(tmp_path: Path) -> None:
    case_dir = tmp_path / "legacy_case"
    case_dir.mkdir()
    (case_dir / "sdk_input.json").write_text(
        json.dumps(
            {
                "case_id": "standardbrief_zone_2_europe",
                "product_id": "standardbrief",
                "zone_id": "zone_2_europe",
                "service_ids": [],
            }
        ),
        encoding="utf-8",
    )
    assert (
        promote_evidence._resolve_case_id(case_dir)
        == "deutschepost.internetmarke.standardbrief.zone_2_europe"
    )


def test_collect_green_cases_from_fixture(tmp_path: Path) -> None:
    run_dir = tmp_path / "run-1"
    case_dir = run_dir / "cases" / "legacy_case"
    case_dir.mkdir(parents=True)
    (case_dir / "validation.json").write_text(
        json.dumps({"ok": True}),
        encoding="utf-8",
    )
    (case_dir / "sdk_input.json").write_text(
        json.dumps(
            {
                "case_id": "legacy_case",
                "product_id": "standardbrief",
                "zone_id": "domestic",
                "service_ids": [],
            }
        ),
        encoding="utf-8",
    )

    green = promote_evidence._collect_green_cases(run_dir, case_filter=None)
    assert "deutschepost.internetmarke.standardbrief.domestic" in green


def test_promote_run_dry_run_uses_existing_lab_run() -> None:
    run_id = "20260707-131725-1c3"
    run_dir = _REPO_ROOT / "labs" / "experiments" / "runs" / run_id
    if not run_dir.is_dir():
        pytest.skip("sample lab run not present")
    assert promote_evidence.promote_run(run_id, dry_run=True) == 0
