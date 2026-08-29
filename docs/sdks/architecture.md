# Porto SDK Architecture

Unified architecture for both SDKs (Python `gruncellka-porto-sdk`, TypeScript `@gruncellka/porto-sdk`). Public API SoT: [public.md](public.md). Resolution detail: [resolution.md](resolution.md).

---

## 1. Core Principle

The SDK is a stable client layer over domain operations, not a collection of helpers. It exposes a **provider-agnostic** API; resolution is data-driven via porto-data and the resolution graph.

> **Invariant:** No service is allowed to combine loader data into a business decision outside resolution primitives.

### Porto (resolved decision) vs PortoMark (execution result)

| Concept | Role |
|--------|------|
| **Porto** — resolved postal decision | Answers *what* should be mailed: catalog `product_id`, zone, weight tier, composed `amount` / `currency` / `components`, selected `services` / `service_ids`, and **execution semantics from porto-data**: `mark_type` (`stamp` \| `label`), tracking (`none` \| `optional` \| `included`), plus `restrictions` (data facts). Populated by `ProviderClient.resolve` / internal `PortoResolver` **before** adapter calls. |
| **PortoMark** | Answers *what the provider returned*: printable `content`, optional `tracking_number`, `external_id`, `format`, plus `provider_raw` for debugging. `PortoMark.type` aligns with `mark_type` from data — adapters map responses; they do not guess stamp vs label from provider name alone. `PortoMark.id` is an SDK execution-result identifier (`{provider}:{external_id}` when the provider returns a stable ref, otherwise a locally generated UUID) — **not** a billing id and not a substitute for application order ids. |

**Identity:** `Porto` is the frozen execution identity. Public `ProviderClient.mark` takes `PortoMarkRequest(porto=…)` and must not re-resolve from envelope/product + weight. Evidence: [public.md](public.md). Cardinality (one vs many items; adapter-owned carts): [gaps.md](gaps.md). Internal prep path: `prepare` → `MarkExecution` → adapter.

**Idempotency (passthrough only):** `ExecutionParameters` carries an optional `idempotency_key` / `idempotencyKey`. The SDK merges it onto the provider request when supported; it **does not** persist keys, **does not** implement a deduplication store, and **does not** own payment or retry policy — the application does.

**Explicitly out of scope (SDK):** who pays, invoices/VAT, job queues, execution ledger persistence, credential storage policy. **Wallet read** is in scope via `provider.wallet` when capabilities declare wallet support (prepaid model only). See [gaps.md](gaps.md).

---

## 2. Strategic Four-Layer Model

| Layer        | Role                    | Examples                                                                                  |
| ------------ | ----------------------- | ----------------------------------------------------------------------------------------- |
| **porto-data** | Truth                   | Products, zones, prices, services, features, resolution graph, restrictions               |
| **resolver**   | Logic                  | Restriction → zone → weight tier → product (+ services) → price                           |
| **adapter**    | Execution (online only) | InternetmarkeAdapter, DataFactoryAdapter                                                 |
| **cli**        | Interface              | Argument parsing, config, output                                                          |

**Core moat:** user intent → resolution primitives → catalog `product_id` + services → price. One pipeline for all providers; provider differences come from data, not code branches.

---

## 3. Fixed Baselines

- Python: `3.13`
- TypeScript: `5.9.x`
- Node: `>=20`

Lab framework versions do not redefine them.

---

## 4. Public surface

**Freeze SoT:** [public.md](public.md). Narrative: [api.md](api.md).

Apps call **`PortoClient`** catalogs and **`client.provider(id)` → `ProviderClient`**. No `client.data`, no public `dataLoader`, no raw porto-data paths.

| Entry point | Role |
| ----------- | ---- |
| `client.provider(id)` | Bound verbs: `resolve` / `options` / `price` / `mark` / `track` / `capabilities` / `can` / `wallet` |
| `client.envelopes` | Catalog: `list()`, `geometry()`, `layout()`, `identify()`, `getMark()` |
| `client.restrictions` | Destination restriction facts (`check`) |
| `client.providers` | Operator registry projection |
| `client.jurisdictions` | Jurisdiction / country helpers |
| `client.address` | Address validation |
| `client.config` | Input `PortoConfig` |

