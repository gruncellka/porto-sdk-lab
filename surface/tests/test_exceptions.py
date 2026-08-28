from surface.compare import parity_diagnostics
from surface.exceptions import exempt_member_keys, load_differences


def test_differences_load():
    items = load_differences()
    assert any(i.get("id") == "data_loading" for i in items)
    assert any(i.get("parity") == "exempt-async" and i.get("member") == "resolve" for i in items)
    assert any(i.get("parity") == "exempt-async" and i.get("member") == "price" for i in items)


def test_async_exempt_for_resolve():
    exempt = exempt_member_keys()
    assert ("ProviderClient", "resolve", "async") in exempt
    py = {
        "symbols": {
            "ProviderClient": {
                "canonical": "ProviderClient",
                "kind": "class",
                "members": {
                    "resolve": {
                        "canonical": "resolve",
                        "kind": "method",
                        "async": False,
                        "returns": "Porto",
                    }
                },
            }
        }
    }
    ts = {
        "symbols": {
            "ProviderClient": {
                "canonical": "ProviderClient",
                "kind": "class",
                "members": {
                    "resolve": {
                        "canonical": "resolve",
                        "kind": "method",
                        "async": True,
                        "returns": "Porto",
                    }
                },
            }
        }
    }
    lines = parity_diagnostics(py, ts)
    assert not any("async drift" in line for line in lines)
