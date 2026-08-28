"""Integration tests for matrix CLI scripts."""

import runpy
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
SDK_SYNC = _REPO_ROOT / "scripts" / "matrix-sdk-sync.py"
ORDERS_SYNC = _REPO_ROOT / "scripts" / "matrix-orders-sync.py"


def test_matrix_sdk_sync_check_exits_zero(monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["matrix-sdk-sync.py", "--check"])
    with pytest.raises(SystemExit) as exc_info:
        runpy.run_path(str(SDK_SYNC), run_name="__main__")
    assert exc_info.value.code == 0


def test_matrix_orders_sync_check_exits_zero(monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["matrix-orders-sync.py", "--check"])
    with pytest.raises(SystemExit) as exc_info:
        runpy.run_path(str(ORDERS_SYNC), run_name="__main__")
    assert exc_info.value.code == 0
