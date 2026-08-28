"""Resolve mark_profile_id from matrix case artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from porto_sdk.services.mark_resolution import resolve_mark_profile_id


def voucher_layout_from_sdk_input(sdk_input: dict[str, Any]) -> str:
    """Internetmarke ``voucherLayout`` from matrix artifacts (not a Porto field)."""
    raw = sdk_input.get("voucher_layout")
    if raw in ("FRANKING_ZONE", "ADDRESS_ZONE"):
        return str(raw)
    if sdk_input.get("mark_type") == "label":
        return "ADDRESS_ZONE"
    return "FRANKING_ZONE"


def mark_profile_from_artifacts(
    case_dir: Path,
    *,
    mark_edges: dict[str, dict[str, Any]],
    default_profile_id: str | None,
) -> str | None:
    output_path = case_dir / "sdk_output.json"
    if output_path.is_file():
        try:
            output = json.loads(output_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            output = {}
        profile_id = output.get("mark_profile_id")
        if profile_id:
            return str(profile_id)

    input_path = case_dir / "sdk_input.json"
    if not input_path.is_file():
        return default_profile_id
    try:
        sdk_input = json.loads(input_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default_profile_id

    zone_id = sdk_input.get("zone_id")
    service_ids = list(sdk_input.get("service_ids") or [])
    return resolve_mark_profile_id(
        mark_edges=mark_edges,
        zone_id=str(zone_id) if zone_id else None,
        service_ids=service_ids,
        default_profile_id=default_profile_id,
    )
