"""Tests for labs.lib.python.matrix.constants."""

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from labs.lib.python.matrix.case_id import case_id_for, parse_case_id  # noqa: E402
from labs.lib.python.matrix.constants import (  # noqa: E402
    ADAPTER_INTERNETMARKE,
    PROVIDER_DEUTSCHEPOST,
)


def test_case_id_for_base_cell() -> None:
    assert (
        case_id_for(
            PROVIDER_DEUTSCHEPOST,
            ADAPTER_INTERNETMARKE,
            "standardbrief",
            "domestic",
        )
        == "deutschepost.internetmarke.standardbrief.domestic"
    )


def test_case_id_for_product_id_with_underscore() -> None:
    assert (
        case_id_for(
            PROVIDER_DEUTSCHEPOST,
            ADAPTER_INTERNETMARKE,
            "maxibrief_ausland",
            "world",
        )
        == "deutschepost.internetmarke.maxibrief_ausland.world"
    )


def test_case_id_for_single_service() -> None:
    assert (
        case_id_for(
            PROVIDER_DEUTSCHEPOST,
            ADAPTER_INTERNETMARKE,
            "standardbrief",
            "domestic",
            ("einschreiben",),
        )
        == "deutschepost.internetmarke.standardbrief.domestic.einschreiben"
    )


def test_case_id_for_composite_service() -> None:
    assert (
        case_id_for(
            PROVIDER_DEUTSCHEPOST,
            ADAPTER_INTERNETMARKE,
            "standardbrief",
            "domestic",
            ("einschreiben_einwurf",),
        )
        == "deutschepost.internetmarke.standardbrief.domestic.einschreiben_einwurf"
    )


def test_parse_case_id_round_trip() -> None:
    case_id = case_id_for(
        PROVIDER_DEUTSCHEPOST,
        ADAPTER_INTERNETMARKE,
        "maxibrief_ausland",
        "zone_1_eu",
        ("einschreiben",),
    )
    assert parse_case_id(case_id) == (
        PROVIDER_DEUTSCHEPOST,
        ADAPTER_INTERNETMARKE,
        "maxibrief_ausland",
        "zone_1_eu",
        ("einschreiben",),
    )


def test_parse_case_id_rejects_too_few_segments() -> None:
    with pytest.raises(ValueError, match="Invalid case_id"):
        parse_case_id("deutschepost.internetmarke.standardbrief")
