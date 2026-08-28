# Porto SDK — test layers

Both SDKs implement one product. Tests must follow the contract, not the implementation path that happened to grow first.

```text
porto-features (shared Gherkin)
        ↓
Python steps / TypeScript steps     same scenario meaning
        ↓
Python units / TypeScript units     same domain folders
        ↓
architecture/                       same invariants
        ↓
adapters/                           provider wires
```

A green test that only mirrors an internal function is not evidence that the public contract holds.

## Four layers

| Layer | Owns | Must not own |
| --- | --- | --- |
| **1. Contract / BDD** | Shared behavior in [porto-features](../../resources/porto-features). Both SDKs run the same scenarios. | A second Python-only or TypeScript-only feature tree |
| **2. Domain units** | Language-specific checks for one domain module (resolution, marks, data, client, …) | Provider HTTP, architecture scans, Gherkin duplicates |
| **3. Architecture guards** | Boundaries and naming invariants, identical concept set in both SDKs | Product prices, mark payloads, adapter error maps |
| **4. Adapter integration** | One provider wire (auth, HTTP, document, mark-execution errors) | Generic `resolve` / `options` / `price` policy |

```text
Shared BDD          → domain behavior
Unit tests          → module / domain behavior
Architecture tests  → boundaries / invariants
Adapter tests       → provider implementation
```

## 1. Contract / BDD

**Source of truth:** `resources/porto-features/porto_features/features/`.

Do not flatten that tree into seven root files. Provider examples stay under `sdk/providers/<id>/`. Paid wires stay under `adapters/`. Core behavior stays under `sdk/core/`. Conceptual domains:

| Domain | Where it lives today |
| --- | --- |
| Resolution | `sdk/providers/*/resolution.feature`, `delivery_resolution.feature` |
| Product options | `sdk/providers/*/product_options.feature` |
| Pricing | `sdk/providers/*/pricing.feature`, `pricing_matrix.feature` |
| Services | `sdk/providers/*/services.feature` |
| Envelopes / catalog | `sdk/core/metadata.feature`, `sdk/core/data.feature` |
| Marks | `sdk/core/mark_requires.feature`, `adapters/*/marks.feature` |
| Errors | `sdk/core/errors.feature`, `adapters/*/errors.feature` |
| Config / CLI | `sdk/core/cli.feature` |
| Validation / restrictions | `sdk/core/validation.feature`, `sdk/core/restrictions.feature` |

Both SDKs execute those scenarios through matching batch ids (`tests/bdd/runner/batches.py` ≡ `batches.ts`). Step **code** may differ by language. Scenario **meaning** must not.

Gherkin phrasing: [porto-features vocabulary](../../resources/porto-features/docs/vocabulary.md).

### Step modules (one domain vocabulary)

`tests/bdd/steps/` in each SDK:

| Module | Domain |
| --- | --- |
| `resolution` | resolve the letter, destination, product id, delivery hint |
| `products` | list product options |
| `services` | service kind / catalog id |
| `pricing` | `price()`, zone + product quotes |
| `marks` | mark requires / create mark (offline contract) |
| `envelopes` | envelope list, geometry, layout identify |
| `data` | catalog inspection |
| `errors` | Porto error codes |
| `config` | CLI / config |
| `validation` | letter and address validation |
| `restrictions` | eligibility / sanctions |
| `letter` | letter-ordering leftovers (fold into `resolution` when phrases overlap) |
| `common` | phrasing aliases only |
| `helpers` / `bdd-context` | technical Given/Then support, not a second vocabulary |

Do not add `porto-vocabulary` vs `step-vocabulary` vs `api-comprehensive` as parallel taxonomies.

## 2. Domain units

Same conceptual folders in both SDKs. Filenames may follow language convention (`test_*.py` vs `*.test.ts`).

```text
tests/
  resolution/     envelope, product, service, delivery, pricing
  marks/          profile, requires, content, identity
  data/           catalog loaders, graph, restrictions
  client/         config, provider, envelopes, jurisdictions, capabilities
  wallet/
  tracking/
  errors/
  architecture/
  adapters/
  bdd/            runner + steps only — no domain units here
```

Name files after the **domain fact**, not the internal type (`service_bind` is acceptable when the fact is “kind vs catalog id pin”; `pipeline_enforcement` is not — that is architecture).

## 3. Architecture guards

Identical invariant set. Python `tests/architecture/test_<name>.py`, TypeScript `tests/architecture/<name>.test.ts`.

| Invariant | What it locks |
| --- | --- |
| `public_surface` | Published core stays provider-neutral; no Lab vocabulary |
| `provider_neutrality` | Generic `services/` has no provider name literals |
| `dependency_direction` | Resolver / execution / validation do not leak adapter or app lifecycle |
| `data_ownership` | Generic services do not construct `PortoDataLoader` |
| `naming` | `ProviderId` ≠ `WireId`; capability states are not booleans |
| `configuration` | `PortoConfig` public fields only |
| `vocabularies` | `ServiceKind` / `FeatureKind` match `kinds.schema.json` |

Architecture tests do not prove that `standardbrief` costs 95 cents. Domain units and BDD do.

## 4. Adapter tests

`tests/adapters/` — Internetmarke (and later peers): HTTP client, auth errors, mark-execution errors, document payload. Fail closed without credentials. Not a substitute for `@sdk` Gherkin.

## Adding a test

1. Is it a **shared behavior** both SDKs must honor? → porto-features scenario, then both step modules.
2. Is it a **module fact** in one language (types, filesystem, embed)? → domain unit in the matching folder; add the sibling when the other SDK has the same module.
3. Is it a **boundary**? → `architecture/` with the same invariant name in both SDKs.
4. Is it a **wire**? → `adapters/`.

Do not start from `test_<internal_function>`.
