"""Parity tests for Python vs TypeScript matrix case sets."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from labs.lib.python.matrix import build_order_cells_from_wire  # noqa: E402


def _porto_data_path() -> Path:
    bundled = _REPO_ROOT / "resources" / "porto-data" / "porto_data"
    if bundled.is_dir():
        return bundled
    raise FileNotFoundError("porto-data not found")


def test_order_cells_json_matches_wire_graph() -> None:
    graph_path = _porto_data_path() / "providers" / "deutschepost" / "graph.json"
    cells = build_order_cells_from_wire(graph_path)
    cases_path = _REPO_ROOT / "matrix" / "cases.generated.json"
    if not cases_path.is_file():
        pytest.skip("cases.generated.json not present")
    doc = json.loads(cases_path.read_text(encoding="utf-8"))
    json_ids = {row["case_id"] for row in doc.get("cases", [])}
    wire_ids = {cell.case_id for cell in cells}
    assert json_ids == wire_ids
    assert len(json_ids) >= 40


def test_service_variant_cells_present() -> None:
    graph_path = _porto_data_path() / "providers" / "deutschepost" / "graph.json"
    cells = build_order_cells_from_wire(graph_path)
    with_services = [cell for cell in cells if cell.service_ids]
    assert len(with_services) >= 20, "expected wire service variants in matrix cells"