**Not public (0.0.1 freeze):** `client.registered`, `ProviderClient.resolver`, `advise` / `prepare` / `bytes`, `estimate`. Internal: `PortoResolver`, `PortoExecution`, `MarkExecution`, `PortoDataLoader`.

**Naming:** Envelope access is `client.envelopes`. Prefer one-word **public types** (`Envelope`, `Porto`, `Product`) per [public.md](public.md).

---

## 5. Resolution Pipeline

Resolution order (see [resolution.md](resolution.md) for full detail):

1. **Restrictions** — country → restriction facts (data; `resolve` does not fail closed)
2. **Zone** — country_code → zone_id
3. **Weight tier** — weight → weight_tier_id
4. **Envelope filter** — optional `envelope_id` drops incompatible products (does not select among leftovers)
5. **Product** — graph ∩ zone ∩ weight tier (+ optional `product_id` pin); ambiguity → `options()` or `PORTO_PRODUCT_AMBIGUOUS`
6. **Services** — `services` (`ServiceKind[]` intent) + optional `service_ids` pins among catalog options
7. **Price** — product_id + zone + weight_tier (+ bound services) → composed amount

**Invariant:** No product or price resolution via direct loader access for “which product/price for this shipment.” All flows through resolution primitives or `PortoResolver`.

**Identity:** Catalog **`product_id`**, **`envelope_id`**, **`services` / `service_ids`**. Cross-provider grouping for services/features uses `kind` (`ServiceKind` / `FeatureKind`) — not a letter size-bucket enum.

**After product selection:** **`Porto`** includes execution semantics — **`mark_type`** / **`markType`** and tracking mode — plus `restrictions`. Provider calls return **`PortoMark`**. See **Porto vs PortoMark** above and [resolution.md](resolution.md).

---

## 6. Data Layer (Pure Access Only)

Lives in `data/loader` only. No orchestration, product selection, or business validation.

| Method                                                  | Purpose                    |
| ------------------------------------------------------- | -------------------------- |
| `get_product(product_id)`                               | Single product lookup      |
| `get_zone(zone_id)`                                     | Single zone lookup         |
| `get_zone_by_country_code(country_code)`                | Zone from country          |
| `get_price_by_product_zone_weight_tier(...)`            | Price lookup               |
| `get_service_price(service_id, zone_id?)`                | Catalog service fee (zoned rows require `zone_id`) |
| Restriction entity reads                                | Legal / routing rows       |

### 6.1 How porto-data enters the SDK (dual runtime)

| SDK | Runtime entry | Mechanism |
|-----|---------------|-----------|
| **Python** | `PortoConfig.data_path` | Read JSON from disk (or package discovery) |
| **TypeScript (Node)** | `@gruncellka/porto-sdk` | Same — filesystem loader |
| **TypeScript (browser)** | `@gruncellka/porto-sdk/browser` | `embeddedFiles` / `PortoDataLoader.fromEmbedded()` — catalog JSON embedded at **SDK build time** |

Entity processing and subservices are identical; only the **transport** into the loader differs. Apps never import porto-data JSON. See **[runtime.md](runtime.md)**.

---

## 7. Target Project Shape

### Python

```
porto_sdk/
├── client.py, provider_client.py, config.py, execution.py, kinds.py
├── data/                  # Pure access
│   ├── loader.py, base_loader.py, context.py
│   ├── porto_data_loader.py, porto_data_registry.py
│   └── entities/
├── services/
│   ├── porto_resolver.py
│   ├── porto_execution.py
│   ├── product_options.py, pricing.py
│   ├── envelope_resolver.py, address.py
│   ├── restrictions/, jurisdictions.py
│   ├── provider_capabilities.py, providers/
│   └── resolution/       # Primitives
│       ├── types.py, price_resolver.py, product_resolver.py
│       ├── weight_tier_resolver.py, zone_resolver.py
│       ├── restriction_resolver.py, feature_resolver.py
│       ├── dimension_resolver.py, service_resolver.py
│       └── __init__.py
├── adapters/
│   ├── deutschepost/internetmarke/
│   └── …
└── transport/
```

