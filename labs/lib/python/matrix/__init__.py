"""Porto SDK Lab matrix tooling — sdk.yaml and wire order sync."""

from labs.lib.python.matrix.case_id import case_id_for, parse_case_id
from labs.lib.python.matrix.constants import (
    ADAPTER_INTERNETMARKE,
    PROVIDER_DEUTSCHEPOST,
    ZONE_COUNTRY,
    zone_country,
)
from labs.lib.python.matrix.orders_sync import (
    OrderCell,
    build_all_order_cells,
    build_order_cells_for_adapter,
    build_order_cells_from_graph,
    build_order_cells_from_wire,
    cells_to_json,
    cells_to_yaml_rows,
    example_row_for_cell,
    sync_orders,
    wire_service_variants,
)
from labs.lib.python.matrix.sdk_sync import dump_sdk_yaml, scan_sdk_features, write_sdk_matrix
from labs.lib.python.matrix.wire_registry import WireAdapter, discover_wire_adapters
from labs.lib.python.matrix.zone_lookup import (
    country_to_zone,
    load_scenario_scope,
    zone_example_country,
)

__all__ = [
    "ADAPTER_INTERNETMARKE",
    "OrderCell",
    "PROVIDER_DEUTSCHEPOST",
    "WireAdapter",
    "ZONE_COUNTRY",
    "build_all_order_cells",
    "build_order_cells_for_adapter",
    "build_order_cells_from_graph",
    "build_order_cells_from_wire",
    "case_id_for",
    "cells_to_json",
    "cells_to_yaml_rows",
    "country_to_zone",
    "discover_wire_adapters",
    "dump_sdk_yaml",
    "example_row_for_cell",
    "load_scenario_scope",
    "parse_case_id",
    "scan_sdk_features",
    "sync_orders",
    "wire_service_variants",
    "write_sdk_matrix",
    "zone_country",
    "zone_example_country",
]
