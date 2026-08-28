# Resolution Flow & resolution graph Architecture

This document describes how the Porto SDK resolves products, prices, and constraints using **porto-data** and **resolution graph**. The design follows a SOLID, DRY, and deterministic approach. Public freeze SoT: [public.md](public.md).

---

## 1. Core Problem: products ≠ real-world availability

Without `resolution graph`, we face:

- **Separate tables** (`products`, `prices`, `zones`, `weight_tiers`) that are not fully normalized
- **Missing context**: Which `weight_tiers` are allowed for a product? Which `zones` apply?
- **Contradictions** between providers (e.g., Deutsche Post: 1 tier/product vs Swiss Post: many tiers/product)

**Key insight:** A product may exist in `products.json` but not be available for a specific weight or zone. `resolution graph` defines **what actually works with what**.

---

## 2. What resolution graph Does

### 2.1 Explicit valid combinations

```json
"standardbrief": {
  "zones": ["domestic", "zone_1_eu", "world"],
  "weight_tiers": ["W0020"]
}
```

This means:

- The product is **not universal** — it has a clear constraint graph
- Only listed zone + weight_tier combinations are valid

### 2.2 Solves combinatorial explosion

| Without resolution graph                        | With resolution graph            |
| ----------------------------------------------- | -------------------------------- |
| Check all combinations: product × zone × weight | Know the valid space immediately |
| Then verify if a price exists                   | No brute-force needed            |
| Slow, dangerous, non-deterministic              | Fast, deterministic              |

### 2.3 Normalizes provider differences

- **Deutsche Post**: 1 weight tier per product
- **Swiss Post**: Many weight tiers per product

The SDK uses the **same logic** for both. `resolution graph` aligns the different data models.

---

## 3. Execution Graph (not just links)

`resolution graph` defines a **dependency graph** for validation, loading, and resolution.

### 3.1 Dependency graph

```yaml
prices depends_on:
    - products
    - services
    - zones
    - weight_tiers
```

This defines:

- **Validation order** — validate dependencies before dependents
- **Loading order** — load in topological order
- **Resolution order** — resolve zone → weight_tier → product → price

### 3.2 Lookup rules (algorithm, not just data)

| Rule                | Formula                                            | Description                                         |
| ------------------- | -------------------------------------------------- | --------------------------------------------------- |
| `price_lookup`      | `product_id + zone + weight_tier`                  | Base postage in **`prices/product_prices.json`**; surcharges in **`prices/service_prices.json`** |
| `weight_resolution` | `min <= weight <= max`                             | Find weight_tier in weights.json               |
| `zone_validation`   | `zone in resolution graph.edges[product_id].zones` | Check zone via resolution graph (not product.zones) |

---

## 4. Where the SDK Uses resolution graph

| SDK method | Uses resolution graph for |
| ---------- | ------------------------- |
| **`options()`** | List valid products for country + weight (+ optional envelope) |
| **`resolve()`** | Select product (+ services) → compose `Porto` |
| **`price()`** | Same selection path → `Pricing` without execution identity |

Envelope **`identify()`** resolves physical face / candidates; it does not replace product graph resolution.

---

## 5. Architectural Role of Data Files

| File                        | Role                              |
| --------------------------- | --------------------------------- |
| `products.json`             | What exists                       |
| `prices/product_prices.json` / `prices/service_prices.json` | Base postage and add-on service amounts |
| `zones.json`                | Where it's possible               |
| `weights.json`         | Weight intervals                  |
| **`resolution graph.json`** | **What actually works with what** |
| `policy/restrictions.json`  | Destination legal / routing facts |

---

## 6. Why This Is Critical for the SDK

| Without resolution graph | With resolution graph |
| ------------------------ | --------------------- |
| Guess-based              | Deterministic         |
| Fragile                  | Provider-agnostic     |
| Provider-specific hacks  | Declarative           |
| Many if/else             | Extensible            |

