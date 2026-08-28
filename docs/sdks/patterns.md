# SDK architecture patterns — industry alignment and pre-1.0 gaps

**Purpose:** Explain *why* the Porto SDK stack is shaped the way it is, how it maps to established integration and decision-management patterns, and which gaps to close **before 1.0**.

**Audience:** SDK contributors, reviewers, and agents working in Porto SDK Lab or either SDK submodule.

**See also:** [architecture.md](architecture.md) (internal layers), [stack.md](../stack.md) (ownership), [public.md](public.md) (public API), [parity.md](parity.md) (BDD coverage).

When this doc disagrees with **public API** wording, [api.md](api.md) wins. When it disagrees with **layering**, [architecture.md](architecture.md) wins.

---

## 1. Problem class

Porto SDKs solve a **multi-provider postal decision** problem with three coupled concerns:

| Concern | Question | Owner |
|---------|----------|--------|
| **Catalog truth** | What products, zones, prices, constraints exist? | **porto-data** |
| **Deterministic decisioning** | Given inputs, which product/price/route is valid? | **SDK resolution** |
| **Provider execution** | How do we purchase/print against one operator API? | **SDK adapters** |

Consumer apps (e.g. Licko) depend on the **SDK**; the SDK depends on **porto-data** as a package. Apps must not parse raw catalog JSON or embed provider-specific branching.

---

## 2. Industry pattern mapping

The stack aligns with patterns documented in DDD, enterprise integration, and shipping/carrier SDK practice:

