from surface.compare import (
    build_report,
    format_drift,
    merge_contract,
    parity_diagnostics,
    validate_contract,
)


def _surface(language: str, mark_name: str = "mark", returns: str = "PortoMark"):
    return {
        "language": language,
        "symbols": {
            "ProviderClient": {
                "name": "ProviderClient",
                "canonical": "ProviderClient",
                "kind": "class",
                "members": {
                    mark_name: {
                        "kind": "method",
                        "canonical": mark_name[0].lower() + mark_name[1:]
                        if mark_name[0].isupper()
                        else mark_name,
                        "async": True,
                        "returns": returns,
                        "params": [],
                    }
                },
            }
        },
    }


def test_missing_symbol():
    py = _surface("python")
    ts = {"language": "typescript", "symbols": {}}
    lines = parity_diagnostics(py, ts)
    assert any("missing in TypeScript" in line for line in lines)


def test_return_drift():
    py = _surface("python", returns="PortoMark")
    ts = _surface("typescript", returns="LetterPricing")
    ts["symbols"]["ProviderClient"]["members"]["mark"]["canonical"] = "mark"
    lines = parity_diagnostics(py, ts)
    assert any("return drift" in line for line in lines)


def test_create_mark_vs_mark_is_missing_member():
    py = _surface("python", mark_name="mark")
    ts = {
        "language": "typescript",
        "symbols": {
            "ProviderClient": {
                "name": "ProviderClient",
                "canonical": "ProviderClient",
                "kind": "class",
                "members": {
                    "createMark": {
                        "kind": "method",
                        "canonical": "createMark",
                        "async": True,
                        "returns": "PortoMark",
                        "params": [],
                    }
                },
            }
        },
    }
    lines = parity_diagnostics(py, ts)
    assert any("mark" in line and "missing" in line for line in lines)
    text = format_drift(lines)
    assert text.startswith("PUBLIC CONTRACT DRIFT")


def test_enum_drift():
    py = {
        "symbols": {
            "MarkType": {
                "canonical": "MarkType",
                "kind": "enum",
                "canonicalValues": ["stamp"],
                "enum_members": {"STAMP": "stamp"},
                "members": {},
            }
        }
    }
    ts = {
        "symbols": {
            "MarkType": {
                "canonical": "MarkType",
                "kind": "enum",
                "canonicalValues": ["stamp", "label"],
                "enum_members": {"STAMP": "stamp", "LABEL": "label"},
                "members": {},
            }
        }
    }
    lines = parity_diagnostics(py, ts)
    assert any("canonicalValues" in line for line in lines)


def test_merge_validates():
    contract = merge_contract(_surface("python"), _surface("typescript"))
    validate_contract(contract)
    assert "ProviderClient" in contract["symbols"]


def _typed_surface(language: str, timeout_type: str, items_type: str, optional: bool):
    return {
        "language": language,
        "symbols": {
            "PortoConfig": {
                "name": "PortoConfig",
                "canonical": "PortoConfig",
                "kind": "class",
                "members": {
                    "timeout": {
                        "kind": "attribute",
                        "canonical": "timeout",
                        "type": timeout_type,
                    },
                    "items": {
                        "kind": "attribute",
                        "canonical": "items",
                        "type": items_type,
                    },
                    "mark": {
                        "kind": "method",
                        "canonical": "mark",
                        "async": True,
                        "returns": "PortoMark",
                        "params": [
                            {
                                "name": "request",
                                "optional": optional,
                                "type": "PortoMarkRequest",
                            }
                        ],
                    },
                },
            }
        },
    }


def test_time_unit_drift_timedelta_vs_ms_number():
    py = _typed_surface("python", "timedelta", "list[str]", False)
    ts = _typed_surface("typescript", "number", "string[]", False)
    ts["symbols"]["PortoConfig"]["members"]["timeout"]["type"] = "number /* milliseconds */"
    lines = parity_diagnostics(py, ts)
    assert any("time-unit" in line for line in lines)


