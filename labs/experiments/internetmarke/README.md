# Internetmarke order matrix (lab experiments)

Graph-driven Internetmarke ordering with artifact capture.

## Commit policy (sensitive)

**Do commit** (source only): this README, `order_matrix.py` / `order_matrix.ts`, `matrix_profiles.yaml`.

**Never commit** (local evidence — may include credentials, HTTP hops, stamps, addresses):

- `labs/experiments/runs/**` (observer run dirs)
- `labs/experiments/latest` (symlink)
- `labs/**/artifacts/**` (matrix case JSON, `stamp.png`, auth dumps)
- root `.env` / `test_credentials.env`

These paths are gitignored. `make check-gitignore` and a pre-commit hook fail if they become tracked. Paid runs stay on your machine; promote green `case_id` values into porto-features Examples only — not raw run trees.

## Quick start

```bash
# From repo root — requires Docker + root .env credentials
cp .env.example .env   # fill PORTO_DEUTSCHEPOST_INTERNETMARKE_*

make labs-internetmarke-canary   # 1 case, Py then TS (costs money)
make labs-internetmarke-full     # full graph matrix (costs money)
make labs-internetmarke-py PROFILE=dry_run   # resolve + wire only, no purchase
make labs-internetmarke-ts PROFILE=canary
```

Preflight (no purchase — run while waiting for DHL app approval):

```bash
make labs-internetmarke-preflight          # API reachability + auth classification
make labs-internetmarke-gate-check         # two gates only (DHL app + Portokasse user)
```

After DHL approves your developer app:

```bash
make labs-internetmarke-gate-check         # step 1 — confirm both gates (no charge)
make labs-internetmarke-post-approval      # gate check → canary purchase if ready
```

Gate 2 failure means the Portokasse user has not authorized your app under **Geschäftsanwendungen** — the matrix stops before any purchase.

```bash
make labs-run-py SCRIPT=example_portokasse_link_check.py
make labs-run-py SCRIPT=example_api_version_check.py
make labs-run-ts SCRIPT=example_portokasse_link_check.ts
```

### Auth status reference

Public SDK contract is always a `PORTO_*` code. Lab `status` values below are
**adapter diagnostics** (`diagnostic_reason`), not public error codes. Original
provider payloads (e.g. `ERR_1000`, unknown channel text) are preserved under
`details.provider_error` on the Porto error.

| Lab `status` (diagnostic) | Porto code | Meaning |
|---------------------------|------------|---------|
| `unknown_channel` / `invalid_app_credentials` | `PORTO_AUTH_DENIED` or `PORTO_AUTH_FAILED` | DHL developer app/channel rejected |
| `pending_portokasse_approval` | `PORTO_LINKAGE_PENDING` | App token path OK conceptually; Portokasse Freigabe missing |
| `invalid_portokasse_credentials` | `PORTO_AUTH_FAILED` | Wrong Portokasse username/password |
| `connected` | — | Both gates OK |

Direction is always **adapter mapper → PORTO_* → Lab**. Lab never invents Porto codes from provider body text.

Exit codes: `0` = ready, `1` = blocked (waiting on approval / unknown channel), `2` = config/API error.

Dry-run matrix (resolve + wire only, no auth probe):

```bash
make labs-internetmarke-py PROFILE=dry_run
```

## Profiles

See [`matrix_profiles.yaml`](./matrix_profiles.yaml):

| Profile | Layout | Purchases | Cases |
|---------|--------|-----------|-------|
| `canary` | `ADDRESS_ZONE` | Yes | 1 (first graph case) |
| `full` | `ADDRESS_ZONE` | Yes | 46 (base + Einschreiben variants) |
| `franking_canary` | `FRANKING_ZONE` | Yes | 4 |
| `franking_full` | `FRANKING_ZONE` | Yes | 46 |
| `dry_run` | `ADDRESS_ZONE` | No | 46, resolve + wire only |

Override: `MAX_CASES=3`, `DRY_RUN=1`, `PROFILE=full`, `VOUCHER_LAYOUT=FRANKING_ZONE`.

### Calibration workflow (porto-data `marks.calibrations[]`)

```bash
make labs-internetmarke-gate-check          # no purchase
make labs-internetmarke-calibration-matrix  # paid: full + franking_full (~€602)
make labs-internetmarke-measure             # measure stamp.png vs porto-data
```

Or one chain: `make labs-internetmarke-calibration`.

Measure library: `python -m labs.lib.python.mark_measure verify --run-dir labs/experiments/runs/<id>`.
Writes `calibration_report.json` and `calibration_summary.json` per run.

## Run directory layout

Observer sets `OBSERVER_RUN_DIR` → `labs/experiments/runs/<run_id>/`:

```text
summary.json          # observer + merged metadata fields
metadata.json         # matrix profile, case counts, spend estimate
process.jsonl
stdout.log / stderr.log
cases/
  _preflight/auth.json
  deutschepost.internetmarke.standardbrief.domestic/
    sdk_input.json
    sdk_output.json
    stamp.png           # on success (extracted from DHL ZIP document link)
    validation.json     # strict price/wire/layout + stamp dimension checks
    error.json          # on PortoError
http/                   # when PORTO_LAB_HTTP_TRACE=1
  001_auth_user.json
  002_cart_init.json
  003_cart_checkout.json
```

Enable HTTP trace: `PORTO_LAB_HTTP_TRACE=1` (set automatically by `make labs-internetmarke-*`). Lab writes hops via an injected tracing transport, not an SDK observer API.

## Analyze a run

1. Open `labs/experiments/latest` (symlink to last run) or pick a run id under `runs/`.
2. Read `summary.json` for exit status and `cases_passed` / `cases_failed`.
3. For failures, open `cases/<case_id>/error.json` — stable `code` + upstream `details`.
4. For checkout issues, compare `cases/<case_id>/sdk_input.json` `wire_code` with `http/*_cart_checkout.json` `productCode`.
5. For mark geometry, read `calibration_report.json` or run `make labs-internetmarke-measure`.
6. Use green `case_id` values when proposing porto-features Examples (see [`docs/labs/boundaries.md`](../../docs/labs/boundaries.md)).

## Per-case flow (0.5.0)

1. `resolver.resolve(...)` → product + price  
2. `resolver.resolve_wire_code(integration=internetmarke, ...)` → wire code from `graph.edges.wire`  
3. `stamps.prepare_mark_order` → `PreparedMarkOrder`  
4. `stamps.post_mark` → `PortoMark` (skipped when `dry_run`)

Case IDs: `{provider}.{adapter}.{product_id}.{zone_id}` (e.g. `deutschepost.internetmarke.standardbrief.domestic`).

## Scripts

| File | Runtime |
|------|---------|
| `order_matrix.py` | Python (via `experiment-py.sh`) |
| `order_matrix.ts` | TypeScript (via `experiment-ts.sh`) |

Paid execution uses `make labs-internetmarke-*` — lab-only, never CI.
