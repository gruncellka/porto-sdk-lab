"""
Internetmarke preflight — API reachability + auth classification (no purchase).

Run while waiting for DHL developer app approval to see a clear blocked state.
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

from labs.lib.python.internetmarke_auth_diagnostic import (  # noqa: E402
    exit_code_for_auth_status,
    probe_internetmarke_auth,
    summarize_internetmarke_gates,
)
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
        out_dir = Path(observer_run_dir)
    else:
        out_dir = Path(__file__).parent / "artifacts" / "preflight"
    out_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    out_path = out_dir / f"internetmarke_preflight_{ts}.json"
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return out_path


def readiness_from(*, api_ok: bool, auth) -> str:
    if not api_ok:
        return "blocked_api_unreachable"
    return summarize_internetmarke_gates(auth).overall


async def main() -> int:
    im = load_internetmarke_config("deutschepost")
    creds = im.credentials if im else {}
    base_url = get_internetmarke_base_url(im)

    print("Internetmarke preflight (no purchase)")
    print("=" * 38)
    print(f"Base URL: {base_url}")
    print()

    try:
        api_result = await health(base_url)
        api_ok = True
    except Exception as exc:  # noqa: BLE001
        api_ok = False
        api_result = {"error": str(exc), "type": type(exc).__name__}

    auth = await probe_internetmarke_auth(
        base_url=base_url,
        username=creds.get("username"),
        password=creds.get("password"),
        api_key=creds.get("dhl_api_key"),
        api_secret=creds.get("dhl_api_secret"),
    )

    readiness = readiness_from(api_ok=api_ok, auth=auth)
    payload = {
        "ts": datetime.now(UTC).isoformat(),
        "readiness": readiness,
        "api_version": {
            "status": "ok" if api_ok else "error",
            "response_json": api_result,
        },
        "auth": auth.to_dict(),
    }
    path = save_result(payload)

    print("1) API version")
    if api_ok:
        amp = api_result.get("amp", api_result)
        print(f"   OK — Internetmarke API reachable ({amp})")
    else:
        print(f"   FAIL — {api_result.get('error', api_result)}")

    print("2) Auth probe")
    print(f"   status: {auth.status}")
    print(f"   blocking_stage: {auth.blocking_stage}")
    print(f"   hint: {auth.hint}")
    if auth.next_steps:
        print("   next_steps:")
        for step in auth.next_steps:
            print(f"     - {step}")

    print()
    print(f"readiness: {readiness}")
    print(f"saved: {path}")

    if not api_ok:
        return 2
    return exit_code_for_auth_status(auth.status)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
