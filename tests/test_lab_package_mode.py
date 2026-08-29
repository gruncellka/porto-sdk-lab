"""Tests for Lab package mode scripts (make lab / make registry)."""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from pathlib import Path

LAB_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_LAB = LAB_ROOT / "scripts" / "lab"
MAKEFILE = LAB_ROOT / "Makefile"


def _run(
    cmd: list[str], *, env: dict[str, str] | None = None, cwd: Path | None = None
) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    return subprocess.run(
        cmd,
        cwd=cwd or LAB_ROOT,
        env=merged,
        capture_output=True,
        text=True,
        check=False,
    )


def test_makefile_has_lab_and_registry_targets() -> None:
    text = MAKEFILE.read_text(encoding="utf-8")
    assert re.search(r"(?m)^lab:", text), "expected make lab target"
    assert re.search(r"(?m)^registry:", text), "expected make registry target"
    assert "lab-resources" not in text
    assert "registry-resources" not in text
    assert "scripts/lab/" in text
    assert "scripts/lab-resources/" not in text


def test_scripts_lab_layout() -> None:
    for name in (
        "overlay-python.sh",
        "restore-python.sh",
        "link-typescript.mjs",
        "unlink-typescript.mjs",
    ):
        path = SCRIPTS_LAB / name
        assert path.is_file(), f"missing {path}"


def test_overlay_python_requires_sdk_root() -> None:
    script = SCRIPTS_LAB / "overlay-python.sh"
    result = _run(["sh", str(script)])
    assert result.returncode != 0
    assert "usage:" in (result.stderr + result.stdout).lower()


def test_restore_python_requires_sdk_root() -> None:
    script = SCRIPTS_LAB / "restore-python.sh"
    result = _run(["sh", str(script)])
    assert result.returncode != 0
    assert "usage:" in (result.stderr + result.stdout).lower()


def test_link_typescript_requires_sdk_root() -> None:
    script = SCRIPTS_LAB / "link-typescript.mjs"
    result = _run(["node", str(script)])
    assert result.returncode != 0
    assert "usage:" in (result.stderr + result.stdout).lower()


def test_unlink_typescript_requires_sdk_root() -> None:
    script = SCRIPTS_LAB / "unlink-typescript.mjs"
    result = _run(["node", str(script)])
    assert result.returncode != 0
    assert "usage:" in (result.stderr + result.stdout).lower()


def test_link_and_unlink_typescript_marker_roundtrip() -> None:
    data = LAB_ROOT / "resources" / "porto-data"
    features = LAB_ROOT / "resources" / "porto-features"
    if not data.is_dir() or not features.is_dir():
        return  # incomplete checkout; skip behavioral check

    with tempfile.TemporaryDirectory() as tmp:
        sdk_root = Path(tmp)
        (sdk_root / "node_modules").mkdir()

        link = _run(["node", str(SCRIPTS_LAB / "link-typescript.mjs"), str(sdk_root)])
        assert link.returncode == 0, link.stderr + link.stdout

        marker = sdk_root / "node_modules" / ".porto-lab"
        assert marker.is_file()
        assert marker.read_text(encoding="utf-8").strip() == "1"

        data_link = sdk_root / "node_modules" / "@gruncellka" / "porto-data"
        features_link = sdk_root / "node_modules" / "@gruncellka" / "porto-features"
        assert data_link.is_symlink()
        assert features_link.is_symlink()
        assert data_link.resolve() == data.resolve()
        assert features_link.resolve() == features.resolve()

        unlink = _run(
            ["node", str(SCRIPTS_LAB / "unlink-typescript.mjs"), str(sdk_root)],
            env={"PORTO_LAB_SKIP_INSTALL": "1"},
        )
        assert unlink.returncode == 0, unlink.stderr + unlink.stdout
        assert not marker.exists()
        assert not data_link.exists()
        assert not features_link.exists()


def test_overlay_python_fails_for_missing_sdk_root() -> None:
    script = SCRIPTS_LAB / "overlay-python.sh"
    result = _run(["sh", str(script), "/tmp/porto-sdk-lab-missing-sdk-root"])
    assert result.returncode != 0


def test_link_typescript_fails_when_resources_missing(tmp_path: Path) -> None:
    """Fail closed if Lab resources/ trees are absent (script resolves labRoot from its path)."""
    fake_lab = tmp_path / "lab"
    scripts_lab = fake_lab / "scripts" / "lab"
    scripts_lab.mkdir(parents=True)
    stub = scripts_lab / "link-typescript.mjs"
    stub.write_text(
        (SCRIPTS_LAB / "link-typescript.mjs").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    sdk_root = tmp_path / "sdk"
    (sdk_root / "node_modules").mkdir(parents=True)
    result = _run(["node", str(stub), str(sdk_root)])
    assert result.returncode != 0
    assert "missing" in (result.stderr + result.stdout).lower()


def test_docs_use_make_lab_not_legacy_names() -> None:
    resources_doc = LAB_ROOT / "docs" / "labs" / "resources.md"
    text = resources_doc.read_text(encoding="utf-8")
    assert "make lab" in text
    assert "make registry" in text
    assert "lab-resources" not in text
    assert "registry-resources" not in text
