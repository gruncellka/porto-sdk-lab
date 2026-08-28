"""Tests for mark measurement and stamp I/O."""

from __future__ import annotations

import struct
from pathlib import Path

import pytest

from labs.lib.python.mark_measure.compare import dimensions_from_px, dimensions_match, px_to_mm
from labs.lib.python.mark_measure.png import read_png_dimensions
from labs.lib.python.mark_measure.stamp_io import normalize_stamp_bytes, repair_stamp_png_file

RUN_STAMP = (
    Path(__file__).resolve().parents[1]
    / "experiments"
    / "runs"
    / "20260707-073933-full"
    / "cases"
    / "grossbrief_domestic"
    / "stamp.png"
)

PORTO_DATA = Path(__file__).resolve().parents[2] / "resources" / "porto-data" / "porto_data"


def _minimal_png(width: int, height: int) -> bytes:
    signature = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    ihdr_chunk = b"IHDR" + ihdr_data
    ihdr = struct.pack(">I", len(ihdr_data)) + ihdr_chunk + struct.pack(">I", 0)
    return signature + ihdr


def test_read_png_dimensions_from_ihdr() -> None:
    width, height = read_png_dimensions(_minimal_png(1004, 508))
    assert width == 1004
    assert height == 508


def test_px_to_mm_dpi300() -> None:
    assert px_to_mm(300, 300) == 25.4
    dims = dimensions_from_px(1004, 508, dpi=300)
    assert abs(dims.width_mm - 85.0) <= 0.1
    assert abs(dims.height_mm - 43.0) <= 0.1


def test_dimensions_match_exact() -> None:
    measured = dimensions_from_px(437, 236, dpi=300)
    expected = {
        "width_px": 437,
        "height_px": 236,
        "width_mm": 37.0,
        "height_mm": 20.0,
    }
    ok, issues = dimensions_match(measured, expected)
    assert ok
    assert issues == []


@pytest.mark.skipif(not RUN_STAMP.exists(), reason="full matrix run artifacts not present")
def test_normalize_zip_wrapped_stamp_download() -> None:
    data = RUN_STAMP.read_bytes()
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    assert normalize_stamp_bytes(data) == data


def test_normalize_raw_png_roundtrip() -> None:
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
    assert normalize_stamp_bytes(png) == png


@pytest.mark.skipif(not RUN_STAMP.exists(), reason="full matrix run artifacts not present")
def test_repair_idempotent_on_png() -> None:
    before = RUN_STAMP.read_bytes()
    assert repair_stamp_png_file(RUN_STAMP) is True
    assert RUN_STAMP.read_bytes() == before


@pytest.mark.skipif(not RUN_STAMP.exists(), reason="full matrix run artifacts not present")
def test_verify_run_against_porto_data() -> None:
    from labs.lib.python.mark_measure.audit import audit_run_dir

    run_dir = RUN_STAMP.parents[2]
    audit = audit_run_dir(
        run_dir,
        porto_data_root=PORTO_DATA,
        provider="deutschepost",
    )
    assert audit["report"]["cases_total"] > 0
    assert audit["report"]["cases_passed"] == audit["report"]["cases_total"]
