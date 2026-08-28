"""Stable dot-scoped case_id slugs for adapter order matrix cells."""

from __future__ import annotations


def case_id_for(
    provider: str,
    adapter: str,
    product_id: str,
    zone_id: str,
    service_ids: tuple[str, ...] = (),
) -> str:
    """Build `{provider}.{adapter}.{product_id}.{zone_id}[.{service_id}...]`."""
    return ".".join((provider, adapter, product_id, zone_id, *service_ids))


def parse_case_id(case_id: str) -> tuple[str, str, str, str, tuple[str, ...]]:
    """Parse dot-scoped case_id — tests/diagnostics only, not product runtime."""
    parts = case_id.split(".")
    if len(parts) < 4:
        raise ValueError(f"Invalid case_id (need at least 4 segments): {case_id!r}")
    provider, adapter, product_id, zone_id = parts[0], parts[1], parts[2], parts[3]
    return provider, adapter, product_id, zone_id, tuple(parts[4:])
