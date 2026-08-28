# Porto SDK — public API reference

Cross-language coordination reference for the public SDK surface. Changing a name, field, or error code listed here is a breaking change for SDK consumers.

Python uses snake_case; TypeScript uses camelCase. Semantic names match after case fold.

Narrative overview: [api.md](api.md). Internal layers: [architecture.md](architecture.md).

## Naming

Core names describe **cross-provider concepts**. Provider words stay in porto-data and adapters. Configuration is **data supplied to the SDK**, not hidden behavior.

1. **Context removes redundant words.** `client.envelopes.layout()`, not `resolveEnvelopeLayout()`.
2. **Generic names in core.** `ServiceKind`, not `EinschreibenType`.
3. **Implementation nouns stay internal** unless they are a documented extension point: `Adapter`, `Loader`, `Resolver`, `Execution`, `HttpClient`.
4. **Three or four word names** usually mix roles (`EnvelopeResolverService`, `mark_anchor_from_layout`) — split or hide them.
5. **Plural vs singular on the client.** Plural = catalog/family over arbitrary members. Singular = an object/value or a singleton facility.
   - Plural catalogs: `client.envelopes`, `client.restrictions`, `client.providers`, `client.jurisdictions`. Never `client.envelope`.
   - Singular facilities: `provider.wallet`, `provider.capabilities`, `client.address`, `client.config`, `client.provider(id)`.
   - Singular domain objects: `EnvelopeIdentity`, `Envelope`, `Address`, `Porto`, `PortoMark`, `Product`, `Service`, `Feature`.
