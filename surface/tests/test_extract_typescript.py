from pathlib import Path

import pytest

from surface.extract.typescript import extract_typescript, parse_typedoc_json

FIXTURE = Path(__file__).parent / "fixtures" / "typescript_sdk"
TOOLS = Path(__file__).resolve().parents[1]


def test_parse_typedoc_json_minimal():
    data = {
        "kind": 1,
        "name": "fixture",
        "children": [
            {
                "kind": 128,
                "name": "ProviderClient",
                "children": [
                    {
                        "kind": 2048,
                        "name": "mark",
                        "signatures": [
                            {
                                "name": "mark",
                                "type": {"type": "reference", "name": "Promise"},
                            }
                        ],
                    },
                    {"kind": 2048, "name": "_hidden", "signatures": []},
                ],
            }
        ],
    }
    surface = parse_typedoc_json(data)
    assert "ProviderClient" in surface["symbols"]
    members = surface["symbols"]["ProviderClient"]["members"]
    assert "mark" in members
    assert "_hidden" not in members
    assert "canonical" not in surface["symbols"]["ProviderClient"]


def test_extract_typescript_fixture():
    typedoc = TOOLS / "node_modules" / ".bin" / "typedoc"
    if not typedoc.is_file():
        pytest.skip("typedoc not installed")
    surface = extract_typescript(FIXTURE, tools_root=TOOLS)
    symbols = surface["symbols"]
    assert "ProviderClient" in symbols
    assert "canonical" not in symbols["ProviderClient"]
    assert "mark" in symbols["ProviderClient"]["members"]
    assert "LetterType" in symbols
    members = symbols["LetterType"].get("enum_members") or {}
    assert "SMALL" in members


def test_parse_typedoc_keeps_uppercase_enum_values():
    data = {
        "kind": 1,
        "name": "fixture",
        "children": [
            {
                "kind": 8,
                "name": "PortoErrorCode",
                "children": [
                    {
                        "kind": 16,
                        "name": "PORTO_DATA_NOT_FOUND",
                        "defaultValue": '"PORTO_DATA_NOT_FOUND"',
                    }
                ],
            }
        ],
    }
    surface = parse_typedoc_json(data)
    enum = surface["symbols"]["PortoErrorCode"]
    assert enum["enum_members"]["PORTO_DATA_NOT_FOUND"] == "PORTO_DATA_NOT_FOUND"


def test_parse_typedoc_keeps_null_union_and_array_element_types():
    data = {
        "kind": 1,
        "name": "fixture",
        "children": [
            {
                "kind": 256,
                "name": "Restrictions",
                "children": [
                    {
                        "kind": 1024,
                        "name": "blocked",
                        "type": {
                            "type": "union",
                            "types": [
                                {"type": "intrinsic", "name": "boolean"},
                                {"type": "intrinsic", "name": "null"},
                            ],
                        },
                    },
                    {
                        "kind": 1024,
                        "name": "applicable",
                        "type": {
                            "type": "array",
                            "elementType": {"type": "reference", "name": "Restriction"},
                        },
                    },
                ],
            }
        ],
    }
    surface = parse_typedoc_json(data)
    members = surface["symbols"]["Restrictions"]["members"]
    assert members["blocked"]["type"] == "boolean | null"
    assert members["applicable"]["type"] == "Restriction[]"


def test_parse_typedoc_unwraps_readonly_type_operator():
    data = {
        "kind": 1,
        "name": "fixture",
        "children": [
            {
                "kind": 256,
                "name": "Porto",
                "children": [
                    {
                        "kind": 1024,
                        "name": "requires",
                        "type": {
                            "type": "typeOperator",
                            "operator": "readonly",
                            "target": {
                                "type": "array",
                                "elementType": {"type": "reference", "name": "Requirement"},
                            },
                        },
                    },
                    {
                        "kind": 1024,
                        "name": "serviceIds",
                        "type": {
                            "type": "typeOperator",
                            "operator": "readonly",
                            "target": {
                                "type": "array",
                                "elementType": {"type": "intrinsic", "name": "string"},
                            },
                        },
                    },
                ],
            }
        ],
    }
    surface = parse_typedoc_json(data)
    members = surface["symbols"]["Porto"]["members"]
    assert members["requires"]["type"] == "Requirement[]"
    assert members["serviceIds"]["type"] == "string[]"