`resolution graph`:

- Removes implicit logic from the SDK
- Moves rules into data
- Enables the same SDK across providers
- Simplifies maintenance and scaling

---

## 7. User Input vs Internal Resolution

**User gives** (`ResolutionRequest` / `options` inputs):

- `country_code` — destination country
- `weight` — weight in grams
- `envelope_id` — optional physical fit filter
- `product_id` — optional catalog pin
- `services` — requested `ServiceKind[]` (intent)
- `service_ids` — optional catalog service pins among options

**Resolved** (internal level — outputs of earlier steps):

- `zone_id` — from country_code via zones.json
- `weight_tier_id` — from weight via weights.json
- catalog **`product_id`** — from graph ∩ filters (+ pin / disambiguation)
- bound **`service_ids`** when services were requested

The ProductResolver operates on the **resolved** inputs. The full flow converts user input → resolved ids → product → services → price.

---

## 8. Product Resolution Flow (Step-by-step)

```
User input: country_code, weight, envelope_id?, product_id?, services?, service_ids?
         │
         ▼
┌────────────────────────────────────────────────────────┐
│ 1. Restriction facts                                    │
│    country_code → restrictions.json → Restrictions      │
│    (resolve does not fail closed; consumer owns policy) │
└────────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────┐
│ 2. Zone resolution                                      │
│    country_code → zones.json → zone_id (resolved)       │
└────────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────┐
│ 3. Weight tier resolution                               │
│    weight → weights.json → weight_tier_id (resolved)    │
│    (lookup_rules.weight_resolution)                     │
└────────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────┐
│ 4. Envelope filter (optional)                           │
│    envelope_id present → drop products whose            │
│    envelope_ids[] does not include it                   │
│    (filter only — never selects among leftovers)        │
└────────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────┐
│ 5. Product resolution (resolution graph)                │
│    Input: zone_id, weight_tier_id, optional product_id  │
│    Find products where (strict matching):               │
│    - zone_id in graph.edges[product_id].zones           │
│    - weight_tier_id in graph.edges[product_id].weight_tiers│
│    - product_id pin when present                        │
└────────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────┐
│ 6. Product selection (when multiple candidates)         │
│    Prefer options() + explicit product_id, or           │
│    PORTO_PRODUCT_AMBIGUOUS with candidates              │
└────────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────┐
│ 7. Services                                             │
│    services = ServiceKind intent; service_ids = pins    │
│    Ambiguous kind → PORTO_SERVICE_AMBIGUOUS             │
└────────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────┐
│ 8. Price lookup                                         │
│    product + zone + weight_tier + bound services        │
│    → amount / currency / components                     │
└────────────────────────────────────────────────────────┘
```

Compose UI pattern: `options(country, weight, envelope_id)` → choose `product_id` → `resolve(...)` with `services` / `service_ids`.

---

## 9. ProductResolver Component

The SDK extracts product resolution into a dedicated **ProductResolver** for:

- **Single Responsibility**: Resolve product from resolved zone + weight tier (+ pin)
- **Testability**: Pure functions over resolution graph
- **DRY**: Shared logic for `options` / `resolve` / `price`
- **Determinism**: No provider branching; data-driven only

See `porto_sdk/services/resolution/product_resolver.py` (Python) and `services/resolution/product-resolver.ts` (TypeScript).

---

## 10. Canonical identity: catalog ids + kinds

**Rule:** Purchasable identity is catalog **`product_id`** (and catalog **`service_ids`** when pinning add-ons). Cross-provider **grouping** for services/features uses `kind` (`ServiceKind` / `FeatureKind`). There is no letter size-bucket taxonomy as public resolution input.

| Concept | Role | Example |
| ------- | ---- | ------- |
| `product_id` | Provider-scoped catalog product | `standardbrief` |
| `envelope_id` | Physical fit filter | `DL` |
| `services` | Intent kinds | `["registered"]` |
| `service_ids` | Chosen catalog service rows | `["einschreiben"]` |
| `kind` | Cross-provider grouping (schema SoT) | `registered` |

