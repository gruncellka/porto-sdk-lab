#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../common.sh"

TARGET_SCRIPT="${1:-example_nextjs_integration.ts}"
TARGET_SCRIPT_ESCAPED="$(shell_escape "$TARGET_SCRIPT")"

echo "▶️ Running TypeScript lab script: $TARGET_SCRIPT"
run_typescript_lab_cmd "pnpm exec tsx $TARGET_SCRIPT_ESCAPED"
