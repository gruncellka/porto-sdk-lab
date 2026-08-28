#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

ensure_host_layout

echo "🔎 Verifying Docker lab compose configuration..."
CONFIG="$(compose config)"

required_config_markers=(
  "lab-py:"
  "lab-ts:"
  "working_dir: /workspace/labs/python"
  "working_dir: /workspace/labs/typescript"
  "target: /workspace"
  "target: /workspace/labs/python/venv"
  "target: /workspace/labs/typescript/node_modules"
  "target: /workspace/sdks/porto-sdk-typescript/node_modules"
)

for marker in "${required_config_markers[@]}"; do
  if [[ "$CONFIG" != *"$marker"* ]]; then
    echo "❌ Missing compose config marker: $marker"
    exit 1
  fi
done

echo "✅ Compose mounts and working directories look correct"

if ! docker_daemon_available; then
  echo "⚠️ Docker daemon is not running; skipping runtime mount checks."
  echo "   Start Docker and run: make labs-verify"
  exit 0
fi

echo "🔬 Running runtime mount checks..."
compose up -d lab-py lab-ts >/dev/null
compose exec lab-py bash -lc "test -d /workspace/labs/python && test -d /workspace/sdks/porto-sdk-python"
compose exec lab-ts bash -lc "test -d /workspace/labs/typescript && test -d /workspace/sdks/porto-sdk-typescript"

echo "✅ Runtime mount checks passed"
