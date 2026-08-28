"""Tests for labs.lib.python.matrix sdk_sync."""

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from labs.lib.python.matrix.sdk_sync import (  # noqa: E402
    dump_sdk_yaml,
    scan_sdk_features,
    write_sdk_matrix,
)


def test_scan_sdk_features_writes_swisspost_cell(tmp_path: Path) -> None:
    features_dir = tmp_path / "features"
    sdk_dir = features_dir / "sdk" / "providers" / "swisspost"
    sdk_dir.mkdir(parents=True)
    (sdk_dir / "resolution.feature").write_text(
        """
@sdk
@provider:swisspost
Feature: Swiss Post resolution
  Scenario: Resolve domestic A-Post standard letter
    Given I want to send a letter to country "CH"
    And the letter weight is 20 grams
    When I resolve the shipping configuration
    Then I should get product with id "a_post_standardbrief"
    And I should get zone with id "domestic"
""".strip(),
        encoding="utf-8",
    )

    cells = scan_sdk_features(features_dir, porto_data_path=None)
    assert len(cells) == 1
    assert cells[0]["provider"] == "swisspost"
    assert "swisspost.resolution" in cells[0]["cell_id"]


def test_write_sdk_matrix_roundtrip(tmp_path: Path) -> None:
    features_dir = tmp_path / "features"
    sdk_dir = features_dir / "sdk" / "providers" / "swisspost"
    sdk_dir.mkdir(parents=True)
    (sdk_dir / "resolution.feature").write_text(
        """
@sdk
@provider:swisspost
Feature: Swiss Post resolution
  Scenario: Resolve domestic A-Post standard letter
    Given I want to send a letter to country "CH"
    When I resolve the shipping configuration
    Then I should get product with id "a_post_standardbrief"
""".strip(),
        encoding="utf-8",
    )
    output_path = tmp_path / "matrix" / "sdk.yaml"
    count = write_sdk_matrix(features_dir, output_path, porto_data_path=None)
    assert count == 1
    content = output_path.read_text(encoding="utf-8")
    assert "matrix-sdk-sync.py" in content
    assert dump_sdk_yaml(scan_sdk_features(features_dir)) == content


def test_sdk_sync_uses_porto_data_for_zone(tmp_path: Path) -> None:
    data_path = _REPO_ROOT / "resources" / "porto-data" / "porto_data"
    if not data_path.is_dir():
        pytest.skip("porto-data submodule not present")

    features_dir = tmp_path / "features"
    sdk_dir = features_dir / "sdk" / "providers" / "deutschepost"
    sdk_dir.mkdir(parents=True)
    (sdk_dir / "resolution.feature").write_text(
        """
@sdk
@provider:deutschepost
Feature: Deutsche Post resolution
  Scenario: Resolve zone 2 europe letter
    Given I want to send a letter to country "UA"
    And the letter porto_id is "small"
    When I resolve the shipping configuration
    Then I should get zone with id "zone_2_europe"
""".strip(),
        encoding="utf-8",
    )

    cells = scan_sdk_features(features_dir, porto_data_path=data_path)
    assert cells[0]["zone"] == "zone_2_europe"
