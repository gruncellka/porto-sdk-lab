# Porto SDK — public API (canonical)

**Purpose:** Narrative for the **platform-agnostic** Porto SDK public surface — catalogs, provider verbs, envelope matching, stability rules, and open-source release gates.

**Audience:** SDK contributors, external adopters, and product integrators that consume the published packages via a thin adapter.

**Public API reference:** [public.md](public.md) wins when this narrative disagrees. Layers: [architecture.md](architecture.md). Identity: [public.md](public.md).

**See also:**

| Doc | Role |
|-----|------|
| [public.md](public.md) | Public API types, verbs, errors |
| [runtime.md](runtime.md) | TS `/` vs `/browser`, Python `data_path`, parity |
| [dependency.md](dependency.md) | Manifest vs config vs discovery for porto-data / porto-features |
| [architecture.md](architecture.md) | Layers, resolution pipeline, adapters |
| [resolution.md](resolution.md) | Graph, primitives, product/service identity |
| [gaps.md](gaps.md) | Known leftovers (including execute cardinality) |

---

## 1. Doc hierarchy

```text
porto-data (schemas, JSON)     →  truth in data repo CI
public.md              →  public API allow-list
api.md (this doc)              →  stable surface narrative
architecture.md                →  internal layers and invariants
Licko porto-sdk.md             →  integration overlay only (vend, HTTP, lib/postal)
```

Product integrators **must not** treat Licko integration docs as the SDK spec. When they diverge, **`public.md` then this doc** win for public surface; **`architecture.md`** wins for layering.

---

## 2. PortoClient + ProviderClient

Apps call **`PortoClient` catalogs** and **`client.provider(id)` → `ProviderClient`**. No `client.data`, no public `dataLoader`, no raw porto-data paths.

**Public API tree:** [public.md](public.md). There is no `client.registered` — registered mail is `resolve(..., services=["registered"], service_ids=...)` then `price` / `mark` / `track`.

### 2.1 Catalogs on `PortoClient`

| Subservice | Role |
|------------|------|
| `envelopes` | Envelope catalog, geometry, layout join, identify |
| `restrictions` | Destination restriction facts (`check`) |
| `providers` | Operator registry projection |
| `jurisdictions` | Country / jurisdiction helpers |
| `address` | Address validation |
| `config` | Input `PortoConfig` |

### 2.2 `ProviderClient` verbs

| Verb | Role |
|------|------|
| `options` | Product candidates for country + weight (+ optional envelope) |
| `resolve` | Intent → frozen `Porto` |
| `price` | Same selection → catalog `Pricing` (optional; not execution identity) |
| `mark` | `PortoMarkRequest` → `PortoMark` (one or many) |
| `track` | Tracking when capability allows |
| `capabilities` / `can` | Feature / execution gates (`FeatureKind` for `can`) |
| `wallet` | Prepaid balance read when supported |

**Not public:** `estimate`, `advise`, `prepare`, `bytes`, `ProviderClient.resolver`.

**Flow:**

```text
options(country_code, weight, envelope_id)
  → consumer chooses product_id
  → resolve(… + product_id + services + service_ids?)
  → Porto
  → mark(PortoMarkRequest(porto=…), ExecutionParameters(credentials=…))
  → PortoMark
```

---

## 3. Providers projection

| Surface | Role |
|---------|------|
| `client.providers` | `list()` and related reads over `providers.json` |
| `provider.capabilities` / `can` | Bound capability facts |

**Rules:**

- **Resolution graph** = single source of truth for product × zone × weight validity.
- **`providers`** = thin **read projection** — **never a second policy engine**.
- When graph and features disagree, **graph wins** for resolution.

---

## 4. `client.envelopes`

`layout()` is a **join of independent facts**. Uniting two axes is not a dependency. Absence is omission — never a fallback CC, never a copied window, never a fake normative object.

```text
Envelope face
+ optional jurisdiction window
+ optional provider mark facts
= Layout facts
```

| Method | Role |
|--------|------|
| `identify(input)` | Dimensions/format → envelope identity + candidate product ids |
| `list()` | Global faces from `envelopes.json` only |
| `geometry(envelope_id, jurisdiction?)` | Face mm + optional window rectangle |
| `layout(envelope_id, jurisdiction?, product_id?, …)` | Face + optional `window` + optional `mark` |
| `getMark(product_id?, …)` | Mark facts: `type`, `size`, and `placement` when available |

Public envelopes operations (freeze): `list` / `geometry` / `layout` / `identify` / `getMark`. Not public: `match`, `resolve`, `validateForProduct`.

Catalog homes: `envelopes.json` face, `layouts.json` window, `marks.json` type/size/placement.

`PortoConfig` has no default provider. `client.provider(id)` always takes an explicit id.

