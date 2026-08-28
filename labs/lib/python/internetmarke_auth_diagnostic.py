"""Shared Internetmarke auth classification for lab preflight scripts.

Lab consumes Internetmarke adapter mapper output only. It must not re-parse
provider body text to invent PORTO_* codes. Direction is always:

  adapter mapper → PORTO_* (+ diagnostic_reason + provider_error) → Lab
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

try:
    import httpx
except ModuleNotFoundError:  # pragma: no cover - optional at import time
    httpx = None

from porto_sdk.adapters.deutschepost.internetmarke.auth_errors import (  # noqa: E402
    DIAG_INVALID_PORTOKASSE_CREDENTIALS,
    DIAG_PENDING_PORTOKASSE_APPROVAL,
    DIAG_UNKNOWN_CHANNEL,
    InternetmarkeAuthEndpoint,
    map_internetmarke_auth_http_error,
)
from porto_sdk.adapters.deutschepost.internetmarke.utils import parse_wallet_balance_cents  # noqa: E402
from porto_sdk.errors import PortoErrorCode  # noqa: E402


@dataclass(frozen=True)
class AuthDiagnostic:
    status: str
    hint: str
    blocking_stage: str
    next_steps: tuple[str, ...]
    app_status: int | None
    user_status: int | None
    app_body_preview: str
    user_body_preview: str
    sdk_error_code: str | None = None
    diagnostic_reason: str | None = None
    provider_error: dict[str, Any] | None = None
    wallet_balance_cents: int | None = None
    estimated_spend_cents: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "hint": self.hint,
            "blocking_stage": self.blocking_stage,
            "next_steps": list(self.next_steps),
            "app_status": self.app_status,
            "user_status": self.user_status,
            "app_body_preview": self.app_body_preview,
            "user_body_preview": self.user_body_preview,
            "sdk_error_code": self.sdk_error_code,
            "diagnostic_reason": self.diagnostic_reason,
            "provider_error": self.provider_error,
            "wallet_balance_cents": self.wallet_balance_cents,
            "estimated_spend_cents": self.estimated_spend_cents,
        }


def _provider_error(info: Any) -> dict[str, Any]:
    details = info.details() if callable(getattr(info, "details", None)) else {}
    bag = details.get("provider_error") if isinstance(details, dict) else None
    return dict(bag) if isinstance(bag, dict) else {}


def _next_steps_for(bag: dict[str, Any]) -> tuple[str, ...]:
    stage = bag.get("stage")
    reason = bag.get("reason")
    if stage == "dhl_developer_app":
        steps = [
            "Open DHL Developer Portal → your app → confirm approval for "
            "Post & Parcel Germany / Internetmarke.",
            "Verify PORTO_DEUTSCHEPOST_INTERNETMARKE_API_KEY and _API_SECRET.",
        ]
        if reason == DIAG_UNKNOWN_CHANNEL:
            steps.insert(
                0,
                "Replace stale/Wing-mapped developer-app credentials — DHL reported "
                "unknown channel for this app.",
            )
        steps.append("Re-run gate check (no purchase required).")
        return tuple(steps)
    if stage == "portokasse_linkage":
        return (
            "Log in to Portokasse → Meine Daten → Geschäftsanwendungen.",
            "Approve the business application (Freigabe).",
            "Re-run gate check (no purchase required).",
        )
    if stage == "portokasse_credentials":
        return (
            "Verify PORTO_DEUTSCHEPOST_INTERNETMARKE_USERNAME and _PASSWORD.",
            "Re-run gate check.",
        )
    return ("Inspect saved JSON provider_error / body_preview.",)


def _diagnostic_from_error(
    *,
    info: Any,
    app_status: int | None,
    user_status: int | None,
    app_body: str,
    user_body: str,
) -> AuthDiagnostic:
    bag = _provider_error(info)
    reason = str(bag.get("reason") or "unknown")
    return AuthDiagnostic(
        status=reason,
        hint=str(bag.get("hint") or ""),
        blocking_stage=str(bag.get("stage") or "unknown"),
        next_steps=_next_steps_for(bag),
        app_status=app_status,
        user_status=user_status,
        app_body_preview=app_body[:2000],
        user_body_preview=user_body[:4000],
        sdk_error_code=getattr(getattr(info, "code", None), "value", None) or str(getattr(info, "code", "") or None),
        diagnostic_reason=reason,
        provider_error=bag,
    )


def classify_internetmarke_auth(
    *,
    app_status: int | None,
    user_status: int | None,
    app_body: str = "",
    user_body: str = "",
) -> AuthDiagnostic:
    """Map DHL app + Portokasse auth HTTP results via the adapter mapper only."""
    if user_status == 200:
        return AuthDiagnostic(
            status="connected",
            hint="App + Portokasse auth succeeded. Safe to run canary/full matrix.",
            blocking_stage="none",
            next_steps=(),
            app_status=app_status,
            user_status=user_status,
            app_body_preview=app_body[:2000],
            user_body_preview=user_body[:4000],
            sdk_error_code=None,
            diagnostic_reason=None,
            provider_error=None,
        )

    if app_status != 200:
        info = map_internetmarke_auth_http_error(
            app_status or 0,
            app_body,
            endpoint=InternetmarkeAuthEndpoint.DHL_APP_TOKEN,
        )
        return _diagnostic_from_error(
            info=info,
            app_status=app_status,
            user_status=user_status,
            app_body=app_body,
            user_body=user_body,
        )

    info = map_internetmarke_auth_http_error(
        user_status or 0,
        user_body,
        endpoint=InternetmarkeAuthEndpoint.PORTOKASSE_USER,
        app_token_obtained=True,
    )
    return _diagnostic_from_error(
        info=info,
        app_status=app_status,
        user_status=user_status,
        app_body=app_body,
        user_body=user_body,
    )


@dataclass(frozen=True)
class GateResult:
    name: str
    state: str
    detail: str


@dataclass(frozen=True)
class GateSummary:
    gate_dhl_app: GateResult
    gate_portokasse_user: GateResult
    overall: str
    auth: AuthDiagnostic


def summarize_internetmarke_gates(auth: AuthDiagnostic) -> GateSummary:
    """Two-step approval model: DHL developer app, then Portokasse user link."""
    if auth.status in {"missing_credentials", "missing_dependency"}:
        return GateSummary(
            gate_dhl_app=GateResult("DHL developer app", "skip", auth.hint),
            gate_portokasse_user=GateResult("Portokasse user approval", "skip", auth.hint),
            overall="blocked_configuration",
            auth=auth,
        )

    gate1_ok = auth.app_status == 200
    gate1 = GateResult(
        name="DHL developer app",
        state="ok" if gate1_ok else "fail",
        detail=(
            "App token OK"
            if gate1_ok
            else (
                f"HTTP {auth.app_status} — "
                f"{auth.sdk_error_code or auth.status}"
                + (
                    f" ({auth.diagnostic_reason})"
                    if auth.diagnostic_reason and auth.diagnostic_reason != auth.status
                    else ""
                )
            )
        ),
    )

    if not gate1_ok:
        return GateSummary(
            gate_dhl_app=gate1,
            gate_portokasse_user=GateResult(
                "Portokasse user approval",
                "skip",
                "Waiting for DHL developer app token first",
            ),
            overall="blocked_dhl_developer_app",
            auth=auth,
        )

    gate2_ok = auth.user_status == 200
    if gate2_ok:
        gate2 = GateResult("Portokasse user approval", "ok", "User authorized this app")
        overall = "ready"
    elif auth.status == DIAG_PENDING_PORTOKASSE_APPROVAL:
        gate2 = GateResult(
            "Portokasse user approval",
            "fail",
            (
                f"HTTP {auth.user_status} — {auth.sdk_error_code or auth.status} "
                "(DHL documents 401 until Geschäftsanwendungen Freigabe)"
            ),
        )
        overall = "blocked_portokasse_approval"
    elif auth.status == DIAG_INVALID_PORTOKASSE_CREDENTIALS:
        gate2 = GateResult(
            "Portokasse user approval",
            "fail",
            f"HTTP {auth.user_status} — invalid Portokasse username/password",
        )
        overall = "blocked_portokasse_credentials"
    else:
        gate2 = GateResult(
            "Portokasse user approval",
            "fail",
            f"HTTP {auth.user_status} — {auth.sdk_error_code or auth.status}",
        )
        overall = "blocked_unknown"

    return GateSummary(
        gate_dhl_app=gate1,
        gate_portokasse_user=gate2,
        overall=overall,
        auth=auth,
    )


def format_gate_report(summary: GateSummary) -> str:
    lines = [
        "Internetmarke approval gates",
        "=" * 28,
        f"Gate 1 — {summary.gate_dhl_app.name}: {summary.gate_dhl_app.state.upper()}",
        f"         {summary.gate_dhl_app.detail}",
        f"Gate 2 — {summary.gate_portokasse_user.name}: {summary.gate_portokasse_user.state.upper()}",
        f"         {summary.gate_portokasse_user.detail}",
        "",
    ]

    if summary.overall == "ready":
        lines.append("Overall: READY — safe to run canary/full matrix")
    elif summary.overall == "blocked_dhl_developer_app":
        lines.append("Overall: NOT READY — waiting on DHL developer portal app approval")
    elif summary.overall == "blocked_portokasse_approval":
        lines.append(
            "Overall: NOT READY — Portokasse user has not authorized this app "
            "(Geschäftsanwendungen / Freigabe)"
        )
    elif summary.overall == "blocked_portokasse_credentials":
        lines.append("Overall: NOT READY — fix Portokasse username/password in .env")
    elif summary.overall == "blocked_configuration":
        lines.append("Overall: NOT READY — fix .env configuration")
    else:
        lines.append(f"Overall: NOT READY — {summary.auth.hint}")

    if summary.auth.next_steps:
        lines.append("")
        lines.append("Next steps:")
        for step in summary.auth.next_steps:
            lines.append(f"  - {step}")

    if summary.auth.provider_error:
        pe = summary.auth.provider_error
        lines.append("")
        lines.append(
            "Provider error (under PORTO_* details): "
            f"{pe.get('provider_code') or pe.get('http_status')} — "
            f"{pe.get('provider_detail') or pe.get('body_preview', '')[:120]}"
        )

    return "\n".join(lines)


def exit_code_for_auth_status(status: str) -> int:
    if status == "connected":
        return 0
    if status in {
        DIAG_UNKNOWN_CHANNEL,
        DIAG_PENDING_PORTOKASSE_APPROVAL,
    }:
        return 1
    return 2


async def probe_internetmarke_auth(
    *,
    base_url: str,
    username: str | None,
    password: str | None,
    api_key: str | None,
    api_secret: str | None,
    timeout: float = 30,
) -> AuthDiagnostic:
    missing = [
        name
        for name, val in [
            ("PORTO_DEUTSCHEPOST_INTERNETMARKE_API_KEY", api_key),
            ("PORTO_DEUTSCHEPOST_INTERNETMARKE_API_SECRET", api_secret),
            ("PORTO_DEUTSCHEPOST_INTERNETMARKE_USERNAME", username),
            ("PORTO_DEUTSCHEPOST_INTERNETMARKE_PASSWORD", password),
        ]
        if not val
    ]
    if missing:
        return AuthDiagnostic(
            status="missing_credentials",
            hint=f"Missing env vars: {', '.join(missing)}",
            blocking_stage="configuration",
            next_steps=("Copy .env.example → .env at repo root and fill Internetmarke values.",),
            app_status=None,
            user_status=None,
            app_body_preview="",
            user_body_preview="",
        )

    if httpx is None:
        return AuthDiagnostic(
            status="missing_dependency",
            hint="Missing dependency: httpx",
            blocking_stage="configuration",
            next_steps=("Run labs setup to install Python lab dependencies.",),
            app_status=None,
            user_status=None,
            app_body_preview="",
            user_body_preview="",
        )

    root = base_url.rstrip("/")

    async with httpx.AsyncClient(timeout=timeout) as client:
        # Production/SDK path: POST /user (what stamp purchase actually uses).
        combined_resp = await client.post(
            f"{root}/user",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "client_credentials",
                "client_id": api_key,
                "client_secret": api_secret,
                "username": username,
                "password": password,
            },
        )
        combined_body = combined_resp.text[:4000]
        if combined_resp.status_code == 200:
            wallet_balance_cents: int | None = None
            try:
                wallet_balance_cents = parse_wallet_balance_cents(combined_resp.json())
            except Exception:  # noqa: BLE001
                wallet_balance_cents = None
            return AuthDiagnostic(
                status="connected",
                hint="App + Portokasse auth succeeded. Safe to run canary/full matrix.",
                blocking_stage="none",
                next_steps=(),
                app_status=200,
                user_status=200,
                app_body_preview="",
                user_body_preview=combined_body[:2000],
                sdk_error_code=None,
                wallet_balance_cents=wallet_balance_cents,
            )

        # Keep the first COMBINED_USER mapping — do not reclassify as DHL_APP_TOKEN
        # (that previously downgraded PORTO_AUTH_DENIED → PORTO_AUTH_FAILED).
        info = map_internetmarke_auth_http_error(
            combined_resp.status_code,
            combined_body,
            endpoint=InternetmarkeAuthEndpoint.COMBINED_USER,
        )
        if _provider_error(info).get("stage") in {"portokasse_linkage", "portokasse_credentials"}:
            app_status = 200
            user_status = combined_resp.status_code
            user_body = combined_body
            app_body = ""
        else:
            app_status = combined_resp.status_code
            user_status = None
            app_body = combined_body
            user_body = ""

        return _diagnostic_from_error(
            info=info,
            app_status=app_status,
            user_status=user_status,
            app_body=app_body,
            user_body=user_body,
        )


# Re-export for callers that type-check against PortoErrorCode.
__all__ = [
    "AuthDiagnostic",
    "GateResult",
    "GateSummary",
    "PortoErrorCode",
    "classify_internetmarke_auth",
    "exit_code_for_auth_status",
    "format_gate_report",
    "probe_internetmarke_auth",
    "summarize_internetmarke_gates",
]
