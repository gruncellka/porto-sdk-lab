"""Shared tracking-time cases stay byte-equivalent across SDK suites."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON_CASES = ROOT / "sdks/porto-sdk-python/tests/tracking/time-cases.json"
TYPESCRIPT_CASES = ROOT / "sdks/porto-sdk-typescript/tests/tracking/time-cases.json"


def test_tracking_time_cases_match_across_sdks() -> None:
    assert PYTHON_CASES.read_bytes() == TYPESCRIPT_CASES.read_bytes()
