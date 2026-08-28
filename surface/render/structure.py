"""Render full SDK structure to JSON, Markdown, and declaration-only stub files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from surface.jsonutil import dump_json


def _format_params(params: list[dict[str, Any]], *, language: str) -> str:
    parts: list[str] = []
    for param in params:
        name = str(param.get("name") or "")
        typ = param.get("type")
        optional = bool(param.get("optional"))
        variadic = param.get("variadic")
        if variadic == "args":
            parts.append(f"*{name}" + (f": {typ}" if typ else ""))
            continue
        if variadic == "kwargs":
            parts.append(f"**{name}" + (f": {typ}" if typ else ""))
            continue
        if language == "typescript":
            suffix = "?" if optional else ""
            parts.append(f"{name}{suffix}: {typ or 'unknown'}")
        else:
            if typ:
                parts.append(f"{name}: {typ}" + (" = ..." if optional else ""))
            else:
                parts.append(f"{name}" + (" = ..." if optional else ""))
    return ", ".join(parts)


def _render_declaration(decl: dict[str, Any], *, language: str, indent: str = "") -> list[str]:
    kind = str(decl.get("kind") or "")
    name = str(decl.get("name") or "")
    lines: list[str] = []

    if kind in {"constant", "variable"}:
        typ = decl.get("type")
        if language == "typescript":
            if kind == "constant":
                lines.append(f"{indent}export const {name}: {typ or 'unknown'};")
            else:
                lines.append(f"{indent}export const {name}: {typ or 'unknown'};")
        else:
            if typ:
                lines.append(f"{indent}{name}: {typ}")
            else:
                lines.append(f"{indent}{name} = ...")
        return lines

    if kind == "type_alias":
        typ = decl.get("type") or decl.get("value") or "unknown"
        if language == "typescript":
            lines.append(f"{indent}export type {name} = {typ};")
        else:
            lines.append(f"{indent}{name}: TypeAlias = {typ}")
        return lines

    if kind == "enum":
        if language == "typescript":
            lines.append(f"{indent}export enum {name} {{")
            closer = "}"
        else:
            lines.append(f"{indent}class {name}(Enum):")
            closer = None
        for member in decl.get("members") or []:
            if not isinstance(member, dict):
                continue
            mname = member.get("name")
            mval = member.get("value")
            if language == "typescript":
                if mval is not None and str(mval) != str(mname):
                    lines.append(f"{indent}  {mname} = {mval!r},")
                else:
                    lines.append(f"{indent}  {mname},")
            elif mval is not None:
                lines.append(f"{indent}  {mname} = {mval!r}")
            else:
                lines.append(f"{indent}  {mname}")
        if closer:
            lines.append(f"{indent}{closer}")
        return lines

    if kind in {"class", "interface"}:
        keyword = "interface" if kind == "interface" else "class"
        export = "export " if language == "typescript" else ""
        bases = decl.get("bases") or []
        if language == "typescript":
            extends = f" extends {', '.join(str(b) for b in bases)}" if bases else ""
            opener, closer = "{", "}"
        else:
            extends = f"({', '.join(str(b) for b in bases)})" if bases else ""
            opener, closer = ":", ""
        lines.append(f"{indent}{export}{keyword} {name}{extends} {opener}".rstrip())
        fields = decl.get("fields") or []
        field_names = {str(f.get("name")) for f in fields if isinstance(f, dict) and f.get("name")}
        for field in fields:
            if not isinstance(field, dict):
                continue
            fname = field.get("name")
            ftype = field.get("type") or "unknown"
            if language == "typescript":
                opt = "?" if field.get("default") is not None else ""
                lines.append(f"{indent}  {fname}{opt}: {ftype};")
            else:
                lines.append(f"{indent}  {fname}: {ftype}")
        for member in decl.get("members") or []:
            if not isinstance(member, dict):
                continue
            mk = str(member.get("kind") or "")
            if mk in {"method", "function"}:
                params = _format_params(member.get("params") or [], language=language)
                ret = member.get("returns") or "None" if language == "python" else "void"
                async_prefix = "async " if member.get("async") else ""
                if language == "typescript":
                    lines.append(f"{indent}  {async_prefix}{member.get('name')}({params}): {ret};")
                else:
                    lines.append(
                        f"{indent}  {async_prefix}def {member.get('name')}({params}) -> {ret}: ..."
                    )
            elif mk == "attribute":
                if member.get("name") in field_names:
                    continue
                mtype = member.get("type") or "unknown"
                if language == "typescript":
                    opt = "?" if member.get("optional") else ""
                    lines.append(f"{indent}  {member.get('name')}{opt}: {mtype};")
                else:
                    lines.append(f"{indent}  {member.get('name')}: {mtype}")
        if language == "python":
            if closer:
                pass  # dataclass-style blocks omit explicit closer
        else:
            lines.append(f"{indent}{closer}")
        return lines

    if kind in {"function", "method"}:
        params = _format_params(decl.get("params") or [], language=language)
        ret = decl.get("returns") or ("None" if language == "python" else "void")
        async_prefix = "async " if decl.get("async") else ""
        if language == "typescript":
            export = "export " if kind == "function" else ""
            lines.append(f"{indent}{export}{async_prefix}function {name}({params}): {ret};")
        else:
            lines.append(f"{indent}{async_prefix}def {name}({params}) -> {ret}: ...")
        return lines

    lines.append(f"{indent}// {kind} {name}")
    return lines


def render_module_stub(module: dict[str, Any], *, language: str) -> str:
    path = str(module.get("path") or "module")
    doc = str(module.get("doc") or "").strip()
    header = [
        f"# Declaration stub — {path}",
        "# Generated by surface/ — no implementations.",
        "",
    ]
    if doc:
        header.extend([f'"""{doc}"""' if language == "python" else f"/** {doc} */", ""])
    body: list[str] = []
    for decl in module.get("declarations") or []:
        if isinstance(decl, dict):
            body.extend(_render_declaration(decl, language=language))
            body.append("")
    if language == "python":
        return "\n".join(header + body).rstrip() + "\n"
    return "\n".join(header + body).rstrip() + "\n"


def _walk_tree(node: dict[str, Any], prefix: str, lines: list[str]) -> None:
    if node.get("kind") == "file":
        count = node.get("declaration_count", 0)
        lines.append(f"{prefix}{node.get('name')} ({count} declarations)")
        return
    children = node.get("children") or {}
    if isinstance(children, dict):
        entries = sorted(children.items(), key=lambda item: item[0])
        for index, (name, child) in enumerate(entries):
            is_last = index == len(entries) - 1
            branch = "└── " if is_last else "├── "
            extension = "    " if is_last else "│   "
            if isinstance(child, dict) and child.get("kind") == "directory":
                lines.append(f"{prefix}{branch}{name}/")
                _walk_tree(child, prefix + extension, lines)
            elif isinstance(child, dict):
                _walk_tree(child, prefix + branch, lines)


def render_structure_markdown(structure: dict[str, Any]) -> str:
    language = str(structure.get("language") or "unknown")
    package = str(structure.get("package") or "")
    module_count = structure.get("module_count", 0)
    lines = [
        f"# Porto SDK structure ({language})",
        "",
        f"- **Package:** `{package}`",
        f"- **Modules:** {module_count}",
        f"- **SDK root:** `{structure.get('sdk_root')}`",
        "",
        "## Directory tree",
        "",
        "```",
        f"{package}/",
    ]
    tree = structure.get("tree") or {}
    _walk_tree(tree, "", lines)
    lines.append("```")
    lines.append("")
    lines.append("## Modules")
    lines.append("")
    for module in structure.get("modules") or []:
        if not isinstance(module, dict):
            continue
        path = module.get("path")
        lines.append(f"### `{path}`")
        lines.append("")
        stub = render_module_stub(module, language=language)
        fence = "python" if language == "python" else "typescript"
        lines.append(f"```{fence}")
        lines.append(stub.rstrip())
        lines.append("```")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_structure_artifacts(
    structure: dict[str, Any],
    *,
    out_dir: Path,
    write_stubs: bool = True,
) -> list[str]:
    language = str(structure.get("language") or "unknown")
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []

    json_path = out_dir / "structure.json"
    dump_json(json_path, structure)
    written.append(str(json_path))

    md_path = out_dir / "STRUCTURE.md"
    md_path.write_text(render_structure_markdown(structure), encoding="utf-8")
    written.append(str(md_path))

    if not write_stubs:
        return written

    stubs_root = out_dir / "stubs"
    if stubs_root.exists():
        import shutil

        shutil.rmtree(stubs_root)
    stubs_root.mkdir(parents=True, exist_ok=True)
    ext = ".py" if language == "python" else ".ts"
    for module in structure.get("modules") or []:
        if not isinstance(module, dict):
            continue
        rel = str(module.get("path") or f"module{ext}")
        if rel.endswith(".py") or rel.endswith(".ts"):
            stub_path = stubs_root / rel
        else:
            stub_path = stubs_root / f"{rel}{ext}"
        stub_path.parent.mkdir(parents=True, exist_ok=True)
        stub_path.write_text(render_module_stub(module, language=language), encoding="utf-8")
        written.append(str(stub_path))
    return written
