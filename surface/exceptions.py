"""Surface contract paths + intentional-difference loaders."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

SURFACE_DIR = Path(__file__).resolve().parent
CONTRACT_DIR = SURFACE_DIR / "contract"
DIFFERENCE_PATH = CONTRACT_DIR / "difference.yml"
CONTRACT_SCHEMA_PATH = CONTRACT_DIR / "schema.yaml"


def load_differences(path: Path | None = None) -> list[dict[str, Any]]:
    target = path or DIFFERENCE_PATH
    raw = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
    items = raw.get("differences") or []
    if not isinstance(items, list):
        raise ValueError("difference.yml: differences must be a list")
    return [item for item in items if isinstance(item, dict)]


def exempt_member_keys(diffs: list[dict[str, Any]] | None = None) -> set[tuple[str, str, str]]:
    """(symbol, member, field) triples that parity must not treat as drift."""
    out: set[tuple[str, str, str]] = set()
    for item in diffs or load_differences():
        symbol = str(item.get("symbol") or "")
        member = str(item.get("member") or "")
        if not symbol or not member:
            continue
        if item.get("parity") == "exempt-async":
            out.add((symbol, member, "async"))
        elif item.get("parity") == "exempt-optional":
            out.add((symbol, member, "optional"))
    return out
