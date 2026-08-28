"""Internetmarke matrix identity constants and zone helpers."""

from __future__ import annotations

from labs.lib.python.matrix.zone_lookup import load_scenario_scope, zone_example_country

PROVIDER_DEUTSCHEPOST = "deutschepost"
ADAPTER_INTERNETMARKE = "internetmarke"

_scope = load_scenario_scope()
ZONE_COUNTRY: dict[str, str] = dict(
    (_scope.get("zone_example_country") or {}).get("deutschepost") or {}
)


def zone_country(zone_id: str, *, world_override: str | None = None) -> str:
    return zone_example_country("deutschepost", zone_id, world_override=world_override)
