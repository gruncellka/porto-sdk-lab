#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../common.sh"

TARGET_SCRIPT="${1:-example_fastapi_integration.py}"
TARGET_SCRIPT_ESCAPED="$(shell_escape "$TARGET_SCRIPT")"

echo "Watching Python lab script: $TARGET_SCRIPT"
run_python_lab_cmd "python -m watchfiles \"python $TARGET_SCRIPT_ESCAPED\" . ../../sdks/porto-sdk-python/src ../../resources/porto-data/porto_data ../../resources/porto-features"
