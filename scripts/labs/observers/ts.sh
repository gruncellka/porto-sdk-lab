#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_SCRIPT="${1:-example_basic.ts}"

python3 "$SCRIPT_DIR/runner.py" \
  --label "labs-run-ts:${TARGET_SCRIPT}" \
  -- \
  bash "$SCRIPT_DIR/../run/ts.sh" "$TARGET_SCRIPT"
