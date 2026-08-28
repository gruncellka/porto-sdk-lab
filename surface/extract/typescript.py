"""TypeDoc JSON extract of the TypeScript public barrel (src/index.ts).

Emits a **raw** surface: language-native names and full docs. Canonicalization
and first-sentence docs belong in ``extract.normalize.normalize_surface``.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

# TypeDoc ReflectionKind (stable subset)
_KIND_PROJECT = 1
_KIND_MODULE = 2
_KIND_NAMESPACE = 4
_KIND_ENUM = 8
_KIND_ENUM_MEMBER = 16
_KIND_VARIABLE = 32
_KIND_FUNCTION = 64
_KIND_CLASS = 128
_KIND_INTERFACE = 256
_KIND_CONSTRUCTOR = 512
_KIND_PROPERTY = 1024
_KIND_METHOD = 2048
_KIND_ACCESSOR = 262144
_KIND_TYPE_ALIAS = 2097152
_KIND_TYPE_LITERAL = 65536

_CONTAINER = {_KIND_PROJECT, _KIND_MODULE, _KIND_NAMESPACE}


def _typedoc_bin(tools_root: Path) -> Path:
    candidate = tools_root / "node_modules" / ".bin" / "typedoc"
    if candidate.is_file():
        return candidate
    raise FileNotFoundError(
        "TypeDoc is not installed for Lab surface extract. "
        "Install typedoc under surface/ or pass tools_root to extract_typescript."
    )


def _comment(node: dict[str, Any]) -> str:
    comment = node.get("comment") or {}
    summary = comment.get("summary") or []
    parts: list[str] = []
    for item in summary:
        if isinstance(item, dict) and item.get("kind") == "text":
            parts.append(str(item.get("text") or ""))
    return "".join(parts).strip()


def _type_name(t: Any) -> str | None:
    if not isinstance(t, dict):
        return None
    name = t.get("name")
    type_args = t.get("typeArguments") or []
    ttype = t.get("type")
    if ttype == "intrinsic":
        token = str(name or "").strip()
        if token in {"null", "undefined", "void", "any", "unknown", "never", "object"}:
            return token
        if token:
            return token
    if ttype == "literal":
        val = t.get("value")
        if val is None and t.get("name") == "null":
            return "null"
        if isinstance(val, bool):
            return "true" if val else "false"
        if isinstance(val, (int, float)):
            return str(val)
        if isinstance(val, str):
            return f'"{val}"'
        if val is None:
            return "null"
    if ttype == "union":
        names = [_type_name(x) for x in t.get("types") or []]
        parts = [n for n in names if n]
        return " | ".join(parts) if parts else None
    if ttype == "array":
        inner = _type_name(t.get("elementType"))
        return f"{inner}[]" if inner else None
    if ttype == "tuple":
        inners = [n for n in (_type_name(x) for x in t.get("elements") or []) if n]
        if inners:
            return f"[{', '.join(inners)}]"
        return None
    if ttype == "typeOperator":
        # TypeDoc emits `readonly T[]` as typeOperator; unwrap to the target type.
        target = _type_name(t.get("target"))
        return target
    if ttype == "reflection":
        decl = t.get("declaration") or {}
        if isinstance(decl, dict):
            children = decl.get("children") or []
            sigs = decl.get("signatures") or []
            if sigs and isinstance(sigs[0], dict):
                ret = _type_name(sigs[0].get("type"))
                return ret
            if children:
                # Inline object type — keep as a named hint so closure can fail if baggy.
                return "object"
        return None
    if ttype == "intersection":
        names = [n for n in (_type_name(x) for x in t.get("types") or []) if n]
        return " & ".join(names) if names else None
    if isinstance(name, str) and name.strip():
        if type_args:
            inners = [n for n in (_type_name(x) for x in type_args) if n is not None]
            if inners:
                return f"{name}<{', '.join(inners)}>"
        return name
    return None


def _is_async(sig: dict[str, Any]) -> bool:
    ret = _type_name(sig.get("type"))
    if ret and (ret == "Promise" or ret.startswith("Promise<")):
        return True
    return False


def _params(sig: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for param in sig.get("parameters") or []:
        if not isinstance(param, dict):
            continue
        name = str(param.get("name") or "")
        if not name or name.startswith("_"):
            continue
        flags = param.get("flags") or {}
        out.append(
            {
                "name": name,
                "optional": bool(flags.get("isOptional") or param.get("defaultValue")),
                "type": _type_name(param.get("type")),
            }
        )
    return out


def _first_sig(node: dict[str, Any]) -> dict[str, Any] | None:
    if node.get("signatures"):
        first = node["signatures"][0]
        if isinstance(first, dict):
            return first
    return None


def _serialize_callable(node: dict[str, Any], kind: str) -> dict[str, Any]:
    sig = _first_sig(node) or {}
    returns = _type_name(sig.get("type") if sig else node.get("type"))
    async_flag = _is_async(sig) if sig else False
    return {
        "kind": kind,
        "async": async_flag,
        "doc": _comment(sig) or _comment(node),
        "params": _params(sig) if sig else [],
        "returns": returns,
    }


def _serialize_enum(node: dict[str, Any]) -> dict[str, Any]:
    enum_members: dict[str, str] = {}
    for child in node.get("children") or []:
        if not isinstance(child, dict):
            continue
        if int(child.get("kind") or 0) != _KIND_ENUM_MEMBER:
            continue
        mname = str(child.get("name") or "")
        if not mname:
            continue
        val = child.get("defaultValue")
        if val is not None:
            text = str(val).strip().strip('"').strip("'")
        else:
            text = mname
        enum_members[mname] = text
    return {
        "kind": "enum",
        "doc": _comment(node),
        "members": {},
        "enum_members": enum_members,
    }


def _serialize_class(node: dict[str, Any]) -> dict[str, Any]:
    members: dict[str, Any] = {}
    for child in node.get("children") or []:
        if not isinstance(child, dict):
            continue
        name = str(child.get("name") or "")
        flags = child.get("flags") or {}
        if not name or name.startswith("_") or flags.get("isPrivate") or flags.get("isProtected"):
            continue
        kind = int(child.get("kind") or 0)
        if kind in {_KIND_METHOD, _KIND_CONSTRUCTOR}:
            if kind == _KIND_CONSTRUCTOR:
                continue
            members[name] = _serialize_callable(child, "method")
        elif kind in {_KIND_PROPERTY, _KIND_ACCESSOR}:
            flags = child.get("flags") or {}
            members[name] = {
                "kind": "attribute",
                "doc": _comment(child),
                "type": _type_name(child.get("type")),
                "optional": bool(flags.get("isOptional") or flags.get("isOptionalElement")),
            }
    return {
        "kind": "class" if int(node.get("kind") or 0) == _KIND_CLASS else "interface",
        "doc": _comment(node),
        "members": members,
    }


def _literal_union_values(t: Any) -> dict[str, str]:
    if not isinstance(t, dict):
        return {}
    if t.get("type") == "union":
        values: dict[str, str] = {}
        for item in t.get("types") or []:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "literal":
                val = item.get("value")
                text = str(val).strip().strip('"').strip("'") if val is not None else ""
                if text:
                    values[text] = text
        return values
    if t.get("type") == "literal":
        val = t.get("value")
        text = str(val).strip().strip('"').strip("'") if val is not None else ""
        return {text: text} if text else {}
    return {}


def _const_object_values(node: dict[str, Any]) -> dict[str, str]:
    t = node.get("type")
    declaration: dict[str, Any] = {}
    if isinstance(t, dict):
        if t.get("type") == "reflection":
            decl = t.get("declaration")
            if isinstance(decl, dict):
                declaration = decl
        elif isinstance(t.get("declaration"), dict):
            declaration = t["declaration"]
    children = declaration.get("children") or node.get("children") or []
    values: dict[str, str] = {}
    for child in children:
        if not isinstance(child, dict):
            continue
        mname = str(child.get("name") or "")
        if not mname or mname.startswith("_"):
            continue
        default = child.get("defaultValue")
        if default is not None:
            text = str(default).strip().strip('"').strip("'")
        else:
            nested = _type_name(child.get("type"))
            text = nested or mname
        values[mname] = text
    return values


def _as_enum_payload(enum_members: dict[str, str], doc: str) -> dict[str, Any]:
    return {
        "kind": "enum",
        "doc": doc,
        "members": {},
        "enum_members": enum_members,
    }


def _merge_symbol(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    if incoming.get("kind") == "enum" and existing.get("kind") != "enum":
        return incoming
    if existing.get("kind") == "enum" and incoming.get("kind") == "enum":
        members = dict(existing.get("enum_members") or {})
        members.update(incoming.get("enum_members") or {})
        return _as_enum_payload(members, str(existing.get("doc") or incoming.get("doc") or ""))
    if existing.get("kind") == "enum":
        extra = incoming.get("enum_members") or {}
        if extra:
            members = dict(existing.get("enum_members") or {})
            members.update(extra)
            return _as_enum_payload(members, str(existing.get("doc") or ""))
    return existing


def _walk(node: dict[str, Any], acc: dict[str, dict[str, Any]]) -> None:
    kind = int(node.get("kind") or 0)
    name = str(node.get("name") or "")
    flags = node.get("flags") or {}
    if flags.get("isInternal") or flags.get("isPrivate") or flags.get("isProtected"):
        if kind not in _CONTAINER:
            return
    if kind in _CONTAINER:
        for child in node.get("children") or []:
            if isinstance(child, dict):
                _walk(child, acc)
        return
    if not name:
        return
    if kind in {_KIND_CLASS, _KIND_INTERFACE}:
        payload = _serialize_class(node)
    elif kind == _KIND_ENUM:
        payload = _serialize_enum(node)
    elif kind == _KIND_FUNCTION:
        payload = _serialize_callable(node, "function")
    elif kind in {_KIND_TYPE_ALIAS, _KIND_VARIABLE, _KIND_TYPE_LITERAL}:
        const_vals = _const_object_values(node) if kind == _KIND_VARIABLE else {}
        union_vals = _literal_union_values(node.get("type"))
        if const_vals:
            payload = _as_enum_payload(const_vals, _comment(node))
        elif union_vals:
            payload = _as_enum_payload(union_vals, _comment(node))
        else:
            payload = {
                "kind": "type" if kind == _KIND_TYPE_ALIAS else "value",
                "doc": _comment(node),
                "type": _type_name(node.get("type")),
            }
            if kind == _KIND_TYPE_ALIAS:
                decl = node.get("type")
                if isinstance(decl, dict) and decl.get("type") == "reflection":
                    declaration = decl.get("declaration") or {}
                    if int(declaration.get("kind") or 0) in {_KIND_INTERFACE, _KIND_CLASS, 0}:
                        nested = (
                            _serialize_class(declaration) if declaration.get("children") else None
                        )
                        if nested and nested.get("members"):
                            payload = nested
                            payload["kind"] = "interface"
    else:
        payload = {"kind": f"kind:{kind}", "doc": _comment(node)}
    payload["name"] = name
    if name in acc:
        acc[name] = _merge_symbol(acc[name], payload)
        return
    acc[name] = payload


def parse_typedoc_json(data: dict[str, Any]) -> dict[str, Any]:
    symbols: dict[str, Any] = {}
    _walk(data, symbols)
    return {"language": "typescript", "symbols": symbols}


def extract_typescript(sdk_root: Path, *, tools_root: Path | None = None) -> dict[str, Any]:
    sdk_root = sdk_root.resolve()
    entry = sdk_root / "src" / "index.ts"
    if not entry.is_file():
        raise FileNotFoundError(f"TypeScript barrel not found: {entry}")
    tools_root = (tools_root or Path(__file__).resolve().parents[1]).resolve()
    typedoc = _typedoc_bin(tools_root)
    tsconfig = sdk_root / "tsconfig.json"
    with tempfile.TemporaryDirectory(prefix="porto-typedoc-") as tmp:
        out = Path(tmp) / "typedoc.json"
        cmd = [
            str(typedoc),
            "--json",
            str(out),
            "--entryPoints",
            str(entry),
            "--excludeInternal",
            "--skipErrorChecking",
        ]
        if tsconfig.is_file():
            cmd.extend(["--tsconfig", str(tsconfig)])
        env = os.environ.copy()
        result = subprocess.run(
            cmd,
            cwd=str(sdk_root),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0 or not out.is_file():
            raise RuntimeError(
                "TypeDoc extract failed:\n" + (result.stdout or "") + "\n" + (result.stderr or "")
            )
        data = json.loads(out.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("TypeDoc JSON root must be an object")
    return parse_typedoc_json(data)
