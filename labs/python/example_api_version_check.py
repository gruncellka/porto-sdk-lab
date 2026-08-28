"""
ApiVersionResource check — uses Porto SDK health check. No credentials required.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from labs.lib.python.internetmarke_health import health  # noqa: E402
from labs.lib.python.load_env import load_lab_env  # noqa: E402

load_lab_env()

from porto_sdk.adapters.deutschepost.internetmarke.bootstrap import (  # noqa: E402
    get_internetmarke_base_url,
    load_internetmarke_config,
)


def save_result(payload: dict[str, Any]) -> Path:
    observer_run_dir = os.getenv("OBSERVER_RUN_DIR")
    if observer_run_dir:
        out_dir = Path(observer_run_dir) / "api"
    else:
        out_dir = Path(__file__).parent / "artifacts" / "api"
    out_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    out_path = out_dir / f"api_version_{ts}.json"
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return out_path


async def main() -> int:
    im = load_internetmarke_config("deutschepost")
    base_url = get_internetmarke_base_url(im)
    version_url = f"{base_url.rstrip('/')}/"

    print("ApiVersionResource check (lab health probe)")
    print("=" * 40)
    print(f"Base URL: {base_url}")
    print(f"Endpoint: GET {version_url}")
    print()

    try:
        result = await health(base_url)
        ok = True
    except Exception as exc:  # noqa: BLE001
        ok = False
        result = {"error": str(exc), "type": type(exc).__name__}

    path = save_result(
        {
            "ts": datetime.now(UTC).isoformat(),
            "status": "ok" if ok else "error",
            "response_json": result,
        }
    )

    if ok:
        print("Result: API available")
        for key, value in result.items():
            print(f"  {key}: {value}")
    else:
        print("Result: API check failed")
        print(f"  error: {result.get('error', result)}")

    print(f"\nSaved: {path}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
