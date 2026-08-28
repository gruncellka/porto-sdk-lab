#!/usr/bin/env python3
"""Promote green lab run artifacts into Lab matrix evidence.

Reads labs/experiments/runs/<run_id>/cases/<case_id>/ and, for cases whose
validation.json reports ok=true, updates matching rows in matrix/orders.generated.yaml
with evidence metadata and last_verified timestamp.

Usage (from Porto SDK Lab root):
  python scripts/labs/promote-evidence.py 20260707-131725-1c3
  python scripts/labs/promote-evidence.py 20260707-131725-1c3 --dry-run
  python scripts/labs/promote-evidence.py 20260707-131725-1c3 --case deutschepost.internetmarke.standardbrief.domestic
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

try:
    import yaml
except ImportError:
    print("❌ PyYAML required: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

from labs.lib.python.matrix.case_id import case_id_for  # noqa: E402
from labs.lib.python.matrix.constants import (  # noqa: E402
    ADAPTER_INTERNETMARKE,
    PROVIDER_DEUTSCHEPOST,
)


def _orders_path() -> Path:
    return _REPO_ROOT / "matrix" / "orders.generated.yaml"


def _runs_root() -> Path:
    return _REPO_ROOT / "labs" / "experiments" / "runs"


def _load_yaml_doc(path: Path) -> tuple[list[str], dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    body_lines = [line for line in lines if line.strip() and not line.strip().startswith("#")]
    doc = yaml.safe_load("\n".join(body_lines))
    return lines, doc if isinstance(doc, dict) else {}


def _normalize_timestamp(value: str | None) -> str:
    if not value:
        return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    normalized = value.replace("+00:00", "Z")
    if normalized.endswith("Z"):
        return normalized
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _resolve_case_id(case_dir: Path) -> str | None:
    sdk_input_path = case_dir / "sdk_input.json"
    if sdk_input_path.is_file():
        payload = json.loads(sdk_input_path.read_text(encoding="utf-8"))
        raw_case_id = payload.get("case_id")
        if isinstance(raw_case_id, str) and raw_case_id.count(".") >= 3:
            return raw_case_id
        product_id = payload.get("product_id")
        zone_id = payload.get("zone_id")
        if isinstance(product_id, str) and isinstance(zone_id, str):
            service_ids = payload.get("service_ids") or []
            if isinstance(service_ids, list):
                services = tuple(str(item) for item in service_ids)
                return case_id_for(
                    PROVIDER_DEUTSCHEPOST,
                    ADAPTER_INTERNETMARKE,
                    product_id,
                    zone_id,
                    services,
                )

    dir_name = case_dir.name
    if dir_name.count(".") >= 3:
        return dir_name
    return None


def _case_is_green(case_dir: Path) -> bool:
    validation_path = case_dir / "validation.json"
    if not validation_path.is_file():
        return False
    payload = json.loads(validation_path.read_text(encoding="utf-8"))
    return payload.get("ok") is True


def _collect_green_cases(
    run_dir: Path,
    *,
    case_filter: set[str] | None,
) -> dict[str, Path]:
    cases_dir = run_dir / "cases"
    if not cases_dir.is_dir():
        return {}

    green: dict[str, Path] = {}
    for case_dir in sorted(cases_dir.iterdir()):
        if not case_dir.is_dir():
            continue
        if not _case_is_green(case_dir):
            continue
        case_id = _resolve_case_id(case_dir)
        if not case_id:
            continue
        if case_filter and case_id not in case_filter:
            continue
        green[case_id] = case_dir
    return green


def _evidence_payload(
    *,
    run_id: str,
    case_dir: Path,
    sdk_language: str | None,
) -> dict[str, str]:
    rel_case = case_dir.relative_to(_REPO_ROOT).as_posix()
    payload: dict[str, str] = {
        "run_id": run_id,
        "case_path": rel_case,
    }
    if sdk_language:
        payload["sdk_language"] = sdk_language
    return payload


def promote_run(
    run_id: str,
    *,
    dry_run: bool = False,
    case_filter: set[str] | None = None,
) -> int:
    run_dir = _runs_root() / run_id
    if not run_dir.is_dir():
        print(f"❌ Run directory not found: {run_dir}", file=sys.stderr)
        return 1

    orders_path = _orders_path()
    if not orders_path.is_file():
        print(f"❌ Missing orders matrix: {orders_path}", file=sys.stderr)
        return 1

    green_cases = _collect_green_cases(run_dir, case_filter=case_filter)
    if not green_cases:
        print(f"❌ No green cases found under {run_dir / 'cases'}", file=sys.stderr)
        return 1

    metadata_path = run_dir / "metadata.json"
    metadata: dict[str, Any] = {}
    if metadata_path.is_file():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    last_verified = _normalize_timestamp(metadata.get("finished_at"))
    sdk_language = metadata.get("sdk_language")
    sdk_language_str = sdk_language if isinstance(sdk_language, str) else None

    header_lines, doc = _load_yaml_doc(orders_path)
    order_cells = doc.get("order_cells")
    if not isinstance(order_cells, list):
        print(f"❌ Invalid orders matrix (missing order_cells): {orders_path}", file=sys.stderr)
        return 1

    known_ids = {
        row.get("case_id")
        for row in order_cells
        if isinstance(row, dict) and isinstance(row.get("case_id"), str)
    }
    promotable = {case_id: path for case_id, path in green_cases.items() if case_id in known_ids}
    skipped = sorted(set(green_cases) - known_ids)
    if skipped:
        print(
            f"⚠️  Skipping {len(skipped)} green case(s) not in orders.generated.yaml",
            file=sys.stderr,
        )
        for skipped_id in skipped:
            print(f"   - {skipped_id}", file=sys.stderr)
    if not promotable:
        print("❌ No green case_ids match orders.generated.yaml.", file=sys.stderr)
        return 1

    updated = 0
    for row in order_cells:
        if not isinstance(row, dict):
            continue
        case_id = row.get("case_id")
        if not isinstance(case_id, str) or case_id not in promotable:
            continue
        row["evidence"] = _evidence_payload(
            run_id=run_id,
            case_dir=promotable[case_id],
            sdk_language=sdk_language_str,
        )
        row["last_verified"] = last_verified
        updated += 1

    if updated == 0:
        print("❌ No matching order_cells updated.", file=sys.stderr)
        return 1

    doc["generated_at"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    body = yaml.dump(doc, sort_keys=False, allow_unicode=True, default_flow_style=False)
    header = "".join(line for line in header_lines if line.strip().startswith("#"))
    if header and not header.endswith("\n"):
        header += "\n"
    output = header + body

    if dry_run:
        print(f"✅ Would update {updated} case(s) in {orders_path}")
        for case_id in sorted(promotable):
            print(f"   - {case_id}")
        return 0

    orders_path.write_text(output, encoding="utf-8")
    print(f"✅ Updated evidence for {updated} green case(s) in {orders_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Promote green lab run cases into orders.generated.yaml evidence."
    )
    parser.add_argument("run_id", help="Run id under labs/experiments/runs/")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned updates without writing orders.generated.yaml",
    )
    parser.add_argument(
        "--case",
        action="append",
        dest="cases",
        metavar="CASE_ID",
        help="Limit promotion to specific case_id (repeatable)",
    )
    args = parser.parse_args()

    case_filter = set(args.cases) if args.cases else None
    return promote_run(args.run_id, dry_run=args.dry_run, case_filter=case_filter)


if __name__ == "__main__":
    raise SystemExit(main())
