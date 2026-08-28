#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../common.sh"

echo "📘 Setting up TypeScript lab inside Docker..."
run_typescript_lab_cmd "./setup.sh"
echo "✅ TypeScript lab is ready"
