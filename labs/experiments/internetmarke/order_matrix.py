"""
Internetmarke order matrix — graph-driven cases with artifact capture.

Replaces removed example_comprehensive_api_test.py.
Writes under OBSERVER_RUN_DIR when set by the lab observer.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from labs.lib.python.load_env import load_lab_env  # noqa: E402
from labs.lib.python.matrix.case_id import case_id_for  # noqa: E402
from labs.lib.python.matrix.constants import (  # noqa: E402
    ADAPTER_INTERNETMARKE,
    PROVIDER_DEUTSCHEPOST,
)
from labs.lib.python.matrix.constants import ZONE_COUNTRY  # noqa: E402
from labs.lib.python.matrix.orders_sync import wire_service_variants  # noqa: E402
from labs.lib.python.porto_client import create_porto_client  # noqa: E402

load_lab_env()

from porto_sdk import (  # noqa: E402
    Address,
    PortoClient,
    PortoConfig,
    PortoMarkRequest,
    ProviderClient,
)
from porto_sdk.adapters.deutschepost.internetmarke.bootstrap import (  # noqa: E402
    get_internetmarke_base_url,
    load_internetmarke_config,
)
from porto_sdk.adapters.deutschepost.internetmarke.utils import (  # noqa: E402
    parse_wallet_balance_cents,
)
from porto_sdk.config import ProviderRuntimeConfig  # noqa: E402
from porto_sdk.errors import PortoError, PortoErrorCode  # noqa: E402
from porto_sdk.execution import ExecutionParameters, PortoMark  # noqa: E402
from porto_sdk.services.execution_binding import ExecutionBinding  # noqa: E402

_FEATURES_ADDRESSES = (
    _REPO_ROOT / "resources" / "porto-features" / "porto_features" / "fixtures" / "addresses"
)
LICKO_COUNTRIES = ("DE", "UA", "FR", "CH", "US")


def _address_from_fixture(fixture_id: str) -> Address:
    raw = json.loads((_FEATURES_ADDRESSES / f"{fixture_id}.json").read_text(encoding="utf-8"))
    return Address(
        name=str(raw["name"]),
        street=raw.get("street") or None,
        house_number=str(raw["house_number"]) if raw.get("house_number") is not None else None,
        postal_code=str(raw["postal_code"]),
        locality=str(raw.get("locality") or raw["city"]),
        country_code=str(raw["country_code"]),
        region_code=raw.get("region_code"),
    )


def lab_country_for_zone(zone_id: str) -> str:
    """Recipient country for a matrix zone (must match porto-data zone membership)."""
    if zone_id == "world":
        override = (os.getenv("LAB_WORLD_COUNTRY") or "").strip().upper()
        if override and override in RECIPIENTS and override not in {"DE", "FR", "CH", "UA"}:
            return override
        return ZONE_COUNTRY["world"]
    return ZONE_COUNTRY.get(zone_id, "DE")


SENDER = _address_from_fixture("origin_DE")
RECIPIENTS: dict[str, Address] = {
    code: _address_from_fixture(f"valid_{code}") for code in LICKO_COUNTRIES
}


DEFAULT_PROFILES: dict[str, dict[str, Any]] = {
    "canary": {"execution": "manual", "purchases": True, "max_cases": 1, "voucher_layout": "ADDRESS_ZONE"},
    "full": {"execution": "manual", "purchases": True, "max_cases": None, "voucher_layout": "ADDRESS_ZONE"},
    "franking_canary": {
        "execution": "manual",
        "purchases": True,
        "max_cases": 4,
        "voucher_layout": "FRANKING_ZONE",
    },
    "franking_full": {
        "execution": "manual",
        "purchases": True,
        "max_cases": None,
        "voucher_layout": "FRANKING_ZONE",
    },
    "dry_run": {"execution": "auto_ok", "purchases": False, "max_cases": None, "voucher_layout": "ADDRESS_ZONE"},
}


@dataclass(frozen=True)
class CaseRunResult:
    ok: bool
    spend_cents: int = 0
    wallet_balance_cents: int | None = None
    insufficient_funds: bool = False


@dataclass(frozen=True)
class MatrixCase:
    case_id: str
    product_id: str
    zone_id: str
    country_code: str
    weight: int
    weight_tier_id: str
    service_ids: tuple[str, ...] = ()


def load_canary_case_ids() -> list[str]:
    """Load curated daily smoke case_ids from porto-features canary.yaml."""
    path = (
        _REPO_ROOT
        / "resources"
        / "porto-features"
        / "porto_features"
        / "matrix"
        / "canary.yaml"
    )
    if not path.is_file():
        return []
    try:
        import yaml
    except ImportError:
        return []
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        return []
    ids = doc.get("case_ids")
    return [str(item) for item in ids] if isinstance(ids, list) else []


def filter_cases_for_profile(
    cases: list[MatrixCase], profile_name: str, max_cases: int | None
) -> list[MatrixCase]:
    profile = load_profile(profile_name)
    if profile_name == "canary":
        canary_ids = load_canary_case_ids()
        if canary_ids:
            allowed = set(canary_ids)
            cases = [case for case in cases if case.case_id in allowed]
    limit = max_cases if max_cases is not None else profile.get("max_cases")
    if limit is not None:
        cases = cases[: int(limit)]
    return cases


def service_surcharge_cents(loader, *, zone_id: str, service_id: str) -> int:
    service_price = loader.get_service_price(service_id, zone_id)
    if service_price is None:
        raise ValueError(f"No service price for {service_id}")
    return service_price


def estimate_checkout_cents(
    loader,
    *,
    product_id: str,
    zone_id: str,
    weight_tier_id: str,
    service_ids: tuple[str, ...],
) -> int:
    pricing = loader.get_price_by_product_zone_weight_tier(product_id, zone_id, weight_tier_id)
    if not pricing:
        raise ValueError(f"No price for {product_id}/{zone_id}/{weight_tier_id}")
    total = pricing.price
    for service_id in service_ids:
        total += service_surcharge_cents(loader, zone_id=zone_id, service_id=service_id)
    return total


def load_profile(name: str) -> dict[str, Any]:
    path = Path(__file__).parent / "matrix_profiles.yaml"
    profile = dict(DEFAULT_PROFILES.get(name, DEFAULT_PROFILES["canary"]))
    if not path.exists():
        return profile
    section: str | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.endswith(":") and not stripped.startswith("-"):
            section = stripped[:-1]
            continue
        if section == name and ":" in stripped:
            key, raw = stripped.split(":", 1)
            key = key.strip()
            raw = raw.strip()
            if raw in {"null", "~"}:
                profile[key] = None
            elif raw == "true":
                profile[key] = True
            elif raw == "false":
                profile[key] = False
            elif raw.isdigit():
                profile[key] = int(raw)
            else:
                profile[key] = raw.strip('"').strip("'")
    return profile


def min_weight_for_tier(tier_id: str, loader) -> int:
    tiers = sorted(loader.get_all_weight_tiers(), key=lambda tier: tier.max_weight)
    prev_max = 0
    for tier in tiers:
        if tier.id == tier_id:
            return max(1, prev_max + 1) if prev_max else 1
        prev_max = tier.max_weight
    return 1


def build_cases(loader, profile_name: str, max_cases: int | None) -> list[MatrixCase]:
    graph = loader.resolution_graph
    wire = graph.wire_edges.get("internetmarke", {})
    links = graph.links or {}
    cases: list[MatrixCase] = []

    for product_id, zones in wire.items():
        product_link = links.get(product_id, {})
        allowed_zones = set(product_link.get("zones", []))
        weight_tiers = product_link.get("weight_tiers", [])
        weight_tier_id = weight_tiers[0] if weight_tiers else "W0020"
        weight = min_weight_for_tier(weight_tier_id, loader)

        for zone_id, zone_wire in zones.items():
            if zone_id not in allowed_zones or not isinstance(zone_wire, dict):
                continue
            if zone_wire.get("base") is None:
                continue
            country = lab_country_for_zone(zone_id)
            for service_ids in wire_service_variants(zone_wire):
                cases.append(
                    MatrixCase(
                        case_id=case_id_for(
                            PROVIDER_DEUTSCHEPOST,
                            ADAPTER_INTERNETMARKE,
                            product_id,
                            zone_id,
                            service_ids,
                        ),
                        product_id=product_id,
                        zone_id=zone_id,
                        country_code=country,
                        weight=weight,
                        weight_tier_id=weight_tier_id,
                        service_ids=service_ids,
                    )
                )

    cases.sort(key=lambda item: item.case_id)
    return filter_cases_for_profile(cases, profile_name, max_cases)


def run_dir() -> Path:
    observer = os.getenv("OBSERVER_RUN_DIR")
    if observer:
        return Path(observer)
    return Path(__file__).parent / "artifacts" / "local"


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")


def porto_error_payload(exc: PortoError) -> dict[str, Any]:
    return {
        "code": exc.code.value,
        "message": exc.message,
        "status_code": exc.status_code,
        "upstream_code": exc.upstream_code,
        "details": exc.details,
        "provider": exc.provider,
        "wire": getattr(exc, "wire", None),
    }


def build_client() -> PortoClient:
    config = PortoConfig.from_env()
    data = config.data or str(_REPO_ROOT / "resources" / "porto-data" / "porto_data")
    im = load_internetmarke_config("deutschepost")
    providers = dict(config.providers or {})
    current = providers.get("deutschepost") or ProviderRuntimeConfig()
    wires = dict(current.wires or {})
    if im is not None:
        wires["internetmarke"] = im
    providers["deutschepost"] = ProviderRuntimeConfig(wires=wires or None)
    return create_porto_client(
        PortoConfig(providers=providers, data=data, transport=config.transport)
    )


def bound_provider(client: PortoClient) -> ProviderClient:
    return client.provider("deutschepost")


def voucher_layout_for(profile_name: str) -> str:
    """Internetmarke ``voucherLayout`` wire token (not a Porto type).

    ``ADDRESS_ZONE`` / ``FRANKING_ZONE`` stay inside this experiment and the
    Internetmarke adapter. They are not passed into SDK ``ExecutionParameters``.
    """
    profile = load_profile(profile_name)
    raw = os.getenv("VOUCHER_LAYOUT") or profile.get("voucher_layout") or "FRANKING_ZONE"
    if raw not in ("ADDRESS_ZONE", "FRANKING_ZONE"):
        raise ValueError(f"Unsupported Internetmarke voucherLayout: {raw}")
    return str(raw)


def estimate_matrix_spend_cents(loader, cases: list[MatrixCase]) -> int:
    total = 0
    for case in cases:
        total += estimate_checkout_cents(
            loader,
            product_id=case.product_id,
            zone_id=case.zone_id,
            weight_tier_id=case.weight_tier_id,
            service_ids=case.service_ids,
        )
    return total


async def run_preflight(
    client: PortoClient,
    out: Path,
    *,
    dry_run: bool,
    cases: list[MatrixCase],
) -> bool:
    from labs.lib.python.internetmarke_auth_diagnostic import probe_internetmarke_auth

    preflight_dir = out / "cases" / "_preflight"
    preflight_dir.mkdir(parents=True, exist_ok=True)

    api_payload: dict[str, Any] = {"status": "skipped", "note": "use lab diagnostic for API version checks"}
    api_ok = True

    auth_payload: dict[str, Any]
    auth_ok = True
    if dry_run:
        auth_payload = {"status": "skipped_dry_run", "blocking_stage": "none"}
    else:
        im = load_internetmarke_config("deutschepost")
        creds = im.credentials if im else {}
        auth = await probe_internetmarke_auth(
            base_url=get_internetmarke_base_url(im),
            username=creds.get("username"),
            password=creds.get("password"),
            api_key=creds.get("dhl_api_key"),
            api_secret=creds.get("dhl_api_secret"),
        )
        auth_ok = auth.status == "connected"
        auth_payload = auth.to_dict()
        provider = bound_provider(client)
        estimated_spend = estimate_matrix_spend_cents(provider._resolver.data_loader, cases)
        auth_payload["estimated_spend_cents"] = estimated_spend
        wallet_balance_cents: int | None = None
        if auth_ok and provider.capabilities().wallet:
            try:
                wallet = await provider.wallet.balance()
                wallet_balance_cents = wallet.balance_cents
                auth_payload["wallet_balance_cents"] = wallet_balance_cents
                auth_payload["wallet_source"] = "provider.wallet.balance"
            except PortoError as exc:
                auth_payload["wallet_error"] = str(exc)
                auth_payload["wallet_error_code"] = exc.code.value
        elif auth.wallet_balance_cents is not None:
            wallet_balance_cents = auth.wallet_balance_cents
        if auth_ok and wallet_balance_cents is not None and wallet_balance_cents < estimated_spend:
            auth_ok = False
            shortfall = estimated_spend - wallet_balance_cents
            auth_payload["status"] = "insufficient_wallet"
            auth_payload["blocking_stage"] = "portokasse_wallet"
            auth_payload["sdk_error_code"] = PortoErrorCode.PORTO_WALLET_INSUFFICIENT.value
            auth_payload["hint"] = (
                f"Portokasse balance €{wallet_balance_cents / 100:.2f} is below "
                f"estimated matrix spend €{estimated_spend / 100:.2f} "
                f"(short €{shortfall / 100:.2f}). Top up via Portokasse → Porto laden."
            )
            auth_payload["next_steps"] = [
                "Open Portokasse → Porto laden (or Interne Aufladung on Entwickler-Portokasse).",
                "Re-run preflight after top-up.",
            ]
            print(auth_payload["hint"])
        elif auth_ok and wallet_balance_cents is not None:
            print(
                f"Portokasse wallet: €{wallet_balance_cents / 100:.2f} "
                f"| estimated matrix: €{estimated_spend / 100:.2f}"
            )
        if not auth_ok and auth.status != "connected":
            from labs.lib.python.internetmarke_auth_diagnostic import (
                format_gate_report,
                summarize_internetmarke_gates,
            )

            print(format_gate_report(summarize_internetmarke_gates(auth)))

    payload = {
        "ts": datetime.now(UTC).isoformat(),
        "api_version": api_payload,
        "auth": auth_payload,
    }
    write_json(preflight_dir / "auth.json", payload)
    return api_ok and auth_ok


def find_checkout_trace(http_dir: Path, shop_order_id: str) -> dict[str, Any] | None:
    if not http_dir.is_dir():
        return None
    for path in sorted(http_dir.glob("*_checkout.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        body = (payload.get("request") or {}).get("body") or {}
        if not isinstance(body, dict):
            continue
        if str(body.get("shopOrderId")) == str(shop_order_id):
            return payload
    return None


def strict_validate_case(
    *,
    case: MatrixCase,
    loader,
    resolved: Any,
    wire_code: int | str,
    checkout_cents: int,
    prepared: Any,
    voucher_layout: str,
    mark: PortoMark | None = None,
    http_dir: Path | None = None,
) -> dict[str, Any]:
    """Strict matrix checks — catalog estimate vs resolver vs API checkout."""

    def row(name: str, expected: Any, actual: Any, *, ok: bool | None = None) -> dict[str, Any]:
        passed = ok if ok is not None else expected == actual
        return {"check": name, "expected": expected, "actual": actual, "ok": passed}

    checks: list[dict[str, Any]] = []
    catalog_cents = estimate_checkout_cents(
        loader,
        product_id=case.product_id,
        zone_id=case.zone_id,
        weight_tier_id=case.weight_tier_id,
        service_ids=case.service_ids,
    )

    checks.append(row("product_id", case.product_id, resolved.product.id))
    checks.append(row("zone_id", case.zone_id, resolved.zone.id))
    checks.append(row("wire_code", wire_code, prepared.wire_code))
    checks.append(row("prepared_product_id", case.product_id, prepared.product_id))
    checks.append(row("catalog_checkout_cents", checkout_cents, catalog_cents))
    checks.append(row("resolver_amount_cents", checkout_cents, resolved.amount))

    if mark is not None:
        checks.append(row("api_value_cents", checkout_cents, mark.amount))

        if mark.external_id and http_dir is not None:
            trace = find_checkout_trace(http_dir, str(mark.external_id))
            bodies = os.getenv("PORTO_LAB_HTTP_TRACE_BODIES", "").strip() == "1"
            if trace is None:
                if bodies:
                    checks.append(
                        {
                            "check": "http_checkout_trace",
                            "expected": f"shopOrderId={mark.external_id}",
                            "actual": None,
                            "ok": False,
                        }
                    )
            else:
                body = (trace.get("request") or {}).get("body") or {}
                positions = body.get("positions") or []
                position = positions[0] if positions else {}
                checks.append(row("http_product_code", int(wire_code), position.get("productCode")))
                checks.append(row("http_total_cents", checkout_cents, body.get("total")))
                checks.append(row("http_voucher_layout", voucher_layout, position.get("voucherLayout")))
                if voucher_layout == "FRANKING_ZONE":
                    checks.append(row("http_address_omitted", None, position.get("address")))
                else:
                    has_address = position.get("address") is not None
                    checks.append(row("http_address_present", True, has_address))

    ok = all(item["ok"] for item in checks)
    return {"ok": ok, "checks": checks}


def validation_failed_checks(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for item in payload.get("checks", []) if not item.get("ok")]


async def run_case(
    client: PortoClient,
    case: MatrixCase,
    *,
    dry_run: bool,
    out: Path,
    voucher_layout: str,
) -> CaseRunResult:
    case_dir = out / "cases" / case.case_id
    case_dir.mkdir(parents=True, exist_ok=True)

    provider = bound_provider(client)
    loader = provider._resolver.data_loader
    recipient = RECIPIENTS.get(case.country_code, RECIPIENTS["DE"])
    service_ids = list(case.service_ids) or None
    services = None
    if service_ids:
        services = []
        for service_id in service_ids:
            row = loader.get_service(service_id)
            if row is None:
                raise ValueError(f"Unknown service {service_id}")
            services.append(row.kind)

    resolved = provider.resolve(
        country_code=case.country_code,
        weight=case.weight,
        product_id=case.product_id,
        service_ids=service_ids,
        services=services,
    )
    wire_code = ExecutionBinding(loader).resolve_wire_code(
        wire="internetmarke",
        product_id=case.product_id,
        zone_id=case.zone_id,
        service_ids=list(case.service_ids) or None,
    )
    checkout_cents = estimate_checkout_cents(
        loader,
        product_id=case.product_id,
        zone_id=case.zone_id,
        weight_tier_id=case.weight_tier_id,
        service_ids=case.service_ids,
    )
    expected_layout = "ADDRESS_ZONE" if resolved.mark_type == "label" else "FRANKING_ZONE"

    request = PortoMarkRequest(
        porto=resolved,
        sender=SENDER,
        recipient=recipient,
        idempotency=f"lab-{case.case_id}-{datetime.now(UTC).strftime('%H%M%S')}",
    )
    prepared = await provider._prepare(request)
    sdk_input = {
        "case_id": case.case_id,
        "product_id": case.product_id,
        "zone_id": case.zone_id,
        "service_ids": list(case.service_ids),
        "wire_code": wire_code,
        "checkout_cents": checkout_cents,
        "voucher_layout": expected_layout,
        "weight": case.weight,
        "request": request.model_dump(mode="json"),
        "prepared": prepared.model_dump(mode="json"),
    }
    write_json(case_dir / "sdk_input.json", sdk_input)

    validation = strict_validate_case(
        case=case,
        loader=loader,
        resolved=resolved,
        wire_code=wire_code,
        checkout_cents=checkout_cents,
        prepared=prepared,
        voucher_layout=expected_layout,
        http_dir=out / "http",
    )
    write_json(case_dir / "validation.json", validation)

    if dry_run:
        write_json(
            case_dir / "sdk_output.json",
            {"dry_run": True, "wire_code": wire_code, "price_cents": resolved.amount},
        )
        return CaseRunResult(ok=validation["ok"], spend_cents=0)

    try:
        mark = await provider.mark(request, ExecutionParameters())
    except PortoError as exc:
        write_json(case_dir / "error.json", porto_error_payload(exc))
        insufficient = exc.code == PortoErrorCode.PORTO_WALLET_INSUFFICIENT
        return CaseRunResult(ok=False, insufficient_funds=insufficient)

    error_path = case_dir / "error.json"
    if error_path.exists():
        error_path.unlink()

    write_json(case_dir / "sdk_output.json", mark.model_dump(mode="json"))
    spend = mark.amount or resolved.amount

    validation = strict_validate_case(
        case=case,
        loader=loader,
        resolved=resolved,
        wire_code=wire_code,
        checkout_cents=checkout_cents,
        prepared=prepared,
        voucher_layout=expected_layout,
        mark=mark,
        http_dir=out / "http",
    )
    write_json(case_dir / "validation.json", validation)
    if not validation["ok"]:
        failed = validation_failed_checks(validation)
        write_json(
            case_dir / "error.json",
            {
                "error": "strict_validation_failed",
                "failed_checks": failed,
            },
        )
        return CaseRunResult(ok=False, spend_cents=spend)

    if mark.content and mark.content.startswith("http"):
        stamp_path = case_dir / "stamp.png"
        try:
            stamp_png = await provider.bytes(mark)
            stamp_path.parent.mkdir(parents=True, exist_ok=True)
            stamp_path.write_bytes(stamp_png)
        except PortoError as exc:
            validation["checks"].append(
                {
                    "id": "stamp_download",
                    "ok": False,
                    "detail": f"{exc.code.value}: {exc.message}",
                }
            )
            validation["ok"] = False
            write_json(case_dir / "validation.json", validation)
            failed = validation_failed_checks(validation)
            write_json(
                case_dir / "error.json",
                {
                    "error": "stamp_download_failed",
                    "failed_checks": failed,
                },
            )
            return CaseRunResult(ok=False, spend_cents=spend)

        from labs.lib.python.mark_measure.audit import verify_case_checks
        from labs.lib.python.mark_measure.calibrations import load_marks

        porto_data_root = loader._base_loader.data_path
        marks_doc = load_marks(porto_data_root, "deutschepost")
        graph_path = porto_data_root / "providers" / "deutschepost" / "graph.json"
        graph = json.loads(graph_path.read_text(encoding="utf-8"))
        mark_edges = (graph.get("edges") or {}).get("marks") or {}
        stamp_checks = verify_case_checks(
            case_dir,
            marks=marks_doc,
            mark_edges=mark_edges,
            default_profile_id=str(marks_doc.get("default_profile") or "") or None,
        )
        validation["checks"].extend(stamp_checks)
        validation["ok"] = all(item["ok"] for item in validation["checks"])
        write_json(case_dir / "validation.json", validation)
        if not validation["ok"]:
            failed = validation_failed_checks(validation)
            write_json(
                case_dir / "error.json",
                {
                    "error": "strict_validation_failed",
                    "failed_checks": failed,
                },
            )
            return CaseRunResult(ok=False, spend_cents=spend)

    wallet_balance = parse_wallet_balance_cents(mark.provider_raw)
    return CaseRunResult(ok=True, spend_cents=spend, wallet_balance_cents=wallet_balance)


async def main() -> int:
    parser = argparse.ArgumentParser(description="Internetmarke order matrix (Python)")
    parser.add_argument("--profile", default=os.getenv("PROFILE", "canary"))
    parser.add_argument("--dry-run", action="store_true", default=os.getenv("DRY_RUN") == "1")
    parser.add_argument("--max-cases", type=int, default=None)
    parser.add_argument(
        "--only-cases",
        default=os.getenv("ONLY_CASES"),
        help="Comma-separated case_id filter (retry subset)",
    )
    args = parser.parse_args()

    profile = load_profile(args.profile)
    dry_run = args.dry_run or not profile.get("purchases", True)
    voucher_layout = voucher_layout_for(args.profile)
    out = run_dir()
    out.mkdir(parents=True, exist_ok=True)

    client = build_client()
    loader = bound_provider(client)._resolver.data_loader
    max_cases = args.max_cases
    if max_cases is None and os.getenv("MAX_CASES"):
        max_cases = int(os.getenv("MAX_CASES", "0")) or None

    if args.only_cases:
        cases = build_cases(loader, args.profile, None)
        allowed = {item.strip() for item in args.only_cases.split(",") if item.strip()}
        cases = [case for case in cases if case.case_id in allowed]
    else:
        cases = build_cases(loader, args.profile, max_cases)
    print(f"Profile: {args.profile} | cases: {len(cases)} | dry_run: {dry_run} | voucher_layout: {voucher_layout}")

    preflight_ok = await run_preflight(client, out, dry_run=dry_run, cases=cases)
    if not preflight_ok and not dry_run:
        print("Preflight failed — see cases/_preflight/auth.json")
        write_json(
            out / "metadata.json",
            {
                "provider": "deutschepost",
                "integration": "internetmarke",
                "profile": args.profile,
                "voucher_layout": voucher_layout,
                "dry_run": dry_run,
                "sdk_language": "python",
                "cases_total": len(cases),
                "cases_passed": 0,
                "cases_failed": 0,
                "estimated_spend_cents": 0,
                "preflight_ok": False,
            },
        )
        return 1

    passed = 0
    failed = 0
    validation_failed = 0
    spend = 0
    wallet_balance_cents: int | None = None
    aborted_insufficient_funds = False
    validation_mismatches: list[dict[str, Any]] = []

    for index, case in enumerate(cases, start=1):
        print(f"[{index}/{len(cases)}] {case.case_id}")
        try:
            outcome = await run_case(
                client, case, dry_run=dry_run, out=out, voucher_layout=voucher_layout
            )
        except PortoError as exc:
            case_dir = out / "cases" / case.case_id
            case_dir.mkdir(parents=True, exist_ok=True)
            write_json(case_dir / "error.json", porto_error_payload(exc))
            outcome = CaseRunResult(
                ok=False,
                insufficient_funds=exc.code == PortoErrorCode.PORTO_WALLET_INSUFFICIENT,
            )
        except Exception as exc:  # noqa: BLE001
            case_dir = out / "cases" / case.case_id
            case_dir.mkdir(parents=True, exist_ok=True)
            write_json(case_dir / "error.json", {"error": str(exc), "type": type(exc).__name__})
            outcome = CaseRunResult(ok=False)

        spend += outcome.spend_cents
        if outcome.wallet_balance_cents is not None:
            wallet_balance_cents = outcome.wallet_balance_cents
        if outcome.ok:
            passed += 1
        else:
            failed += 1
            validation_path = out / "cases" / case.case_id / "validation.json"
            if validation_path.exists():
                payload = json.loads(validation_path.read_text(encoding="utf-8"))
                if not payload.get("ok"):
                    validation_failed += 1
                    validation_mismatches.append(
                        {
                            "case_id": case.case_id,
                            "failed_checks": validation_failed_checks(payload),
                        }
                    )
            if outcome.insufficient_funds:
                err_path = out / "cases" / case.case_id / "error.json"
                details: dict[str, Any] = {}
                if err_path.exists():
                    details = json.loads(err_path.read_text(encoding="utf-8")).get("details") or {}
                required = details.get("required_cents")
                wallet_account_id = details.get("wallet_account_id")
                print(
                    "Portokasse wallet empty — top up via Portokasse → Porto laden"
                    f"{f' (need €{required / 100:.2f}' if isinstance(required, int) else ''}"
                    f"{f', have €{wallet_balance_cents / 100:.2f}' if isinstance(wallet_balance_cents, int) else ''}"
                    f"{')' if isinstance(required, int) else ''}"
                    f"{f' [{wallet_account_id}]' if isinstance(wallet_account_id, str) else ''}"
                )
                aborted_insufficient_funds = True
                break

    write_json(
        out / "validation_summary.json",
        {
            "strict_checks": True,
            "cases_validation_failed": validation_failed,
            "mismatches": validation_mismatches,
        },
    )

    write_json(
        out / "metadata.json",
        {
            "provider": "deutschepost",
            "integration": "internetmarke",
            "profile": args.profile,
            "voucher_layout": voucher_layout,
            "dry_run": dry_run,
            "sdk_language": "python",
            "cases_total": len(cases),
            "cases_passed": passed,
            "cases_failed": failed,
            "cases_validation_failed": validation_failed,
            "estimated_spend_cents": spend,
            "wallet_balance_cents": wallet_balance_cents,
            "aborted_insufficient_funds": aborted_insufficient_funds,
            "preflight_ok": preflight_ok,
            "finished_at": datetime.now(UTC).isoformat(),
        },
    )

    if validation_mismatches:
        print(f"Validation mismatches: {len(validation_mismatches)}")
        for item in validation_mismatches[:5]:
            print(
                f"  - {item['case_id']}: "
                f"{[c.get('check') or c.get('id') for c in item['failed_checks']]}"
            )

    print(
        f"Done: passed={passed} failed={failed} validation_failed={validation_failed} "
        f"spend_cents={spend}"
        f"{f' wallet_balance_cents={wallet_balance_cents}' if wallet_balance_cents is not None else ''}"
        f"{' aborted_insufficient_funds' if aborted_insufficient_funds else ''}"
    )
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
