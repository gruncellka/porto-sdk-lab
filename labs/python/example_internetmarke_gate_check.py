"""
Internetmarke gate check — two approval steps, no purchase.

Run right after DHL approves your developer app (and again before canary).
Detects Portokasse user not having authorized the app (Geschäftsanwendungen).
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
    format_gate_report,
    probe_internetmarke_auth,
    summarize_internetmarke_gates,
)
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
        out_dir = Path(__file__).parent / "artifacts" / "gate_check"
    out_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    out_path = out_dir / f"internetmarke_gate_check_{ts}.json"
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return out_path


async def main() -> int:
    im = load_internetmarke_config("deutschepost")
    creds = im.credentials if im else {}
    base_url = get_internetmarke_base_url(im)

    auth = await probe_internetmarke_auth(
        base_url=base_url,
        username=creds.get("username"),
        password=creds.get("password"),
        api_key=creds.get("dhl_api_key"),
        api_secret=creds.get("dhl_api_secret"),
    )
    summary = summarize_internetmarke_gates(auth)
    report = format_gate_report(summary)

    path = save_result(
        {
            "ts": datetime.now(UTC).isoformat(),
            "overall": summary.overall,
            "gate_dhl_app": {
                "state": summary.gate_dhl_app.state,
                "detail": summary.gate_dhl_app.detail,
            },
            "gate_portokasse_user": {
                "state": summary.gate_portokasse_user.state,
                "detail": summary.gate_portokasse_user.detail,
            },
            "auth": auth.to_dict(),
        }
    )

    print(report)
    print(f"\nsaved: {path}")
    return exit_code_for_auth_status(auth.status)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
