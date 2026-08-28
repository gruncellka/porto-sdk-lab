"""Tests for labs.lib.python.matrix."""

import json
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from labs.lib.python.matrix import (  # noqa: E402
    build_order_cells_from_wire,
    wire_service_variants,
)


def _porto_data_path() -> Path:
    bundled = _REPO_ROOT / "resources" / "porto-data" / "porto_data"
    if bundled.is_dir():
        return bundled
    raise FileNotFoundError("porto-data not found")


def _graph_path(data_path: Path) -> Path:
    return data_path / "providers" / "deutschepost" / "graph.json"


def test_wire_service_variants_empty() -> None:
    assert wire_service_variants({"base": "x"}) == [()]


def test_wire_service_variants_sorted() -> None:
    zone_wire = {
        "base": "x",
        "services": {"einschreiben": "y", "einschreiben_einwurf": "z"},
    }
    assert wire_service_variants(zone_wire) == [
        (),
        ("einschreiben",),
        ("einschreiben_einwurf",),
    ]


def test_build_order_cells_matches_orders_yaml_count() -> None:
    data_path = _porto_data_path()
    graph_path = _graph_path(data_path)
    cells = build_order_cells_from_wire(graph_path)
    orders_path = _REPO_ROOT / "matrix" / "orders.generated.yaml"
    if not orders_path.is_file():
        pytest.skip("orders.generated.yaml not present")
    text = orders_path.read_text(encoding="utf-8")
    yaml_count = sum(
        1 for line in text.splitlines() if "case_id:" in line and not line.strip().startswith("#")
    )
    assert len(cells) == yaml_count
    assert len(cells) >= 40


def test_cases_generated_json_matches_wire_cells() -> None:
    data_path = _porto_data_path()
    graph_path = _graph_path(data_path)
    cells = build_order_cells_from_wire(graph_path)
    cases_path = _REPO_ROOT / "matrix" / "cases.generated.json"
    if not cases_path.is_file():
        pytest.skip("cases.generated.json not present")
    doc = json.loads(cases_path.read_text(encoding="utf-8"))
    case_ids = {row["case_id"] for row in doc.get("cases", [])}
    assert case_ids == {cell.case_id for cell in cells}


def test_canary_subset_of_orders() -> None:
    try:
        import yaml
    except ImportError:
        pytest.skip("PyYAML not installed")
    matrix_dir = _REPO_ROOT / "matrix"
    canary_path = matrix_dir / "canary.yaml"
    orders_path = matrix_dir / "orders.generated.yaml"
    if not canary_path.is_file() or not orders_path.is_file():
        pytest.skip("matrix files missing")
    canary = yaml.safe_load(canary_path.read_text(encoding="utf-8"))
    orders = yaml.safe_load(
        "\n".join(
            line
            for line in orders_path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        )
    )
    order_ids = {row["case_id"] for row in orders.get("order_cells", [])}
    for case_id in canary.get("case_ids", []):
        assert case_id in order_ids
