"""Tests for scripts/check-paid-ci-safety.sh."""

import subprocess
from pathlib import Path


def test_check_paid_ci_safety_passes() -> None:
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "check-paid-ci-safety.sh"
    result = subprocess.run(
        ["sh", str(script)], cwd=root, check=False, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stdout + result.stderr
