"""
Portokasse linkage diagnostic (no stamp order, no charge).

Checks DHL app token + Portokasse user auth via Internetmarke REST v1.
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
)
from labs.lib.python.load_env import load_lab_env  # noqa: E402

load_lab_env()

from porto_sdk.adapters.deutschepost.internetmarke.bootstrap import (  # noqa: E402
    get_internetmarke_base_url,
    load_internetmarke_config,
)


def mask(value: str | None) -> str:
    if not value:
        return "MISSING"
    if len(value) <= 6:
        return "***"
    return f"{value[:3]}...{value[-3:]}"


def save_result(payload: dict[str, Any]) -> Path:
    observer_run_dir = os.getenv("OBSERVER_RUN_DIR")
    if observer_run_dir:
        out_dir = Path(observer_run_dir) / "auth"
    else:
        out_dir = Path(__file__).parent / "artifacts" / "auth"
    out_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    out_path = out_dir / f"portokasse_link_check_{ts}.json"
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return out_path


async def main() -> int:
    im = load_internetmarke_config("deutschepost")
    creds = im.credentials if im else {}
    base_url = get_internetmarke_base_url(im)

    print("Portokasse linkage diagnostic")
    print("=" * 34)
    print(f"DHL API key:    {mask(creds.get('dhl_api_key'))}")
    print(f"DHL API secret: {mask(creds.get('dhl_api_secret'))}")
    print(f"Base URL:       {base_url}")
    print(f"Portokasse user:{mask(creds.get('username'))}")

    auth = await probe_internetmarke_auth(
        base_url=base_url,
        username=creds.get("username"),
        password=creds.get("password"),
        api_key=creds.get("dhl_api_key"),
        api_secret=creds.get("dhl_api_secret"),
    )

    path = save_result(
        {
            "ts": datetime.now(UTC).isoformat(),
            **auth.to_dict(),
            "checks": {
                "app_auth": {
                    "endpoint": f"{base_url.rstrip('/')}/auth/token",
                    "status_code": auth.app_status,
                    "body_preview": auth.app_body_preview,
                },
                "user_auth": {
                    "endpoint": f"{base_url.rstrip('/')}/user/authenticate",
                    "status_code": auth.user_status,
                    "body_preview": auth.user_body_preview,
                },
            },
        }
    )

    print(f"\nstatus: {auth.status}")
    print(f"blocking_stage: {auth.blocking_stage}")
    print(f"hint: {auth.hint}")
    if auth.next_steps:
        print("next_steps:")
        for step in auth.next_steps:
            print(f"  - {step}")
    print(f"saved: {path}")
    return exit_code_for_auth_status(auth.status)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
