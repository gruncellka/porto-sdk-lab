"""Tests for labs.lib.python.matrix zone lookup and scenario scope."""

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from labs.lib.python.matrix.zone_lookup import (  # noqa: E402
    country_to_zone,
    load_scenario_scope,
    zone_example_country,
)


def _porto_data_path() -> Path:
    bundled = _REPO_ROOT / "resources" / "porto-data" / "porto_data"
    if bundled.is_dir():
        return bundled
    raise FileNotFoundError("porto-data not found")


def test_scenario_scope_primary_countries() -> None:
    scope = load_scenario_scope()
    assert scope["primary_countries"] == ["DE", "UA", "FR", "US"]


def test_zone_example_country_deutschepost_zone_2_is_ua() -> None:
    assert zone_example_country("deutschepost", "zone_2_europe") == "UA"


def test_country_to_zone_deutschepost_domestic() -> None:
    data_path = _porto_data_path()
    assert country_to_zone("deutschepost", "DE", porto_data_path=data_path) == "domestic"


def test_country_to_zone_deutschepost_ua_is_zone_2() -> None:
    data_path = _porto_data_path()
    assert country_to_zone("deutschepost", "UA", porto_data_path=data_path) == "zone_2_europe"


def test_country_to_zone_swisspost_domestic_ch() -> None:
    data_path = _porto_data_path()
    assert country_to_zone("swisspost", "CH", porto_data_path=data_path) == "domestic"
