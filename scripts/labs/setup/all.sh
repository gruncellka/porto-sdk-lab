#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

bash "$SCRIPT_DIR/py.sh"
bash "$SCRIPT_DIR/ts.sh"

echo "✅ All labs are ready"
