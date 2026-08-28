from pathlib import Path

from surface.extract.normalize import normalize_surface
from surface.extract.python import _literal_values, extract_python, parse_dunder_all

FIXTURE = Path(__file__).parent / "fixtures" / "python_sdk"


def test_parse_all():
    names = parse_dunder_all(FIXTURE / "porto_sdk" / "__init__.py")
    assert names == ["ProviderClient", "PortoMark", "LetterType"]


def test_extract_python_fixture_raw():
    surface = extract_python(FIXTURE)
    symbols = surface["symbols"]
    assert set(symbols) == {"ProviderClient", "PortoMark", "LetterType"}
    client = symbols["ProviderClient"]
    assert "canonical" not in client
    assert "mark" in client["members"]
    assert client["members"]["mark"]["async"] is True
    assert "resolve" in client["members"]
    assert client["members"]["resolve"]["async"] is False
    params = {p["name"]: p for p in client["members"]["resolve"]["params"]}
    assert "country_from" in params
    assert "canonical" not in params["country_from"]
    assert symbols["LetterType"]["kind"] == "enum"
    assert "small" in symbols["LetterType"]["enum_members"].values()


def test_normalize_python_fixture():
    from surface.extract.filter import filter_surface

    surface = normalize_surface(filter_surface(extract_python(FIXTURE), policy={}))
    client = surface["symbols"]["ProviderClient"]
    assert client["canonical"] == "ProviderClient"
    params = {p["canonical"]: p for p in client["members"]["resolve"]["params"]}
    assert "countryFrom" in params
    letter = surface["symbols"]["LetterType"]
    assert "small" in letter["canonicalValues"]


def test_literal_type_alias_values():
    values = _literal_values("Literal['stamp', 'label']")
    assert values == {"stamp": "stamp", "label": "label"}
