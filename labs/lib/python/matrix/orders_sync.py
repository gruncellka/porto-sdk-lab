"""porto-data wire graph → order cells, YAML, JSON, and adapter Gherkin Examples."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]

from labs.lib.python.matrix.case_id import case_id_for
from labs.lib.python.matrix.wire_registry import WireAdapter, discover_wire_adapters
from labs.lib.python.matrix.zone_lookup import zone_example_country

WIRE_CELL_FIELDS = (
    "case_id",
    "provider",
    "adapter",
    "product_id",
    "zone_id",
    "service_ids",
    "layout_profiles",
    "status",
    "refs",
)


def wire_service_variants(zone_wire: dict[str, Any]) -> list[tuple[str, ...]]:
    """Base product plus each wired service SKU (one service per purchase)."""
    variants: list[tuple[str, ...]] = [()]
    services = zone_wire.get("services")
    if isinstance(services, dict):
        for service_id in sorted(services):
            if services[service_id] is not None:
                variants.append((service_id,))
    return variants


@dataclass(frozen=True)
class OrderCell:
    case_id: str
    provider: str
    adapter: str
    product_id: str
    zone_id: str
    service_ids: tuple[str, ...]


def build_order_cells_from_graph(
    graph: dict[str, Any],
    *,
    provider: str,
    adapter: str,
) -> list[OrderCell]:
    """Build order cells from parsed graph.json for one wire adapter."""
    edges = graph.get("edges") or {}
    products_raw = edges.get("products")
    links: dict[str, Any] = products_raw if isinstance(products_raw, dict) else {}
    wire = (edges.get("wire") or {}).get(adapter) or {}
    cells: list[OrderCell] = []

    for product_id, zones in wire.items():
        if not isinstance(zones, dict):
            continue
        raw_link = links.get(product_id)
        product_link = raw_link if isinstance(raw_link, dict) else {}
        allowed_zones = set(product_link.get("zones", []))
        for zone_id, zone_wire in zones.items():
            if zone_id not in allowed_zones or not isinstance(zone_wire, dict):
                continue
            if zone_wire.get("base") is None:
                continue
            for service_ids in wire_service_variants(zone_wire):
                cells.append(
                    OrderCell(
                        case_id=case_id_for(
                            provider, adapter, product_id, zone_id, service_ids
                        ),
                        provider=provider,
                        adapter=adapter,
                        product_id=product_id,
                        zone_id=zone_id,
                        service_ids=service_ids,
                    )
                )

    cells.sort(key=lambda item: item.case_id)
    return cells


def build_order_cells_for_adapter(
    graph_path: Path,
    *,
    provider: str,
    adapter: str,
) -> list[OrderCell]:
    data = json.loads(graph_path.read_text(encoding="utf-8"))
    return build_order_cells_from_graph(data, provider=provider, adapter=adapter)


def build_all_order_cells(porto_data_path: Path) -> list[OrderCell]:
    """Aggregate wire cells for every adapter discovered in porto-data."""
    all_cells: list[OrderCell] = []
    for entry in discover_wire_adapters(porto_data_path):
        graph_path = entry.graph_path(porto_data_path)
        if not graph_path.is_file():
            continue
        all_cells.extend(
            build_order_cells_for_adapter(
                graph_path, provider=entry.provider, adapter=entry.adapter
            )
        )
    all_cells.sort(key=lambda item: item.case_id)
    return all_cells


def build_order_cells_from_wire(graph_path: Path) -> list[OrderCell]:
    """Backward-compatible: deutschepost/internetmarke from a graph path."""
    return build_order_cells_for_adapter(
        graph_path, provider="deutschepost", adapter="internetmarke"
    )


def load_weight_tiers(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        tiers = data.get("weight_tiers") or data.get("tiers") or []
        return tiers if isinstance(tiers, list) else []
    return []


def graph_product_links(graph_path: Path) -> dict[str, Any]:
    data = json.loads(graph_path.read_text(encoding="utf-8"))
    edges = data.get("edges") or {}
    links = edges.get("products")
    return links if isinstance(links, dict) else {}


def min_weight_for_tier(tier_id: str, tiers: list[dict[str, Any]]) -> int:
    sorted_tiers = sorted(tiers, key=lambda row: row.get("max_weight", 0))
    prev_max = 0
    for tier in sorted_tiers:
        if tier.get("id") == tier_id:
            return max(1, prev_max + 1) if prev_max else 1
        prev_max = int(tier.get("max_weight", 0))
    return 1


def example_row_for_cell(
    cell: OrderCell,
    *,
    weight_tiers: list[dict[str, Any]],
    graph_links: dict[str, Any],
) -> dict[str, str | int]:
    product_link = graph_links.get(cell.product_id, {})
    weight_tier_id = (product_link.get("weight_tiers") or ["W0020"])[0]
    weight = min_weight_for_tier(weight_tier_id, weight_tiers)
    service_ids = ",".join(cell.service_ids) if cell.service_ids else ""
    return {
        "product_id": cell.product_id,
        "zone_id": cell.zone_id,
        "country_code": zone_example_country(cell.provider, cell.zone_id),
        "weight": weight,
        "service_ids": service_ids,
    }


def cells_to_json(
    cells: list[OrderCell],
    *,
    weight_tiers_by_provider: dict[str, list[dict[str, Any]]],
    graph_links_by_provider: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for cell in cells:
        weight_tiers = weight_tiers_by_provider.get(cell.provider, [])
        graph_links = graph_links_by_provider.get(cell.provider, {})
        example = example_row_for_cell(
            cell, weight_tiers=weight_tiers, graph_links=graph_links
        )
        rows.append(
            {
                "case_id": cell.case_id,
                "product_id": cell.product_id,
                "zone_id": cell.zone_id,
                "service_ids": list(cell.service_ids),
                "country_code": example["country_code"],
                "weight": example["weight"],
            }
        )
    return rows


def adapter_feature_ref(provider: str, adapter: str) -> str:
    return f"adapters/{provider}/{adapter}.feature:Outline:stamp_order"


def cells_to_yaml_rows(
    cells: list[OrderCell],
    *,
    evidence_by_case_id: dict[str, dict] | None = None,
) -> list[dict]:
    evidence_lookup = evidence_by_case_id or {}
    rows: list[dict] = []
    for cell in cells:
        preserved = evidence_lookup.get(cell.case_id, {})
        rows.append(
            {
                "case_id": cell.case_id,
                "provider": cell.provider,
                "adapter": cell.adapter,
                "product_id": cell.product_id,
                "zone_id": cell.zone_id,
                "service_ids": list(cell.service_ids),
                "layout_profiles": ["ADDRESS_ZONE", "FRANKING_ZONE"],
                "status": "required",
                "refs": [adapter_feature_ref(cell.provider, cell.adapter)],
                "evidence": preserved.get("evidence"),
                "last_verified": preserved.get("last_verified"),
            }
        )
    return rows


def wire_cell_payload(row: dict) -> dict:
    return {field: row.get(field) for field in WIRE_CELL_FIELDS}


def semantic_orders_payload(yaml_rows: list[dict]) -> dict:
    return {
        "schema_version": 1,
        "source": "porto-data graph.edges.wire",
        "order_cells": [wire_cell_payload(row) for row in yaml_rows],
    }


def render_orders_yaml(yaml_rows: list[dict]) -> str:
    if yaml is None:
        raise RuntimeError("PyYAML required for orders YAML output")
    payload = {
        **semantic_orders_payload(yaml_rows),
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    header = (
        "# GENERATED by Porto SDK Lab scripts/matrix-orders-sync.py — do not hand-edit case_ids.\n"
        "# Re-run from Lab root after porto-data wire changes.\n"
    )
    return header + yaml.dump(payload, sort_keys=False, allow_unicode=True, default_flow_style=False)


def render_cases_json(
    cells: list[OrderCell],
    *,
    weight_tiers_by_provider: dict[str, list[dict[str, Any]]],
    graph_links_by_provider: dict[str, dict[str, Any]],
) -> str:
    payload = {
        "schema_version": 1,
        "source": "porto-data graph.edges.wire",
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "cases": cells_to_json(
            cells,
            weight_tiers_by_provider=weight_tiers_by_provider,
            graph_links_by_provider=graph_links_by_provider,
        ),
    }
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def render_gherkin_examples(
    cells: list[OrderCell],
    *,
    weight_tiers: list[dict[str, Any]],
    graph_links: dict[str, Any],
) -> str:
    header = "      | product_id | zone_id | country_code | weight | service_ids |\n"
    rows: list[str] = []
    for cell in cells:
        row = example_row_for_cell(
            cell, weight_tiers=weight_tiers, graph_links=graph_links
        )
        service_ids = row["service_ids"] or ""
        rows.append(
            f'      | {row["product_id"]} | {row["zone_id"]} | {row["country_code"]} | {row["weight"]} | {service_ids} |'
        )
    return header + "\n".join(rows) + "\n"


def update_adapter_feature_examples(
    cells: list[OrderCell],
    *,
    weight_tiers: list[dict[str, Any]],
    graph_links: dict[str, Any],
    feature_path: Path,
) -> bool:
    if not feature_path.is_file():
        return False
    text = feature_path.read_text(encoding="utf-8")
    marker_start = "    Examples:\n"
    outline_marker = "  Scenario Outline: stamp_order\n"
    if outline_marker not in text or marker_start not in text:
        return False

    outline_start = text.index(outline_marker)
    examples_start = text.index(marker_start, outline_start)
    examples_body_start = examples_start + len(marker_start)

    rest = text[examples_body_start:]
    end_offset = 0
    for line in rest.splitlines(keepends=True):
        if line.strip() == "" or (line.startswith("  ") and not line.startswith("      ")):
            break
        end_offset += len(line)

    new_examples = render_gherkin_examples(
        cells, weight_tiers=weight_tiers, graph_links=graph_links
    )
    new_text = text[:examples_body_start] + new_examples + rest[end_offset:]
    if new_text == text:
        return False
    feature_path.write_text(new_text, encoding="utf-8")
    return True


def load_yaml_doc(text: str) -> dict:
    if yaml is None:
        return {}
    lines = [
        line for line in text.splitlines() if line.strip() and not line.strip().startswith("#")
    ]
    doc = yaml.safe_load("\n".join(lines))
    return doc if isinstance(doc, dict) else {}


def load_evidence_by_case_id(path: Path) -> dict[str, dict]:
    if not path.is_file():
        return {}
    doc = load_yaml_doc(path.read_text(encoding="utf-8"))
    order_cells = doc.get("order_cells")
    if not isinstance(order_cells, list):
        return {}
    lookup: dict[str, dict] = {}
    for row in order_cells:
        if not isinstance(row, dict):
            continue
        case_id = row.get("case_id")
        if not isinstance(case_id, str):
            continue
        lookup[case_id] = {
            "evidence": row.get("evidence"),
            "last_verified": row.get("last_verified"),
        }
    return lookup


def provider_catalog_context(
    porto_data_path: Path,
    cells: list[OrderCell],
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, dict[str, Any]]]:
    weight_tiers_by_provider: dict[str, list[dict[str, Any]]] = {}
    graph_links_by_provider: dict[str, dict[str, Any]] = {}
    providers = {cell.provider for cell in cells}
    for provider in providers:
        provider_dir = porto_data_path / "providers" / provider
        weight_tiers_by_provider[provider] = load_weight_tiers(provider_dir / "weights.json")
        graph_path = provider_dir / "graph.json"
        if graph_path.is_file():
            graph_links_by_provider[provider] = graph_product_links(graph_path)
        else:
            graph_links_by_provider[provider] = {}
    return weight_tiers_by_provider, graph_links_by_provider


def sync_orders(
    porto_data_path: Path,
    *,
    orders_output: Path,
    cases_json_output: Path,
    features_root: Path,
) -> tuple[list[OrderCell], list[Path]]:
    cells = build_all_order_cells(porto_data_path)
    evidence_by_case_id = load_evidence_by_case_id(orders_output)
    yaml_rows = cells_to_yaml_rows(cells, evidence_by_case_id=evidence_by_case_id)
    weight_tiers_by_provider, graph_links_by_provider = provider_catalog_context(
        porto_data_path, cells
    )

    orders_output.parent.mkdir(parents=True, exist_ok=True)
    orders_output.write_text(render_orders_yaml(yaml_rows), encoding="utf-8")
    cases_json_output.write_text(
        render_cases_json(
            cells,
            weight_tiers_by_provider=weight_tiers_by_provider,
            graph_links_by_provider=graph_links_by_provider,
        ),
        encoding="utf-8",
    )

    updated_features: list[Path] = []
    by_adapter: dict[tuple[str, str], list[OrderCell]] = {}
    for cell in cells:
        by_adapter.setdefault((cell.provider, cell.adapter), []).append(cell)

    for (provider, adapter), adapter_cells in by_adapter.items():
        feature_path = features_root / "adapters" / provider / f"{adapter}.feature"
        weight_tiers = weight_tiers_by_provider.get(provider, [])
        graph_links = graph_links_by_provider.get(provider, {})
        if update_adapter_feature_examples(
            adapter_cells,
            weight_tiers=weight_tiers,
            graph_links=graph_links,
            feature_path=feature_path,
        ):
            updated_features.append(feature_path)

    return cells, updated_features
