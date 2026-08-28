"""Shared redaction helpers for lab artifacts and HTTP traces."""

from __future__ import annotations

import re
from typing import Any

SENSITIVE_KEYS = frozenset(
    {
        "password",
        "passwd",
        "token",
        "authorization",
        "api_key",
        "api_secret",
        "api-key",
        "x-api-key",
        "client_secret",
        "client_id",
        "access_token",
        "refresh_token",
        "cookie",
        "set-cookie",
        "username",
        "partner_id",
        "signature",
        "secret",
        "portokasse",
        "application_id",
        "account_id",
        "account_number",
        "app_secret",
        "private_key",
    }
)

_SENSITIVE_FRAGMENTS = (
    "password",
    "passwd",
    "secret",
    "token",
    "authorization",
    "cookie",
    "apikey",
    "apisecret",
)

SECRET_KV_PATTERN = re.compile(
    r"(?i)\b(password|passwd|secret|token|api[_-]?key|client[_-]?secret)\b\s*([:=])\s*([^\s,;]+)"
)


def _normalized_key(key: str) -> str:
    return re.sub(r"[^a-z0-9]", "", key.lower())


_SENSITIVE_NORMALIZED = frozenset(_normalized_key(key) for key in SENSITIVE_KEYS)


def is_sensitive_key(key: str) -> bool:
    normalized = _normalized_key(key)
    if normalized in _SENSITIVE_NORMALIZED:
        return True
    return any(fragment in normalized for fragment in _SENSITIVE_FRAGMENTS)


def redact_headers(headers: dict[str, str] | None) -> dict[str, str]:
    if not headers:
        return {}
    out: dict[str, str] = {}
    for key, value in headers.items():
        out[key] = "[REDACTED]" if is_sensitive_key(key) else value
    return out


def redact_payload(payload: Any) -> Any:
    if isinstance(payload, dict):
        redacted: dict[str, Any] = {}
        for key, value in payload.items():
            if is_sensitive_key(str(key)):
                redacted[key] = "[REDACTED]"
            else:
                redacted[key] = redact_payload(value)
        return redacted
    if isinstance(payload, list):
        return [redact_payload(item) for item in payload]
    return payload


def redact_text(text: str) -> str:
    return SECRET_KV_PATTERN.sub(
        lambda match: f"{match.group(1)}{match.group(2)}[REDACTED]",
        text,
    )


def redact_url(url: str) -> str:
    from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

    parts = urlsplit(url)
    if not parts.query:
        return url
    redacted = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        if is_sensitive_key(key):
            redacted.append((key, "[REDACTED]"))
        else:
            redacted.append((key, value))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(redacted), parts.fragment))
