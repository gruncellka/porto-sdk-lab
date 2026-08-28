#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
COMPOSE_FILE="$REPO_ROOT/docker-compose.labs.yml"
PYTHON_LAB_SERVICE="lab-py"
TYPESCRIPT_LAB_SERVICE="lab-ts"

if docker compose version >/dev/null 2>&1; then
  COMPOSE_CMD=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE_CMD=(docker-compose)
else
  echo "❌ Error: docker compose is not installed."
  exit 1
fi

ensure_host_layout() {
  local required_paths=(
    "$COMPOSE_FILE"
    "$REPO_ROOT/labs/python/setup.sh"
    "$REPO_ROOT/labs/typescript/setup.sh"
    "$REPO_ROOT/sdks/porto-sdk-python"
    "$REPO_ROOT/sdks/porto-sdk-typescript"
  )

  local path
  for path in "${required_paths[@]}"; do
    if [ ! -e "$path" ]; then
      echo "❌ Error: required path is missing: $path"
      exit 1
    fi
  done
}

docker_daemon_available() {
  docker info >/dev/null 2>&1
}

require_docker_daemon() {
  if ! docker_daemon_available; then
    echo "❌ Error: Docker daemon is not running."
    echo "   Start Docker Desktop (or Docker daemon) and retry."
    exit 1
  fi
}

compose() {
  ensure_host_layout
  (
    cd "$REPO_ROOT"
    "${COMPOSE_CMD[@]}" -f "$COMPOSE_FILE" "$@"
  )
}

shell_escape() {
  printf "%q" "$1"
}

# Observer paths are host-absolute from runner.py; inside the lab container use /workspace/...
host_path_to_workspace() {
  local path="$1"
  case "$path" in
    "$REPO_ROOT")
      printf '/workspace'
      ;;
    "$REPO_ROOT"/*)
      printf '/workspace/%s' "${path#$REPO_ROOT/}"
      ;;
    *)
      printf '%s' "$path"
      ;;
  esac
}

start_lab_python() {
  require_docker_daemon
  compose up -d "$PYTHON_LAB_SERVICE"
}

start_lab_typescript() {
  require_docker_daemon
  compose up -d "$TYPESCRIPT_LAB_SERVICE"
}

start_labs() {
  require_docker_daemon
  compose up -d "$PYTHON_LAB_SERVICE" "$TYPESCRIPT_LAB_SERVICE"
}

run_python_lab_cmd() {
  local command="$1"
  local -a env_args=()
  if [ -n "${OBSERVER_RUN_ID:-}" ]; then
    env_args+=(-e "OBSERVER_RUN_ID=$OBSERVER_RUN_ID")
  fi
  if [ -n "${OBSERVER_RUN_DIR:-}" ]; then
    env_args+=(-e "OBSERVER_RUN_DIR=$(host_path_to_workspace "$OBSERVER_RUN_DIR")")
  fi
  if [ -n "${OBSERVER_ARTIFACTS_ROOT:-}" ]; then
    env_args+=(-e "OBSERVER_ARTIFACTS_ROOT=$(host_path_to_workspace "$OBSERVER_ARTIFACTS_ROOT")")
  fi
  if [ -n "${PORTO_LAB_HTTP_TRACE:-}" ]; then
    env_args+=(-e "PORTO_LAB_HTTP_TRACE=$PORTO_LAB_HTTP_TRACE")
  fi
  if [ -n "${PORTO_LAB_HTTP_TRACE_BODIES:-}" ]; then
    env_args+=(-e "PORTO_LAB_HTTP_TRACE_BODIES=$PORTO_LAB_HTTP_TRACE_BODIES")
  fi
  if [ -n "${PROFILE:-}" ]; then
    env_args+=(-e "PROFILE=$PROFILE")
  fi
  if [ -n "${DRY_RUN:-}" ]; then
    env_args+=(-e "DRY_RUN=$DRY_RUN")
  fi
  if [ -n "${MAX_CASES:-}" ]; then
    env_args+=(-e "MAX_CASES=$MAX_CASES")
  fi
  env_args+=(-e "PORTO_DATA_PATH=/workspace/resources/porto-data/porto_data")
  start_lab_python
  compose exec "${env_args[@]}" "$PYTHON_LAB_SERVICE" bash -lc "if [ ! -f venv/bin/activate ]; then ./setup.sh; fi; source venv/bin/activate; $command"
}

run_typescript_lab_cmd() {
  local command="$1"
  local -a env_args=()
  if [ -n "${OBSERVER_RUN_ID:-}" ]; then
    env_args+=(-e "OBSERVER_RUN_ID=$OBSERVER_RUN_ID")
  fi
  if [ -n "${OBSERVER_RUN_DIR:-}" ]; then
    env_args+=(-e "OBSERVER_RUN_DIR=$(host_path_to_workspace "$OBSERVER_RUN_DIR")")
  fi
  if [ -n "${OBSERVER_ARTIFACTS_ROOT:-}" ]; then
    env_args+=(-e "OBSERVER_ARTIFACTS_ROOT=$(host_path_to_workspace "$OBSERVER_ARTIFACTS_ROOT")")
  fi
  if [ -n "${PORTO_LAB_HTTP_TRACE:-}" ]; then
    env_args+=(-e "PORTO_LAB_HTTP_TRACE=$PORTO_LAB_HTTP_TRACE")
  fi
  if [ -n "${PORTO_LAB_HTTP_TRACE_BODIES:-}" ]; then
    env_args+=(-e "PORTO_LAB_HTTP_TRACE_BODIES=$PORTO_LAB_HTTP_TRACE_BODIES")
  fi
  if [ -n "${PROFILE:-}" ]; then
    env_args+=(-e "PROFILE=$PROFILE")
  fi
  if [ -n "${DRY_RUN:-}" ]; then
    env_args+=(-e "DRY_RUN=$DRY_RUN")
  fi
  if [ -n "${MAX_CASES:-}" ]; then
    env_args+=(-e "MAX_CASES=$MAX_CASES")
  fi
  env_args+=(-e "PORTO_DATA_PATH=/workspace/resources/porto-data/porto_data")
  start_lab_typescript
  compose exec "${env_args[@]}" "$TYPESCRIPT_LAB_SERVICE" bash -lc "if ! command -v pnpm >/dev/null 2>&1 || [ ! -x node_modules/.bin/tsx ]; then corepack enable && corepack prepare pnpm@10 --activate && ./setup.sh; fi; $command"
}
