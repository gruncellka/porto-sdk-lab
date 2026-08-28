"""Canonical naming, return unwrap, and enum semantics (after filter)."""

from __future__ import annotations

import re
from typing import Any

_SNAKE = re.compile(r"^[a-z][a-z0-9]*(_[a-z0-9]+)+$")
_PROMISE = re.compile(r"^Promise\s*<\s*(.+)\s*>$", re.DOTALL)
_OPTIONAL = re.compile(r"^Optional\s*\[\s*(.+)\s*\]$", re.DOTALL)


def to_canonical(name: str) -> str:
    """Python snake_case → camelCase. PascalCase, UPPER, and single words stay."""
    if not name:
        return name
    if name.isupper() and "_" not in name:
        return name
    if _SNAKE.fullmatch(name):
        parts = name.split("_")
        return parts[0] + "".join(p.title() for p in parts[1:])
    return name


# Python list[T] / Sequence[T] (mark one-or-many). TypeScript arrays are T[].
_LIST_GENERIC = re.compile(r"^(?:list|sequence)\s*\[\s*(.+)\s*\]$", re.I | re.DOTALL)
# Python dict[K, V]. TypeScript Record<K, V> is handled by the Record< prefix.
_DICT_GENERIC = re.compile(r"^dict\s*\[\s*(.+)\s*\]$", re.I | re.DOTALL)

_SCALAR_ALIASES = {
    "bool": "boolean",
    "boolean": "boolean",
    "true": "boolean",
    "false": "boolean",
    "str": "string",
    "string": "string",
    "int": "number",
    "float": "number",
    "number": "number",
    "none": "null",
    "null": "null",
    "void": "void",
    "undefined": "void",
    "any": "unknown",
    "object": "unknown",
    "unknown": "unknown",
    "timedelta": "seconds",
    "seconds": "seconds",
    "datetime": "timestamp",
    "date": "timestamp",
}

# Named Literal aliases vs their expanded unions (quoted after normalize).
_NAMED_UNIONS: dict[str, frozenset[str]] = {
    "DeliverySpan": frozenset({'"next"', '"within"', '"between"'}),
    "DeliveryWeekdays": frozenset({'"mon_fri"', '"mon_sat"'}),
    "PriceComponentKind": frozenset({'"product"', '"service"'}),
    "MarkOutputMime": frozenset({'"image/png"', '"application/pdf"'}),
    "TrackingKind": frozenset({'"shipment"', '"stamp"'}),
}

_STRING_ALIASES = frozenset(
    {
        "ProviderId",
        "WireId",
        "EnvelopeFormat",
        "MarkOutputMime",
    }
)

_DURATION_PARTS = frozenset({"seconds", "number"})
_LITERAL_WRAP = re.compile(r"^Literal\s*\[(.+)\]$", re.I | re.DOTALL)
_PARTIAL_WRAP = re.compile(r"^Partial\s*<\s*(.+)\s*>$", re.I | re.DOTALL)
_QUOTED = re.compile(r"^(['\"])(.*)\1$")

# Collection wrappers that mean "array of T" across languages.
_COLLECTION_GENERIC = re.compile(
    r"^(?:frozenset|set|tuple|sequence|readonlyarray|readonly)\s*[<\[]\s*(.+)\s*[>\]]$",
    re.I | re.DOTALL,
)


def _split_union(text: str) -> list[str]:
    parts: list[str] = []
    depth = 0
    current: list[str] = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch in "[<(":
            depth += 1
            current.append(ch)
        elif ch in "]>)":
            depth = max(0, depth - 1)
            current.append(ch)
        elif ch == "|" and depth == 0:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
        i += 1
    tail = "".join(current).strip()
    if tail:
        parts.append(tail)
    return parts or [text.strip()]


def _split_args(text: str) -> list[str]:
    parts: list[str] = []
    depth = 0
    current: list[str] = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch in "[<(":
            depth += 1
            current.append(ch)
        elif ch in "]>)":
            depth = max(0, depth - 1)
            current.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
        i += 1
    tail = "".join(current).strip()
    if tail:
        parts.append(tail)
    return parts or [text.strip()]


def _normalize_map(inner: str) -> str:
    args = _split_args(inner)
    value = normalize_type_syntax(args[1]) if len(args) > 1 else "unknown"
    return f"map<{value}>" if value else "map<unknown>"


