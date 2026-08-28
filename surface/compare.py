"""Cross-SDK public contract merge + drift diagnostics (Lab only)."""

from __future__ import annotations

import json
import re
from typing import Any, Literal

import yaml
from jsonschema import Draft202012Validator

from surface.exceptions import (
    CONTRACT_SCHEMA_PATH,
    exempt_member_keys,
    load_differences,
)
from surface.extract.filter import allowlist_symbol_keys, load_contract
from surface.extract.normalize import (
    equivalent_types,
    normalize_type_syntax,
    to_canonical,
    type_is_nullable,
)

SCHEMA_PATH = CONTRACT_SCHEMA_PATH
Severity = Literal["error", "warning", "intentional"]


def _index(surface: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not surface:
        return {}
    symbols = surface.get("symbols") or {}
    out: dict[str, dict[str, Any]] = {}
    for name, payload in symbols.items():
        if not isinstance(payload, dict):
            continue
        canonical = str(payload.get("canonical") or to_canonical(name))
        out[canonical] = {**payload, "name": name, "canonical": canonical}
    return out


def _member_index(symbol: dict[str, Any]) -> dict[str, dict[str, Any]]:
    members = symbol.get("members") or {}
    out: dict[str, dict[str, Any]] = {}
    for name, payload in members.items():
        if not isinstance(payload, dict):
            continue
        canonical = str(payload.get("canonical") or to_canonical(name))
        out[canonical] = {**payload, "name": name, "canonical": canonical}
    return out


def _enum_values(symbol: dict[str, Any]) -> set[str]:
    vals = symbol.get("canonicalValues")
    if isinstance(vals, list) and vals:
        return {str(v) for v in vals}
    members = _enum_member_map(symbol)
    if members:
        return set(members.values())
    return set()


def _enum_member_map(symbol: dict[str, Any]) -> dict[str, str]:
    raw = symbol.get("enum_members") or {}
    if isinstance(raw, dict):
        return {str(k): str(v) for k, v in raw.items()}
    return {}


def _diff(
    *,
    concept: str,
    kind: str,
    python: Any,
    typescript: Any,
    expected: Any = None,
    severity: Severity = "error",
) -> dict[str, Any]:
    return {
        "concept": concept,
        "kind": kind,
        "python": python,
        "typescript": typescript,
        "expected": expected,
        "severity": severity,
    }


def _type_semantics(type_str: object) -> dict[str, Any]:
    """Compare type meaning, not language syntax.

    Remaining drift after normalize_type_syntax: collection vs scalar vs map,
    and time units (seconds vs milliseconds vs timestamp).
    """
    text = str(type_str or "").strip()
    compact = text.replace(" ", "")
    lower = compact.lower()
    norm = normalize_type_syntax(text) or ""
    cores = [p.strip() for p in norm.split("|") if p.strip() not in {"", "void"}]
    shape = "scalar"
    if any(p.endswith("[]") for p in cores):
        shape = "collection"
    elif any(p == "map" or p.startswith("map<") for p in cores):
        shape = "map"
    time_unit: str | None = None
    if "_ms" in lower or "milliseconds" in lower or "durationms" in lower:
        time_unit = "milliseconds"
    elif "timedelta" in lower or any(p.lower() == "seconds" for p in cores):
        time_unit = "seconds"
    elif "datetime" in lower or lower in {"date"}:
        time_unit = "timestamp"
    return {
        "shape": shape,
        "time_unit": time_unit,
    }


def _param_optional(param: object) -> bool | None:
    if isinstance(param, dict) and "optional" in param:
        return bool(param.get("optional"))
    return None


def _param_type(param: object) -> str | None:
    if isinstance(param, dict):
        raw = param.get("type")
        return str(raw) if raw is not None else None
    return None


def _slot_optional(optional_flag: object, type_str: object) -> bool:
    """Omit and explicit null are the same public slot (Python T | None vs TS T | null)."""
    if bool(optional_flag):
        return True
    if type_str is None:
        return False
    return type_is_nullable(str(type_str))


def _required_null_keys(policy: dict[str, Any] | None) -> set[tuple[str, str]]:
    """Symbol.member pairs that must be required keys with explicit null (not omissible)."""
    raw = (policy or {}).get("required_null_members") or []
    out: set[tuple[str, str]] = set()
    for item in raw:
        text = str(item).strip()
        if "." not in text:
            continue
        symbol, member = text.split(".", 1)
        out.add((to_canonical(symbol), to_canonical(member)))
    return out


def merge_contract(
    python_surface: dict[str, Any] | None,
    typescript_surface: dict[str, Any] | None,
) -> dict[str, Any]:
    py = _index(python_surface)
    ts = _index(typescript_surface)
    symbols: dict[str, Any] = {}
    for name in sorted(set(py) | set(ts)):
        left = py.get(name)
        right = ts.get(name)
        kind = (left or right or {}).get("kind") or "unknown"
        members_py = _member_index(left) if left else {}
        members_ts = _member_index(right) if right else {}
        members: dict[str, Any] = {}
        for member in sorted(set(members_py) | set(members_ts)):
            mp = members_py.get(member)
            mt = members_ts.get(member)
            returns = (mp or {}).get("returns") or (mt or {}).get("returns")
            members[member] = {
                "kind": (mp or mt or {}).get("kind") or "unknown",
                "canonical": member,
                "returns": returns,
                "python": (
                    {"async": bool(mp.get("async")), "params": mp.get("params") or []}
                    if mp
                    else None
                ),
                "typescript": (
                    {"async": bool(mt.get("async")), "params": mt.get("params") or []}
                    if mt
                    else None
                ),
                "signature": None,
            }
        entry: dict[str, Any] = {
            "kind": kind,
            "canonical": name,
            "python": {"name": left["name"]} if left else None,
            "typescript": {"name": right["name"]} if right else None,
            "members": members,
            "signature": None,
        }
        if kind == "enum" or _enum_values(left or {}) or _enum_values(right or {}):
            entry["canonicalValues"] = sorted(_enum_values(left or {}) | _enum_values(right or {}))
            entry["python"] = (
                {"name": left["name"], "members": _enum_member_map(left)} if left else None
            )
            entry["typescript"] = (
                {"name": right["name"], "members": _enum_member_map(right)} if right else None
            )
        symbols[name] = entry
    return {"added": [], "removed": [], "symbols": symbols}


def validate_contract(contract: dict[str, Any]) -> None:
    raw = SCHEMA_PATH.read_text(encoding="utf-8")
    try:
        schema = yaml.safe_load(raw)
    except yaml.YAMLError:
        schema = json.loads(raw)
    Draft202012Validator(schema).validate(contract)


def parity_differences(
    python_surface: dict[str, Any] | None,
    typescript_surface: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Machine-readable drift rows (JSON-first report payload)."""
    py = _index(python_surface)
    ts = _index(typescript_surface)
    exempt = exempt_member_keys(load_differences())
    required_null = _required_null_keys(load_contract())
    differences: list[dict[str, Any]] = []

    for name in sorted(set(py) - set(ts)):
        differences.append(
            _diff(
                concept=name,
                kind="missing_symbol",
                python=py[name].get("kind"),
                typescript=None,
                expected=name,
            )
        )
    for name in sorted(set(ts) - set(py)):
        differences.append(
            _diff(
                concept=name,
                kind="missing_symbol",
                python=None,
                typescript=ts[name].get("kind"),
                expected=name,
            )
        )

    for name in sorted(set(py) & set(ts)):
        left = py[name]
        right = ts[name]
        kinds = {left.get("kind"), right.get("kind")}
        if left.get("kind") != right.get("kind") and kinds <= {
            "class",
            "interface",
            "type",
            "value",
            "enum",
        }:
            pass
        elif left.get("kind") != right.get("kind"):
            differences.append(
                _diff(
                    concept=name,
                    kind="kind_mismatch",
                    python=left.get("kind"),
                    typescript=right.get("kind"),
                    expected=left.get("kind"),
                )
            )

        py_vals = _enum_values(left)
        ts_vals = _enum_values(right)
        if (py_vals or ts_vals) and py_vals != ts_vals:
            differences.append(
                _diff(
                    concept=name,
                    kind="enum_values_mismatch",
                    python=sorted(py_vals),
                    typescript=sorted(ts_vals),
                    expected=sorted(py_vals | ts_vals),
                )
            )

        mp = _member_index(left)
        mt = _member_index(right)
        for member in sorted(set(mp) - set(mt)):
            differences.append(
                _diff(
                    concept=f"{name}.{member}",
                    kind="missing_member",
                    python=mp[member].get("name") or member,
                    typescript=None,
                    expected=member,
                )
            )
        for member in sorted(set(mt) - set(mp)):
            differences.append(
                _diff(
                    concept=f"{name}.{member}",
                    kind="missing_member",
                    python=None,
                    typescript=mt[member].get("name") or member,
                    expected=member,
                )
            )
        for member in sorted(set(mp) & set(mt)):
            if (name, member, "async") not in exempt and bool(mp[member].get("async")) != bool(
                mt[member].get("async")
            ):
                differences.append(
                    _diff(
                        concept=f"{name}.{member}",
                        kind="async_mismatch",
                        python=bool(mp[member].get("async")),
                        typescript=bool(mt[member].get("async")),
                        expected=bool(mp[member].get("async")),
                    )
                )
            ret_p = mp[member].get("returns")
            ret_t = mt[member].get("returns")
            if ret_p and ret_t and not equivalent_types(str(ret_p), str(ret_t)):
                differences.append(
                    _diff(
                        concept=f"{name}.{member}",
                        kind="return_mismatch",
                        python=ret_p,
                        typescript=ret_t,
                        expected=ret_p,
                    )
                )
            type_p = mp[member].get("type") or mp[member].get("returns")
            type_t = mt[member].get("type") or mt[member].get("returns")
            if mp[member].get("kind") == "attribute" and mt[member].get("kind") == "attribute":
                if type_p is None or type_t is None:
                    differences.append(
                        _diff(
                            concept=f"{name}.{member}",
                            kind="missing_type",
                            python=type_p,
                            typescript=type_t,
                            expected="typed public member",
                        )
                    )
                elif not equivalent_types(str(type_p), str(type_t)):
                    differences.append(
                        _diff(
                            concept=f"{name}.{member}",
                            kind="type_mismatch",
                            python=type_p,
                            typescript=type_t,
                            expected=type_p,
                        )
                    )
            opt_attr_p = mp[member].get("optional")
            opt_attr_t = mt[member].get("optional")
            if (
                mp[member].get("kind") == "attribute"
                and mt[member].get("kind") == "attribute"
                and opt_attr_p is not None
                and opt_attr_t is not None
                and (name, member, "optional") not in exempt
            ):
                key = (to_canonical(name), to_canonical(member))
                if key in required_null:
                    # Required + explicit null: raw omission flags must match and be false.
                    if bool(opt_attr_p) or bool(opt_attr_t):
                        differences.append(
                            _diff(
                                concept=f"{name}.{member}",
                                kind="optional_mismatch",
                                python=bool(opt_attr_p),
                                typescript=bool(opt_attr_t),
                                expected=False,
                            )
                        )
                    elif not (
                        type_is_nullable(str(type_p or "")) and type_is_nullable(str(type_t or ""))
                    ):
                        differences.append(
                            _diff(
                                concept=f"{name}.{member}",
                                kind="optional_mismatch",
                                python=type_p,
                                typescript=type_t,
                                expected="nullable required key",
                            )
                        )
                elif _slot_optional(opt_attr_p, type_p) != _slot_optional(opt_attr_t, type_t):
                    differences.append(
                        _diff(
                            concept=f"{name}.{member}",
                            kind="optional_mismatch",
                            python=bool(opt_attr_p),
                            typescript=bool(opt_attr_t),
                            expected=bool(opt_attr_p),
                        )
                    )
            if type_p and type_t:
                sem_p = _type_semantics(type_p)
                sem_t = _type_semantics(type_t)
                if sem_p["shape"] != sem_t["shape"]:
                    differences.append(
                        _diff(
                            concept=f"{name}.{member}",
                            kind="shape_mismatch",
                            python=sem_p["shape"],
                            typescript=sem_t["shape"],
                            expected=sem_p["shape"],
                        )
                    )
                if (
                    sem_p["time_unit"]
                    and sem_t["time_unit"]
                    and sem_p["time_unit"] != sem_t["time_unit"]
                ):
                    differences.append(
                        _diff(
                            concept=f"{name}.{member}",
                            kind="time_unit_mismatch",
                            python=sem_p["time_unit"],
                            typescript=sem_t["time_unit"],
                            expected="seconds",
                        )
                    )
            params_p = mp[member].get("params") or []
            params_t = mt[member].get("params") or []
            if isinstance(params_p, list) and isinstance(params_t, list):
                by_py = {
                    to_canonical(str(p.get("name") if isinstance(p, dict) else p)): p
                    for p in params_p
                }
                by_ts = {
                    to_canonical(str(p.get("name") if isinstance(p, dict) else p)): p
                    for p in params_t
                }
                for pname in sorted(set(by_py) & set(by_ts)):
                    opt_p = _param_optional(by_py[pname])
                    opt_t = _param_optional(by_ts[pname])
                    typ_p = _param_type(by_py[pname])
                    typ_t = _param_type(by_ts[pname])
                    if typ_p is None or typ_t is None:
                        differences.append(
                            _diff(
                                concept=f"{name}.{member}.{pname}",
                                kind="missing_type",
                                python=typ_p,
                                typescript=typ_t,
                                expected="typed public parameter",
                            )
                        )
                    if (
                        opt_p is not None
                        and opt_t is not None
                        and (name, member, "optional") not in exempt
                        and _slot_optional(opt_p, typ_p) != _slot_optional(opt_t, typ_t)
                    ):
                        differences.append(
                            _diff(
                                concept=f"{name}.{member}.{pname}",
                                kind="optional_mismatch",
                                python=opt_p,
                                typescript=opt_t,
                                expected=opt_p,
                            )
                        )
                    if typ_p and typ_t and not equivalent_types(typ_p, typ_t):
                        differences.append(
                            _diff(
                                concept=f"{name}.{member}.{pname}",
                                kind="type_mismatch",
                                python=typ_p,
                                typescript=typ_t,
                                expected=typ_p,
                            )
                        )
                    if typ_p and typ_t:
                        sem_p = _type_semantics(typ_p)
                        sem_t = _type_semantics(typ_t)
                        if sem_p["shape"] != sem_t["shape"]:
                            differences.append(
                                _diff(
                                    concept=f"{name}.{member}.{pname}",
                                    kind="shape_mismatch",
                                    python=sem_p["shape"],
                                    typescript=sem_t["shape"],
                                    expected=sem_p["shape"],
                                )
                            )
                        if (
                            sem_p["time_unit"]
                            and sem_t["time_unit"]
                            and sem_p["time_unit"] != sem_t["time_unit"]
                        ):
                            differences.append(
                                _diff(
                                    concept=f"{name}.{member}.{pname}",
                                    kind="time_unit_mismatch",
                                    python=sem_p["time_unit"],
                                    typescript=sem_t["time_unit"],
                                    expected="seconds",
                                )
                            )

    for item in load_differences():
        concept = str(item.get("id") or item.get("symbol") or "intentional")
        if item.get("symbol") and item.get("member"):
            concept = f"{item['symbol']}.{item['member']}"
        elif item.get("symbol"):
            concept = str(item["symbol"])
        differences.append(
            _diff(
                concept=concept,
                kind="intentional",
                python=item.get("python"),
                typescript=item.get("typescript"),
                expected=item.get("contract"),
                severity="intentional",
            )
        )
    return differences


_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_PRIMITIVE_TOKENS = {
    "str",
    "string",
    "int",
    "float",
    "number",
    "bool",
    "boolean",
    "none",
    "null",
    "void",
    "undefined",
    "true",
    "false",
    "bytes",
    "timedelta",
    "datetime",
    "date",
    "seconds",
}
_WRAPPER_TOKENS = {
    "list",
    "dict",
    "tuple",
    "frozenset",
    "set",
    "sequence",
    "optional",
    "record",
    "readonly",
    "readonlyarray",
    "promise",
    "partial",
    "map",
    "literal",
    "union",
    "readonlyset",
    "builtins",
}
_STRIP_STRINGS = re.compile(r"""(['"])(?:\\.|(?!\1).)*\1""")
_BAGGY_TOKENS = {"any", "unknown", "object"}


def _type_strings_of(payload: dict[str, Any]) -> list[str]:
    texts: list[str] = []
    if payload.get("type") is not None:
        texts.append(str(payload["type"]))
    if payload.get("returns") is not None:
        texts.append(str(payload["returns"]))
    for param in payload.get("params") or []:
        if isinstance(param, dict) and param.get("type") is not None:
            texts.append(str(param["type"]))
    return texts


def _baggy_allowed(policy: dict[str, Any]) -> set[str]:
    raw = policy.get("baggy_allowed") or []
    out: set[str] = set()
    for item in raw:
        text = str(item)
        out.add(text)
        if "." in text:
            symbol, member = text.split(".", 1)
            folded = f"{to_canonical(symbol)}.{to_canonical(member)}"
            out.add(folded)
            out.add(f"{symbol}.{to_canonical(member)}")
            out.add(f"{to_canonical(symbol)}.{member}")
    return out


def _concept_baggy_keys(concept: str) -> set[str]:
    keys = {concept, to_canonical(concept)}
    if "." in concept:
        symbol, member = concept.split(".", 1)
        keys.add(f"{to_canonical(symbol)}.{to_canonical(member)}")
        keys.add(f"{symbol}.{to_canonical(member)}")
        keys.add(f"{to_canonical(symbol)}.{member}")
    return keys


def _closure_allow(policy: dict[str, Any]) -> set[str]:
    raw = policy.get("closure_allow") or []
    out: set[str] = set()
    for item in raw:
        name = str(item)
        out.add(name)
        out.add(to_canonical(name))
    return out


def _check_type_closure(
    concept: str,
    type_str: str,
    allowed: set[str],
    *,
    sdk: str,
    baggy_ok: set[str],
) -> list[dict[str, Any]]:
    diffs: list[dict[str, Any]] = []
    tokens = _IDENT.findall(_STRIP_STRINGS.sub(" ", type_str))
    baggy = False
    untracked: list[str] = []
    for token in tokens:
        lower = token.lower()
        if lower in _PRIMITIVE_TOKENS or lower in _WRAPPER_TOKENS:
            continue
        if lower in _BAGGY_TOKENS:
            baggy = True
            continue
        keys = {token, to_canonical(token)}
        if not (keys & allowed):
            untracked.append(token)
    if baggy and not (_concept_baggy_keys(concept) & baggy_ok):
        diffs.append(
            _diff(
                concept=concept,
                kind="baggy_type",
                python=type_str if sdk == "python" else None,
                typescript=type_str if sdk == "typescript" else None,
                expected="primitive or allowlisted type",
            )
        )
    for name in untracked:
        diffs.append(
            _diff(
                concept=concept,
                kind="untracked_type",
                python=name if sdk == "python" else None,
                typescript=name if sdk == "typescript" else None,
                expected=name,
            )
        )
    return diffs


def closure_differences(
    python_surface: dict[str, Any] | None,
    typescript_surface: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Every referenced public type must be a primitive or an allowlisted symbol."""
    policy = load_contract()
    allow = allowlist_symbol_keys(policy) or set()
    baggy_ok = _baggy_allowed(policy)
    diffs: list[dict[str, Any]] = []
    for sdk, surface in (("python", python_surface), ("typescript", typescript_surface)):
        if not surface:
            continue
        symbols = surface.get("symbols") or {}
        allowed = set(allow) | _closure_allow(policy)
        for name in symbols:
            allowed.add(str(name))
            allowed.add(to_canonical(str(name)))
        for sname, spayload in symbols.items():
            if not isinstance(spayload, dict):
                continue
            if spayload.get("type") is not None:
                diffs.extend(
                    _check_type_closure(
                        str(sname),
                        str(spayload["type"]),
                        allowed,
                        sdk=sdk,
                        baggy_ok=baggy_ok,
                    )
                )
            members = spayload.get("members") or {}
            if not isinstance(members, dict):
                continue
            for mname, mpayload in members.items():
                if not isinstance(mpayload, dict):
                    continue
                concept = f"{sname}.{mname}"
                for text in _type_strings_of(mpayload):
                    diffs.extend(
                        _check_type_closure(
                            concept,
                            text,
                            allowed,
                            sdk=sdk,
                            baggy_ok=baggy_ok,
                        )
                    )
    return diffs


def extra_symbol_differences(
    extra_python: list[str] | None,
    extra_typescript: list[str] | None,
) -> list[dict[str, Any]]:
    differences: list[dict[str, Any]] = []
    for name in extra_python or []:
        differences.append(
            _diff(
                concept=name,
                kind="extra_symbol",
                python=name,
                typescript=None,
                expected=None,
            )
        )
    for name in extra_typescript or []:
        differences.append(
            _diff(
                concept=name,
                kind="extra_symbol",
                python=None,
                typescript=name,
                expected=None,
            )
        )
    return differences


def build_report(
    python_surface: dict[str, Any] | None,
    typescript_surface: dict[str, Any] | None,
    *,
    extra_python: list[str] | None = None,
    extra_typescript: list[str] | None = None,
) -> dict[str, Any]:
    differences = (
        extra_symbol_differences(extra_python, extra_typescript)
        + parity_differences(python_surface, typescript_surface)
        + closure_differences(python_surface, typescript_surface)
    )
    errors = sum(1 for d in differences if d["severity"] == "error")
    warnings = sum(1 for d in differences if d["severity"] == "warning")
    intentional = sum(1 for d in differences if d["severity"] == "intentional")
    status = "ok" if errors == 0 and warnings == 0 else "drift"
    return {
        "status": status,
        "summary": {
            "errors": errors,
            "warnings": warnings,
            "intentional": intentional,
        },
        "differences": differences,
    }


def parity_diagnostics(
    python_surface: dict[str, Any] | None,
    typescript_surface: dict[str, Any] | None,
    *,
    extra_python: list[str] | None = None,
    extra_typescript: list[str] | None = None,
) -> list[str]:
    """Human line form of non-intentional differences (tests / CLI)."""
    lines: list[str] = []
    rows = (
        extra_symbol_differences(extra_python, extra_typescript)
        + parity_differences(python_surface, typescript_surface)
        + closure_differences(python_surface, typescript_surface)
    )
    for row in rows:
        if row["severity"] == "intentional":
            continue
        kind = row["kind"]
        concept = row["concept"]
        if kind == "extra_symbol":
            if row["python"] is not None and row["typescript"] is None:
                lines.append(f"{concept}: extra symbol in Python (not in allowlist_symbols)")
            else:
                lines.append(f"{concept}: extra symbol in TypeScript (not in allowlist_symbols)")
        elif kind == "missing_symbol":
            if row["python"] is not None and row["typescript"] is None:
                lines.append(f"{concept}: missing in TypeScript (Python has {row['python']})")
            else:
                lines.append(f"{concept}: missing in Python (TypeScript has {row['typescript']})")
        elif kind == "kind_mismatch":
            lines.append(
                f"{concept}: kind drift Python={row['python']} TypeScript={row['typescript']}"
            )
        elif kind == "enum_values_mismatch":
            lines.append(
                f"{concept}: enum canonicalValues "
                f"Python={row['python']} TypeScript={row['typescript']}"
            )
        elif kind == "missing_member":
            if row["python"] is not None and row["typescript"] is None:
                lines.append(f"{concept}: missing in TypeScript")
            else:
                lines.append(f"{concept}: missing in Python")
        elif kind == "async_mismatch":
            lines.append(
                f"{concept}: async drift Python={row['python']} TypeScript={row['typescript']}"
            )
        elif kind == "return_mismatch":
            lines.append(
                f"{concept}: return drift Python={row['python']} TypeScript={row['typescript']}"
            )
        elif kind == "type_mismatch":
            lines.append(
                f"{concept}: type drift Python={row['python']} TypeScript={row['typescript']}"
            )
        elif kind == "baggy_type":
            lines.append(f"{concept}: baggy public type (Any/unknown/object)")
        elif kind == "untracked_type":
            lines.append(f"{concept}: untracked nested type {row['python'] or row['typescript']}")
        elif kind == "missing_type":
            lines.append(f"{concept}: missing public type")
        elif kind == "optional_mismatch":
            lines.append(
                f"{concept}: optional drift Python={row['python']} TypeScript={row['typescript']}"
            )
        elif kind == "shape_mismatch":
            lines.append(
                f"{concept}: shape drift Python={row['python']} TypeScript={row['typescript']}"
            )
        elif kind == "time_unit_mismatch":
            lines.append(
                f"{concept}: time-unit drift Python={row['python']} TypeScript={row['typescript']}"
            )
        else:
            lines.append(f"{concept}: {kind}")
    return lines


def format_drift(lines: list[str]) -> str:
    if not lines:
        return ""
    body = "\n".join(f"  {line}" for line in lines)
    return f"PUBLIC CONTRACT DRIFT\n{body}\n"


def observed_surface(surface: dict[str, Any] | None, *, sdk: str) -> dict[str, Any]:
    """Stable observed artifact shape for python.json / typescript.json."""
    if not surface:
        return {"sdk": sdk, "symbols": {}}
    symbols_out: dict[str, Any] = {}
    for name, payload in (surface.get("symbols") or {}).items():
        if not isinstance(payload, dict):
            continue
        entry: dict[str, Any] = {"kind": payload.get("kind") or "unknown"}
        members = payload.get("members") or {}
        if isinstance(members, dict) and members:
            members_out: dict[str, Any] = {}
            for mname, mpayload in members.items():
                if not isinstance(mpayload, dict):
                    continue
                member: dict[str, Any] = {"kind": mpayload.get("kind") or "unknown"}
                params = mpayload.get("params")
                if isinstance(params, list):
                    member["params"] = [
                        {
                            "name": (p.get("name") if isinstance(p, dict) else str(p)),
                            **(
                                {"optional": bool(p.get("optional"))}
                                if isinstance(p, dict) and "optional" in p
                                else {}
                            ),
                            **(
                                {"type": p.get("type")}
                                if isinstance(p, dict) and p.get("type") is not None
                                else {}
                            ),
                        }
                        if isinstance(p, dict)
                        else str(p)
                        for p in params
                    ]
                if mpayload.get("returns") is not None:
                    member["returns"] = mpayload.get("returns")
                if "async" in mpayload:
                    member["async"] = bool(mpayload.get("async"))
                if mpayload.get("type") is not None:
                    member["type"] = mpayload.get("type")
                if "optional" in mpayload:
                    member["optional"] = bool(mpayload.get("optional"))
                members_out[str(mname)] = member
            entry["members"] = members_out
        if payload.get("kind") == "enum" or payload.get("canonicalValues"):
            entry["values"] = sorted(_enum_values(payload))
            enum_members = _enum_member_map(payload)
            if enum_members:
                entry["enum_members"] = enum_members
        symbols_out[str(name)] = entry
    return {"sdk": sdk, "symbols": symbols_out}
