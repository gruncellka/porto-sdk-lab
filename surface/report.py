"""Write surface compare artifacts (JSON-first; optional Markdown view)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from surface.compare import (
    build_report,
    merge_contract,
    observed_surface,
    parity_diagnostics,
    validate_contract,
)
from surface.jsonutil import dump_json

ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"


def _report_markdown(report: dict[str, Any]) -> str:
    summary = report.get("summary") or {}
    lines = [
        "# Surface parity report",
        "",
        f"**Status:** `{report.get('status')}`",
        "",
        "## Summary",
        "",
        f"- errors: {summary.get('errors', 0)}",
        f"- warnings: {summary.get('warnings', 0)}",
        f"- intentional: {summary.get('intentional', 0)}",
        "",
        "## Differences",
        "",
    ]
    differences = report.get("differences") or []
    if not differences:
        lines.append("_No differences._")
        lines.append("")
        return "\n".join(lines)
    for row in differences:
        if not isinstance(row, dict):
            continue
        lines.append(
            f"- `{row.get('concept')}` · `{row.get('kind')}` · "
            f"severity=`{row.get('severity')}` · "
            f"python=`{row.get('python')}` · typescript=`{row.get('typescript')}`"
        )
    lines.append("")
    return "\n".join(lines)


def write_report(
    python_surface: dict[str, Any] | None,
    typescript_surface: dict[str, Any] | None,
    *,
    artifacts_dir: Path | None = None,
    write_markdown: bool = True,
    extra_python: list[str] | None = None,
    extra_typescript: list[str] | None = None,
) -> list[str]:
    """Persist observed surfaces + machine report; optional human Markdown view.

    Primary artifacts:
      - python.json
      - typescript.json
      - report.json

    Secondary (optional):
      - report.md  (generated from report.json; not the primary artifact)
    """
    out = Path(artifacts_dir or ARTIFACTS_DIR)
    out.mkdir(parents=True, exist_ok=True)

    dump_json(out / "python.json", observed_surface(python_surface, sdk="python"))
    dump_json(out / "typescript.json", observed_surface(typescript_surface, sdk="typescript"))

    report = build_report(
        python_surface,
        typescript_surface,
        extra_python=extra_python,
        extra_typescript=extra_typescript,
    )
    dump_json(out / "report.json", report)
    if write_markdown:
        (out / "report.md").write_text(_report_markdown(report), encoding="utf-8")

    contract = merge_contract(python_surface, typescript_surface)
    validate_contract(contract)

    lines = parity_diagnostics(
        python_surface,
        typescript_surface,
        extra_python=extra_python,
        extra_typescript=extra_typescript,
    )
    return lines
