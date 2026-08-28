#!/usr/bin/env sh
# Fail when standard CI workflows reference heavy/lab/API test entrypoints.
set -eu

ROOT="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

FORBIDDEN='labs-internetmarke|pytest -m api|make test-canary|make test-heavy|make heavy|make test-api'
violations=0

scan_workflows() {
    dir="$1"
    [ -d "$dir" ] || return 0
    for file in "$dir"/*.yml "$dir"/*.yaml; do
        [ -f "$file" ] || continue
        base=$(basename "$file")
        # publish + heavy may run Internetmarke. Ordinary validation must not.
        case "$base" in
            publish.yml|publish.yaml|heavy.yml|heavy.yaml) continue ;;
        esac
        if grep -E -n "$FORBIDDEN" "$file" >/tmp/paid-ci-violations.$$ 2>/dev/null; then
            echo "Forbidden heavy/API pattern in $file:"
            sed 's/^/   /' /tmp/paid-ci-violations.$$
            violations=1
        fi
    done
}

scan_workflows ".github/workflows"
scan_workflows "sdks/porto-sdk-python/.github/workflows"
scan_workflows "sdks/porto-sdk-typescript/.github/workflows"

rm -f /tmp/paid-ci-violations.$$

if [ "$violations" -ne 0 ]; then
    echo ""
    echo "Heavy provider tests belong on heavy.yml or publish.yml (or make labs-internetmarke-*), not validation."
    echo "Standard CI must not invoke labs-internetmarke, pytest -m api, make heavy, or make test-api."
    exit 1
fi

echo "No forbidden heavy/API patterns in standard CI workflows."
