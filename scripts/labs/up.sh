#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../common.sh"

case "${LABS:-both}" in
  py | python)
    start_lab_python
    ;;
  ts | typescript)
    start_lab_typescript
    ;;
  both | *)
    start_labs
    ;;
esac

echo "✅ Lab containers are running"
