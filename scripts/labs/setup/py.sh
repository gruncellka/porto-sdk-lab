#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../common.sh"

echo "🐍 Setting up Python lab inside Docker..."
run_python_lab_cmd "./setup.sh"
echo "✅ Python lab is ready"
