# Lab boundaries — CI vs manual vs paid API

Single source for what runs where in Porto SDK Lab. **porto-features** remains the scenario catalog; lab runs produce evidence only.

See porto-features [`docs/scenarios.md`](../../resources/porto-features/docs/scenarios.md) for tag glossary.

## Execution tiers

| Tier | Pays Portokasse? | Who runs it | Entry | In CI? |
|------|------------------|-------------|-------|--------|
| **SDK (`@sdk`)** | No | CI / any dev | SDK pytest/vitest BDD | Yes |
| **Dry-run** | No | CI or dev | `order_matrix` with `PROFILE=dry_run` or `DRY_RUN=1` | Optional smoke |
| **Adapter canary** | Yes (subset) | Lab cron / operator | `make labs-internetmarke-canary` | Never |
| **Preflight manual** | No* | Before canary/full | `example_portokasse_link_check`, `example_api_version_check` | Never |
| **Adapter full** | Yes (matrix) | Lab cron / operator | `make labs-internetmarke-full` | Never |
| **Calibration matrix** | Yes (~92) | Operator, manually | `make labs-internetmarke-calibration-matrix` | Never |
| **Stamp measure** | No | After paid matrix | `make labs-internetmarke-measure` | Never |
| **Interactive manual** | Yes (ad hoc) | Operator | paid matrix / preflight scripts | Never |
| **BDD `@adapters @canary`** | Yes | Lab only | porto-features + `matrix/canary.yaml` | Never |
| **BDD `@adapters @full`** | Yes | Lab only | porto-features + Lab `matrix/orders.generated.yaml` | Never |

\*Preflight may hit auth endpoints but does not purchase stamps.

Profiles are defined in [`labs/experiments/internetmarke/matrix_profiles.yaml`](../../labs/experiments/internetmarke/matrix_profiles.yaml).

## Layer roles

| Layer | Runs in CI | Costs money | Artifact home |
|-------|------------|-------------|---------------|
| SDK unit tests | Yes | No | none |
| SDK BDD `@sdk` | Yes (Py + TS) | No | none |
| **Lab scripts via observer** | No (lint only) | Optional | `labs/experiments/runs/<id>/` |
| **Lab Internetmarke matrix** | No | Yes | same + `cases/` + `http/` |

## Paid order matrix vs adapter Gherkin

| Artifact | Role | Paid? | Promotion |
|----------|------|-------|-----------|
| **`labs/experiments/internetmarke/order_matrix.{py,ts}`** | Imperative paid SoT — runs wire cells, writes artifacts | Yes | Source of truth for *whether* a cell is green |
| **`resources/porto-features/.../adapters/**/*.feature`** (`@adapters`) | Declarative promotion target — scenario outlines + Examples | Yes (when run in lab) | Add/refine only after lab evidence |
| **`matrix/orders.generated.yaml`** | Coverage index from porto-data wire (Lab SoT) | No (index only) | Lab attaches `evidence:` / `last_verified:` via `scripts/labs/promote-evidence.py` |

**Do not** treat adapter Gherkin as the paid execution source of truth. Lab matrix scripts decide execution order, spend gates, and artifact layout; porto-features adapter scenarios are promoted *from* green lab runs.

## Order matrix sync (porto-data → Lab `matrix/`)

When porto-data wire graph changes, regenerate adapter order index at Lab boundary:

```bash
make matrix-orders-sync          # write orders.generated.yaml + cases.generated.json
make matrix-orders-sync-check    # CI-style --check
```

## SDK matrix sync (Gherkin → Lab `matrix/`)

When `@sdk` scenarios are added or renamed, regenerate the SDK coverage index:

```bash
make matrix-sdk-sync             # write sdk.yaml
make matrix-sdk-sync-check       # CI-style --check
```

Both generators:

```bash
make matrix-sync
make matrix-sync-check
```

Shared library: `labs/lib/python/matrix/` (`zone_lookup`, `wire_registry`, `sdk_sync`, `orders_sync`, `scenario_scope.yaml`). Language-paired helpers (HTTP trace, auth diagnostics, env load) live under `labs/lib/{python,typescript}/`.

Lab runs attach `evidence:` on existing `case_id`s — they never define the order list.

Promote green cases after a paid run:

```bash
python scripts/labs/promote-evidence.py <run_id>          # write evidence + last_verified
python scripts/labs/promote-evidence.py <run_id> --dry-run
```

## Lab → porto-features promotion

1. Run paid experiments in lab (canary → full) with full artifacts.
2. Analyze failures, wire codes, auth errors under `labs/experiments/runs/<run_id>/`.
3. Refine Gherkin in `resources/porto-features` only for scenarios you have evidence for.
4. SDK CI consumes published/local porto-features; lab does **not** duplicate scenario definitions.

**Promotion checklist:**

- Lab `case_id` green on both Py + TS → candidate for porto-features scenario outline
- Capture expected `wire_code`, price band, error codes in scenario Examples table
- Tag `@adapters @canary` or `@adapters @full` only after lab artifact attached to PR description (link to run dir)

## Credentials

One place: repo root `.env` (see [`.env.example`](../../.env.example)). Docker lab services load it via `docker-compose.labs.yml` `env_file`.

## Paid API policy

Use `make labs-internetmarke-*` for paid provider matrix runs (manual only).
- Free Portokasse test balance does **not** authorize CI or scheduled full-matrix runs.
- Only scenarios that survived a **manual lab run** with artifacts get promoted to porto-features `@adapters`.