Several valid catalog options for the same kind is normal — expose them via `options` / candidates; do not silently pick.

---

## 10.1 Execution semantics (mark_type, tracking)

Resolved **`Porto`** carries:

- **`mark_type`**: `stamp` \| `label` — from the resolved mark profile
- **tracking**: `none` \| `optional` \| `included`

These are **not** runtime tracking numbers (those appear only on **`PortoMark.tracking_number`** after a successful provider call). Adapters map HTTP responses into **`PortoMark`**; they should not infer `mark_type` from provider id when data supplies it.

---

## 10.2 Restrictions as data

`Porto.restrictions` is the same `Restrictions` shape as `provider.restrictions.check(country_code)` — country precision on `resolve`. Region drill-down is only via `restrictions.check(country, region)`. Public shape: `{ impact, legal, routing }`. `resolve` does not fail closed on restriction facts; consumer policy stays outside Porto. See [public.md](public.md).

---

## 10.3 Data Layer vs Public API

**Pure data layer** (lives in `data/loader` only — no orchestration):

| Method                                                                       | Purpose                            |
| ---------------------------------------------------------------------------- | ---------------------------------- |
| `get_product(product_id)`                                                    | Single product lookup              |
| `get_zone(zone_id)`                                                          | Single zone lookup                 |
| `get_zone_by_country_code(country_code)`                                     | Zone from country                  |
| `get_price_by_product_zone_weight_tier(product_id, zone_id, weight_tier_id)` | Price lookup                       |
| `get_service_price(service_id, zone_id?)`                                     | Catalog service fee; zoned rows require `zone_id` |

**No `client.data` facade.** Public callers use:

| Entry point | Role |
| ----------- | ---- |
| `client.provider(id).options` | Product candidates for UI |
| `client.provider(id).resolve` | Full `Porto` |
| `client.provider(id).price` | Catalog `Pricing` |
| `client.provider(id).mark` / `track` / `wallet` / `can` | Execution and capability verbs |
| `client.restrictions` / `provider.restrictions` | Restriction facts |

---

## 10.4 SDK Invariant

> **No code is allowed to resolve product or price without going through resolution primitives.**

Direct calls to `get_product()`, `get_price_by_product_zone_weight_tier()`, or similar data lookups for the purpose of resolving "which product/price for this shipment" violate this invariant. All product and price resolution must flow through `ProductResolver`, `PriceResolver`, or `PortoResolver` (which orchestrates them).

---

## 11. Shared ResolvedInput / ResolutionContext

All resolution primitives operate on a shared input (illustrative):

```ts
ResolvedInput = {
  zone_id: string
  weight_tier_id: string
  product_id?: string
  services?: ServiceKind[]
  service_ids?: string[]
  restrictions?: Restrictions
}
```

**Resolution primitives** (each resolves one concern):

- Restriction facts from country (and optional region on `check`)
- `ZoneResolver.resolve(countryCode)` → zone_id
- `WeightTierResolver.resolve(weight)` → weight_tier_id
- `ProductResolver.resolve(resolvedInput)` → product (catalog id)
- Service binding from kinds + pins
- `PriceResolver.resolve(resolvedInput, productId)` → price

**Orchestration** (public API on `ProviderClient`):

- `options()` = candidates for zone + weight (+ envelope)
- `resolve()` = options path + pin/disambiguation + services → `Porto`
- `price()` = same selection → `Pricing`

---

## 12. Related architecture docs

| Doc | Purpose |
|-----|---------|
| [public.md](public.md) | Public freeze — request fields, errors, verbs |
| [architecture.md](architecture.md) | Layers, Porto vs PortoMark, adapter contract |
| [public.md](public.md) | resolve / price / mark identity |
| [api.md](api.md) | Public contract narrative |