### TypeScript

```
src/
├── client.ts, provider-client.ts, config.ts, types/, execution/
├── data/
│   ├── loader.ts, porto-data-loader.ts, context.ts
│   └── entities/
├── services/
│   ├── porto-resolver.ts
│   ├── porto-execution.ts
│   ├── product-options.ts, pricing.ts
│   ├── envelope-resolver.ts, address.ts
│   ├── restrictions/, jurisdictions.ts
│   ├── provider-capabilities.ts, providers.ts
│   └── resolution/
│       ├── types.ts, price-resolver.ts, product-resolver.ts
│       ├── weight-tier-resolver.ts, zone-resolver.ts
│       ├── restriction-resolver.ts, feature-resolver.ts
│       ├── dimension-resolver.ts, service-resolver.ts
│       └── index.ts
├── adapters/
│   ├── deutschepost/internetmarke/
│   └── …
└── transport/
```

---

## 8. CLI Separated from SDK

CLI is a **thin shell** over the SDK. It must **call** the SDK and must **not duplicate** business logic.

| CLI responsibility  | Description                                            |
| ------------------- | ------------------------------------------------------ |
| Parse args          | Flags (`--country`, `--weight`, `--product`, etc.)     |
| Resolve config      | env + `~/.porto/config.json` + flags → `PortoConfig`    |
| Store credentials   | `auth login` writes to config store                    |
| Dispatch commands   | Bound `provider.resolve` / `options` / `price` / `mark` |
| Format output      | JSON or human-readable                                 |

CLI does **not** do: price calculation, product resolution, zone lookup, HTTP calls, auth token handling, business validation.

---

## 9. Auth (Two-Level Model)

| Level       | Source               | Type                 | Scope                    |
| ----------- | -------------------- | -------------------- | ------------------------ |
| **Level 1** | DHL Developer Portal | API key + API secret | Integrator app           |
| **Level 2** | Customer Portokasse  | username + password  | Per tenant (BYO)         |

Auth lives **inside adapters**, not CLI. Config flows: env → `~/.porto/config.json` → `PortoConfig` → adapters. See [auth.md](auth.md).

---

## 10. Adapters (Connector Rules)

Adapters are the **API integration layer** only. They:

- Build request, send request, return response
- Own auth (tokens, headers)
- Map provider errors to `PortoError`

Adapters **must not** contain:

- Pricing logic
- Product selection
- Zone resolution
- Business-rule decisions

**Contract:** Adapter receives **fully resolved input** (resolved product on `MarkExecution`). It does not call ProductResolver, PriceResolver, or zone lookup. `PortoExecution` prepares first, then passes resolved product to the adapter. **Execution methods return `PortoMark`** — a normalized cross-provider execution result; provider-specific payloads may appear under `provider_raw`.

---

## 11. Provider registry (`client.providers`)

| Method | Role |
|--------|------|
| `list()` | Operators from `providers.json` |
| Capability reads | Feature / wallet / mark gates via `ProviderClient.capabilities` / `can` |

**Single source of truth:** Resolution **graph** defines product × zone × weight validity. `providers` is a **read projection** over `features.json`, `services.json`, and graph — **not a second policy engine**. When graph and feature flags disagree, graph wins for resolution.

---

## 12. Error Normalization

Adapters normalize provider HTTP bodies to unified `PortoErrorCode` values. Public consumers branch on `error.code` — not provider names or raw `title` fields.

