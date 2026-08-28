from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from labs.lib.python.http_trace import TracingTransport, persist_hop_file, wrap_transport
from labs.lib.python.redaction import redact_headers, redact_payload, redact_text, redact_url


class _Inner:
    def __init__(self, response: Any) -> None:
        self.response = response
        self.calls = 0

    async def request(self, **kwargs: Any) -> Any:
        self.calls += 1
        return self.response

    async def close(self) -> None:
        return None


def _json_response() -> SimpleNamespace:
    return SimpleNamespace(
        status_code=200,
        headers={"Content-Type": "application/json"},
        content=b'{"ok": true}',
        text='{"ok": true}',
        json=lambda: {"ok": True},
    )


def test_redaction_covers_credential_fields() -> None:
    headers = redact_headers(
        {
            "Authorization": "Bearer secret-token",
            "X-Api-Key": "app-key",
            "Content-Type": "application/json",
        }
    )
    assert headers["Authorization"] == "[REDACTED]"
    assert headers["X-Api-Key"] == "[REDACTED]"
    assert headers["Content-Type"] == "application/json"
    payload = redact_payload(
        {
            "clientSecret": "shh",
            "applicationId": "app-1",
            "account_number": "12345",
            "destination": "DE",
        }
    )
    assert payload["clientSecret"] == "[REDACTED]"
    assert payload["applicationId"] == "[REDACTED]"
    assert payload["account_number"] == "[REDACTED]"
    assert payload["destination"] == "DE"
    assert "hunter2" not in redact_url("https://api.example.test/user?password=hunter2")
    assert "hunter2" not in redact_text("password=hunter2")


@pytest.mark.asyncio
async def test_tracing_transport_redacts_secrets_and_survives_writer_errors() -> None:
    hops: list[dict[str, Any]] = []

    def persist(hop: dict[str, Any]) -> None:
        hops.append(hop)
        raise RuntimeError("disk full")

    inner = _Inner(_json_response())
    transport = TracingTransport(inner, persist=persist)
    result = await transport.request(
        method="POST",
        url="https://api.example.test/user?password=hunter2",
        headers={"Authorization": "Bearer secret-token", "Content-Type": "application/json"},
        json={"username": "lab", "password": "hunter2"},
    )
    assert result.status_code == 200
    assert inner.calls == 1
    assert hops
    blob = json.dumps(hops)
    assert "secret-token" not in blob
    assert "hunter2" not in blob
    assert "[REDACTED]" in blob
    assert "body" not in hops[0]["request"]


@pytest.mark.asyncio
async def test_tracing_transport_redacts_bodies_and_never_persists_secrets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PORTO_LAB_HTTP_TRACE_BODIES", "1")
    monkeypatch.setenv("PORTO_LAB_HTTP_TRACE_DIR", str(tmp_path))
    inner = _Inner(_json_response())
    transport = TracingTransport(inner, persist=persist_hop_file)
    await transport.request(
        method="POST",
        url="https://api.example.test/authenticate?password=hunter2",
        headers={"Authorization": "Bearer secret-token", "X-Api-Key": "app-key"},
        json={
            "username": "lab-user",
            "password": "hunter2",
            "clientSecret": "shh",
            "applicationId": "app-1",
        },
    )
    files = list(tmp_path.glob("*.json"))
    assert files
    blob = files[0].read_text(encoding="utf-8")
    hop = json.loads(blob)
    assert "secret-token" not in blob
    assert "hunter2" not in blob
    assert "app-key" not in blob
    assert hop["request"]["body"]["password"] == "[REDACTED]"
    assert hop["request"]["body"]["clientSecret"] == "[REDACTED]"
    assert hop["request"]["body"]["applicationId"] == "[REDACTED]"
    assert hop["request"]["body"]["username"] == "[REDACTED]"


@pytest.mark.asyncio
async def test_tracing_transport_keeps_inner_errors() -> None:
    class Boom:
        async def request(self, **kwargs: Any) -> Any:
            raise RuntimeError("upstream down")

        async def close(self) -> None:
            return None

    hops: list[dict[str, Any]] = []
    transport = TracingTransport(Boom(), persist=hops.append)
    with pytest.raises(RuntimeError, match="upstream down"):
        await transport.request(method="GET", url="https://api.example.test/status")
    assert hops
    assert hops[0]["error"] == "upstream down"


def test_wrap_transport_is_passthrough_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PORTO_LAB_HTTP_TRACE", raising=False)
    inner = _Inner(_json_response())
    assert wrap_transport(inner) is inner
