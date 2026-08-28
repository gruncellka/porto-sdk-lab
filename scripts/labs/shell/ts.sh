#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../common.sh"

start_lab_typescript

echo "📘 Opening TypeScript lab shell..."
compose exec "$TYPESCRIPT_LAB_SERVICE" bash
