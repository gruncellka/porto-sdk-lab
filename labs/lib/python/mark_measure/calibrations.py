"""Load mark calibrations from porto-data marks.json."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def marks_path(porto_data_root: Path, provider: str) -> Path:
    return porto_data_root / "providers" / provider.strip().lower() / "marks.json"


def load_marks(porto_data_root: Path, provider: str) -> dict[str, Any]:
    path = marks_path(porto_data_root, provider)
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def profile_ids(marks: dict[str, Any]) -> set[str]:
    profiles = marks.get("profiles") or []
    return {str(row["id"]) for row in profiles if isinstance(row, dict) and row.get("id")}


def find_calibration(
    marks: dict[str, Any],
    *,
    integration: str,
    voucher_layout: str,
    mime_type: str = "image/png",
    dpi: int = 300,
) -> dict[str, Any] | None:
    for row in marks.get("calibrations") or []:
        if not isinstance(row, dict):
            continue
        if (
            str(row.get("integration")) == integration
            and str(row.get("voucher_layout")) == voucher_layout
            and str(row.get("mime_type")) == mime_type
            and int(row.get("dpi") or 0) == dpi
        ):
            return row
    return None


def expected_dimensions(
    marks: dict[str, Any],
    *,
    integration: str,
    voucher_layout: str,
    mark_profile_id: str | None,
    mime_type: str = "image/png",
    dpi: int = 300,
) -> dict[str, Any] | None:
    calibration = find_calibration(
        marks,
        integration=integration,
        voucher_layout=voucher_layout,
        mime_type=mime_type,
        dpi=dpi,
    )
    if calibration is None:
        return None
    if voucher_layout == "ADDRESS_ZONE":
        canvas = calibration.get("label_canvas")
        return dict(canvas) if isinstance(canvas, dict) else None
    if voucher_layout == "FRANKING_ZONE":
        if not mark_profile_id:
            return None
        by_profile = calibration.get("by_mark_profile") or {}
        entry = by_profile.get(mark_profile_id)
        return dict(entry) if isinstance(entry, dict) else None
    return None