def _strip_null_union(norm: str) -> str:
    parts = [p.strip() for p in _split_union(norm) if p.strip() not in {"", "null", "void"}]
    return " | ".join(sorted(parts)) if parts else "null"


def _is_duration(norm: str) -> bool:
    parts = {p.strip().lower() for p in _split_union(norm) if p.strip()}
    return bool(parts) and parts <= _DURATION_PARTS


def _is_stringy(norm: str) -> bool:
    parts = {p.strip() for p in _split_union(norm) if p.strip()}
    allowed = {"string"} | _STRING_ALIASES | _NAMED_UNIONS["MarkOutputMime"]
    return bool(parts) and parts <= allowed


def type_is_nullable(text: str | None) -> bool:
    """True when the type includes None/null/void (absence or explicit null)."""
    if not text:
        return False
    norm = normalize_type_syntax(text) or ""
    parts = {p.strip().lower() for p in _split_union(norm)}
    return bool(parts & {"null", "void"})


def normalize_type_syntax(text: str | None) -> str | None:
    """Fold language syntax so bool/boolean, list[T]/T[], dict/Record compare equal."""
    if text is None:
        return None
    raw = " ".join(str(text).split())
    if not raw:
        return None
    if raw.lower().startswith("builtins."):
        raw = raw[len("builtins.") :].lstrip()
    compact = raw.replace(" ", "")
    lower = compact.lower()
    if lower in {"dict", "record"}:
        return "map<unknown>"
    partial_m = _PARTIAL_WRAP.match(raw)
    if partial_m:
        return normalize_type_syntax(partial_m.group(1).strip())
    union_parts = _split_union(raw)
    if len(union_parts) > 1:
        parts = [normalize_type_syntax(p) or p for p in union_parts]
        unique: list[str] = []
        for part in parts:
            if part not in unique:
                unique.append(part)
        return " | ".join(sorted(unique))
    lit_m = _LITERAL_WRAP.match(raw)
    if lit_m:
        args = _split_args(lit_m.group(1))
        parts = [normalize_type_syntax(a.strip()) or a.strip() for a in args]
        unique: list[str] = []
        for part in parts:
            if part not in unique:
                unique.append(part)
        return unique[0] if len(unique) == 1 else " | ".join(sorted(unique))
    quoted = _QUOTED.match(raw)
    if quoted:
        return f'"{quoted.group(2)}"'
    if lower.startswith("readonly") and compact.endswith("[]"):
        inner_raw = raw[len("readonly") :].strip()
        inner = normalize_type_syntax(inner_raw)
        return inner
    if compact.endswith("[]"):
        inner = normalize_type_syntax(raw[: raw.rfind("[")].strip())
        return f"{inner}[]" if inner else "[]"
    list_m = _LIST_GENERIC.match(raw)
    if list_m:
        inner = normalize_type_syntax(list_m.group(1).strip())
        return f"{inner}[]" if inner else "[]"
    coll_m = _COLLECTION_GENERIC.match(raw)
    if coll_m:
        inner_raw = coll_m.group(1).strip()
        if "," in inner_raw:
            inner_raw = inner_raw.split(",", 1)[0].strip()
        inner = normalize_type_syntax(inner_raw)
        return f"{inner}[]" if inner else "[]"
    dict_m = _DICT_GENERIC.match(raw)
    if dict_m:
        return _normalize_map(dict_m.group(1))
    if lower.startswith("record<"):
        inner = raw[raw.find("<") + 1 : raw.rfind(">")]
        return _normalize_map(inner)
    token = raw.rsplit(".", 1)[-1]
    aliased = _SCALAR_ALIASES.get(token.lower())
    if aliased:
        return aliased
    return to_canonical(token)


def equivalent_types(left: str | None, right: str | None) -> bool:
    if left is None or right is None:
        return False
    a = normalize_type_syntax(left)
    b = normalize_type_syntax(right)
    if a == b:
        return True
    # Empty return: Python None vs TypeScript void.
    if a is None or b is None:
        return False
    if {a, b} <= {"null", "void"}:
        return True
    if _is_duration(a) and _is_duration(b):
        return True
    sa, sb = _strip_null_union(a), _strip_null_union(b)
    if sa == sb:
        return True
    if _is_duration(sa) and _is_duration(sb):
        return True
    if _is_stringy(sa) and _is_stringy(sb):
        return True
    for name, arms in _NAMED_UNIONS.items():
        a_parts = frozenset(p.strip() for p in _split_union(sa) if p.strip())
        b_parts = frozenset(p.strip() for p in _split_union(sb) if p.strip())
        if (sa == name and b_parts == arms) or (sb == name and a_parts == arms):
            return True
    return False


