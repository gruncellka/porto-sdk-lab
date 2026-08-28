"""Full Python package structure extract (declarations only, no bodies)."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

_SKIP_DIR_NAMES = {"__pycache__", ".pytest_cache", ".mypy_cache", "_bundled"}
_SKIP_FILE_SUFFIXES = {".pyc", ".pyo"}


def _unparse(node: ast.AST | None) -> str | None:
    if node is None:
        return None
    try:
        return ast.unparse(node).strip()
    except Exception:
        return None


def _decorator_names(node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    names: list[str] = []
    for deco in node.decorator_list:
        text = _unparse(deco)
        if text:
            names.append(text.split("(")[0].strip())
    return names


def _is_enum_class(node: ast.ClassDef) -> bool:
    for base in node.bases:
        text = _unparse(base) or ""
        if "Enum" in text:
            return True
    return False


def _is_dataclass(node: ast.ClassDef) -> bool:
    return any(name.startswith("dataclass") for name in _decorator_names(node))


def _is_pydantic_model(node: ast.ClassDef) -> bool:
    for base in node.bases:
        text = _unparse(base) or ""
        if "BaseModel" in text:
            return True
    return False


def _serialize_args(args: ast.arguments) -> list[dict[str, Any]]:
    params: list[dict[str, Any]] = []
    positional = list(args.posonlyargs) + list(args.args)
    defaults_offset = len(positional) - len(args.defaults)
    for index, arg in enumerate(positional):
        if arg.arg in {"self", "cls"}:
            continue
        default_index = index - defaults_offset
        optional = default_index >= 0
        params.append(
            {
                "name": arg.arg,
                "type": _unparse(arg.annotation),
                "optional": optional,
            }
        )
    if args.vararg and args.vararg.arg not in {"self", "cls"}:
        params.append(
            {
                "name": args.vararg.arg,
                "type": _unparse(args.vararg.annotation),
                "variadic": "args",
            }
        )
    for arg, default in zip(args.kwonlyargs, args.kw_defaults, strict=False):
        params.append(
            {
                "name": arg.arg,
                "type": _unparse(arg.annotation),
                "optional": default is not None,
            }
        )
    if args.kwarg and args.kwarg.arg not in {"self", "cls"}:
        params.append(
            {
                "name": args.kwarg.arg,
                "type": _unparse(args.kwarg.annotation),
                "variadic": "kwargs",
            }
        )
    return params


def _serialize_function(
    node: ast.FunctionDef | ast.AsyncFunctionDef, *, kind: str
) -> dict[str, Any]:
    return {
        "kind": kind,
        "name": node.name,
        "async": isinstance(node, ast.AsyncFunctionDef),
        "params": _serialize_args(node.args),
        "returns": _unparse(node.returns),
        "decorators": _decorator_names(node),
    }


def _serialize_enum_members(node: ast.ClassDef) -> list[dict[str, Any]]:
    members: list[dict[str, Any]] = []
    for item in node.body:
        if isinstance(item, ast.Assign):
            for target in item.targets:
                if isinstance(target, ast.Name):
                    value = _unparse(item.value)
                    members.append({"name": target.id, "value": value})
        elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
            members.append(
                {
                    "name": item.target.id,
                    "type": _unparse(item.annotation),
                    "value": _unparse(item.value),
                }
            )
    return members


def _serialize_class_fields(node: ast.ClassDef) -> list[dict[str, Any]]:
    fields: list[dict[str, Any]] = []
    for item in node.body:
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
            if item.target.id.startswith("_") and not item.target.id.startswith("__"):
                continue
            fields.append(
                {
                    "name": item.target.id,
                    "type": _unparse(item.annotation),
                    "default": _unparse(item.value),
                }
            )
        elif isinstance(item, ast.Assign):
            for target in item.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    fields.append(
                        {
                            "name": target.id,
                            "kind": "constant",
                            "value": _unparse(item.value),
                        }
                    )
    return fields


def _serialize_class(node: ast.ClassDef) -> dict[str, Any]:
    bases = [_unparse(base) for base in node.bases]
    bases = [b for b in bases if b]
    if _is_enum_class(node):
        return {
            "kind": "enum",
            "name": node.name,
            "bases": bases,
            "members": _serialize_enum_members(node),
        }
    members: list[dict[str, Any]] = []
    for item in node.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if item.name.startswith("_") and not item.name.startswith("__"):
                continue
            members.append(_serialize_function(item, kind="method"))
        elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
            if item.target.id.startswith("_"):
                continue
            members.append(
                {
                    "kind": "attribute",
                    "name": item.target.id,
                    "type": _unparse(item.annotation),
                    "default": _unparse(item.value),
                }
            )
    payload: dict[str, Any] = {
        "kind": "class",
        "name": node.name,
        "bases": bases,
        "decorators": _decorator_names(node),
        "members": members,
    }
    if _is_dataclass(node) or _is_pydantic_model(node):
        payload["fields"] = _serialize_class_fields(node)
    return payload


def _serialize_module_assign(node: ast.Assign | ast.AnnAssign) -> dict[str, Any] | None:
    if isinstance(node, ast.AnnAssign):
        if not isinstance(node.target, ast.Name):
            return None
        name = node.target.id
        if name.startswith("_"):
            return None
        kind = "constant" if name.isupper() else "variable"
        return {
            "kind": kind,
            "name": name,
            "type": _unparse(node.annotation),
            "value": _unparse(node.value),
        }
    if not isinstance(node, ast.Assign):
        return None
    out: list[dict[str, Any]] = []
    for target in node.targets:
        if not isinstance(target, ast.Name):
            continue
        name = target.id
        if name.startswith("_") or name == "__all__":
            continue
        kind = "constant" if name.isupper() else "variable"
        out.append(
            {
                "kind": kind,
                "name": name,
                "value": _unparse(node.value),
            }
        )
    return out[0] if len(out) == 1 else {"kind": "assign_group", "names": out}


def _serialize_type_alias(node: ast.AnnAssign) -> dict[str, Any] | None:
    if not isinstance(node.target, ast.Name):
        return None
    name = node.target.id
    if name.startswith("_"):
        return None
    if name.isupper():
        return None
    return {
        "kind": "type_alias",
        "name": name,
        "type": _unparse(node.annotation),
        "value": _unparse(node.value),
    }


def extract_python_module(path: Path, *, package_root: Path) -> dict[str, Any]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    declarations: list[dict[str, Any]] = []
    module_doc = ast.get_docstring(tree) or ""
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            declarations.append(_serialize_class(node))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("_"):
                continue
            declarations.append(_serialize_function(node, kind="function"))
        elif isinstance(node, ast.AnnAssign):
            alias = _serialize_type_alias(node)
            if alias:
                declarations.append(alias)
                continue
            item = _serialize_module_assign(node)
            if item:
                declarations.append(item)
        elif isinstance(node, ast.Assign):
            item = _serialize_module_assign(node)
            if item:
                declarations.append(item)
    rel = path.relative_to(package_root).as_posix()
    return {
        "path": rel,
        "module": rel.replace("/", ".").removesuffix(".py"),
        "doc": module_doc.split("\n\n")[0].strip() if module_doc else "",
        "declarations": declarations,
    }


def _should_skip_path(path: Path) -> bool:
    if path.suffix not in {".py"}:
        return True
    if path.suffix in _SKIP_FILE_SUFFIXES:
        return True
    return any(part in _SKIP_DIR_NAMES for part in path.parts)


def walk_python_package(package_dir: Path) -> list[Path]:
    files = sorted(
        path for path in package_dir.rglob("*.py") if path.is_file() and not _should_skip_path(path)
    )
    return files


def extract_python_structure(sdk_root: Path, *, package_name: str = "porto_sdk") -> dict[str, Any]:
    sdk_root = sdk_root.resolve()
    package_dir = sdk_root / package_name
    if not package_dir.is_dir():
        raise FileNotFoundError(f"Python package not found: {package_dir}")
    modules: list[dict[str, Any]] = []
    for path in walk_python_package(package_dir):
        modules.append(extract_python_module(path, package_root=package_dir))
    tree = _build_tree(modules, root_name=package_name)
    return {
        "language": "python",
        "sdk_root": str(sdk_root),
        "package": package_name,
        "module_count": len(modules),
        "modules": modules,
        "tree": tree,
    }


def _build_tree(modules: list[dict[str, Any]], *, root_name: str) -> dict[str, Any]:
    tree: dict[str, Any] = {"name": root_name, "kind": "directory", "children": {}}

    def _insert(parts: list[str], payload: dict[str, Any]) -> None:
        cursor = tree["children"]
        for part in parts[:-1]:
            node = cursor.setdefault(part, {"name": part, "kind": "directory", "children": {}})
            cursor = node["children"]
        leaf = parts[-1]
        cursor[leaf] = {
            "name": leaf,
            "kind": "file",
            "path": payload.get("path"),
            "module": payload.get("module"),
            "declaration_count": len(payload.get("declarations") or []),
        }

    for module in modules:
        rel = str(module.get("path") or "")
        _insert(rel.split("/"), module)
    return tree
