# Porto Stack Architecture

Canonical architecture for the Porto postal stack. Describes **implemented** ownership and dependency direction.

## Codegen and types

| Concern | Source of truth | SDK handling |
| --- | --- | --- |
| Domain types (`Porto`, `Address`, …) | porto-data schemas + hand-written models | Pydantic / Zod in SDK repos; parity via BDD |
| Public error codes (`PORTO_*`) | `porto-features/errors.json` | Generated into both SDKs via `make sync-bindings`; drift check via `make bindings` |

Domain types are **not** generated from JSON Schema. Error string values are the only generated enum path.

## Layer stack

```text
porto-data          postal facts, schemas, validators (published JSON)
    ↓
porto-features      behavioral Gherkin contracts, fixtures
    ↓
Porto SDK Py/TS     resolution, validation, pricing, adapter execution
    ↓
Porto SDK Lab       paid validation, evidence, matrix indexes (matrix/)
```

**Rule:** dependency flows downward only. Upper layers never import implementation from lower product layers (SDK does not own Gherkin; Lab does not own business rules).

## Ownership

| Concern | Owner |
|---------|--------|
| Postal facts (products, zones, prices, wire codes) | **porto-data** |
| SDK execution manifest (`execution.json`, capabilities) | **porto-data** (published fact) |
| Behavioral contracts (Gherkin) | **porto-features** |
| Step vocabulary | **porto-features** `docs/vocabulary.md` |
| Step definitions | **SDK Python + TypeScript** (`tests/steps/`) |
| Resolution / pricing / validation logic | **SDK services** |
| Wire order obligation list | **porto-data** `graph.edges.wire` → generated `orders.generated.yaml` |
| Coverage index (`sdk.yaml`, `canary.yaml`) | **Lab** `matrix/` (generated or hand-curated index only) |
| Paid execution + artifacts | **Lab** `labs/experiments/runs/` |

## Identifier taxonomy

See [porto-data/docs/identity.md](../resources/porto-data/docs/identity.md).

- **`kind` (`ServiceKind` / `FeatureKind`)** — cross-provider intent grouping (not purchasable identity)
- **catalog `id` / `product_id` / `service_ids`** — provider-scoped keys in graph, prices, rules
- **`envelope_id`** — physical fit filter on resolve / options
- **`wire_code`** — adapter payload values in `graph.edges.wire` only
- **`provider`** — implied by `providers/<id>/` path (not repeated on JSON rows)
- **`execution` / `wire`** — wire channel id in `execution.json`
- **`case_id` / `cell_id`** — matrix slugs for coverage and artifact paths (not parsed in product runtime)

## Resolution pipeline

Single orchestrated path in both SDKs:

```text
restriction → zone → weight_tier → product → service compatibility → price → execution metadata
```

- Data-driven via porto-data graph + resolution index
- **No silent fallback** — unsupported routes raise typed `PortoErrorCode`
- Generic `services/` and `services/resolution/` layers must not contain provider name literals (enforced by unit tests)

## porto-features layout

```text
features/sdk/core/           @sdk @core
features/sdk/providers/<id>/ @sdk @provider:<id>
features/adapters/<id>/      @adapters @provider:<id> @wire:<adapter>
matrix/sdk.yaml              SDK coverage index (Lab scripts/matrix-sdk-sync.py)
matrix/orders.generated.yaml Wire cells from porto-data (Lab scripts/matrix-orders-sync.py)
matrix/canary.yaml           Daily paid smoke case_ids
```

Adapter `stamp_order` outline Examples are **generated** from wire cells (`product_id`, `zone_id`, `service_ids`) — not hand-maintained `porto_id` buckets.

## Python / TypeScript parity policy

- Same canonical `.feature` files from porto-features
- Step definitions live only in SDK repos — thin wrappers over public API
- `scripts/parity-report.py` → `docs/sdks/parity.md`
- Breaking 0.x: prefer fixing architecture over preserving weak abstractions

## Provider adapter boundary

- SDK resolves wire via **porto-data `execution.json` `wire` field** + credentials — not `if provider == "deutschepost"` in generic code
- Missing credentials → `UnavailableExecutionAdapter` (`FEATURE_NOT_SUPPORTED`)
- Provider-specific code only under `adapters/<id>/`

## Matrix role

Matrix YAML is a **coverage index** — pointers to Gherkin and wire cells. It must not duplicate scenario text or independent business outcomes.

| File | Maintainer |
|------|------------|
| `orders.generated.yaml` | Generated from porto-data wire |
| `cases.generated.json` | Generated alongside orders (TS lab parity) |
| `sdk.yaml` | Generated from `@sdk` Gherkin via Lab `matrix-sdk-sync.py` |
| `canary.yaml` | Hand-curated ⊆ orders |

Drift check: `make matrix-sync-check` (CI in Lab + porto-features).

## Live test safety

| Tier | Pays? | CI? |
|------|-------|-----|
| `@sdk` BDD | No | Yes (both SDKs) |
| Lab `order_matrix` dry_run | No | Optional |
| Lab canary/full | Yes | **Never** |
| SDK `make heavy` / lab `labs-internetmarke-*` | Yes | Manual only |

Paid SoT: imperative `order_matrix` (Py + TS). `@adapters` Gherkin is the **promotion target** after evidence (`scripts/labs/promote-evidence.py`).

## Breaking-change policy (0.x)

- Fix structural mistakes now: identifier conflation, duplicated matrix tables, provider defaults in generic layers
- Document migrations in package CHANGELOGs
- Do not add speculative multi-provider frameworks without a shipped adapter

## Related docs

- [sdks/patterns.md](sdks/patterns.md)
- [labs/boundaries.md](labs/boundaries.md)
- [porto-features/docs/scenarios.md](../resources/porto-features/docs/scenarios.md)
- [porto-features/docs/vocabulary.md](../resources/porto-features/docs/vocabulary.md)
- [sdks/runtime.md](sdks/runtime.md)
