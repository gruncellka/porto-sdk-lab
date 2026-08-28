"""Integration tests against bundled porto-features / porto-data."""

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from labs.lib.python.matrix.orders_sync import build_all_order_cells, sync_orders  # noqa: E402
from labs.lib.python.matrix.sdk_sync import scan_sdk_features, write_sdk_matrix  # noqa: E402


def _features_dir() -> Path:
    return _REPO_ROOT / "resources" / "porto-features" / "porto_features" / "features"


def _data_path() -> Path:
    return _REPO_ROOT / "resources" / "porto-data" / "porto_data"


def test_scan_bundled_sdk_features() -> None:
    features_dir = _features_dir()
    data_path = _data_path()
    cells = scan_sdk_features(features_dir, porto_data_path=data_path)
    assert len(cells) >= 100


def test_build_all_order_cells_bundled() -> None:
    cells = build_all_order_cells(_data_path())
    assert len(cells) >= 40


def test_write_sdk_matrix_to_tmp(tmp_path: Path) -> None:
    features_dir = _features_dir()
    output = tmp_path / "sdk.yaml"
    count = write_sdk_matrix(features_dir, output, porto_data_path=_data_path())
    assert count >= 100
    assert "matrix-sdk-sync.py" in output.read_text(encoding="utf-8")


def test_sync_orders_to_tmp(tmp_path: Path) -> None:
    orders_out = tmp_path / "orders.generated.yaml"
    cases_out = tmp_path / "cases.generated.json"
    cells, _ = sync_orders(
        _data_path(),
        orders_output=orders_out,
        cases_json_output=cases_out,
        features_root=_features_dir(),
    )
    assert len(cells) >= 40
    assert orders_out.is_file()
    assert cases_out.is_file()
