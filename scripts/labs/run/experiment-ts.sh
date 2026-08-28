#!/usr/bin/env bash
# Run a repo-root TypeScript experiment script inside the lab container.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../common.sh"

TARGET="${1:?experiment script path relative to repo root}"
TARGET_ESCAPED="$(shell_escape "$TARGET")"

run_typescript_lab_cmd "cd /workspace/labs/typescript && NODE_PATH=/workspace/labs/typescript/node_modules pnpm exec tsx /workspace/$TARGET_ESCAPED"
