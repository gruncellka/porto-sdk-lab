#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

require_docker_daemon

echo "🛑 Stopping lab containers..."
compose down --remove-orphans
echo "✅ Lab containers are stopped"
