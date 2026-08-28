#!/usr/bin/env python3
"""
Sync Lab matrix/orders.generated.yaml from porto-data wire graph.

Input: porto-data catalog (never lab run output).
Output: committed YAML/JSON under Lab matrix/ (not shipped in porto-features).

Also emits cases.generated.json for TS lab parity and regenerates adapter Gherkin Examples.

Usage (from Porto SDK Lab root):
  python scripts/matrix-orders-sync.py
  python scripts/matrix-orders-sync.py --check
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from labs.lib.python.matrix.orders_sync import (  # noqa: E402
    build_all_order_cells,
    cells_to_yaml_rows,
    load_evidence_by_case_id,
    load_yaml_doc,
    provider_catalog_context,
    render_cases_json,
    semantic_orders_payload,
    sync_orders,
    wire_cell_payload,
)


def _porto_data_path() -> Path:
    env = __import__("os").environ.get("PORTO_DATA_PATH")
    if env:
        candidate = Path(env).expanduser().resolve()
        if (candidate / "mappings.json").exists() or (candidate / "metadata.json").exists():
            return candidate
    bundled = _REPO_ROOT / "resources" / "porto-data" / "porto_data"
    if bundled.is_dir():
        return bundled
    raise FileNotFoundError(
        "porto-data not found. Set PORTO_DATA_PATH or run from Lab with resources/porto-data submodule."
    )


def _porto_features_root() -> Path:
    env = __import__("os").environ.get("PORTO_FEATURES_PATH")
    if env:
        candidate = Path(env).expanduser().resolve()
        if (candidate / "features").is_dir():
            return candidate
        if (candidate / "porto_features" / "features").is_dir():
            return candidate / "porto_features"
    bundled = _REPO_ROOT / "resources" / "porto-features" / "porto_features"
    if bundled.is_dir():
        return bundled
    raise FileNotFoundError("porto-features not found. Set PORTO_FEATURES_PATH or run from Lab.")


def _lab_matrix_dir() -> Path:
    return _REPO_ROOT / "matrix"


def _orders_output_path() -> Path:
    return _lab_matrix_dir() / "orders.generated.yaml"


def _cases_json_output_path() -> Path:
    return _lab_matrix_dir() / "cases.generated.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync orders.generated.yaml from porto-data wire.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 if committed files differ from porto-data sync.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output orders YAML path (default: matrix/orders.generated.yaml)",
    )
    args = parser.parse_args()

    data_path = _porto_data_path()
    features_root = _porto_features_root()
    orders_output = args.output or _orders_output_path()
    cases_json_output = _cases_json_output_path()

    cells = build_all_order_cells(data_path)
    evidence_by_case_id = load_evidence_by_case_id(orders_output)
    yaml_rows = cells_to_yaml_rows(cells, evidence_by_case_id=evidence_by_case_id)
    weight_tiers_by_provider, graph_links_by_provider = provider_catalog_context(data_path, cells)
    cases_json = render_cases_json(
        cells,
        weight_tiers_by_provider=weight_tiers_by_provider,
        graph_links_by_provider=graph_links_by_provider,
    )

    if args.check:
        existing = orders_output.read_text(encoding="utf-8") if orders_output.is_file() else ""
        existing_doc = load_yaml_doc(existing)
        existing_doc.pop("generated_at", None)
        if isinstance(existing_doc.get("order_cells"), list):
            existing_doc["order_cells"] = [
                wire_cell_payload(row)
                for row in existing_doc["order_cells"]
                if isinstance(row, dict)
            ]
        fresh_doc = semantic_orders_payload(yaml_rows)
        if existing_doc != fresh_doc:
            print(f"❌ {orders_output} is out of sync with porto-data wire ({len(cells)} cells).")
            print("   Run: make matrix-orders-sync")
            return 1

        if cases_json_output.is_file():
            existing_cases = json.loads(cases_json_output.read_text(encoding="utf-8"))
            existing_cases.pop("generated_at", None)
            fresh_cases = json.loads(cases_json)
            fresh_cases.pop("generated_at", None)
            if existing_cases != fresh_cases:
                print(f"❌ {cases_json_output} is out of sync with porto-data wire.")
                print("   Run: make matrix-orders-sync")
                return 1

        print(f"✅ {orders_output} matches porto-data wire ({len(cells)} cells).")
        return 0

    _, updated_features = sync_orders(
        data_path,
        orders_output=orders_output,
        cases_json_output=cases_json_output,
        features_root=features_root / "features",
    )
    print(f"✅ Wrote {len(cells)} order_cells to {orders_output}")
    print(f"✅ Wrote {len(cells)} cases to {cases_json_output}")
    for feature_path in updated_features:
        print(f"✅ Updated adapter Examples in {feature_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
