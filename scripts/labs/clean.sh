#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

require_docker_daemon

echo "🧹 Removing lab containers and volumes..."
compose down --volumes --remove-orphans
echo "✅ Lab Docker state cleaned"
