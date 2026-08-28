"""Normalize Internetmarke stamp downloads — delegates to Porto SDK."""

from __future__ import annotations

from pathlib import Path

from porto_sdk.adapters.deutschepost.internetmarke.document_payload import (
    normalize_document_payload as normalize_stamp_bytes,
)
from porto_sdk.mark_content import fetch_mark_bytes_sync

__all__ = [
    "download_stamp_png",
    "normalize_stamp_bytes",
    "repair_stamp_png_file",
    "save_stamp_png",
]


def download_stamp_png(url: str, *, timeout: int = 30, retries: int = 3) -> bytes:
    """Download document link and return viewable PNG bytes."""
    from porto_sdk.execution import PortoMark

    mark = PortoMark(
        id="repair:download",
        content=url,
        content_type="image/png",
        value=0,
        provider="deutschepost",
        integration="internetmarke",
        generated_at="1970-01-01T00:00:00",
    )
    return fetch_mark_bytes_sync(mark, timeout=float(timeout), retries=retries)


def save_stamp_png(url: str, path: Path, *, timeout: int = 30, retries: int = 3) -> Path:
    """Download and write a real PNG file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(download_stamp_png(url, timeout=timeout, retries=retries))
    return path


def repair_stamp_png_file(path: Path) -> bool:
    """Rewrite stamp.png on disk when it was saved as a ZIP by mistake."""
    if not path.exists():
        return False
    raw = path.read_bytes()
    try:
        png = normalize_stamp_bytes(raw)
    except ValueError:
        return False
    if png is raw:
        return True
    path.write_bytes(png)
    return True
