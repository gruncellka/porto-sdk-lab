#!/usr/bin/env python3
"""
Regenerate Lab matrix/sdk.yaml from @sdk Gherkin scenarios.

Usage (from Porto SDK Lab root):
  python scripts/matrix-sdk-sync.py
  python scripts/matrix-sdk-sync.py --check
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from labs.lib.python.matrix.sdk_sync import (  # noqa: E402
    dump_sdk_yaml,
    scan_sdk_features,
    write_sdk_matrix,
)


def _porto_features_root() -> Path:
    env = __import__("os").environ.get("PORTO_FEATURES_PATH")
    if env:
        candidate = Path(env).expanduser().resolve()
        if (candidate / "features").is_dir():
            return candidate
        if (candidate / "porto_features" / "features").is_dir():
            return candidate / "porto_features"
    bundled = _REPO_ROOT / "resources" / "porto-features" / "porto_features"
    if bundled.is_dir():
        return bundled
    raise FileNotFoundError(
        "porto-features not found. Set PORTO_FEATURES_PATH or run from Lab with resources/porto-features."
    )


def _porto_data_path() -> Path | None:
    env = __import__("os").environ.get("PORTO_DATA_PATH")
    if env:
        candidate = Path(env).expanduser().resolve()
        if (candidate / "providers.json").exists() or (candidate / "metadata.json").exists():
            return candidate
    bundled = _REPO_ROOT / "resources" / "porto-data" / "porto_data"
    if bundled.is_dir():
        return bundled
    return None


def _lab_matrix_dir() -> Path:
    return _REPO_ROOT / "matrix"


def _sdk_output_path() -> Path:
    return _lab_matrix_dir() / "sdk.yaml"


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync Lab matrix/sdk.yaml from @sdk scenarios.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero if sdk.yaml is out of date (no write).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output sdk.yaml path (default: matrix/sdk.yaml)",
    )
    args = parser.parse_args()

    features_root = _porto_features_root()
    features_dir = features_root / "features"
    output_path = args.output or _sdk_output_path()
    porto_data_path = _porto_data_path()

    expected = dump_sdk_yaml(scan_sdk_features(features_dir, porto_data_path=porto_data_path))

    if args.check:
        if not output_path.is_file():
            print(f"❌ Missing {output_path} — run: make matrix-sdk-sync")
            return 1
        actual = output_path.read_text(encoding="utf-8")
        if actual != expected:
            print(f"❌ {output_path} is out of date — run: make matrix-sdk-sync")
            return 1
        print(f"✅ sdk.yaml is up to date ({expected.count('cell_id:')} cells)")
        return 0

    count = write_sdk_matrix(features_dir, output_path, porto_data_path=porto_data_path)
    if count == 0:
        print("❌ No @sdk scenarios found")
        return 1
    rel = (
        output_path.relative_to(_REPO_ROOT)
        if output_path.is_relative_to(_REPO_ROOT)
        else output_path
    )
    print(f"✅ Wrote {count} sdk cells to {rel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
