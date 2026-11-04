"""Naming checker: four or more words fail; one repeated directory word fails; three words warn."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import scripts.naming as naming


def test_short_names_pass(tmp_path: Path) -> None:
    (tmp_path / "status_map.py").write_text(
        "MAP = {}\n\nclass Adapter:\n    pass\n", encoding="utf-8"
    )
    assert naming.failures(naming.scan(tmp_path, "py"), set()) == []


def test_four_word_definition_fails_until_baselined(tmp_path: Path) -> None:
    (tmp_path / "loader.py").write_text(
        "def get_price_by_product_zone_weight_tier():\n    return None\n",
        encoding="utf-8",
    )
    hits = naming.scan(tmp_path, "py")
    assert naming.failures(hits, set())
    assert naming.failures(hits, {"symbol get_price_by_product_zone_weight_tier"}) == []


def test_three_word_name_is_a_warning(tmp_path: Path) -> None:
    (tmp_path / "acl.py").write_text(
        "def map_native_status(code):\n    return code\n", encoding="utf-8"
    )
    hits = naming.scan(tmp_path, "py")
    assert naming.warnings(hits) == 1
    assert naming.failures(hits, set()) == []


def test_filename_that_repeats_its_directory_fails(tmp_path: Path) -> None:
    nested = tmp_path / "adapters" / "deutschepost" / "tracking"
    nested.mkdir(parents=True)
    (nested / "deutschepost-status.ts").write_text("export const status = 1\n", encoding="utf-8")
    (nested / "status-map.ts").write_text("export const MAP = {}\n", encoding="utf-8")
    hits = naming.scan(tmp_path, "ts")
    bad = naming.failures(hits, set())
    assert len(bad) == 1
    assert "deutschepost-status.ts" in bad[0].key
    assert "status-map.ts" not in bad[0].key


def test_naming_ok_comment_exempts_a_long_definition(tmp_path: Path) -> None:
    (tmp_path / "mod.py").write_text(
        "def get_price_by_product_zone_weight_tier():  # naming: ok\n    return None\n",
        encoding="utf-8",
    )
    assert naming.failures(naming.scan(tmp_path, "py"), set()) == []


def test_sdk_sources_match_the_baseline() -> None:
    assert naming.check() == []


def test_edges(tmp_path: Path, monkeypatch) -> None:
    assert naming.words("") == []
    assert naming.words("getHTTPResponse") == ["get", "HTTP", "Response"]
    assert naming.scan(tmp_path / "missing", "py") == []
    cache = tmp_path / "__pycache__"
    cache.mkdir()
    (cache / "mod.py").write_text(
        "def get_price_by_product_zone_weight_tier():\n    pass\n", encoding="utf-8"
    )
    (tmp_path / "test_skip.py").write_text(
        "def get_price_by_product_zone_weight_tier():\n    pass\n",
        encoding="utf-8",
    )
    (tmp_path / "skip.d.ts").write_text(
        "export function getPriceByProductZoneWeightTier() {}\n",
        encoding="utf-8",
    )
    (tmp_path / "skip.test.ts").write_text(
        "export function getPriceByProductZoneWeightTier() {}\n",
        encoding="utf-8",
    )
    assert naming.scan(tmp_path, "py") == []
    assert naming.load_baseline(tmp_path / "nope") == set()
    baseline = tmp_path / "baseline.txt"
    baseline.write_text("# note\n\nignore\nsymbol kept\npath py a.py\n", encoding="utf-8")
    assert naming.load_baseline(baseline) == {"symbol kept", "path py a.py"}

    root = tmp_path / "src"
    root.mkdir()
    (root / "mod.py").write_text(
        "def get_price_by_product_zone_weight_tier():\n    return None\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(naming, "ROOTS", (("py", root),))
    assert naming.main(["--write-baseline", "--baseline", str(baseline)]) == 0
    assert "symbol get_price_by_product_zone_weight_tier" in baseline.read_text(encoding="utf-8")
    baseline.write_text("# cleared\n", encoding="utf-8")
    assert naming.main(["--baseline", str(baseline)]) == 1
    monkeypatch.setattr(naming, "ROOTS", (("py", tmp_path / "absent"),))
    assert naming.main([]) == 1


def test_cli_reports_ok() -> None:
    result = subprocess.run(
        [sys.executable, str(naming.LAB / "scripts" / "naming.py")],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "naming: ok" in result.stdout
