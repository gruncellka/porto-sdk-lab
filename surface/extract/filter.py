"""Filter raw extract to declared public members only."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from surface.exceptions import CONTRACT_DIR
from surface.extract.normalize import to_canonical

CONTRACT_PATH = CONTRACT_DIR / "contract.yaml"


@lru_cache(maxsize=1)
def load_contract(path: str | None = None) -> dict[str, Any]:
    target = Path(path) if path else CONTRACT_PATH
    raw = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError("contract.yaml must be a mapping")
    return raw


def _folded(names: set[str]) -> set[str]:
    """Identity plus snake_case → camelCase. One YAML spelling matches both SDKs."""
    return names | {to_canonical(n) for n in names}


def _deny_names(policy: dict[str, Any], symbol: str) -> set[str]:
    out = {str(x) for x in (policy.get("denylist_global") or [])}
    by_sym = policy.get("denylist_by_symbol") or {}
    if isinstance(by_sym, dict):
        out.update(str(x) for x in (by_sym.get(symbol) or []))
    return out


def _allow_names(policy: dict[str, Any], symbol: str) -> set[str] | None:
    by_sym = policy.get("allowlist_by_symbol") or {}
    if not isinstance(by_sym, dict) or symbol not in by_sym:
        return None
    return {str(x) for x in (by_sym.get(symbol) or [])}


def allowlist_symbol_keys(policy: dict[str, Any]) -> set[str] | None:
    """Names in allowlist_symbols, plus their camelCase fold. None when unset."""
    raw = policy.get("allowlist_symbols")
    if raw is None:
        return None
    return _folded({str(x) for x in raw})


def _symbol_allowed(name: str, allow: set[str]) -> bool:
    return bool({name, to_canonical(name)} & allow)


def extra_symbols(raw: dict[str, Any], *, policy: dict[str, Any] | None = None) -> list[str]:
    """Root extract names that are not in allowlist_symbols (empty when unset)."""
    if policy is None:
        policy = load_contract()
    allow = allowlist_symbol_keys(policy)
    if allow is None:
        return []
    extras: list[str] = []
    symbols_in = raw.get("symbols") or {}
    if not isinstance(symbols_in, dict):
        return []
    for name in symbols_in:
        if not _symbol_allowed(str(name), allow):
            extras.append(str(name))
    return sorted(extras)


def _keep_member(name: str, symbol: str, policy: dict[str, Any]) -> bool:
    if not name or name.startswith("_"):
        return False
    keys = {name, to_canonical(name)}
    if keys & _folded(_deny_names(policy, symbol)):
        return False
    allow = _allow_names(policy, symbol)
    if allow is None:
        return True
    return bool(keys & _folded(allow))


def filter_members(members: dict[str, Any], symbol: str, policy: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for name, payload in members.items():
        if not isinstance(payload, dict):
            continue
        if not _keep_member(str(name), symbol, policy):
            continue
        out[str(name)] = dict(payload)
    return out


def filter_symbol(name: str, payload: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    out = dict(payload)
    if isinstance(out.get("members"), dict):
        out["members"] = filter_members(out["members"], name, policy)
    return out


def filter_surface(raw: dict[str, Any], *, policy: dict[str, Any] | None = None) -> dict[str, Any]:
    """Raw extract → public-only symbols/members."""
    if policy is None:
        policy = load_contract()
    symbols_in = raw.get("symbols") or {}
    if not isinstance(symbols_in, dict):
        raise ValueError("surface.symbols must be an object")
    allow = allowlist_symbol_keys(policy)
    symbols_out: dict[str, Any] = {}
    for name, payload in symbols_in.items():
        if not isinstance(payload, dict):
            continue
        if allow is not None and not _symbol_allowed(str(name), allow):
            continue
        symbols_out[str(name)] = filter_symbol(str(name), payload, policy)
    return {**raw, "symbols": symbols_out}
