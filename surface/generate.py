"""Generate public-surface artifacts for both Porto SDKs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from surface.extract import extra_symbols, extract_python, extract_typescript, filter_surface
from surface.extract.normalize import normalize_surface
from surface.report import write_report

LAB_ROOT = Path(__file__).resolve().parents[1]
SURFACE_ROOT = Path(__file__).resolve().parent
DEFAULT_PY_SDK = LAB_ROOT / "sdks" / "porto-sdk-python"
DEFAULT_TS_SDK = LAB_ROOT / "sdks" / "porto-sdk-typescript"
DEFAULT_OUT = SURFACE_ROOT / "artifacts"


def observed_python(sdk_root: Path) -> dict[str, Any]:
    return normalize_surface(filter_surface(extract_python(sdk_root)))


def observed_typescript(sdk_root: Path) -> dict[str, Any]:
    return normalize_surface(filter_surface(extract_typescript(sdk_root, tools_root=SURFACE_ROOT)))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Generate public-surface artifacts (python.json / typescript.json / "
            "report.json) for both Porto SDKs."
        ),
    )
    parser.add_argument("--python-sdk", type=Path, default=DEFAULT_PY_SDK)
    parser.add_argument("--typescript-sdk", type=Path, default=DEFAULT_TS_SDK)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--language",
        choices=("python", "typescript", "both"),
        default="both",
    )
    parser.add_argument(
        "--no-markdown",
        action="store_true",
        help="Skip the optional report.md view",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero when report.json summary errors > 0",
    )
    args = parser.parse_args(argv)

    extras_py: list[str] = []
    extras_ts: list[str] = []
    py = None
    ts = None
    if args.language in {"python", "both"}:
        raw_py = extract_python(args.python_sdk)
        extras_py = extra_symbols(raw_py)
        py = normalize_surface(filter_surface(raw_py))
    if args.language in {"typescript", "both"}:
        raw_ts = extract_typescript(args.typescript_sdk, tools_root=SURFACE_ROOT)
        extras_ts = extra_symbols(raw_ts)
        ts = normalize_surface(filter_surface(raw_ts))

    lines = write_report(
        py,
        ts,
        artifacts_dir=args.out,
        write_markdown=not args.no_markdown,
        extra_python=extras_py,
        extra_typescript=extras_ts,
    )
    print(f"Wrote public-surface artifacts under {args.out}")
    for name in ("python.json", "typescript.json", "report.json", "report.md"):
        path = args.out / name
        if path.is_file():
            print(f"  - {path}")
    if lines:
        print("Parity diagnostics:")
        for line in lines:
            print(f"  {line}")

    if args.check:
        report_path = args.out / "report.json"
        if not report_path.is_file():
            print("surface-check: missing report.json", file=sys.stderr)
            return 1
        report = json.loads(report_path.read_text(encoding="utf-8"))
        errors = int((report.get("summary") or {}).get("errors") or 0)
        if errors > 0:
            print(f"surface-check: {errors} error(s) in report.json", file=sys.stderr)
            return 1
        print("surface-check: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
