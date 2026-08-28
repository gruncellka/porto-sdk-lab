#!/usr/bin/env sh
# Lab-owned: editable-install Lab porto-data + porto-features into Python SDK .venv.
# Usage: overlay-python.sh <path-to-porto-sdk-python>
set -eu

SDK_ROOT="${1:?usage: overlay-python.sh <sdk-python-root>}"
LAB_ROOT="$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)"
DATA="$LAB_ROOT/resources/porto-data"
FEATURES="$LAB_ROOT/resources/porto-features"

test -d "$DATA" || {
    echo "missing $DATA" >&2
    exit 1
}
test -d "$FEATURES" || {
    echo "missing $FEATURES" >&2
    exit 1
}

cd "$SDK_ROOT"
if [ ! -x .venv/bin/python ]; then
    PYTHON_BOOT="$(command -v python3.13 2>/dev/null || command -v python3)"
    "$PYTHON_BOOT" -m venv .venv
    .venv/bin/pip install -q -U pip
fi
.venv/bin/pip install -e "$DATA"
.venv/bin/pip install -e "$FEATURES"
.venv/bin/pip install -e ".[dev]"
echo "Python SDK local resources linked (Lab-owned)."