| Unified `code` | Typical cause |
|----------------|---------------|
| `POSTAGE_WALLET_INSUFFICIENT` | Prepaid wallet too low |
| `PROVIDER_AUTH_FAILED` | Customer credentials rejected |
| `PROVIDER_LINKAGE_PENDING` | Integrator app not approved (Freigabe) |
| `PROVIDER_AUTH_DENIED` | Integrator app/key rejected |
| `PORTO_CAPABILITY_UNSUPPORTED` | Capability absent from integration manifest |

`PortoError` fields: `code` (primary), `upstream_code` (provider token), `provider` / `integration` (context), `details` (structured extras).

Stable hierarchy: `PortoError`, `ValidationError`, `AuthenticationError`, `TransportError`, `ProviderError`, `ConfigurationError`, `DataError`. Adapter-internal mappers live under `adapters/<provider>/`.

---

## 13. Data-Driven Values Rule

Do not hardcode enums for values that come from porto-data. Products, dimensions, weight tiers, zones, service availability must be dynamically resolved. Static SDK enums only for protocol / vocabulary constants (`ServiceKind`, `FeatureKind`, `MarkType`, …).

---

## 14. Multi-Provider Rule

**One resolver architecture**, not per-provider forks. Provider differences come from provider datasets and resolution graph, not `if provider == ...` branches. Output is always provider-native catalog ids (`product_id`, zone, weight_tier, price).

---

## 15. Offline and Validation

Offline mode supports: zone resolution, product resolution, price calculation, service availability, restrictions lookup.

Validation before provider calls: request shape, business invariants, local data availability.

---

## 16. Runtime Dependency Rule

SDK consumes published `porto-data` and `porto-features` packages. No local Lab `resources/` paths at production runtime.

**Two layers:** (1) **manifest semver** — version contract in `package.json` / `pyproject.toml`; (2) **runtime instance** — `data_path` / `PORTO_DATA_PATH` or installed package default. Auto-discovery when unset is dev/deploy convenience, not the primary integrator contract. Hub: [dependency.md](dependency.md).

**Committed manifests:** `package.json`, `pyproject.toml`, and `pnpm-lock.yaml` use registry semver only. Lab development overlays installed packages from outside the SDK (Lab `make lab`) — never committed `file:` specs. Enforced by each SDK’s `make registry` (pre-commit, CI).

---

## 17. Cross-SDK Consistency

Must match: method names and API intent, request/response semantics, error codes, offline/online boundaries, domain concept naming.

May differ: `snake_case` vs `camelCase`, class vs function preference, internal file layout, **TypeScript `/browser` embed vs Python `data_path`** (same semantics — see [runtime.md](runtime.md)).

---

## 18. Optional and Out-of-Scope

- **Optional:** Cache only when justified
- **Out of scope:** Plugin system, event bus, factory-of-factories

---

## 19. Testing and Release Gates

- Shared BDD from `porto-features`
- Unit + integration tests per SDK
- Both SDKs must pass for release
- SDK CI (`validation.yml`): `registry`, lint, types, `test-cov`, `sdk`, `adapters`, build → aggregator `validate`
- Publish is per SDK (`validation` → version → `artifact` ∥ mandatory `heavy` → registry → GitHub Release). Lab does not publish SDK packages.

---

## See Also

| Doc | Purpose |
|-----|---------|
| [public.md](public.md) | **Public freeze** — types, verbs, errors |
| [api.md](api.md) | Public contract narrative |
| [runtime.md](runtime.md) | TS `/browser` embed vs PY `data_path`; drift avoidance |
| [dependency.md](dependency.md) | Manifest vs `data_path` vs Lab dev shortcuts |
| [resolution.md](resolution.md) | Resolution graph, primitives, product/service identity |
| [gaps.md](gaps.md) | Known leftovers (including execute cardinality) |
| [auth.md](auth.md) | Auth details |
| [patterns.md](patterns.md) | Industry alignment, pre-1.0 gaps, enforcement checklist |
| [framework.md](../labs/framework.md) | Lab framework |
