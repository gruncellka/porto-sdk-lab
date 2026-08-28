#!/usr/bin/env bash
# Measure stamp.png dimensions in calibration matrix runs vs porto-data.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
RUNS_DIR="$REPO_ROOT/labs/experiments/runs"
PORTO_DATA="$REPO_ROOT/resources/porto-data/porto_data"

find_latest_layout_run() {
  local layout="$1"
  local run_dir=""
  local candidate
  for candidate in $(ls -td "$RUNS_DIR"/* 2>/dev/null || true); do
    [ -f "$candidate/metadata.json" ] || continue
    if python3 - "$candidate/metadata.json" "$layout" <<'PY'
import json
import sys
from pathlib import Path

meta_path = Path(sys.argv[1])
layout = sys.argv[2]
meta = json.loads(meta_path.read_text(encoding="utf-8"))
if meta.get("cases_failed", 1) != 0:
    sys.exit(1)
if int(meta.get("cases_passed") or 0) < int(meta.get("cases_total") or 0):
    sys.exit(1)
mark_layout = meta.get("mark_layout")
voucher_layout = meta.get("voucher_layout")
profile = str(meta.get("profile") or "")

if layout == "FRANKING_ZONE":
    ok = (
        mark_layout == "franking_only"
        or voucher_layout == "FRANKING_ZONE"
        or profile.startswith("franking")
        or "franking" in meta_path.parent.name
    )
else:
    ok = (
        mark_layout == "address_block"
        or voucher_layout == "ADDRESS_ZONE"
        or (profile == "full" and "franking" not in meta_path.parent.name)
    )
sys.exit(0 if ok else 1)
PY
    then
      run_dir="$candidate"
      break
    fi
  done
  printf '%s' "$run_dir"
}

RUN_DIRS=()
if [ -n "${RUN_ADDRESS:-}" ]; then
  RUN_DIRS+=("$RUN_ADDRESS")
else
  ADDR_RUN="$(find_latest_layout_run ADDRESS_ZONE)"
  [ -n "$ADDR_RUN" ] && RUN_DIRS+=("$ADDR_RUN")
fi

if [ -n "${RUN_FRANKING:-}" ]; then
  RUN_DIRS+=("$RUN_FRANKING")
else
  FRANK_RUN="$(find_latest_layout_run FRANKING_ZONE)"
  [ -n "$FRANK_RUN" ] && RUN_DIRS+=("$FRANK_RUN")
fi

if [ "${#RUN_DIRS[@]}" -eq 0 ]; then
  echo "No run directories found. Set RUN_ADDRESS / RUN_FRANKING or run calibration matrix first." >&2
  exit 1
fi

ARGS=()
for dir in "${RUN_DIRS[@]}"; do
  echo "Measuring: $dir"
  ARGS+=(--run-dir "$dir")
done

cd "$REPO_ROOT"
# shellcheck disable=SC1091
source labs/python/venv/bin/activate
exec python3 -m labs.lib.python.mark_measure verify "${ARGS[@]}" --porto-data "$PORTO_DATA"
