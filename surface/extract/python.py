"""Static Python public-surface extract via AST (__all__) + Griffe.

Emits a **raw** surface: language-native names and full docs. Canonicalization
and first-sentence docs belong in ``extract.normalize.normalize_surface``.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any


def _kind_name(obj: Any) -> str:
    kind = getattr(obj, "kind", None)
    if kind is None:
        return ""
    name = getattr(kind, "name", None)
    if isinstance(name, str):
        return name.lower().replace("_", " ")
    return str(kind).replace("Kind.", "").lower().replace("_", " ")


def parse_dunder_all(init_path: Path) -> list[str]:
    tree = ast.parse(init_path.read_text(encoding="utf-8"), filename=str(init_path))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "__all__":
                if not isinstance(node.value, (ast.List, ast.Tuple)):
                    raise ValueError(f"{init_path}: __all__ must be a list or tuple")
                names: list[str] = []
                for elt in node.value.elts:
                    if not isinstance(elt, ast.Constant) or not isinstance(elt.value, str):
                        raise ValueError(f"{init_path}: __all__ entries must be string literals")
                    names.append(elt.value)
                return names
    raise ValueError(f"{init_path}: __all__ not found")


def _ann(annotation: Any) -> str | None:
    if annotation is None:
        return None
    text = str(annotation)
    text = text.replace("porto_sdk.", "")
    return text or None


_LITERAL = re.compile(r"Literal\s*\[(.+)\]", re.DOTALL | re.I)


def _literal_values(*texts: str | None) -> dict[str, str]:
    for text in texts:
        if not text:
            continue
        match = _LITERAL.search(str(text))
        if not match:
            continue
        found = re.findall(r"['\"]([^'\"]+)['\"]", match.group(1))
        if found:
            return {value: value for value in found}
    return {}


def _raw_doc(obj: Any) -> str:
    value = getattr(getattr(obj, "docstring", None), "value", None)
    return str(value).strip() if value else ""


def _iter_parameters(obj: Any) -> list[tuple[str, Any]]:
    parameters = getattr(obj, "parameters", None)
    if not parameters:
        return []
    items = getattr(parameters, "items", None)
    if callable(items):
        return list(items())
    return [(str(getattr(param, "name", "")), param) for param in parameters]


def _serialize_function(obj: Any) -> dict[str, Any]:
    params: list[dict[str, Any]] = []
    for pname, param in _iter_parameters(obj):
        if pname in {"self", "cls"}:
            continue
        optional = _annotation_optional(
            _ann(getattr(param, "annotation", None)),
            getattr(param, "default", None),
        )
        kind = _kind_name(param)
        if "var keyword" in kind or pname == "kwargs":
            continue
        if "var positional" in kind:
            continue
        params.append(
            {
                "name": pname,
                "optional": optional,
                "type": _ann(getattr(param, "annotation", None)),
            }
        )
    returns = _ann(getattr(obj, "returns", None))
    labels = {str(x).lower() for x in (getattr(obj, "labels", set()) or set())}
    is_async = bool(getattr(obj, "is_async", False)) or "async" in labels
    return {
        "kind": "function",
        "async": is_async,
        "doc": _raw_doc(obj),
        "params": params,
        "returns": returns,
    }


def _annotation_optional(annotation: str | None, default: Any) -> bool:
    """True when the key may be omitted from the public payload.

    Explicit null (``T | None`` / ``T | null``) is not optional by itself —
    only a non-sentinel default marks the slot omissible.
    """
    text = str(default) if default is not None else ""
    if text in {"", "empty", "...", "Ellipsis", "PydanticUndefined"}:
        return False
    if default is None:
        # Defaulted to None → omissible key (input/config style).
        return True
    return True


def _serialize_class(obj: Any) -> dict[str, Any]:
    members: dict[str, Any] = {}
    labels = {str(x).lower() for x in (getattr(obj, "labels", set()) or set())}
    bases = [str(b) for b in (getattr(obj, "bases", []) or [])]
    is_enum = "enum" in labels or any("enum" in b.lower() for b in bases)
    enum_members: dict[str, str] = {}
    for name, member in (getattr(obj, "members", {}) or {}).items():
        if name.startswith("_"):
            continue
        member = _unwrap(member)
        kind = _kind_name(member)
        if kind in {"method", "function"}:
            payload = _serialize_function(member)
            payload["kind"] = "method"
            members[name] = payload
        elif kind in {"attribute", "static attribute"} and is_enum:
            val = getattr(member, "value", None)
            text = name if val is None else str(val).strip()
            if len(text) >= 2 and text[0] == text[-1] and text[0] in {"'", '"'}:
                text = text[1:-1]
            enum_members[name] = text
        elif kind in {"attribute", "property", "static attribute"}:
            annotation = _ann(getattr(member, "annotation", None))
            default = getattr(member, "default", None)
            members[name] = {
                "kind": "attribute",
                "doc": _raw_doc(member),
                "type": annotation,
                "optional": _annotation_optional(annotation, default),
            }
    out: dict[str, Any] = {
        "kind": "enum" if is_enum or enum_members else "class",
        "doc": _raw_doc(obj),
        "members": members,
    }
    if out["kind"] == "enum":
        out["enum_members"] = enum_members
    return out


def _unwrap(obj: Any) -> Any:
    seen = 0
    while getattr(obj, "is_alias", False) and seen < 8:
        target = getattr(obj, "target", None)
        if target is None:
            break
        obj = target
        seen += 1
    return obj


def _serialize(obj: Any) -> dict[str, Any]:
    obj = _unwrap(obj)
    kind = _kind_name(obj)
    if kind in {"class", "enum"}:
        return _serialize_class(obj)
    if kind in {"function", "method"}:
        return _serialize_function(obj)
    if kind in {"attribute", "module", "typealias", "type alias"}:
        annotation = _ann(getattr(obj, "annotation", None))
        value = getattr(obj, "value", None)
        literals = _literal_values(
            annotation, _ann(value), str(value) if value is not None else None
        )
        if literals:
            return {
                "kind": "enum",
                "doc": _raw_doc(obj),
                "enum_members": literals,
            }
        return {
            "kind": "type" if "type" in kind else "value",
            "doc": _raw_doc(obj),
            "type": annotation,
        }
    return {
        "kind": kind or "unknown",
        "doc": _raw_doc(obj),
    }


def extract_python(sdk_root: Path) -> dict[str, Any]:
    sdk_root = sdk_root.resolve()
    init_path = sdk_root / "porto_sdk" / "__init__.py"
    if not init_path.is_file():
        raise FileNotFoundError(f"Python SDK __init__.py not found: {init_path}")
    names = parse_dunder_all(init_path)

    import griffe

    module = griffe.load(
        "porto_sdk",
        search_paths=[str(sdk_root)],
        allow_inspection=False,
        resolve_aliases=True,
    )
    symbols: dict[str, Any] = {}
    for name in names:
        obj = module.members.get(name)
        if obj is None:
            symbols[name] = {"kind": "unknown", "doc": "", "missing": True}
            continue
        payload = _serialize(obj)
        payload["name"] = name
        symbols[name] = payload
    return {"language": "python", "symbols": symbols}