| Pattern | Typical source | Porto mapping |
|---------|------------------|---------------|
| **Anti-Corruption Layer** | DDD (Evans); [Microsoft ACL](https://learn.microsoft.com/en-us/azure/architecture/patterns/anti-corruption-layer) | `adapters/` translate provider APIs → `PortoMark` + `PortoErrorCode` |
| **Ports & Adapters (hexagonal)** | Clean / hexagonal architecture | `PortoClient` = stable port; adapters = infrastructure |
| **Strategy + Registry** | Multi-carrier shipping SDKs | `integration_registry` + per-operator adapters |
| **Externalized business rules** | [arc42 — externalized rules](https://quality.arc42.org/approaches/externalized-business-rules) | **porto-data** + resolution graph (volatile rules as versioned data, not `if` chains) |
| **Decision pipeline (DMN-style)** | [OMG DMN](https://www.omg.org/spec/DMN/1.3/PDF) | restriction → zone → weight → product → price = chained eligibility / validation / calculation |
| **Catalog / engine separation** | Pricing-engine and PIM literature | porto-data = catalog; `services/resolution/` = engine; adapters = execution |

DMN categorizes operational decisions as **eligibility**, **validation**, and **calculation** — matching restriction facts, `options`/`resolve` validation, and composed price.

**Verdict:** The four-layer model (porto-data → resolver → adapter → cli) is the standard shape for long-lived multi-provider postal/shipping intelligence SDKs. The main risk at 0.x is not missing layers but **soft boundaries** that allow bypasses.

---

## 3. Reference architecture

```text
Consumer (Licko / CLI / Lab)
            │
┌───────────▼───────────────────────────────────────────┐
│  PortoClient — catalogs + client.provider(id)           │
│  ProviderClient: resolve | options | price | mark | …   │
└───────────┬─────────────────────────┬───────────────────┘
            │                         │
 ┌──────────▼──────────┐     ┌────────▼────────┐
 │ PortoResolver       │     │ Adapters (ACL)  │
 │ (orchestration only)│     │ auth, HTTP, map │
 └──────────┬──────────┘     └─────────────────┘
            │
 ┌──────────▼──────────────────────────────────────────┐
 │ Resolution primitives — zone, weight, product, price │
 └──────────┬──────────────────────────────────────────┘
            │
 ┌──────────▼──────────┐
 │ Data access layer    │  load/validate only; ResolutionIndex
 └──────────┬──────────┘
            │
 ┌──────────▼──────────┐
 │ porto-data (SoT)     │
 └─────────────────────┘
```

**Rules that age well:**

1. **One decision pipeline** — never fork resolvers per provider.
2. **Adapters are dumb translators** — no product/zone/price logic inside adapters.
3. **Catalog changes ship without SDK redeploy** (within semver bounds on porto-data).
4. **Cross-language parity is a product requirement**, not a nice-to-have.
5. **Contracts before code** — porto-features `@sdk` Gherkin + [api.md](api.md) gate releases.

---

## 4. Porto vs PortoMark (decision vs execution)

| Concept | Role |
|---------|------|
| **Porto / `ResolvedData`** | *What* to mail: product, zone, tier, price, `mark_type`, `tracking_mode` — resolved **before** any adapter call |
| **PortoMark** | *What the provider returned*: printable content, tracking, `provider_raw` |

Adapters receive **fully resolved input** and return `PortoMark`. Idempotency keys are **passthrough only** — the SDK does not own execution ledger or payment policy.

---

## 5. Two catalog tables — never conflate

| Artifact | Purpose |
|----------|---------|
| **`execution.json`** | Wire channel id, billing/execution capability gates |
| **`graph.edges.wire`** | Checkout product codes for provider APIs |

Enforced in SDK BUGBOT rules and [stack.md](../stack.md). Canonical identity docs: porto-data `docs/identity.md`.

---

## 6. Pre-1.0 gap backlog

Tracked in [gaps.md](gaps.md) and [architecture.md](architecture.md). Close these while the surface is still small.

### P0 — Architectural enforcement

| Gap | Risk | Action |
|-----|------|--------|
| Loader bypass for product/price | Resolution graph ignored; non-deterministic paths | Treat loader price/product methods as internal; architecture tests block direct calls outside `services/resolution/` and `PortoResolver` |
| `validation` re-walks graph | Duplicated resolution logic | Delegate weight/product checks to `PortoResolver` or resolution primitives |
| `registered` service fees | Closed — no `RegisteredService`. Use `resolve(..., services=["registered"])` then `price` / `mark` / `track` | Do not reintroduce a parallel fee path |
| Capabilities vs graph drift | resolver yes + capabilities no | **Graph wins** for validity; `client.providers` is read projection only |

### P1 — Correctness and parity

| Gap | Risk | Action |
|-----|------|--------|
| Decision explainability | Support/audit cannot answer “why this product?” | Structured `ResolutionTrace` or enriched `PRODUCT_AMBIGUOUS` candidates (not English prose) |
| Catalog time semantics | Wrong price at tariff boundaries | Thread `effective_at` / `as_of` through resolution; frozen-date tests in porto-features |
| TS/PY data-layer shape | Schema/validation drift | Keep `data/entities/*` mirrored; CI neutrality + loader parity |
| Swiss Post `rules.json` | Loaded but unevaluated → silent wrong answers | Implement minimal evaluator **or** fail loud with `FEATURE_NOT_SUPPORTED` |
| BDD phrase parity | Contract drift between SDKs | porto-features `@sdk` = semver contract; align `batches.py` ↔ `batches.ts` |

### P2 — Execution boundary

| Gap | Risk | Action |
|-----|------|--------|
| Non–Deutsche Post online adapters | Implicit expectations | `UnavailableExecutionAdapter` default; document per-provider execution maturity in [gaps.md](gaps.md) / [gaps.md](gaps.md) |

---

## 7. Pre-1.0 detection checklist

Run before tagging 1.0 or widening consumer APIs.

| Check | Pass criteria |
|-------|---------------|
| Invariant tests | CI fails if non-resolution code calls product/price loader resolution methods |
| Graph vs capabilities | No undocumented disagreement between resolver and `providers` projection |
| Determinism | Same inputs + same catalog version → same `product_id` and price (golden/property tests) |
| Ambiguity policy | `options`, `resolve`, `mark` handle `PORTO_PRODUCT_AMBIGUOUS` consistently |
| Catalog version surface | Resolved output exposes data package version or checksum where consumers need audit |
| Adapter purity | No `ProductResolver` / `PriceResolver` imports under `adapters/` |
| Parity | `make all` green on **both** SDKs; review [parity.md](parity.md) |
| Time | At least one test at `effective_from` / sunset boundary ([architecture.md](architecture.md)) |
| Explainability | Resolution failures include structured candidates, stable `PortoErrorCode` |

---

## 8. What not to build (yet)

Defer unless a task explicitly requires scope:

- Separate Drools/DMN runtime server — graph + `ResolutionIndex` is a **compiled decision model**; sufficient for Porto.
- Plugin / factory-of-factories frameworks.
- SDK-owned payment ledger, invoice, or idempotency deduplication store.
- Per-provider resolver forks (`if provider == …` in generic `services/`).

Externalized-rules literature warns against rule engines when logic is stable and coupling cost exceeds benefit. **Resolution order** is stable; **tariff tables** are volatile — that split is correct.

---

## 9. Related docs

| Doc | Role |
|-----|------|
| [public.md](public.md) | Public freeze allow-list |
| [architecture.md](architecture.md) | Four-layer model, `ProviderClient` surface, adapters |
| [resolution.md](resolution.md) | Graph, primitives, product/service identity |
| [gaps.md](gaps.md) | Non-blocking leftovers |
| [dependency.md](dependency.md) | Manifest semver vs runtime `data_path` |
| [runtime.md](runtime.md) | TS `/browser` embed vs Python `data_path` |
| [architecture.md](architecture.md) | Effective dates and time anchors |

Per-SDK summaries: `sdks/porto-sdk-python/docs/patterns.md`, `sdks/porto-sdk-typescript/docs/patterns.md`.
