"""FastAPI integration lab for the Python Porto SDK."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from porto_sdk import PortoConfig  # noqa: E402
from porto_sdk.config import ProviderRuntimeConfig  # noqa: E402

from labs.lib.python.porto_client import create_porto_client  # noqa: E402

app = FastAPI(title="Porto SDK Python Lab", version="0.0.1")
PROVIDER_ID = os.environ.get("PORTO_PROVIDER", "deutschepost")
client = create_porto_client(PortoConfig(providers={PROVIDER_ID: ProviderRuntimeConfig()}))


class QuoteRequest(BaseModel):
    country_code: str = Field(min_length=2, max_length=2, default="DE")
    weight: int = Field(ge=1, le=2000, default=20)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "framework": "fastapi", "sdk": "gruncellka-porto-sdk"}


@app.post("/api/quote")
async def quote(request: QuoteRequest) -> dict[str, object]:
    try:
        resolved = client.provider(PROVIDER_ID).resolve(
            country_code=request.country_code.upper(),
            weight=request.weight,
        )
    except Exception as exc:  # pragma: no cover - integration surface
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "framework": "fastapi",
        "product_id": resolved.product.id,
        "zone_id": resolved.zone.id,
        "base_price_cents": resolved.base_price,
        "currency": resolved.currency,
        "is_valid": resolved.is_valid,
    }
