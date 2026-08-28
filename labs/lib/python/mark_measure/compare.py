"""Compare measured stamp dimensions against expected calibration values."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Dimensions:
    width_px: int
    height_px: int
    width_mm: float
    height_mm: float


def px_to_mm(px: int, dpi: int) -> float:
    return round(px * 25.4 / dpi, 2)


def dimensions_from_px(width_px: int, height_px: int, *, dpi: int) -> Dimensions:
    return Dimensions(
        width_px=width_px,
        height_px=height_px,
        width_mm=px_to_mm(width_px, dpi),
        height_mm=px_to_mm(height_px, dpi),
    )


def dimensions_match(
    measured: Dimensions,
    expected: dict[str, Any],
    *,
    mm_tolerance: float = 0.1,
) -> tuple[bool, list[str]]:
    """Return (ok, mismatch messages)."""
    issues: list[str] = []
    exp_w_px = int(expected["width_px"])
    exp_h_px = int(expected["height_px"])
    exp_w_mm = float(expected["width_mm"])
    exp_h_mm = float(expected["height_mm"])

    if measured.width_px != exp_w_px:
        issues.append(f"width_px: expected {exp_w_px}, got {measured.width_px}")
    if measured.height_px != exp_h_px:
        issues.append(f"height_px: expected {exp_h_px}, got {measured.height_px}")
    if abs(measured.width_mm - exp_w_mm) > mm_tolerance:
        issues.append(f"width_mm: expected {exp_w_mm}, got {measured.width_mm}")
    if abs(measured.height_mm - exp_h_mm) > mm_tolerance:
        issues.append(f"height_mm: expected {exp_h_mm}, got {measured.height_mm}")
    return not issues, issues
