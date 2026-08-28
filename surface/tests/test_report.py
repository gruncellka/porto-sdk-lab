from pathlib import Path

from surface.compare import merge_contract
from surface.report import write_report


def test_write_report_ok(tmp_path: Path):
    payload = {
        "language": "python",
        "symbols": {
            "ProviderClient": {
                "name": "ProviderClient",
                "canonical": "ProviderClient",
                "kind": "class",
                "members": {
                    "mark": {
                        "kind": "method",
                        "canonical": "mark",
                        "async": True,
                        "returns": "PortoMark",
                        "params": [],
                    }
                },
            }
        },
    }
    ts = {
        "language": "typescript",
        "symbols": payload["symbols"],
    }
    lines = write_report(payload, ts, artifacts_dir=tmp_path)
    assert lines == []
    assert (tmp_path / "python.json").is_file()
    assert (tmp_path / "typescript.json").is_file()
    assert (tmp_path / "report.json").is_file()
    assert (tmp_path / "report.md").is_file()
    merged = merge_contract(payload, ts)
    assert "ProviderClient" in merged["symbols"]
