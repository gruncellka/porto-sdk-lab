from surface.extract.filter import extra_symbols, filter_surface
from surface.extract.normalize import (
    equivalent_types,
    first_sentence,
    normalize_surface,
    normalize_type_syntax,
    to_canonical,
    unwrap_return_type,
)


def test_snake_to_camel():
    assert to_canonical("country_from") == "countryFrom"
    assert to_canonical("mark") == "mark"
    assert to_canonical("PortoMark") == "PortoMark"
    assert to_canonical("SMALL") == "SMALL"


def test_does_not_alias_drift_names():
    assert to_canonical("get_mark") == "getMark"
    assert to_canonical("getMark") == "getMark"
    assert to_canonical("mark") != to_canonical("create_mark")
    assert to_canonical("track") != to_canonical("tracking")


def test_first_sentence():
    assert first_sentence("One. Two.") == "One."
    assert first_sentence("Single line") == "Single line"


def test_unwrap_promise():
    typ, async_flag = unwrap_return_type("Promise<PortoMark>", is_async=False)
    assert typ == "PortoMark"
    assert async_flag is True
    typ, async_flag = unwrap_return_type("Optional[str]", is_async=False)
    assert typ == "str | None"
    assert async_flag is False
    typ, async_flag = unwrap_return_type("boolean | null", is_async=False)
    assert typ == "boolean | null"


def test_normalize_surface_adds_canonical_and_truncates_doc():
    raw = {
        "language": "python",
        "symbols": {
            "get_mark": {
                "name": "get_mark",
                "kind": "function",
                "doc": "Returns mark facts. More detail follows.",
                "params": [{"name": "envelope_id", "optional": False, "type": "str"}],
                "returns": "Promise<PortoMark>",
                "async": False,
            }
        },
    }
    surface = normalize_surface(raw)
    sym = surface["symbols"]["get_mark"]
    assert sym["canonical"] == "getMark"
    assert sym["doc"] == "Returns mark facts."
    assert sym["params"][0]["canonical"] == "envelopeId"
    assert sym["returns"] == "PortoMark"
    assert sym["async"] is True


def test_normalize_enum_canonical_values():
    raw = {
        "language": "python",
        "symbols": {
            "MarkType": {
                "kind": "enum",
                "enum_members": {"STAMP": "stamp", "LABEL": "label"},
                "members": {},
            }
        },
    }
    surface = normalize_surface(raw)
    enum = surface["symbols"]["MarkType"]
    assert enum["canonicalValues"] == ["label", "stamp"]
    assert enum["enum_members"]["STAMP"] == "stamp"
    assert "values" not in enum


def test_filter_drops_error_and_pydantic_members():
    policy = {
        "denylist_global": [
            "modelConfig",
            "trimWhitespace",
            "validatePostalCode",
        ],
        "denylist_by_symbol": {
            "PortoError": ["captureStackTrace", "stack"],
        },
        "allowlist_by_symbol": {
            "ProviderClient": ["resolve"],
        },
    }
    raw = {
        "language": "typescript",
        "symbols": {
            "PortoError": {
                "kind": "class",
                "members": {
                    "code": {"kind": "attribute"},
                    "stack": {"kind": "attribute"},
                    "captureStackTrace": {"kind": "method", "params": [], "async": False},
                },
            },
            "Address": {
                "kind": "class",
                "members": {
                    "street": {"kind": "attribute"},
                    "modelConfig": {"kind": "attribute"},
                    "model_config": {"kind": "attribute"},
                    "trimWhitespace": {"kind": "method", "params": [], "async": False},
                    "trim_whitespace": {"kind": "method", "params": [], "async": False},
                    "validate_postal_code": {"kind": "method", "params": [], "async": False},
                },
            },
            "ProviderClient": {
                "kind": "class",
                "members": {
                    "resolve": {"kind": "method", "params": [], "async": False},
                    "options": {"kind": "method", "params": [], "async": False},
                },
            },
        },
    }
    filtered = filter_surface(raw, policy=policy)
    assert "code" in filtered["symbols"]["PortoError"]["members"]
    assert "stack" not in filtered["symbols"]["PortoError"]["members"]
    assert "captureStackTrace" not in filtered["symbols"]["PortoError"]["members"]
    assert "street" in filtered["symbols"]["Address"]["members"]
    assert "modelConfig" not in filtered["symbols"]["Address"]["members"]
    assert "model_config" not in filtered["symbols"]["Address"]["members"]
    assert "trimWhitespace" not in filtered["symbols"]["Address"]["members"]
    assert "trim_whitespace" not in filtered["symbols"]["Address"]["members"]
    assert "validate_postal_code" not in filtered["symbols"]["Address"]["members"]
    assert "resolve" in filtered["symbols"]["ProviderClient"]["members"]
    assert "options" not in filtered["symbols"]["ProviderClient"]["members"]


