#!/usr/bin/env sh
# Post-approval workflow: gate check (no charge) → canary purchase if both gates pass.
#
# Gate 1: DHL developer app token
# Gate 2: Portokasse user approved the app (Geschäftsanwendungen)

set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$REPO_ROOT"

echo "Step 1/2 — approval gate check (no purchase)"
echo ""

if bash "$SCRIPT_DIR/run/py.sh" example_internetmarke_gate_check.py; then
  :
else
  code=$?
  echo ""
  if [ "$code" -eq 1 ]; then
    echo "Stopped before purchase — resolve the gate above, then re-run:"
    echo "  make labs-internetmarke-post-approval"
  fi
  exit "$code"
fi

echo ""
echo "Step 2/2 — canary purchase (1 case, costs money)"
echo ""

exec make labs-internetmarke-canary
