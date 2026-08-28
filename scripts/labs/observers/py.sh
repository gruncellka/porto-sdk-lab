#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_SCRIPT="${1:-example_basic.py}"
PYTHON_BIN="${PYTHON:-$(command -v python3.13 2>/dev/null || command -v python3)}"

"$PYTHON_BIN" "$SCRIPT_DIR/runner.py" \
  --label "labs-run-py:${TARGET_SCRIPT}" \
  -- \
  bash "$SCRIPT_DIR/../run/py.sh" "$TARGET_SCRIPT"
