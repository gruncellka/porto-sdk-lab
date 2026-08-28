"""Country ↔ zone helpers from porto-data zones.json and Lab scenario_scope.yaml."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]

_MATRIX_DIR = Path(__file__).resolve().parent
_SCENARIO_SCOPE_PATH = _MATRIX_DIR / "scenario_scope.yaml"


@lru_cache(maxsize=1)
def load_scenario_scope() -> dict[str, Any]:
    if yaml is None:
        raise RuntimeError("PyYAML required for scenario_scope.yaml")
    if not _SCENARIO_SCOPE_PATH.is_file():
        return {"primary_countries": ["DE", "UA", "FR", "US"], "zone_example_country": {}}
    doc = yaml.safe_load(_SCENARIO_SCOPE_PATH.read_text(encoding="utf-8"))
    return doc if isinstance(doc, dict) else {}


def zone_example_country(provider: str, zone_id: str, *, world_override: str | None = None) -> str:
    """Example ISO country for a zone in wire/cases JSON (scenario policy, not resolution)."""
    if zone_id == "world" and world_override:
        return world_override
    scope = load_scenario_scope()
    by_provider = scope.get("zone_example_country") or {}
    provider_map = by_provider.get(provider) or {}
    if zone_id in provider_map:
        return str(provider_map[zone_id])
    primary = scope.get("primary_countries") or ["DE"]
    return str(primary[0])


@lru_cache(maxsize=8)
def _provider_home_countries(porto_data_path: str) -> dict[str, str]:
    root = Path(porto_data_path)
    providers_file = root / "providers.json"
    if not providers_file.is_file():
        return {}
    data = json.loads(providers_file.read_text(encoding="utf-8"))
    providers = data.get("providers") or {}
    homes: dict[str, str] = {}
    for provider_id, meta in providers.items():
        if isinstance(meta, dict) and meta.get("country"):
            homes[str(provider_id)] = str(meta["country"]).upper()
    return homes


@lru_cache(maxsize=8)
def _country_to_zone_by_provider(porto_data_path: str) -> dict[str, dict[str, str]]:
    root = Path(porto_data_path)
    providers_dir = root / "providers"
    if not providers_dir.is_dir():
        return {}
    mapping: dict[str, dict[str, str]] = {}
    for provider_dir in sorted(providers_dir.iterdir()):
        if not provider_dir.is_dir():
            continue
        zones_file = provider_dir / "zones.json"
        if not zones_file.is_file():
            continue
        data = json.loads(zones_file.read_text(encoding="utf-8"))
        zones = data.get("zones") or []
        country_map: dict[str, str] = {}
        for zone in zones:
            if not isinstance(zone, dict):
                continue
            zone_id = zone.get("id")
            if not zone_id:
                continue
            for code in zone.get("country_codes") or []:
                if isinstance(code, str):
                    country_map[code.upper()] = str(zone_id)
        mapping[provider_dir.name] = country_map
    return mapping


def country_to_zone(
    provider: str,
    country: str,
    *,
    porto_data_path: Path | None = None,
) -> str | None:
    """Map destination country to zone id for matrix indexing (not SDK resolution)."""
    if not country:
        return None
    country = country.upper()
    if country == "XX":
        return "invalid"

    data_path = porto_data_path
    if data_path is None:
        return None

    path_key = str(data_path.resolve())
    homes = _provider_home_countries(path_key)
    home = homes.get(provider)
    if home and country == home:
        return "domestic"

    zone_maps = _country_to_zone_by_provider(path_key)
    lookup_provider = provider if provider != "global" else "deutschepost"
    provider_zones = zone_maps.get(lookup_provider, {})
    if country in provider_zones:
        return provider_zones[country]

    if provider == "global":
        for prov_zones in zone_maps.values():
            if country in prov_zones:
                return prov_zones[country]
    return None


def clear_caches() -> None:
    """Test helper — reset cached porto-data reads."""
    _provider_home_countries.cache_clear()
    _country_to_zone_by_provider.cache_clear()
    load_scenario_scope.cache_clear()