def test_shape_drift_list_vs_scalar():
    py = _typed_surface("python", "timedelta", "list[str]", False)
    ts = _typed_surface("typescript", "Seconds", "string", False)
    lines = parity_diagnostics(py, ts)
    assert any("shape" in line for line in lines)


def test_optional_param_drift():
    py = _typed_surface("python", "timedelta", "list[str]", False)
    ts = _typed_surface("typescript", "Seconds", "string[]", True)
    lines = parity_diagnostics(py, ts)
    assert any("optional" in line for line in lines)


def test_extra_symbol_in_report():
    payload = _surface("python")
    report = build_report(payload, payload, extra_python=["HttpClient"], extra_typescript=[])
    kinds = [row["kind"] for row in report["differences"]]
    assert "extra_symbol" in kinds
    lines = parity_diagnostics(payload, payload, extra_python=["HttpClient"])
    assert any("extra symbol" in line for line in lines)


def test_language_syntax_is_not_return_or_shape_drift():
    py = {
        "language": "python",
        "symbols": {
            "PortoMarkRequest": {
                "name": "PortoMarkRequest",
                "canonical": "PortoMarkRequest",
                "kind": "class",
                "members": {
                    "design": {"kind": "attribute", "type": "dict"},
                    "mark": {
                        "kind": "method",
                        "canonical": "mark",
                        "async": True,
                        "returns": "PortoMark | list[PortoMark]",
                        "params": [
                            {
                                "name": "request",
                                "optional": False,
                                "type": "PortoMarkRequest | Sequence[PortoMarkRequest]",
                            }
                        ],
                    },
                },
            }
        },
    }
    ts = {
        "language": "typescript",
        "symbols": {
            "PortoMarkRequest": {
                "name": "PortoMarkRequest",
                "canonical": "PortoMarkRequest",
                "kind": "class",
                "members": {
                    "design": {"kind": "attribute", "type": "Record<string, unknown>"},
                    "mark": {
                        "kind": "method",
                        "canonical": "mark",
                        "async": True,
                        "returns": "PortoMark | PortoMark[]",
                        "params": [
                            {
                                "name": "request",
                                "optional": False,
                                "type": "PortoMarkRequest | PortoMarkRequest[]",
                            }
                        ],
                    },
                },
            }
        },
    }
    lines = parity_diagnostics(py, ts)
    assert lines == []


def test_ttl_timedelta_and_seconds_are_not_time_unit_drift():
    py = {
        "symbols": {
            "CacheConfig": {
                "canonical": "CacheConfig",
                "kind": "class",
                "members": {
                    "ttl": {"kind": "attribute", "type": "timedelta"},
                },
            }
        }
    }
    ts = {
        "symbols": {
            "CacheConfig": {
                "canonical": "CacheConfig",
                "kind": "interface",
                "members": {
                    "ttl": {"kind": "attribute", "type": "number | Seconds"},
                },
            }
        }
    }
    lines = parity_diagnostics(py, ts)
    assert not any("time-unit" in line for line in lines)


def test_unparameterized_dict_union_is_map_not_scalar():
    py = {
        "symbols": {
            "PortoMarkRequest": {
                "canonical": "PortoMarkRequest",
                "kind": "class",
                "members": {
                    "design": {"kind": "attribute", "type": "dict | None"},
                },
            }
        }
    }
    ts = {
        "symbols": {
            "PortoMarkRequest": {
                "canonical": "PortoMarkRequest",
                "kind": "interface",
                "members": {
                    "design": {"kind": "attribute", "type": "Record<string, unknown>"},
                },
            }
        }
    }
    lines = parity_diagnostics(py, ts)
    assert not any("shape" in line for line in lines)