**Internal only:** match policy, format catalog, normalizer — not a second public API.

---

## 5. `Match` — structured facts, not prose

Where match structures are used internally / in envelope tooling, the SDK returns **structured facts**. Applications own user-visible copy (i18n).

```typescript
type AdvisoryReason =
  | "dimensions_close"
  | "regional_format"
  | "unlisted_supply"
  | "ambiguous_dimensions"

type Match =
  | { kind: "strict_match"; envelopeId: string; advisoryOnly: false }
  | {
      kind: "advisory_match"
      envelopeId: string
      closestAllowedId: string
      score: number
      advisoryOnly: true
      reason: AdvisoryReason
      toleranceMm?: number
    }
  | { kind: "no_match"; reason?: "not_in_product_list" | "beyond_tolerance" | "unknown_envelope" }
```

**Invariant:** Advisory geometry **never** upgrades to `strict_match` unless `envelope_id ∈ products.envelope_ids`.

See [public.md](public.md) for algorithms.

---

## 6. Loader boundary (non-negotiable)

| Rule | Detail |
|------|--------|
| Loader is **internal** | Not on public `PortoClient` type; not in package root exports |
| Tests | Use test harness / `@internal` factory — not `client.dataLoader` in app code |
| Public reads | Only via catalogs and `ProviderClient` verbs above |
| Orchestration methods on loader | **Internal** — price/product shortcuts not on public loader type |

---

## 7. Errors

Public methods throw **`PortoError`** with stable **`PortoErrorCode`** — not raw `Error` strings.

| Code (examples) | When |
|-----------------|------|
| `PORTO_DATA_NOT_FOUND` | Missing bundle or entity |
| `PORTO_ENVELOPE_NOT_FOUND` | Unknown envelope id |
| `PORTO_PRODUCT_NOT_FOUND` | Unknown product id |
| `PORTO_PRODUCT_AMBIGUOUS` | Multiple products; need `options` + pin |
| `PORTO_SERVICE_AMBIGUOUS` | Multiple services for a kind |
| `PORTO_VALIDATION_FAILED` | Input shape / business invariant |

Integrators map codes to localized copy; SDK does not embed English user messages in result types. Full list: [public.md](public.md).

---

## 8. Cross-SDK parity & BDD contract-first

**Rule:** No new public method merges in Python without:

1. Shared **porto-features** scenario (or scenario stub + issue) defining inputs/outputs
2. TypeScript implementation or explicit `@experimental` mark in release notes

Python leads Licko (Porto is Python); TypeScript lag is acceptable only when marked experimental.

### 8.1 TypeScript dual runtime (`/` vs `/browser`)

TypeScript ships two **package exports** with the **same** public surface:

| Export | Data loader |
|--------|-------------|
| `@gruncellka/porto-sdk` | Filesystem / Node |
| `@gruncellka/porto-sdk/browser` | Embedded porto-data at SDK build time |

Python has a single filesystem loader (`data_path`). That asymmetry is **runtime transport only**, not a second public API.

Full doctrine: **[runtime.md](runtime.md)**.

---

## 9. Stability & semver (pre-1.0)

| Surface | Policy |
|---------|--------|
| Names in `public.md` | Breaking change if renamed/removed |
| Method signatures | Minor additions OK; breaking changes → major |
| `Porto`, `Product`, `Envelope` fields | Additive only in minor; enum extensions documented |
| porto-data pin | SDK release notes cite compatible porto-data version range |

---

## 10. Release gates

Before integrators vend-copy or publish:

| Gate | Blocks |
|------|--------|
| porto-data `make validate` | orphan envelope ids, graph drift |
| Entity loaders: envelopes, layouts, marks, providers | honest geometry reads |
| Loader boundary | public loader leak |
| porto-features scenarios | cross-SDK drift |
| Python + TS CI green | parity regression |

---

## 11. Minimal quickstart

```python
from porto_sdk import PortoClient, PortoConfig

client = PortoClient(PortoConfig(data_path="/path/to/porto_data"))
dp = client.provider("deutschepost")

options = dp.options(country_code="DE", weight=20, envelope_id="DL")
porto = dp.resolve(
    country_code="DE",
    weight=20,
    envelope_id="DL",
    product_id=options[0].id,
)
# mark(PortoMarkRequest(porto=porto), ExecutionParameters(...))
```

TypeScript: same verbs; `camelCase` method names per [architecture.md §17](architecture.md).

---

## 12. Provider id canonical keys

porto-data registry ids are canonical (e.g. `deutschepost`). Product apps map their own enums in the app adapter only — not in SDK or porto-data.

---

*Public API narrative — Porto SDK Lab. Reference: [public.md](public.md).*
