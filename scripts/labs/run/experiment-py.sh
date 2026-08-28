#!/usr/bin/env bash
# Run a repo-root Python experiment script inside the lab container.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../common.sh"

TARGET="${1:?experiment script path relative to repo root}"
TARGET_ESCAPED="$(shell_escape "$TARGET")"

run_python_lab_cmd "cd /workspace && source labs/python/venv/bin/activate && python3 $TARGET_ESCAPED"
