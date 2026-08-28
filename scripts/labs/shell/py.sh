#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../common.sh"

start_lab_python

echo "🐍 Opening Python lab shell..."
compose exec "$PYTHON_LAB_SERVICE" bash