def first_sentence(doc: str | None) -> str:
    if not doc:
        return ""
    text = " ".join(doc.strip().split())
    for sep in (". ", ".\n"):
        idx = text.find(sep)
        if idx != -1:
            return text[: idx + 1].strip()
    return text


def unwrap_return_type(returns: str | None, *, is_async: bool = False) -> tuple[str | None, bool]:
    """Strip Promise wrappers only. Keep null/None union arms (nullability is contract)."""
    if returns is None:
        return None, is_async
    text = str(returns).strip()
    if not text:
        return None, is_async
    async_flag = is_async
    m = _PROMISE.match(text)
    if m:
        text = m.group(1).strip()
        async_flag = True
    elif text == "Promise":
        return None, True
    m = _OPTIONAL.match(text)
    if m:
        inner = m.group(1).strip()
        text = f"{inner} | None"
    return (text or None), async_flag


def _normalize_param(param: dict[str, Any]) -> dict[str, Any]:
    out = dict(param)
    pname = str(out.get("name") or "")
    out["canonical"] = to_canonical(pname)
    if "type" in out and out["type"] is not None:
        typ, _ = unwrap_return_type(str(out["type"]))
        if typ is not None:
            out["type"] = typ
    return out


def _normalize_callable(payload: dict[str, Any]) -> dict[str, Any]:
    out = dict(payload)
    if "doc" in out:
        out["doc"] = first_sentence(out.get("doc"))
    if isinstance(out.get("params"), list):
        out["params"] = [_normalize_param(p) for p in out["params"] if isinstance(p, dict)]
    ret, async_flag = unwrap_return_type(
        None if out.get("returns") is None else str(out.get("returns")),
        is_async=bool(out.get("async")),
    )
    out["returns"] = ret
    out["async"] = async_flag
    return out


def _normalize_member(payload: dict[str, Any]) -> dict[str, Any]:
    kind = str(payload.get("kind") or "")
    if kind in {"method", "function"}:
        return _normalize_callable(payload)
    out = dict(payload)
    if "doc" in out:
        out["doc"] = first_sentence(out.get("doc"))
    if "type" in out and out["type"] is not None:
        typ, _ = unwrap_return_type(str(out["type"]))
        if typ is not None:
            out["type"] = typ
    if "optional" in out:
        out["optional"] = bool(out["optional"])
    return out


def _normalize_enum(name: str, payload: dict[str, Any]) -> dict[str, Any]:
    out = dict(payload)
    if "doc" in out:
        out["doc"] = first_sentence(out.get("doc"))
    enum_members = out.get("enum_members")
    members_map: dict[str, str] = {}
    if isinstance(enum_members, dict):
        for k, v in enum_members.items():
            members_map[str(k)] = str(v)
    canonical_values = sorted({str(v) for v in members_map.values()})
    out["canonicalValues"] = canonical_values
    out["enum_members"] = members_map
    out.pop("values", None)
    out["name"] = name
    out["canonical"] = to_canonical(name)
    out["kind"] = "enum"
    return out


def _normalize_symbol(name: str, payload: dict[str, Any]) -> dict[str, Any]:
    kind = str(payload.get("kind") or "")
    if kind == "enum":
        return _normalize_enum(name, payload)
    if kind in {"function", "method"}:
        out = _normalize_callable(payload)
    else:
        out = dict(payload)
        if "doc" in out:
            out["doc"] = first_sentence(out.get("doc"))
        if isinstance(out.get("members"), dict):
            out["members"] = {
                mname: _normalize_member(mpayload)
                for mname, mpayload in out["members"].items()
                if isinstance(mpayload, dict)
            }
    out["name"] = name
    out["canonical"] = to_canonical(name)
    return out


def normalize_surface(raw: dict[str, Any]) -> dict[str, Any]:
    """Filtered extract → canonical names, unwrapped returns, enum semantics."""
    symbols_in = raw.get("symbols") or {}
    if not isinstance(symbols_in, dict):
        raise ValueError("surface.symbols must be an object")
    symbols_out: dict[str, Any] = {}
    for name, payload in symbols_in.items():
        if not isinstance(payload, dict):
            continue
        symbols_out[str(name)] = _normalize_symbol(str(name), payload)
    return {**raw, "symbols": symbols_out}
