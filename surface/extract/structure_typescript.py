"""Run TypeScript structure extract via Node + typescript compiler API."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


def _typescript_module_root(sdk_root: Path) -> Path:
    candidate = sdk_root / "node_modules" / "typescript"
    if candidate.is_dir():
        return candidate
    raise FileNotFoundError(
        f"TypeScript package not found under SDK node_modules. Run `make` in {sdk_root} first."
    )


def extract_typescript_structure(sdk_root: Path, *, src_dir: str = "src") -> dict:
    sdk_root = sdk_root.resolve()
    src_root = sdk_root / src_dir
    if not src_root.is_dir():
        raise FileNotFoundError(f"TypeScript src root not found: {src_root}")

    script = Path(__file__).resolve().parent / "structure-typescript.mjs"
    ts_root = _typescript_module_root(sdk_root)
    result = subprocess.run(
        ["node", str(script), str(src_root), str(ts_root)],
        cwd=str(sdk_root),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "TypeScript structure extract failed:\n"
            + (result.stdout or "")
            + "\n"
            + (result.stderr or "")
        )
    payload = json.loads(result.stdout)
    if not isinstance(payload, dict):
        raise ValueError("TypeScript structure extract must return a JSON object")
    return payload
