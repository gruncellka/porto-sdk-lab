"""CLI for mark measurement and calibration verification."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from labs.lib.python.mark_measure.audit import (  # noqa: E402
    audit_run_dir,
    propose_calibrations_from_runs,
    write_audit_reports,
)
from labs.lib.python.mark_measure.stamp_io import repair_stamp_png_file  # noqa: E402


def _default_porto_data() -> Path:
    return _REPO_ROOT / "resources" / "porto-data" / "porto_data"


def _parse_run_dirs(values: list[str]) -> list[Path]:
    paths: list[Path] = []
    for raw in values:
        path = Path(raw)
        if not path.is_absolute():
            path = _REPO_ROOT / path
        paths.append(path.resolve())
    return paths


def cmd_verify(args: argparse.Namespace) -> int:
    run_dirs = _parse_run_dirs(args.run_dir)
    porto_data = Path(args.porto_data)
    if not porto_data.is_absolute():
        porto_data = _REPO_ROOT / porto_data

    overall_ok = True
    for run_dir in run_dirs:
        if not run_dir.is_dir():
            print(f"error: run dir not found: {run_dir}", file=sys.stderr)
            return 2
        audit = audit_run_dir(
            run_dir,
            porto_data_root=porto_data,
            provider=args.provider,
            integration=args.integration,
            dpi=args.dpi,
        )
        write_audit_reports(run_dir, audit)
        report = audit["report"]
        print(
            f"{run_dir.name}: {report['cases_passed']}/{report['cases_total']} passed "
            f"(ok={report['ok']})"
        )
        if not report["ok"]:
            overall_ok = False
            for case in report["cases"]:
                if not case.get("ok"):
                    print(f"  FAIL {case['case_id']}: {case.get('issues') or case.get('error')}")

    return 0 if overall_ok else 1


def cmd_propose_calibrations(args: argparse.Namespace) -> int:
    run_dirs = _parse_run_dirs(args.run_dir)
    porto_data = Path(args.porto_data)
    if not porto_data.is_absolute():
        porto_data = _REPO_ROOT / porto_data

    calibrations = propose_calibrations_from_runs(
        run_dirs,
        porto_data_root=porto_data,
        provider=args.provider,
        integration=args.integration,
        dpi=args.dpi,
    )
    print(json.dumps(calibrations, indent=2))
    return 0


def cmd_repair(args: argparse.Namespace) -> int:
    root = Path(args.root)
    if not root.is_absolute():
        root = _REPO_ROOT / root
    repaired = 0
    for stamp_path in sorted(root.rglob("stamp.png")):
        before = stamp_path.read_bytes()
        if repair_stamp_png_file(stamp_path):
            after = stamp_path.read_bytes()
            if after != before:
                repaired += 1
                print(f"repaired {stamp_path}")
    print(f"repaired {repaired} file(s)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Measure Internetmarke stamps vs porto-data")
    sub = parser.add_subparsers(dest="command", required=True)

    verify = sub.add_parser("verify", help="Measure stamp.png in run dir(s) and compare to porto-data")
    verify.add_argument(
        "--run-dir",
        action="append",
        required=True,
        help="Run directory (repeatable). Relative paths are from repo root.",
    )
    verify.add_argument("--porto-data", default=str(_default_porto_data()))
    verify.add_argument("--provider", default="deutschepost")
    verify.add_argument("--integration", default="internetmarke")
    verify.add_argument("--dpi", type=int, default=300)
    verify.set_defaults(func=cmd_verify)

    propose = sub.add_parser("propose-calibrations", help="Print calibrations[] JSON from run consensus")
    propose.add_argument("--run-dir", action="append", required=True)
    propose.add_argument("--porto-data", default=str(_default_porto_data()))
    propose.add_argument("--provider", default="deutschepost")
    propose.add_argument("--integration", default="internetmarke")
    propose.add_argument("--dpi", type=int, default=300)
    propose.set_defaults(func=cmd_propose_calibrations)

    repair = sub.add_parser("repair", help="Normalize ZIP-wrapped stamp.png files under a directory")
    repair.add_argument("--root", required=True, help="Directory to scan for stamp.png")
    repair.set_defaults(func=cmd_repair)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
