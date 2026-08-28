"""Goldens for public-surface extract artifacts (run after `make surface`)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ARTIFACTS = Path(__file__).resolve().parents[1] / "artifacts"

pytestmark = pytest.mark.skipif(
    not (ARTIFACTS / "report.json").is_file(),
    reason="surface artifacts missing — run make surface (or rely on surface-check CI job)",
)

HIDDEN = (
    "DEFAULT_PROVIDER",
    "EnvelopeResolverService",
    "RestrictionsService",
    "HttpClient",
    "Letter",
    "LetterType",
    "EnvelopeIdentification",
    "PortoExecution",
    "PortoResolver",
    "NormalizedPortoConfig",
)

ENVELOPES_MEMBERS = {"list", "geometry", "layout", "identify", "getMark", "get_mark"}
PORTO_CLIENT_MEMBERS = {
    "config",
    "providers",
    "provider",
    "envelopes",
    "restrictions",
    "jurisdictions",
    "address",
}
PROVIDER_CLIENT_MEMBERS = {
    "resolve",
    "options",
    "price",
    "mark",
    "track",
    "capabilities",
    "can",
    "wallet",
    "restrictions",
}


def _load(name: str) -> dict:
    return json.loads((ARTIFACTS / name).read_text(encoding="utf-8"))


def test_report_has_no_errors():
    report = _load("report.json")
    assert report["status"] == "ok"
    assert report["summary"]["errors"] == 0
    extras = [d for d in report["differences"] if d["kind"] == "extra_symbol"]
    assert extras == []


def test_public_json_hides_machinery():
    for name in ("python.json", "typescript.json"):
        symbols = _load(name)["symbols"]
        for hidden in HIDDEN:
            assert hidden not in symbols, f"{hidden} leaked into {name}"
        client = symbols["PortoClient"]["members"]
        assert set(client) == PORTO_CLIENT_MEMBERS
        assert client["config"]["type"] == "PortoConfig"
        assert client["envelopes"]["type"] == "Envelopes"
        assert client["restrictions"]["type"] == "RestrictionsService"
        provider = set(symbols["ProviderClient"]["members"])
        assert provider == PROVIDER_CLIENT_MEMBERS
        for ghost in ("advise", "prepare", "bytes", "tracking", "registered", "resolver"):
            assert ghost not in provider
        envelopes = set(symbols["Envelopes"]["members"])
        assert envelopes <= ENVELOPES_MEMBERS
        assert {"list", "geometry", "layout", "identify"} <= envelopes
        assert "getMark" in envelopes or "get_mark" in envelopes
        for ghost in (
            "match",
            "catalog",
            "getLayout",
            "getGeometry",
            "listCatalog",
            "validateForProduct",
        ):
            assert ghost not in envelopes
        restrictions = set(symbols["Restrictions"]["members"])
        assert restrictions == {"impact", "legal", "routing"}
        config = symbols["PortoConfig"]["members"]
        assert "default_provider" not in config
        assert "defaultProvider" not in config
        caps = set(symbols["ProviderCapabilities"]["members"])
        assert "trackingExpected" not in caps
        assert "tracking_expected" not in caps
        assert "provider_id" not in caps
        assert "providerId" not in caps
        assert {"mark", "track", "wallet"} <= caps
        assert "differentiator" not in symbols["ProductOption"]["members"]


def test_envelope_identity_dimensions_is_dimensions():
    for name in ("python.json", "typescript.json"):
        ident = _load(name)["symbols"]["EnvelopeIdentity"]["members"]
        assert ident["dimensions"]["type"] == "Dimensions"
        assert "format" in ident
        assert "resolution_weight" in ident or "resolutionWeight" in ident
        assert "candidate_product_ids" not in ident
        assert "candidateProductIds" not in ident
        assert "detected_format" not in ident
        assert "detectedFormat" not in ident


def test_porto_mark_requires_wire():
    for name in ("python.json", "typescript.json"):
        members = _load(name)["symbols"]["PortoMark"]["members"]
        assert "wire" in members
        assert "amount" in members
        assert "value" not in members
        assert "pre_calculated_price" not in members
        assert "preCalculatedPrice" not in members
        assert "diagnostics" not in members


def test_pricing_uses_zone_id():
    for name in ("python.json", "typescript.json"):
        members = _load(name)["symbols"]["Pricing"]["members"]
        assert "zoneId" in members or "zone_id" in members
        assert "zone" not in members


def test_envelope_geometry_has_no_mm_suffix():
    for name in ("python.json", "typescript.json"):
        for symbol in ("Envelope", "EnvelopeGeometry", "EnvelopeLayout"):
            members = _load(name)["symbols"][symbol]["members"]
            assert "width" in members
            assert "height" in members
            assert "widthMm" not in members
            assert "heightMm" not in members
            assert "width_mm" not in members
            assert "height_mm" not in members


def test_porto_requires_services_typed():
    ts = _load("typescript.json")["symbols"]["Porto"]["members"]
    assert ts["requires"]["type"] == "Requirement[]"
    assert ts["services"]["type"] == "ServiceKind[]"
    assert ts["serviceIds"]["type"] == "string[]"


def test_porto_has_no_dimension_specs():
    py = _load("python.json")["symbols"]["Porto"]["members"]
    ts = _load("typescript.json")["symbols"]["Porto"]["members"]
    assert "dimension_specs" not in py
    assert "dimensionSpecs" not in ts


def test_porto_carries_restrictions():
    for name in ("python.json", "typescript.json"):
        members = _load(name)["symbols"]["Porto"]["members"]
        field = members.get("restrictions")
        assert field is not None
        assert field["type"] == "Restrictions"
        result = _load(name)["symbols"]["Restrictions"]["members"]
        assert "impact" in result
        assert "legal" in result
        assert "routing" in result
        assert "items" not in result
        assert "restrictions" not in result
        assert "operational" not in result
        assert "blocked" not in result
        assert "allowed" not in result


def test_typescript_public_fields_are_camel_case():
    ts = _load("typescript.json")
    for symbol, payload in ts["symbols"].items():
        if payload.get("kind") == "enum":
            continue
        for member in payload.get("members", {}):
            if "_" in member and member != member.upper():
                raise AssertionError(f"{symbol}.{member} is snake_case on the TS surface")
