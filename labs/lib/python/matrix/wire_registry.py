"""Discover wired adapters from porto-data execution.json + graph.edges.wire."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WireAdapter:
    provider: str
    adapter: str

    def graph_path(self, porto_data_path: Path) -> Path:
        return porto_data_path / "providers" / self.provider / "graph.json"

    def weight_tiers_path(self, porto_data_path: Path) -> Path:
        return porto_data_path / "providers" / self.provider / "weights.json"

    def execution_path(self, porto_data_path: Path) -> Path:
        return porto_data_path / "providers" / self.provider / "execution.json"


def discover_wire_adapters(porto_data_path: Path) -> list[WireAdapter]:
    """Return (provider, adapter) pairs with non-empty graph.edges.wire[adapter]."""
    providers_dir = porto_data_path / "providers"
    if not providers_dir.is_dir():
        return []

    adapters: list[WireAdapter] = []
    for provider_dir in sorted(providers_dir.iterdir()):
        if not provider_dir.is_dir():
            continue
        provider = provider_dir.name
        execution_path = provider_dir / "execution.json"
        graph_path = provider_dir / "graph.json"
        if not execution_path.is_file() or not graph_path.is_file():
            continue
        execution = json.loads(execution_path.read_text(encoding="utf-8"))
        adapter = execution.get("wire")
        if not isinstance(adapter, str) or not adapter:
            continue
        graph = json.loads(graph_path.read_text(encoding="utf-8"))
        wire = (graph.get("edges") or {}).get("wire") or {}
        adapter_wire = wire.get(adapter)
        if not isinstance(adapter_wire, dict) or not adapter_wire:
            continue
        adapters.append(WireAdapter(provider=provider, adapter=adapter))
    return adapters