6. **Domain plurals for collections; verbs for operations.** Prefer catalog structure in public results (e.g. `Restrictions.legal` / `Restrictions.routing`). Generic nouns (`items`, `*Info`, `*Data`, `*Result`) are a signal to check for flattened domain — see [Naming map](#naming-map) below. Do not invent an anti-stutter `items` convention.

### Public API rules

| Rule | Meaning |
|---|---|
| Domain nouns / plurals / verbs | Already in place |
| Same concept → same type | Discovery + resolution share enums (`MarkType`, `TrackingMode`) |
| IDs named `*Id` | Identifier ≠ entity (`zoneId` / `zone_id` vs `Porto.zone`) |
| One money vocab | `amount` + `currency` (quotes and `PortoMark`) |
| Geometry in mm | Public face fields are `width` / `height` (no `Mm` / `_mm` suffix); porto-data schema is unit SoT |
| Resolved output | Always present keys; `null` / `false` explicit |
| Input/config | Omission may mean default |
| No extract holes | No missing member types; no baggy `object`/`any` on stable consumer models |

### Service projections (keep all four)

| Field | Type | Role |
|---|---|---|
| `ProductOption.services` | `ServiceOption[]` | Discovery: priced add-ons for product×zone |
| `Porto.availableServices` / `available_services` | `Service[]` | Resolved: full catalog rows applicable to product×zone |
| `Porto.services` | `ServiceKind[]` | Selected kinds on this resolve |
| `Porto.serviceIds` / `service_ids` | `string[]` | Bound catalog ids for execution |

`availableServices` is not a rename of `ServiceOption` (catalog metadata vs priced UI row).

## Flow

```text
options(country_code, weight, envelope_id)
  → consumer chooses product_id
  → resolve(same names + product_id)
  → Porto
  → mark(PortoMarkRequest(porto=…), ExecutionParameters(credentials=…))
  → PortoMark
```

`Porto` is the frozen execution identity. `mark` must not re-resolve from envelope/product + weight.

`Porto.restrictions` is the same `Restrictions` value as `provider.restrictions.check(country_code)` — **country precision only**. `resolve()` does not accept `region_code` / `regionCode` for restriction evaluation. Region drill-down is only via `restrictions.check(country, region)`. Country-level: any regional facts → `impact: "warn"` with those legal/routing leaves included (never promote a child regional `block` to country `block`). Exact region via `check`: full legal → `block`; partial legal / routing → `warn`; unaffected region → `impact: null`. Public shape is `{ impact, legal, routing }` (catalog structure preserved; not a flat `items` bag or `restrictions.restrictions`). `resolve` does not fail closed on restriction facts. Consumer policy stays outside Porto.

Country/zone resolves product. Address is execution input only when `Porto.requires` says so.

## Public types

Client: `PortoClient`, `ProviderClient`

Resolution: `ResolutionRequest`, `Porto`, `PriceComponent`

Execution: `PortoMarkRequest`, `PortoMark`, `ExecutionParameters`

Address / envelopes: `Address`, `Dimensions`, `Envelopes` (type of `client.envelopes`), `EnvelopeIdentity`, `Envelope`, `EnvelopeGeometry`, `EnvelopeLayout`, `EnvelopeMark`, `EnvelopeMarkFact`, `EnvelopeRect`, `EnvelopeSheet`, `EnvelopeSize`

Restrictions: `Restrictions` (`impact` + `legal[]` + `routing[]`), `LegalRestriction`, `RoutingRestriction`, `RestrictionJurisdiction`, `JurisdictionInstrument`, `RestrictionImpact`

Options: `ProductOption`, `Pricing`, `PriceInput`, `DeliveryHint`, `PriceComponent`

Vocabulary: `ServiceKind`, `FeatureKind`, `Requirement`, `MarkType`, `TrackingMode`, `MarkOutputMime`, `CapabilityState`

Errors: `PortoError`, `PortoErrorCode`

Configuration: `PortoConfig`, `CacheConfig`, `TransportConfig`, `WireConfig`, `ProviderRuntimeConfig`

`client.config` is input `PortoConfig`, not a normalized runtime object. `PortoResolver`, `PortoExecution`, `EnvelopeResolverService`, `NormalizedPortoConfig`, and `HttpClient` are not public types.

`PortoClient()` / `new PortoClient()` — config is optional. `client.provider(id)` binds a catalog-known id without a dummy `providers: { id: {} }` row. `PortoConfig.providers` is wires/credentials and, when present, an allowlist:

- omitted — no allowlist overlay; any catalog provider is bindable; runtime has no wires
- present — unlisted ids fail `PORTO_PROVIDER_NOT_CONFIGURED`; a listed `{}` means allow with no wires

Unknown catalog id, or an id excluded by a present allowlist, is `PORTO_PROVIDER_NOT_CONFIGURED`. There is no public `defaultProvider`.

Public envelopes operations: `list` / `geometry` / `layout` / `identify` / `getMark`. Not public: `match`, `resolve`, `validateForProduct`.

Public restrictions operations: `check` on `client.restrictions` and `provider.restrictions`. Destination facts are `country_code` / `countryCode` and optional `region_code` / `regionCode`. The lookup type is not a public export. Not public: singular `restriction: ResolvedRestriction`.

ProviderClient verbs: `resolve` / `options` / `price` / `mark` / `track` / `capabilities` / `can` / `wallet`. Not public: `estimate`, `registered`, `resolver`, `advise`, `prepare`, `bytes`.

`ProviderCapabilities` is facts only: `mark`, `track`, `wallet`, `trackingKind`.

## Kind vs purchasable options

`kind` is **cross-provider grouping** (schema SoT: `kinds.schema.json`). A consumer may pass a `kind` as intent. It is not a unique purchasable variant.

Resolution may validly return multiple matching products or services for the same kind. If the provider offers several valid variants, expose them as options with their catalog `id`, price, delivery, features, and let the consumer choose.

Do not create a new global `kind` only to encode one provider-specific variant. Example: `registered` → `einschreiben` and `einschreiben_einwurf` may both be valid options (same pattern as cheaper/slower vs faster/more expensive products).

Catalog `id` is concrete provider-scoped identity (the SDK may mint it). Do not call it a native id.

## `ResolutionRequest`

- `country_code` / `countryCode`
- `weight`
- `envelope_id` / `envelopeId` (physical fit filter; from `identify` or explicit). Absent = no constraint. Present = drop incompatible products. Never selects among remaining rows — leftover twins → `PORTO_PRODUCT_AMBIGUOUS` or `options()` + `product_id`. Empty `products.envelope_ids[]` currently matches any envelope.
- `product_id` / `productId` (chosen product option when known)
- `services` — requested `ServiceKind[]` (grouping). Example: `registered`. Never catalog ids.
- `service_ids` / `serviceIds` — chosen catalog `Service.id` pins among options. Same role as `product_id`. Kind strings in this field are invalid. A pin’s `kind` must be in `services`.
- `region_code` / `regionCode` (when relevant)
- optional origin country, delivery preference, indemnity tier (already public)

Use `options(country_code, weight, envelope_id)` to list product candidates, then `resolve` with `product_id` and/or `services` (plus `service_ids` when more than one service option matches). `options` / `resolve` / `price` all use `country_code` / `countryCode` for destination country.

No address on resolution.

`can(feature)` takes `FeatureKind` only (example: `can("tracking")`). Catalog feature ids are not a public `can()` argument.

## `Porto` (resolved identity)

Must carry: product, zone, weight tier, `amount`, `currency`, `components` (`PriceComponent[]`: `kind` `product` | `service`, catalog `id`, `amount` in the same cents as the parent), `features` (`Feature[]`), `available_services` / `availableServices` (`Service[]` options), `services` (selected `ServiceKind[]`), bound chosen catalog service ids for execution (`service_ids` / `serviceIds`), `requires` (`Requirement` tokens), `mark_type` / `markType` (`stamp` | `label`), tracking (`none` | `optional` | `included`), validity/warnings, `restrictions` (`Restrictions`: `impact` + `legal[]` + `routing[]`), delivery hint (`DeliveryHint`).

Not public on `Porto`: `dimension_specs` / `dimensionSpecs`, `wire`, `base_price` / `basePrice`, `pricing`. Loader `PortoPricing.price` stays internal. Indemnity `max_amount` is an insurance cap, not postage.

`amount` is the authoritative composed quote in catalog cents (product grid row plus every bound service). After a successful compose, `components` is complete and `sum(component.amount) == amount`. A bound/requested service with no `service_prices` row fails `resolve` / `price` with `PORTO_PRICE_NOT_FOUND` (`service_id` in details) — no Porto, no partial `amount`. Catalog `amount: 0` is explicit no extra charge and appears in `components`. `price()` returns `Pricing` with the same `amount` / `currency` / `components` for the same selection; it is not required after `resolve()`.

Product options list catalog facts (`id`, row `amount`, `delivery_hint`, indemnity, tracking) plus priced add-ons in `services` / `ServiceOption[]` for that product × the destination zone used by `options()`. Each `ServiceOption` carries catalog `id` (pin value), `kind`, `name`, optional `label`, zone tariff `amount`, `currency`, and optional `combinable_with` / `combinableWith`. Discovery rows may expose a missing option price as null; binding that id in `resolve` / `price` fails. Do not attach `components` to options. `service_ids` / `serviceIds` on resolve remain catalog pins from discovery — do not invent them. The SDK does not infer a `speed` / `coverage` differentiator from those facts.

`mark_type` is copied from the **resolved** `marks.profiles[].type`, not from `products.json` `mark_type`.

`requires` is the union of product + selected services + features + that mark profile. Tokens: `ADDRESS_SENDER`, `ADDRESS_RECIPIENT`. Unknown catalog tokens are invalid data.

`available_services` and `services` are different concepts. Do not collapse them.

Several valid options for the same kind is normal. Do not silently pick. Resolve without a choice when more than one service option matches → `PORTO_SERVICE_AMBIGUOUS` with candidates (same pattern as `PORTO_PRODUCT_AMBIGUOUS`). An explicit `ServiceKind` that is satisfied by neither a catalog service nor a product-included capability → `PORTO_SERVICE_UNSUPPORTED`. Do not omit the kind and continue.

## `PortoMarkRequest`

- `porto` (required)
- `sender?`, `recipient?`
- `design?`
- `idempotency?`
- `mime?`

No request `id`. Result identity is `PortoMark.id`. `mark` / internal `prepare` copies `porto.amount` into `MarkRequest.value`. It must not add service prices at execution.

## `Pricing` (`price()`)

Must carry: `product_id` / `productId`, `zone_id` / `zoneId`, `weight`, `amount`, `currency`, `components`. Same compose rules as `Porto`. No `base_price` / `basePrice`. No embedded `PortoZone` on Pricing — identifier only.

## `mark(one | many)`

Same verb, language overloads. No public `markMany`, batch, or report types.

**Ownership (SDK vs consumer app):**

```text
PORTO SDK                         CONSUMER APP
─────────────────────             ─────────────────────────
product/service resolution        mail/envelope identity
pricing                           document/page composition
restrictions                      address placement
mark profile                      stamp/label placement
requires                          which jobs to batch
provider execution                grouping strategy
mark(one | many)                  map jobs ↔ batch positions
positional I/O preservation       persist marks
provider request construction     business-level retries
```

- SDK knows what a provider/wire can execute and how to build a correct request/output.
- The consumer app decides which letters to batch and how to correlate returned marks to envelopes/jobs.
- Core and adapters must **not** group / sort / partition Portos, require Porto equality, or invent correlation ids.
- Internetmarke fact: multi-position cart + **positional** request/response (no consumer correlation id).

1. many list must be non-empty (`PORTO_MARK_INVALID` if empty)
2. Adapter may pass any mix when the wire call can be built; preserve input order; return one `PortoMark` per input slot
3. Provider/HTTP cart failure → ordinary execution error (typically `PORTO_MARK_FAILED` with upstream details) — not a grouping / mismatch / many-unsupported family

No sort, partition, or regroup. Consumer app groups.

### Addresses (profile `requires`, not services)

Address requirements stay in the SDK. They derive from the **selected mark/output profile**, not from services like `registered`:

| Output | Rule |
|---|---|
| `stamp` / franking-zone wire layout | Address not required (CIS: Einschreiben encoded in franking graphic) |
| `label` / address-zone wire layout | Canonical SDK output expects address data → `Porto.requires` contains `ADDRESS_*` when that profile is selected |

Provider may technically accept empty address fields; SDK still refuses a meaningless empty address-zone label when `requires` says so. Do not promote wire layout tokens (`FRANKING_ZONE` / `ADDRESS_ZONE`) to the public SDK.

Deutsche Post CIS **R-202802**: descriptive addresses; franking vs address-zone; consumer may buy stamp now and compose labels later (Sperrflächen); **~10-day** backend deletion of address data on DP URL/Portokasse — consumer apps must persist marks at purchase.

Requirement validation is central (catalog address forms):

- missing required sender → `PORTO_ADDRESS_SENDER_REQUIRED`
- invalid sender → `PORTO_ADDRESS_SENDER_INVALID`
- missing required recipient → `PORTO_ADDRESS_RECIPIENT_REQUIRED`
- invalid recipient → `PORTO_ADDRESS_RECIPIENT_INVALID`
- requirement absent → do not require; do not forward unused addresses as domain knowledge

Serialized error values are the uppercase codes themselves. There is no generic `PORTO_ADDRESS_INVALID`.

## Envelope `layout()`

`layout()` is a join of independent facts. Composition policy belongs to the consumer.

```text
Envelope face
+ optional jurisdiction window
+ optional provider mark facts
= Layout facts
```

- Face `width` / `height` (millimetres; porto-data schema is unit SoT) from `envelopes.json`
- `window?: { x, y, width, height }` from `layouts.json` when a jurisdiction is supplied and a row exists — a window, not an address-placement rule
- `mark?` when a provider profile exists: `type` (`stamp` | `label`), catalog `size`, and `placement` when `marks.json` publishes it for that envelope

Absence is omission, never fallback:

- no jurisdiction → no window
- missing layouts row or unsupported window → omit `window` (still return face; still attach `mark` when the profile resolves)
- unknown envelope id → `PORTO_DATA_NOT_FOUND`
- omit `placement` when the envelope is unknown to marks or no row exists; never `{0,0}`

`list()` is global faces only (no jurisdiction argument, no `has_window`). `geometry()` is the same face plus optional window rectangle. `get_mark` / `getMark` returns the same mark facts; drop `jurisdiction`; without an envelope id, omit `placement`.

No `restricted_areas`. No aliases (`get_layout` / `getLayout`, `get_geometry` / `getGeometry`, `catalog` / `list_catalog` / `listCatalog`). The SDK must not infer one provider or jurisdiction’s geometry from another.

## `PortoMark` public fields

`id`, `content`, `content_type` / `contentType` (`MarkOutputMime`), `amount`, `currency`, `generated_at` / `generatedAt`, `external_id` / `externalId`, `tracking_number` / `trackingNumber`, `provider`, `wire`

Not public on `PortoMark`: `provider_raw`, `pre_calculated_price`, `price_difference`, `price_mismatch`, `mark_profile_id` (adapter/internal only).

## Root exports

Allowed families: `PortoClient` / `ProviderClient`, config types, resolution + mark types, `PriceComponent`, envelope identify results (`Match` variants), vocabulary, errors.

Not root-exported: `DEFAULT_PROVIDER`, `PortoResolver`, `PortoExecution`, `EnvelopeResolverService`, `RestrictionsService`, `NormalizedPortoConfig`, `HttpClient`, `loadPortoConfigFromEnv`, `MarkRequest`, `MarkExecution`, `prepare`, `execute`, adapter REST schemas, `voucherLayout`, `FRANKING_ZONE`, `ADDRESS_ZONE`.

`client.provider(id)` always takes an explicit provider id. There is no public default provider.

Adapter `MarkRequest` is internal only. It must not compete with `PortoMarkRequest` as product identity.

## Notes

- Address validation is `client.address.validate`. Dimensions validation uses an internal validation service.
- Public `price()` takes destination facts (`country_code` / `countryCode`, weight). Product advice types (`Advice` / `Estimate`) are discovery helpers, not a second quote API.
- **`PortoMark.wire`** is the integration that ran. `ExecutionParameters.wire` is an optional pin. `Porto` and `PortoMarkRequest` have no `wire`.
- Physical constraint code is `PORTO_TOO_HEAVY` (weight-tier / zone max). There is no dimension PortoError until an independent physical-domain check exists.

## Provider translation (adapter-only)

Canonical `stamp` → Deutsche Post Internetmarke `FRANKING_ZONE`

Canonical `label` → Deutsche Post Internetmarke `ADDRESS_ZONE`

Do not invent a generic public `presentation` for those tokens.

---

## Naming map

One canonical name per concept. Python snake_case / TypeScript camelCase only.

| Concept | Porto Data | Python | TypeScript |
| --- | --- | --- | --- |
| Mark profile kind | `marks.profiles[].type` (`stamp` \| `label`) | loader `MarkProfile.mark_type` ← `type` | loader `markType` / `mark_type` ← `type` |
| Resolved mark kind | — | `Porto.mark_type` | `Porto.markType` |
| Requirement tokens | `requires[]` | `Requirement` / `Porto.requires` | `Requirement` / `Porto.requires` |
| Sender token | `ADDRESS_SENDER` | `ADDRESS_SENDER` | `ADDRESS_SENDER` |
| Recipient token | `ADDRESS_RECIPIENT` | `ADDRESS_RECIPIENT` | `ADDRESS_RECIPIENT` |
| Service/feature grouping | `kind` | `ServiceKind` / `FeatureKind` | `ServiceKind` / `FeatureKind` |
| Catalog service row | `services[]` | `Service` | `Service` |
| Catalog feature row | `features[]` | `Feature` | `Feature` |
| Catalog service possibilities | services catalog | `Porto.available_services` (`Service[]`) | `Porto.availableServices` (`Service[]`) |
| Requested service grouping | — | `ResolutionRequest.services` | `ResolutionRequest.services` |
| Chosen service option | catalog `id` | `ResolutionRequest.service_ids` / bound `Porto.service_ids` | `ResolutionRequest.serviceIds` / bound `Porto.serviceIds` |
| Selected service kinds | — | `Porto.services` | `Porto.services` |
| Authoritative quote | catalog cents | `Porto.amount` / `Pricing.amount` | `Porto.amount` / `Pricing.amount` |
| Quote breakdown | — | `Porto.components` / `Pricing.components` (`PriceComponent`) | `Porto.components` / `Pricing.components` (`PriceComponent`) |
| Public mark input | — | `PortoMarkRequest` | `PortoMarkRequest` |
| Mark result | — | `PortoMark` | `PortoMark` |
| Used integration | porto-data `execution.json` `wire` | `PortoMark.wire` | `PortoMark.wire` |
| Destination restriction lookup | — | `client.restrictions.check` | `client.restrictions.check` |

`available_services` (option rows) and `services` (selected kinds) are two concepts. `service_ids` are catalog identity pins, never kinds.
