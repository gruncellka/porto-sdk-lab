"""Lab-owned HTTP tracing transport. SDK must not import this module."""

from __future__ import annotations

import json
import os
import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

import httpx

from .redaction import redact_headers, redact_payload, redact_text, redact_url


class Transport(Protocol):
    """Structural match for porto_sdk.transport.Transport (Lab does not import SDK)."""

    async def request(
        self,
        *,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        json: Any = None,
        data: Any = None,
        idempotent: bool = True,
        idempotency_key: str | None = None,
    ) -> httpx.Response: ...

    async def close(self) -> None: ...

_counter = 0
_lock = threading.Lock()
_BODY_LIMIT = 4096
_BINARY_PREFIXES = ("image/", "audio/", "video/")
_BINARY_TYPES = {
    "application/pdf",
    "application/zip",
    "application/octet-stream",
    "application/gzip",
}

PersistHop = Callable[[dict[str, Any]], None]


def tracing_enabled() -> bool:
    return os.getenv("PORTO_LAB_HTTP_TRACE", "").strip() == "1"


def bodies_enabled() -> bool:
    return os.getenv("PORTO_LAB_HTTP_TRACE_BODIES", "").strip() == "1"


def _dir() -> Path:
    explicit = os.getenv("PORTO_LAB_HTTP_TRACE_DIR")
    if explicit:
        return Path(explicit)
    observer = os.getenv("OBSERVER_RUN_DIR")
    if observer:
        return Path(observer) / "http"
    return Path("artifacts") / "http"


def _label(url: str) -> str:
    if "/user" in url or "/authenticate" in url or "/auth/" in url:
        return "auth"
    if "/shoppingcart/png" in url or "/shoppingcart/pdf" in url:
        return "checkout"
    if "/shoppingcart" in url:
        return "cart"
    return "http"


def _bounded(value: Any) -> Any:
    if isinstance(value, str) and len(value) > _BODY_LIMIT:
        return value[:_BODY_LIMIT]
    encoded = json.dumps(value, default=str)
    if len(encoded) > _BODY_LIMIT:
        return encoded[:_BODY_LIMIT]
    return value


def _is_binary(content_type: str, payload: bytes | None) -> bool:
    lowered = content_type.split(";")[0].strip().lower()
    if any(lowered.startswith(prefix) for prefix in _BINARY_PREFIXES) or lowered in _BINARY_TYPES:
        return True
    if payload and payload[:8] == b"\x89PNG\r\n\x1a\n":
        return True
    if payload and payload[:4] == b"%PDF":
        return True
    return False


def _preview_request(*, json_body: Any, data: Any, include_bodies: bool) -> Any | None:
    if not include_bodies:
        return None
    raw = json_body if json_body is not None else data
    if raw is None:
        return None
    if isinstance(raw, (bytes, bytearray)):
        return {"kind": "binary", "bytes": len(raw)}
    if isinstance(raw, str):
        return _bounded(redact_text(raw))
    return _bounded(redact_payload(raw))


def _preview_response(response: httpx.Response, include_bodies: bool) -> Any | None:
    if not include_bodies:
        return None
    content_type = response.headers.get("content-type", "")
    payload = bytes(response.content or b"")
    if _is_binary(content_type, payload):
        return {"kind": "binary", "bytes": len(payload)}
    try:
        return _bounded(redact_payload(response.json()))
    except Exception:
        text = response.text or ""
        return _bounded(redact_text(text))


def persist_hop_file(hop: dict[str, Any]) -> None:
    out = _dir()
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{hop['seq']:03d}_{hop['label']}.json"
    path.write_text(json.dumps(hop, indent=2, default=str) + "\n", encoding="utf-8")


class TracingTransport:
    """Delegates to an inner Transport and records redacted hops for Lab."""

    def __init__(self, inner: Transport, persist: PersistHop | None = None) -> None:
        self._inner = inner
        self._persist = persist or persist_hop_file

    async def request(
        self,
        *,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        json: Any = None,
        data: Any = None,
        idempotent: bool = True,
        idempotency_key: str | None = None,
    ) -> httpx.Response:
        started = time.perf_counter()
        try:
            response = await self._inner.request(
                method=method,
                url=url,
                headers=headers,
                json=json,
                data=data,
                idempotent=idempotent,
                idempotency_key=idempotency_key,
            )
        except Exception as exc:
            self._safe_persist(
                method=method,
                url=url,
                headers=headers,
                json_body=json,
                data=data,
                status=None,
                response=None,
                error=str(exc),
                duration_ms=int((time.perf_counter() - started) * 1000),
            )
            raise
        self._safe_persist(
            method=method,
            url=url,
            headers=headers,
            json_body=json,
            data=data,
            status=response.status_code,
            response=response,
            error=None,
            duration_ms=int((time.perf_counter() - started) * 1000),
        )
        return response

    async def close(self) -> None:
        await self._inner.close()

    def _safe_persist(
        self,
        *,
        method: str,
        url: str,
        headers: dict[str, str] | None,
        json_body: Any,
        data: Any,
        status: int | None,
        response: httpx.Response | None,
        error: str | None,
        duration_ms: int,
    ) -> None:
        try:
            global _counter
            with _lock:
                _counter += 1
                seq = _counter
            include_bodies = bodies_enabled()
            hop: dict[str, Any] = {
                "seq": seq,
                "label": _label(url),
                "timestamp": datetime.now(UTC).isoformat(),
                "duration_ms": duration_ms,
                "request": {
                    "method": method,
                    "url": redact_url(url),
                    "headers": redact_headers(headers),
                },
                "response": {
                    "status_code": status,
                    "headers": redact_headers(
                        dict(response.headers) if response is not None else None
                    ),
                },
            }
            request_body = _preview_request(
                json_body=json_body, data=data, include_bodies=include_bodies
            )
            if request_body is not None:
                hop["request"]["body"] = request_body
            if response is not None:
                response_body = _preview_response(response, include_bodies)
                if response_body is not None:
                    hop["response"]["body"] = response_body
            if error is not None:
                hop["error"] = error
            self._persist(hop)
        except Exception:
            return


def wrap_transport(inner: Transport) -> Transport:
    if tracing_enabled():
        return TracingTransport(inner)
    return inner