def test_enum_vs_const_union_is_not_kind_drift():
    py = {
        "symbols": {
            "CapabilityState": {
                "canonical": "CapabilityState",
                "kind": "enum",
                "canonicalValues": ["absent", "ready"],
                "enum_members": {"ABSENT": "absent", "READY": "ready"},
                "members": {},
            }
        }
    }
    ts = {
        "symbols": {
            "CapabilityState": {
                "canonical": "CapabilityState",
                "kind": "type",
                "canonicalValues": ["absent", "ready"],
                "enum_members": {"Absent": "absent", "Ready": "ready"},
                "members": {},
            }
        }
    }
    lines = parity_diagnostics(py, ts)
    assert not any("kind drift" in line for line in lines)


def test_envelope_identification_dimensions_and_porto_specs_are_not_drift():
    py = {
        "symbols": {
            "EnvelopeIdentity": {
                "canonical": "EnvelopeIdentity",
                "kind": "class",
                "members": {
                    "dimensions": {"kind": "attribute", "type": "Dimensions"},
                },
            },
            "Porto": {
                "canonical": "Porto",
                "kind": "class",
                "members": {
                    "requires": {"kind": "attribute", "type": "frozenset[Requirement]"},
                },
            },
        }
    }
    ts = {
        "symbols": {
            "EnvelopeIdentity": {
                "canonical": "EnvelopeIdentity",
                "kind": "interface",
                "members": {
                    "dimensions": {"kind": "attribute", "type": "Dimensions"},
                },
            },
            "Porto": {
                "canonical": "Porto",
                "kind": "interface",
                "members": {
                    "requires": {"kind": "attribute", "type": "readonly Requirement[]"},
                },
            },
        }
    }
    lines = parity_diagnostics(py, ts)
    assert not any("shape" in line for line in lines)
    assert not any("return drift" in line for line in lines)
    assert not any("type drift" in line for line in lines)


def test_null_union_is_not_stripped_as_drift():
    py = {
        "symbols": {
            "Restrictions": {
                "canonical": "Restrictions",
                "kind": "class",
                "members": {
                    "blocked": {
                        "kind": "attribute",
                        "type": "bool | None",
                        "optional": False,
                    }
                },
            }
        }
    }
    ts = {
        "symbols": {
            "Restrictions": {
                "canonical": "Restrictions",
                "kind": "interface",
                "members": {
                    "blocked": {
                        "kind": "attribute",
                        "type": "boolean | null",
                        "optional": False,
                    }
                },
            }
        }
    }
    assert parity_diagnostics(py, ts) == []


def test_attribute_optional_drift():
    # True drift: required non-null vs optional non-null (not T|None vs optional T|null).
    py = {
        "symbols": {
            "Address": {
                "canonical": "Address",
                "kind": "class",
                "members": {
                    "city": {"kind": "attribute", "type": "str", "optional": False},
                },
            }
        }
    }
    ts = {
        "symbols": {
            "Address": {
                "canonical": "Address",
                "kind": "interface",
                "members": {
                    "city": {"kind": "attribute", "type": "string", "optional": True},
                },
            }
        }
    }
    lines = parity_diagnostics(py, ts)
    assert any("optional" in line for line in lines)


def test_nullable_slot_folds_optional_flag():
    py = {
        "symbols": {
            "Address": {
                "canonical": "Address",
                "kind": "class",
                "members": {
                    "street": {"kind": "attribute", "type": "str | None", "optional": False},
                },
            }
        }
    }
    ts = {
        "symbols": {
            "Address": {
                "canonical": "Address",
                "kind": "interface",
                "members": {
                    "street": {"kind": "attribute", "type": "string | null", "optional": True},
                },
            }
        }
    }
    assert parity_diagnostics(py, ts) == []


def test_closure_fails_on_any_and_untracked():
    from surface.compare import build_report

    py = {
        "symbols": {
            "Porto": {
                "canonical": "Porto",
                "kind": "class",
                "members": {
                    "validation": {"kind": "attribute", "type": "LetterValidationService"},
                    "specs": {"kind": "attribute", "type": "list[Any]"},
                },
            }
        }
    }
    report = build_report(py, py)
    kinds = {row["kind"] for row in report["differences"]}
    assert "untracked_type" in kinds
    assert "baggy_type" in kinds
