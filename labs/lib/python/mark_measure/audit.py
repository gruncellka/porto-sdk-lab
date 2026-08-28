"""Audit matrix run directories: measure stamp.png and compare to porto-data calibrations."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .calibrations import expected_dimensions, load_marks
from .compare import dimensions_from_px, dimensions_match
from .png import read_png_dimensions_from_path
from .resolve import mark_profile_from_artifacts, voucher_layout_from_sdk_input


@dataclass
class CaseMeasureResult:
    case_id: str
    ok: bool
    voucher_layout: str
    mark_profile_id: str | None
    measured: dict[str, Any]
    expected: dict[str, Any] | None
    issues: list[str] = field(default_factory=list)
    error: str | None = None


def verify_case(
    case_dir: Path,
    *,
    marks: dict[str, Any],
    mark_edges: dict[str, dict[str, Any]],
    default_profile_id: str | None,
    integration: str = "internetmarke",
    dpi: int = 300,
    mm_tolerance: float = 0.1,
) -> CaseMeasureResult:
    case_id = case_dir.name
    stamp_path = case_dir / "stamp.png"
    sdk_input_path = case_dir / "sdk_input.json"

    if not stamp_path.is_file():
        return CaseMeasureResult(
            case_id=case_id,
            ok=False,
            voucher_layout="",
            mark_profile_id=None,
            measured={},
            expected=None,
            error="missing stamp.png",
        )
    if not sdk_input_path.is_file():
        return CaseMeasureResult(
            case_id=case_id,
            ok=False,
            voucher_layout="",
            mark_profile_id=None,
            measured={},
            expected=None,
            error="missing sdk_input.json",
        )

    try:
        sdk_input = json.loads(sdk_input_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return CaseMeasureResult(
            case_id=case_id,
            ok=False,
            voucher_layout="",
            mark_profile_id=None,
            measured={},
            expected=None,
            error=f"invalid sdk_input.json: {exc}",
        )

    voucher_layout = voucher_layout_from_sdk_input(sdk_input)
    mark_profile_id = mark_profile_from_artifacts(
        case_dir,
        mark_edges=mark_edges,
        default_profile_id=default_profile_id,
    )

    try:
        width_px, height_px = read_png_dimensions_from_path(stamp_path)
    except (OSError, ValueError) as exc:
        return CaseMeasureResult(
            case_id=case_id,
            ok=False,
            voucher_layout=voucher_layout,
            mark_profile_id=mark_profile_id,
            measured={},
            expected=None,
            error=str(exc),
        )

    measured = dimensions_from_px(width_px, height_px, dpi=dpi)
    measured_dict = {
        "width_px": measured.width_px,
        "height_px": measured.height_px,
        "width_mm": measured.width_mm,
        "height_mm": measured.height_mm,
    }

    expected = expected_dimensions(
        marks,
        integration=integration,
        voucher_layout=voucher_layout,
        mark_profile_id=mark_profile_id,
        dpi=dpi,
    )
    if expected is None:
        return CaseMeasureResult(
            case_id=case_id,
            ok=False,
            voucher_layout=voucher_layout,
            mark_profile_id=mark_profile_id,
            measured=measured_dict,
            expected=None,
            error="no calibration entry in porto-data",
        )

    ok, issues = dimensions_match(measured, expected, mm_tolerance=mm_tolerance)
    return CaseMeasureResult(
        case_id=case_id,
        ok=ok,
        voucher_layout=voucher_layout,
        mark_profile_id=mark_profile_id,
        measured=measured_dict,
        expected=expected,
        issues=issues,
    )


def verify_case_checks(
    case_dir: Path,
    *,
    marks: dict[str, Any],
    mark_edges: dict[str, dict[str, Any]],
    default_profile_id: str | None,
    integration: str = "internetmarke",
    dpi: int = 300,
) -> list[dict[str, Any]]:
    """Validation-style checks for order_matrix strict_validate_case."""
    result = verify_case(
        case_dir,
        marks=marks,
        mark_edges=mark_edges,
        default_profile_id=default_profile_id,
        integration=integration,
        dpi=dpi,
    )
    checks: list[dict[str, Any]] = []
    if result.error:
        checks.append(
            {
                "check": "stamp_measure",
                "expected": "measurable stamp.png",
                "actual": result.error,
                "ok": False,
            }
        )
        return checks

    expected = result.expected or {}
    checks.append(
        {
            "check": "stamp_width_px",
            "expected": expected.get("width_px"),
            "actual": result.measured.get("width_px"),
            "ok": result.measured.get("width_px") == expected.get("width_px"),
        }
    )
    checks.append(
        {
            "check": "stamp_height_px",
            "expected": expected.get("height_px"),
            "actual": result.measured.get("height_px"),
            "ok": result.measured.get("height_px") == expected.get("height_px"),
        }
    )
    return checks


def _load_mark_edges(porto_data_root: Path, provider: str) -> dict[str, dict[str, Any]]:
    graph_path = porto_data_root / "providers" / provider / "graph.json"
    with graph_path.open(encoding="utf-8") as handle:
        graph = json.load(handle)
    edges = graph.get("edges") or {}
    marks_map = edges.get("marks") or {}
    return marks_map if isinstance(marks_map, dict) else {}


def audit_run_dir(
    run_dir: Path,
    *,
    porto_data_root: Path,
    provider: str = "deutschepost",
    integration: str = "internetmarke",
    dpi: int = 300,
    mm_tolerance: float = 0.1,
) -> dict[str, Any]:
    marks = load_marks(porto_data_root, provider)
    mark_edges = _load_mark_edges(porto_data_root, provider)
    default_profile_id = marks.get("default_profile")
    if default_profile_id is not None:
        default_profile_id = str(default_profile_id)

    cases_root = run_dir / "cases"
    case_dirs = sorted(
        path for path in cases_root.iterdir() if path.is_dir() and not path.name.startswith("_")
    )

    case_results: list[dict[str, Any]] = []
    groups: dict[tuple[str, str | None], list[tuple[int, int]]] = defaultdict(list)

    for case_dir in case_dirs:
        result = verify_case(
            case_dir,
            marks=marks,
            mark_edges=mark_edges,
            default_profile_id=default_profile_id,
            integration=integration,
            dpi=dpi,
            mm_tolerance=mm_tolerance,
        )
        payload = {
            "case_id": result.case_id,
            "ok": result.ok,
            "voucher_layout": result.voucher_layout,
            "mark_profile_id": result.mark_profile_id,
            "measured": result.measured,
            "expected": result.expected,
            "issues": result.issues,
            "error": result.error,
        }
        case_results.append(payload)
        if result.measured and not result.error:
            key = (result.voucher_layout, result.mark_profile_id)
            groups[key].append(
                (int(result.measured["width_px"]), int(result.measured["height_px"]))
            )

    summary_groups: list[dict[str, Any]] = []
    consensus_ok = True
    for (voucher_layout, mark_profile_id), sizes in sorted(groups.items()):
        unique = sorted(set(sizes))
        group_ok = len(unique) == 1
        if not group_ok:
            consensus_ok = False
        summary_groups.append(
            {
                "voucher_layout": voucher_layout,
                "mark_profile_id": mark_profile_id,
                "case_count": len(sizes),
                "consensus_px": list(unique[0]) if group_ok else None,
                "unique_px_sizes": unique,
                "ok": group_ok,
            }
        )

    passed = sum(1 for row in case_results if row.get("ok"))
    failed = len(case_results) - passed

    report = {
        "run_dir": str(run_dir),
        "provider": provider,
        "integration": integration,
        "dpi": dpi,
        "cases_total": len(case_results),
        "cases_passed": passed,
        "cases_failed": failed,
        "ok": failed == 0 and consensus_ok,
        "cases": case_results,
    }
    summary = {
        "run_dir": str(run_dir),
        "provider": provider,
        "integration": integration,
        "dpi": dpi,
        "groups": summary_groups,
        "ok": consensus_ok and failed == 0,
    }
    return {"report": report, "summary": summary}


def propose_calibrations_from_runs(
    run_dirs: list[Path],
    *,
    porto_data_root: Path,
    provider: str = "deutschepost",
    integration: str = "internetmarke",
    dpi: int = 300,
) -> list[dict[str, Any]]:
    """Build calibrations[] entries from measured consensus across one or more runs."""
    by_layout: dict[str, dict[str, dict[str, Any]]] = {
        "FRANKING_ZONE": {},
        "ADDRESS_ZONE": {},
    }
    label_canvas: dict[str, Any] | None = None

    for run_dir in run_dirs:
        audit = audit_run_dir(
            run_dir,
            porto_data_root=porto_data_root,
            provider=provider,
            integration=integration,
            dpi=dpi,
        )
        for group in audit["summary"]["groups"]:
            if not group.get("ok") or not group.get("consensus_px"):
                continue
            width_px, height_px = group["consensus_px"]
            dims = dimensions_from_px(width_px, height_px, dpi=dpi)
            entry = {
                "width_px": dims.width_px,
                "height_px": dims.height_px,
                "width_mm": dims.width_mm,
                "height_mm": dims.height_mm,
            }
            layout = group["voucher_layout"]
            if layout == "ADDRESS_ZONE":
                label_canvas = entry
            elif layout == "FRANKING_ZONE":
                profile_id = group.get("mark_profile_id")
                if profile_id:
                    by_layout["FRANKING_ZONE"][str(profile_id)] = entry

    calibrations: list[dict[str, Any]] = []
    if by_layout["FRANKING_ZONE"]:
        calibrations.append(
            {
                "integration": integration,
                "voucher_layout": "FRANKING_ZONE",
                "mime_type": "image/png",
                "dpi": dpi,
                "by_mark_profile": by_layout["FRANKING_ZONE"],
            }
        )
    if label_canvas:
        calibrations.append(
            {
                "integration": integration,
                "voucher_layout": "ADDRESS_ZONE",
                "mime_type": "image/png",
                "dpi": dpi,
                "label_canvas": label_canvas,
            }
        )
    return calibrations


def write_audit_reports(run_dir: Path, audit: dict[str, Any]) -> None:
    report_path = run_dir / "calibration_report.json"
    summary_path = run_dir / "calibration_summary.json"
    report_path.write_text(json.dumps(audit["report"], indent=2) + "\n", encoding="utf-8")
    summary_path.write_text(json.dumps(audit["summary"], indent=2) + "\n", encoding="utf-8")
