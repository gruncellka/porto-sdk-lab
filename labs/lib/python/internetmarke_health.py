"""Lab-only Internetmarke API root probe (not a PortoClient method)."""

from __future__ import annotations

from typing import Any

import httpx


async def health(base_url: str, *, timeout: float = 30) -> dict[str, Any]:
    url = base_url.rstrip("/") + "/"
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(url)
    if response.status_code >= 400:
        raise RuntimeError(
            f"Internetmarke API unavailable: {response.status_code} GET {url}"
        )
    try:
        payload = response.json()
    except Exception:
        payload = {"text": response.text[:2000]}
    if not isinstance(payload, dict):
        return {"body": payload}
    return payload
