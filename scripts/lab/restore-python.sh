#!/usr/bin/env sh
# Lab-owned: restore PyPI porto-data + porto-features in Python SDK .venv.
# Usage: restore-python.sh <path-to-porto-sdk-python>
set -eu

SDK_ROOT="${1:?usage: restore-python.sh <sdk-python-root>}"
cd "$SDK_ROOT"
if [ ! -x .venv/bin/python ]; then
    PYTHON_BOOT="$(command -v python3.13 2>/dev/null || command -v python3)"
    "$PYTHON_BOOT" -m venv .venv
    .venv/bin/pip install -q -U pip
fi
# Versions come from the SDK pyproject when reinstalling editable; force registry packages.
.venv/bin/pip install --force-reinstall "gruncellka-porto-data" "gruncellka-porto-features"
.venv/bin/pip install -e ".[dev]"
echo "Python SDK registry packages restored."
