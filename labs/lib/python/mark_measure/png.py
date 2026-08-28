"""PNG dimension helpers (stdlib only)."""

from __future__ import annotations

import struct
from pathlib import Path


def read_png_dimensions(data: bytes) -> tuple[int, int]:
    """Return (width_px, height_px) from PNG IHDR chunk."""
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("Not a PNG file")
    if len(data) < 24:
        raise ValueError("PNG too short for IHDR")
    chunk_length = struct.unpack(">I", data[8:12])[0]
    chunk_type = data[12:16]
    if chunk_type != b"IHDR" or chunk_length < 8:
        raise ValueError("PNG missing IHDR chunk")
    width, height = struct.unpack(">II", data[16:24])
    if width < 1 or height < 1:
        raise ValueError(f"Invalid PNG dimensions: {width}x{height}")
    return width, height


def read_png_dimensions_from_path(path: Path) -> tuple[int, int]:
    return read_png_dimensions(path.read_bytes())
