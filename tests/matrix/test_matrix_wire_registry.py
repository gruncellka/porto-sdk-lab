"""Tests for labs.lib.python.matrix wire_registry."""

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from labs.lib.python.matrix.wire_registry import discover_wire_adapters  # noqa: E402


def test_discover_wire_adapters_finds_internetmarke() -> None:
    data_path = _REPO_ROOT / "resources" / "porto-data" / "porto_data"
    if not data_path.is_dir():
        pytest.skip("porto-data submodule not present")

    adapters = discover_wire_adapters(data_path)
    assert any(a.provider == "deutschepost" and a.adapter == "internetmarke" for a in adapters)