def test_denylist_camel_drops_snake_extract_name():
    policy = {"denylist_global": ["defaultProvider", "getMark"]}
    raw = {
        "language": "python",
        "symbols": {
            "PortoConfig": {
                "kind": "class",
                "members": {
                    "data": {"kind": "attribute"},
                    "default_provider": {"kind": "attribute"},
                },
            },
            "Envelopes": {
                "kind": "class",
                "members": {
                    "list": {"kind": "method"},
                    "get_mark": {"kind": "method"},
                },
            },
        },
    }
    filtered = filter_surface(raw, policy=policy)
    assert "data" in filtered["symbols"]["PortoConfig"]["members"]
    assert "default_provider" not in filtered["symbols"]["PortoConfig"]["members"]
    assert "list" in filtered["symbols"]["Envelopes"]["members"]
    assert "get_mark" not in filtered["symbols"]["Envelopes"]["members"]


def test_allowlist_symbols_drops_undeclared_and_extra_symbols():
    policy = {"allowlist_symbols": ["PortoClient", "PortoMark"]}
    raw = {
        "language": "python",
        "symbols": {
            "PortoClient": {"kind": "class", "members": {}},
            "PortoMark": {"kind": "class", "members": {}},
            "HttpClient": {"kind": "class", "members": {}},
            "EnvelopeResolverService": {"kind": "class", "members": {}},
        },
    }
    filtered = filter_surface(raw, policy=policy)
    assert set(filtered["symbols"]) == {"PortoClient", "PortoMark"}
    assert extra_symbols(raw, policy=policy) == ["EnvelopeResolverService", "HttpClient"]


def test_allowlist_get_mark_keeps_python_snake_name():
    policy = {"allowlist_by_symbol": {"Envelopes": ["getMark"]}}
    raw = {
        "language": "python",
        "symbols": {
            "Envelopes": {
                "kind": "class",
                "members": {
                    "list": {"kind": "method"},
                    "get_mark": {"kind": "method"},
                },
            }
        },
    }
    filtered = filter_surface(raw, policy=policy)
    members = filtered["symbols"]["Envelopes"]["members"]
    assert "get_mark" in members
    assert "list" not in members


def test_empty_policy_does_not_load_contract_yaml():
    raw = {
        "language": "python",
        "symbols": {
            "HttpClient": {"kind": "class", "members": {"get": {"kind": "method"}}},
        },
    }
    filtered = filter_surface(raw, policy={})
    assert "HttpClient" in filtered["symbols"]
    assert "get" in filtered["symbols"]["HttpClient"]["members"]


def test_type_syntax_aliases():
    assert equivalent_types("bool", "boolean")
    assert equivalent_types("str", "string")
    assert equivalent_types("None", "void")
    assert equivalent_types("dict[str, object]", "Record<string, unknown>")
    assert equivalent_types("dict", "Record<string, unknown>")
    assert equivalent_types("list[PortoMark]", "PortoMark[]")
    assert equivalent_types("list[dict[str, object]]", "Record<string, unknown>[]")
    assert normalize_type_syntax("Record<string, unknown>[]") == "map<unknown>[]"
    assert equivalent_types("bool | None", "boolean | null")
    assert equivalent_types("frozenset[Requirement]", "Requirement[]")
    assert equivalent_types("tuple[ServiceKind, ...]", "ServiceKind[]")
    assert equivalent_types("dict[str, str]", "Record<string, string>")
    assert equivalent_types(
        "PortoMark | Sequence[PortoMark]",
        "PortoMark | PortoMark[]",
    )
    assert equivalent_types("PortoMark | list[PortoMark]", "PortoMark | PortoMark[]")
    assert normalize_type_syntax("PortoMark | PortoMark[]") == "PortoMark | PortoMark[]"
    assert normalize_type_syntax("dict") == "map<unknown>"
    assert equivalent_types("Literal['advisory_match']", '"advisory_match"')
    assert equivalent_types("bool", "true")
    assert equivalent_types("timedelta", "number | Seconds")
    assert equivalent_types("DeliverySpan", '"next" | "within" | "between"')
    assert equivalent_types("float | None", "number")
    assert equivalent_types("MarkOutputMime | str", "string")
    assert not equivalent_types("PortoMark", "LetterPricing")
