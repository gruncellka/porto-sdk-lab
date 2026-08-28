# BDD step parity report (`@sdk`)

## 0.0.1 behavior matrix

Shared BDD proves the public SDK contract. Provider BDD proves each adapter/catalog maps that contract to real product ids. Step-file layout may differ; the behaviors below must exist in both SDKs.

```text
Behavior                              Python   TypeScript
core resolve                          yes      yes
price == resolved amount              yes      yes
price components sum                  yes      yes
service unique bind                   yes      yes
service ambiguity                     yes      yes
service unsupported                   yes      yes
service incompatibility (DE)          yes      yes
restrictions country facts            yes      yes
restrictions region select            yes      yes
restrictions routing CY               yes      yes
restrictions country-only warn        yes      yes
standalone restrictions.check         yes      yes
address validation                    yes      yes
mark requirements                     yes      yes
many-mark errors                      yes      yes
metadata/envelopes global ownership   yes      yes
DE provider product resolution        yes      yes
DE provider services                  yes      yes
DE provider pricing (countryCode)     yes      yes
FR provider resolution                yes      yes
CH provider resolution                yes      yes
UA provider resolution                yes      yes
```

Coverage:

- Core: `features/sdk/core/resolution.feature`, `restrictions.feature`, `validation.feature`, `metadata.feature`, `cli.feature`
- CLI provider catalogs: `features/sdk/providers/*/cli.feature`
- DE: `features/sdk/providers/deutschepost/{resolution,services,pricing,products}.feature`
- FR: `features/sdk/providers/laposte/resolution.feature`
- CH: `features/sdk/providers/swisspost/resolution.feature`
- UA: `features/sdk/providers/ukrposhta/resolution.feature`

Unit layer (public API, mirrors core BDD):

- Python: `tests/resolution/test_public_contract.py`, `test_quote.py`, `test_restrictions_surface.py`
- TypeScript: `tests/resolution/public_contract.test.ts`, `quote.test.ts`, `restrictions_surface.test.ts`
---

Generated at `2026-08-26T21:29:43Z` by `scripts/parity-report.py`.

Compares porto-features `@sdk` scenario steps against Python pytest-bdd
and TypeScript Cucumber step definitions in both SDK repos.

The generated inventory below is a step-string dump; the **0.0.1 behavior matrix**
above is the semantic contract for the freeze.

## Summary

- Features scanned: **21**
- Unique steps: **137**
- Covered in both SDKs: **137**
- Python only: **0**
- TypeScript only: **0**
- Missing in both SDKs: **0**

## Per-feature steps

### `core/cli.feature`

- `And I have a Porto SDK client initialized` — Py: **yes**, TS: **yes**
- `And I have porto-data available` — Py: **yes**, TS: **yes**
- `And the "data_path" fields should match` — Py: **yes**, TS: **yes**
- `And the products array should be stored for comparison` — Py: **yes**, TS: **yes**
- `And the result should have field "entities"` — Py: **yes**, TS: **yes**
- `And the result should have field "errors" as array` — Py: **yes**, TS: **yes**
- `And the result should have field "generated_at"` — Py: **yes**, TS: **yes**
- `And the result should have field "retries" as number` — Py: **yes**, TS: **yes**
- `And the result should have field "timeout" as number` — Py: **yes**, TS: **yes**
- `Given I have a valid address JSON data` — Py: **yes**, TS: **yes**
- `Given I have porto-data available` — Py: **yes**, TS: **yes**
- `Given provider is "deutschepost"` — Py: **yes**, TS: **yes**
- `Given provider is "laposte"` — Py: **yes**, TS: **yes**
- `Given provider is "swisspost"` — Py: **yes**, TS: **yes**
- `Given provider is "ukrposhta"` — Py: **yes**, TS: **yes**
- `Then the products array should differ from the stored products array` — Py: **yes**, TS: **yes**
- `Then the result should be stored for comparison` — Py: **yes**, TS: **yes**
- `Then the result should have array "products"` — Py: **yes**, TS: **yes**
- `Then the result should have field "data_path"` — Py: **yes**, TS: **yes**
- `Then the result should have field "valid" with value true` — Py: **yes**, TS: **yes**
- `Then the result should have field "version"` — Py: **yes**, TS: **yes**
- `Then the results should have same structure` — Py: **yes**, TS: **yes**
- `When I call CLI config command` — Py: **yes**, TS: **yes**
- `When I call CLI data info command` — Py: **yes**, TS: **yes**
- `When I call CLI data products command` — Py: **yes**, TS: **yes**
- `When I call CLI validate address command` — Py: **yes**, TS: **yes**

### `core/data.feature`

- `And I have a Porto SDK client initialized` — Py: **yes**, TS: **yes**
- `And each envelope should have field "height_mm"` — Py: **yes**, TS: **yes**
- `And each envelope should have field "id"` — Py: **yes**, TS: **yes**
- `And each envelope should have field "width"` — Py: **yes**, TS: **yes**
- `And providers should include provider "deutschepost"` — Py: **yes**, TS: **yes**
- `And providers should include provider "laposte"` — Py: **yes**, TS: **yes**
- `And providers should include provider "swisspost"` — Py: **yes**, TS: **yes**
- `And providers should include provider "ukrposhta"` — Py: **yes**, TS: **yes**
- `And the envelopes array should contain envelope with id "C4"` — Py: **yes**, TS: **yes**
- `And the envelopes array should contain envelope with id "C5"` — Py: **yes**, TS: **yes**
- `And the envelopes array should contain envelope with id "C6"` — Py: **yes**, TS: **yes**
- `And the envelopes array should contain envelope with id "DL"` — Py: **yes**, TS: **yes**
- `And the letter weight is 20 grams` — Py: **yes**, TS: **yes**
- `Given I have porto-data available` — Py: **yes**, TS: **yes**
- `Given I want to send a letter to country "DE"` — Py: **yes**, TS: **yes**
- `Then I should get a non-empty list of product options` — Py: **yes**, TS: **yes**
- `Then I should get an array of envelopes` — Py: **yes**, TS: **yes**
- `Then I should get providers information` — Py: **yes**, TS: **yes**
- `When I inspect envelopes data` — Py: **yes**, TS: **yes**
- `When I inspect the provider registry` — Py: **yes**, TS: **yes**
- `When I list product options` — Py: **yes**, TS: **yes**

### `core/errors.feature`

- `And I have a Porto SDK client initialized` — Py: **yes**, TS: **yes**
- `And I have access to porto-data` — Py: **yes**, TS: **yes**
- `And I should get Porto error code "PORTO_DESTINATION_INVALID"` — Py: **yes**, TS: **yes**
- `And I should get Porto error code "PORTO_PRODUCT_AMBIGUOUS"` — Py: **yes**, TS: **yes**
- `And I want to send a letter to country "FR"` — Py: **yes**, TS: **yes**
- `And the letter weight is 20 grams` — Py: **yes**, TS: **yes**
- `And the letter weight is 50000 grams` — Py: **yes**, TS: **yes**
- `Given I want to send a letter to country "DE"` — Py: **yes**, TS: **yes**
- `Given I want to send a letter to country "XX"` — Py: **yes**, TS: **yes**
- `Given provider is "deutschepost"` — Py: **yes**, TS: **yes**
- `Given provider is "laposte"` — Py: **yes**, TS: **yes**
- `Then I should get Porto error code "PORTO_TOO_HEAVY"` — Py: **yes**, TS: **yes**
- `Then the resolution should be invalid` — Py: **yes**, TS: **yes**
- `When I resolve the letter` — Py: **yes**, TS: **yes**

### `core/mark.feature`

- `And I have access to porto-data` — Py: **yes**, TS: **yes**
- `And every returned mark should have an id` — Py: **yes**, TS: **yes**
- `And recipient fails the jurisdiction form` — Py: **yes**, TS: **yes**
- `And recipient is missing` — Py: **yes**, TS: **yes**
- `And recipient is valid` — Py: **yes**, TS: **yes**
- `And sender and recipient are valid` — Py: **yes**, TS: **yes**
- `And sender fails the jurisdiction form` — Py: **yes**, TS: **yes**
- `And sender is missing` — Py: **yes**, TS: **yes**
- `And sender is valid` — Py: **yes**, TS: **yes**
- `And the returned mark ids should be distinct` — Py: **yes**, TS: **yes**
- `Given I have a Porto SDK client initialized` — Py: **yes**, TS: **yes**
- `Given a resolved Porto that requires ADDRESS_SENDER and ADDRESS_RECIPIENT` — Py: **yes**, TS: **yes**
- `Given a resolved stamp Porto` — Py: **yes**, TS: **yes**
- `Given the resolved Porto includes registered mail` — Py: **yes**, TS: **yes**
- `Then I should get Porto error code "PORTO_ADDRESS_RECIPIENT_INVALID"` — Py: **yes**, TS: **yes**
- `Then I should get Porto error code "PORTO_ADDRESS_RECIPIENT_REQUIRED"` — Py: **yes**, TS: **yes**
- `Then I should get Porto error code "PORTO_ADDRESS_SENDER_INVALID"` — Py: **yes**, TS: **yes**
- `Then I should get Porto error code "PORTO_ADDRESS_SENDER_REQUIRED"` — Py: **yes**, TS: **yes**
- `Then mark creation should succeed` — Py: **yes**, TS: **yes**
- `Then three marks should be returned` — Py: **yes**, TS: **yes**
- `When I attempt to create a mark` — Py: **yes**, TS: **yes**
- `When I create a mark` — Py: **yes**, TS: **yes**
- `When I create a mark without sender or recipient` — Py: **yes**, TS: **yes**
- `When I create three equivalent marks together` — Py: **yes**, TS: **yes**

### `core/metadata.feature`

- `And the envelopes list should contain envelope id "C6"` — Py: **yes**, TS: **yes**
- `And the providers list should contain provider id "laposte"` — Py: **yes**, TS: **yes**
- `And the providers list should contain provider id "swisspost"` — Py: **yes**, TS: **yes**
- `And the providers list should contain provider id "ukrposhta"` — Py: **yes**, TS: **yes**
- `Given I have a Porto SDK client initialized` — Py: **yes**, TS: **yes**
- `Then the envelopes list should contain envelope id "DL"` — Py: **yes**, TS: **yes**
- `Then the providers list should contain provider id "deutschepost"` — Py: **yes**, TS: **yes**
- `When I list envelope catalog` — Py: **yes**, TS: **yes**
- `When I list postal providers` — Py: **yes**, TS: **yes**

### `core/resolution.feature`

- `And I get the price` — Py: **yes**, TS: **yes**
- `And I have a Porto SDK client initialized` — Py: **yes**, TS: **yes**
- `And I have access to porto-data` — Py: **yes**, TS: **yes**
- `And I should get Porto error code "PORTO_SERVICE_AMBIGUOUS"` — Py: **yes**, TS: **yes**
- `And I should get Porto error code "PORTO_SERVICE_UNSUPPORTED"` — Py: **yes**, TS: **yes**
- `And a concrete product id is pinned from catalog options` — Py: **yes**, TS: **yes**
- `And envelope id is "DL"` — Py: **yes**, TS: **yes**
- `And service kind is "registered"` — Py: **yes**, TS: **yes**
- `And service kind is "registered_return_receipt"` — Py: **yes**, TS: **yes**
- `And service kind is "thickness"` — Py: **yes**, TS: **yes**
- `And the letter weight is 20 grams` — Py: **yes**, TS: **yes**
- `And the quoted amount should equal the resolved amount` — Py: **yes**, TS: **yes**
- `And the resolved Porto components should sum to the resolved amount` — Py: **yes**, TS: **yes**
- `And the resolved Porto should have a product id` — Py: **yes**, TS: **yes**
- `And the resolved Porto should have the pinned product id` — Py: **yes**, TS: **yes**
- `And the resolved Porto should include a restrictions result` — Py: **yes**, TS: **yes**
- `And the resolved Porto should include service kind "registered_return_receipt"` — Py: **yes**, TS: **yes**
- `And the resolved amount should be a positive number` — Py: **yes**, TS: **yes**
- `And the resolved currency is present` — Py: **yes**, TS: **yes**
- `Given I want to send a letter to country "DE"` — Py: **yes**, TS: **yes**
- `Given provider is "deutschepost"` — Py: **yes**, TS: **yes**
- `Then the quoted amount should equal the resolved amount` — Py: **yes**, TS: **yes**
- `Then the resolution should be invalid` — Py: **yes**, TS: **yes**
- `Then the resolution should be valid` — Py: **yes**, TS: **yes**
- `When I resolve the letter` — Py: **yes**, TS: **yes**

### `core/restrictions.feature`

- `And I check destination restrictions` — Py: **yes**, TS: **yes**
- `And I have access to porto-data` — Py: **yes**, TS: **yes**
- `And I want to send a letter to country "CY"` — Py: **yes**, TS: **yes**
- `And I want to send a letter to country "DE"` — Py: **yes**, TS: **yes**
- `And I want to send a letter to country "FR"` — Py: **yes**, TS: **yes**
- `And I want to send a letter to country "UA"` — Py: **yes**, TS: **yes**
- `And destination region code is "CY-01"` — Py: **yes**, TS: **yes**
- `And destination region code is "UA-32"` — Py: **yes**, TS: **yes**
- `And destination region code is "UA-43"` — Py: **yes**, TS: **yes**
- `And destination region code is "UA-65"` — Py: **yes**, TS: **yes**
- `And the letter weight is 20 grams` — Py: **yes**, TS: **yes**
- `And the resolved Porto restrictions should have no impact` — Py: **yes**, TS: **yes**
- `And the resolved Porto restrictions list should be empty` — Py: **yes**, TS: **yes**
- `And the resolved Porto restrictions should match standalone restriction lookup` — Py: **yes**, TS: **yes**
- `And the resolved Porto should include a restrictions result` — Py: **yes**, TS: **yes**
- `And the restriction result impact should be "warn"` — Py: **yes**, TS: **yes**
- `And the restriction result impact should be "block"` — Py: **yes**, TS: **yes**
- `And the restriction result impact should be null` — Py: **yes**, TS: **yes**
- `And the restriction result list should be empty` — Py: **yes**, TS: **yes**
- `And the restriction result should include legal region "UA-14"` — Py: **yes**, TS: **yes**
- `And the restriction result should include legal region "UA-43"` — Py: **yes**, TS: **yes**
- `And the restriction result should include legal region "UA-65"` — Py: **yes**, TS: **yes**
- `And the restriction result should not include legal region "UA-43"` — Py: **yes**, TS: **yes**
- `And the restriction result legal region "UA-65" should be partial` — Py: **yes**, TS: **yes**
- `And the restriction result legal jurisdictions should include "eur-lex.europa.eu"` — Py: **yes**, TS: **yes**
- `And the restriction result legal jurisdictions should include "seco.admin.ch"` — Py: **yes**, TS: **yes**
- `And the restriction result legal jurisdictions should include "zakon.rada.gov.ua"` — Py: **yes**, TS: **yes**
- `And the restriction result legal jurisdictions should not include "eur-lex.europa.eu"` — Py: **yes**, TS: **yes**
- `And the restriction result legal jurisdictions should not include "seco.admin.ch"` — Py: **yes**, TS: **yes**
- `And the restriction result legal jurisdictions should not include "zakon.rada.gov.ua"` — Py: **yes**, TS: **yes**
- `And the restriction result should include routing region "CY-01"` — Py: **yes**, TS: **yes**
- `And the restriction result routing region "CY-01" should be partial` — Py: **yes**, TS: **yes**
- `And the restriction result routing authority should be "CY"` — Py: **yes**, TS: **yes**
- `Given I have a Porto SDK client initialized` — Py: **yes**, TS: **yes**
- `Given provider is "<provider>"` — Py: **yes**, TS: **yes**
- `Given provider is "deutschepost"` — Py: **yes**, TS: **yes**
- `Given provider is "swisspost"` — Py: **yes**, TS: **yes**
- `Given provider is "ukrposhta"` — Py: **yes**, TS: **yes**
- `Then the resolution should be valid` — Py: **yes**, TS: **yes**
- `When I check destination restrictions` — Py: **yes**, TS: **yes**
- `When I resolve the letter` — Py: **yes**, TS: **yes**

### `core/validation.feature`

- `And I have access to porto-data` — Py: **yes**, TS: **yes**
- `And I should get an error about invalid address` — Py: **yes**, TS: **yes**
- `And I should get an error about invalid country code` — Py: **yes**, TS: **yes**
- `And I should get errors about missing required fields` — Py: **yes**, TS: **yes**
- `And country code "DE"` — Py: **yes**, TS: **yes**
- `And country code "XX"` — Py: **yes**, TS: **yes**
- `And house number "123"` — Py: **yes**, TS: **yes**
- `And locality "Berlin"` — Py: **yes**, TS: **yes**
- `And missing postal code` — Py: **yes**, TS: **yes**
- `And missing street` — Py: **yes**, TS: **yes**
- `And postal code "10115"` — Py: **yes**, TS: **yes**
- `And street "Main Street"` — Py: **yes**, TS: **yes**
- `And there should be no errors` — Py: **yes**, TS: **yes**
- `Given I have a Porto SDK client initialized` — Py: **yes**, TS: **yes**
- `Given I have an address with name "John Doe"` — Py: **yes**, TS: **yes**
- `Given I have destination address fixture "<fixture>"` — Py: **yes**, TS: **yes**
- `Then the validation should fail` — Py: **yes**, TS: **yes**
- `Then the validation should pass` — Py: **yes**, TS: **yes**
- `When I validate the address` — Py: **yes**, TS: **yes**

### `providers/deutschepost/cli.feature`

- `And I have a Porto SDK client initialized` — Py: **yes**, TS: **yes**
- `And I have porto-data available` — Py: **yes**, TS: **yes**
- `And the "data_path" fields should match` — Py: **yes**, TS: **yes**
- `And the products array should contain product with id "kompaktbrief"` — Py: **yes**, TS: **yes**
- `And the products array should contain product with id "standardbrief"` — Py: **yes**, TS: **yes**
- `And the result should have field "amount" as number` — Py: **yes**, TS: **yes**
- `And the result should have field "currency" with value "EUR"` — Py: **yes**, TS: **yes**
- `And the result should have field "data_path"` — Py: **yes**, TS: **yes**
- `And the result should have field "is_valid" with value true` — Py: **yes**, TS: **yes**
- `And the result should have field "price" as number` — Py: **yes**, TS: **yes**
- `And the result should have field "weight" with value 20` — Py: **yes**, TS: **yes**
- `And the result should have field "zone" with nested "id" "domestic"` — Py: **yes**, TS: **yes**
- `And the result should have field "zone" with nested "id" "world"` — Py: **yes**, TS: **yes**
- `And the result should have field "zone" with value "zone_1_eu"` — Py: **yes**, TS: **yes**
- `And the services array should contain service with id "einschreiben"` — Py: **yes**, TS: **yes**
- `And the services array should contain service with id "einschreiben_einwurf"` — Py: **yes**, TS: **yes**
- `And the zones array should contain zone with id "domestic"` — Py: **yes**, TS: **yes**
- `And the zones array should contain zone with id "world"` — Py: **yes**, TS: **yes**
- `And the zones array should contain zone with id "zone_1_eu"` — Py: **yes**, TS: **yes**
- `Given provider is "deutschepost"` — Py: **yes**, TS: **yes**
- `Then the result should be stored for comparison` — Py: **yes**, TS: **yes**
- `Then the result should have array "products"` — Py: **yes**, TS: **yes**
- `Then the result should have array "services"` — Py: **yes**, TS: **yes**
- `Then the result should have array "zones"` — Py: **yes**, TS: **yes**
- `Then the result should have field "product"` — Py: **yes**, TS: **yes**
- `Then the result should have field "product" with nested "id" "standardbrief"` — Py: **yes**, TS: **yes**
- `Then the result should have field "product" with value "standardbrief"` — Py: **yes**, TS: **yes**
- `Then the result should have field "provider" with value "deutschepost"` — Py: **yes**, TS: **yes**
- `Then the results should be identical` — Py: **yes**, TS: **yes**
- `Then the results should have same structure` — Py: **yes**, TS: **yes**
- `When I call CLI config command` — Py: **yes**, TS: **yes**
- `When I call CLI data price command with product "standardbrief" zone "zone_1_eu" weight 20` — Py: **yes**, TS: **yes**
- `When I call CLI data products command` — Py: **yes**, TS: **yes**
- `When I call CLI data services command` — Py: **yes**, TS: **yes**
- `When I call CLI data zones command` — Py: **yes**, TS: **yes**
- `When I call CLI price command with country "DE" weight 20` — Py: **yes**, TS: **yes**
- `When I call CLI price command with country "US" weight 20` — Py: **yes**, TS: **yes**

### `providers/deutschepost/pricing.feature`

- `And I have a Porto SDK client initialized` — Py: **yes**, TS: **yes**
- `And I have access to porto-data` — Py: **yes**, TS: **yes**
- `And the currency should be "EUR"` — Py: **yes**, TS: **yes**
- `And the letter weight is 100 grams` — Py: **yes**, TS: **yes**
- `And the letter weight is 20 grams` — Py: **yes**, TS: **yes**
- `And the letter weight is 30 grams` — Py: **yes**, TS: **yes**
- `And the letter weight is 501 grams` — Py: **yes**, TS: **yes**
- `And the letter weight is <weight> grams` — Py: **yes**, TS: **yes**
- `And the price should be greater than 0` — Py: **yes**, TS: **yes**
- `And the quoted components should sum to the quoted amount` — Py: **yes**, TS: **yes**
- `And the quoted product id should be "grossbrief"` — Py: **yes**, TS: **yes**
- `And the quoted product id should be "kompaktbrief"` — Py: **yes**, TS: **yes**
- `And the quoted product id should be "maxibrief"` — Py: **yes**, TS: **yes**
- `And the quoted product id should be "standardbrief"` — Py: **yes**, TS: **yes**
- `And the resolved zone id should be "<expected_zone>"` — Py: **yes**, TS: **yes**
- `And the resolved zone id should be "domestic"` — Py: **yes**, TS: **yes**
- `And the resolved zone id should be "world"` — Py: **yes**, TS: **yes**
- `And the resolved zone id should be "zone_1_eu"` — Py: **yes**, TS: **yes**
- `Given I want to send a letter to country "<country_code>"` — Py: **yes**, TS: **yes**
- `Given I want to send a letter to country "DE"` — Py: **yes**, TS: **yes**
- `Given I want to send a letter to country "FR"` — Py: **yes**, TS: **yes**
- `Given I want to send a letter to country "US"` — Py: **yes**, TS: **yes**
- `Given provider is "deutschepost"` — Py: **yes**, TS: **yes**
- `Then I should get a price in cents` — Py: **yes**, TS: **yes**
- `Then I should store the result` — Py: **yes**, TS: **yes**
- `Then the prices should be identical` — Py: **yes**, TS: **yes**
- `Then the quoted amount should be 110` — Py: **yes**, TS: **yes**
- `Then the quoted amount should be 125` — Py: **yes**, TS: **yes**
- `Then the quoted amount should be 180` — Py: **yes**, TS: **yes**
- `Then the quoted amount should be 290` — Py: **yes**, TS: **yes**
- `Then the quoted amount should be 95` — Py: **yes**, TS: **yes**
- `When I get the price` — Py: **yes**, TS: **yes**
- `When I get the price again with the same parameters` — Py: **yes**, TS: **yes**

### `providers/deutschepost/products.feature`

- `And I have a Porto SDK client initialized` — Py: **yes**, TS: **yes**
- `And I have access to porto-data` — Py: **yes**, TS: **yes**
- `And the letter weight is 1700 grams` — Py: **yes**, TS: **yes**
- `And the letter weight is 501 grams` — Py: **yes**, TS: **yes**
- `Given I want to send a letter to country "DE"` — Py: **yes**, TS: **yes**
- `Given I want to send a letter to country "FR"` — Py: **yes**, TS: **yes**
- `Given provider is "deutschepost"` — Py: **yes**, TS: **yes**
- `Then product options should include "maxibrief"` — Py: **yes**, TS: **yes**
- `Then product options should include "maxibrief_ausland"` — Py: **yes**, TS: **yes**
- `When I list product options` — Py: **yes**, TS: **yes**

### `providers/deutschepost/resolution.feature`

- `And I have a Porto SDK client initialized` — Py: **yes**, TS: **yes**
- `And I have access to porto-data` — Py: **yes**, TS: **yes**
- `And I should get Porto error code "PORTO_DESTINATION_INVALID"` — Py: **yes**, TS: **yes**
- `And I should get Porto error code "PORTO_TOO_HEAVY"` — Py: **yes**, TS: **yes**
- `And I should get weight tier "W0020"` — Py: **yes**, TS: **yes**
- `And I should get weight tier "W0050"` — Py: **yes**, TS: **yes**
- `And I should get weight tier "W0500"` — Py: **yes**, TS: **yes**
- `And I should get weight tier "W1000"` — Py: **yes**, TS: **yes**
- `And I should get weight tier "W2000"` — Py: **yes**, TS: **yes**
- `And I should get zone with id "domestic"` — Py: **yes**, TS: **yes**
- `And I should get zone with id "world"` — Py: **yes**, TS: **yes**
- `And I should get zone with id "zone_1_eu"` — Py: **yes**, TS: **yes**
- `And I should get zone with id "zone_2_europe"` — Py: **yes**, TS: **yes**
- `And delivery hint days max should be 2` — Py: **yes**, TS: **yes**
- `And delivery hint span should be "between"` — Py: **yes**, TS: **yes**
- `And delivery hint weekdays should be "mon_sat"` — Py: **yes**, TS: **yes**
- `And the letter weight is 100 grams` — Py: **yes**, TS: **yes**
- `And the letter weight is 1700 grams` — Py: **yes**, TS: **yes**
- `And the letter weight is 20 grams` — Py: **yes**, TS: **yes**
- `And the letter weight is 2500 grams` — Py: **yes**, TS: **yes**
- `And the letter weight is 30 grams` — Py: **yes**, TS: **yes**
- `And the letter weight is 501 grams` — Py: **yes**, TS: **yes**
- `And the resolution should be valid` — Py: **yes**, TS: **yes**
- `And the resolution should include currency "EUR"` — Py: **yes**, TS: **yes**
- `Given I want to send a letter to country "DE"` — Py: **yes**, TS: **yes**
- `Given I want to send a letter to country "FR"` — Py: **yes**, TS: **yes**
- `Given I want to send a letter to country "UA"` — Py: **yes**, TS: **yes**
- `Given I want to send a letter to country "US"` — Py: **yes**, TS: **yes**
- `Given I want to send a letter to country "XX"` — Py: **yes**, TS: **yes**
- `Given provider is "deutschepost"` — Py: **yes**, TS: **yes**
- `Then I should get product with id "grossbrief"` — Py: **yes**, TS: **yes**
- `Then I should get product with id "kompaktbrief"` — Py: **yes**, TS: **yes**
- `Then I should get product with id "maxibrief"` — Py: **yes**, TS: **yes**
- `Then I should get product with id "maxibrief_ausland"` — Py: **yes**, TS: **yes**
- `Then I should get product with id "standardbrief"` — Py: **yes**, TS: **yes**
- `Then the resolution should be invalid` — Py: **yes**, TS: **yes**
- `Then the resolved amount should be a positive number` — Py: **yes**, TS: **yes**
- `When I resolve the letter` — Py: **yes**, TS: **yes**

### `providers/deutschepost/services.feature`

- `And I have a Porto SDK client initialized` — Py: **yes**, TS: **yes**
- `And I have access to porto-data` — Py: **yes**, TS: **yes**
- `And I should get Porto error code "PORTO_SERVICES_INCOMPATIBLE"` — Py: **yes**, TS: **yes**
- `And I should get Porto error code "PORTO_SERVICE_AMBIGUOUS"` — Py: **yes**, TS: **yes**
- `And I should get product with id "standardbrief"` — Py: **yes**, TS: **yes**
- `And available services should include "einschreiben_einwurf"` — Py: **yes**, TS: **yes**
- `And available services should include "einschreiben_rueckschein"` — Py: **yes**, TS: **yes**
- `And each available service should have field "id"` — Py: **yes**, TS: **yes**
- `And each available service should have field "kind"` — Py: **yes**, TS: **yes**
- `And product id is "standardbrief"` — Py: **yes**, TS: **yes**
- `And service ids are "einschreiben"` — Py: **yes**, TS: **yes**
- `And service ids are "einschreiben,einschreiben_einwurf"` — Py: **yes**, TS: **yes**
- `And service kind is "registered"` — Py: **yes**, TS: **yes**
- `And service kind is "registered_return_receipt"` — Py: **yes**, TS: **yes**
- `And the letter weight is 20 grams` — Py: **yes**, TS: **yes**
- `And the resolved Porto should include service id "einschreiben"` — Py: **yes**, TS: **yes**
- `And the resolved Porto should include service kind "registered_return_receipt"` — Py: **yes**, TS: **yes**
- `And the resolved amount should be greater than the product component amount` — Py: **yes**, TS: **yes**
- `Given I want to send a letter to country "DE"` — Py: **yes**, TS: **yes**
- `Given provider is "deutschepost"` — Py: **yes**, TS: **yes**
- `Then available services should include "einschreiben"` — Py: **yes**, TS: **yes**
- `Then the resolution should be invalid` — Py: **yes**, TS: **yes**
- `Then the resolution should be valid` — Py: **yes**, TS: **yes**
- `Then the resolved Porto should include service id "einschreiben_rueckschein"` — Py: **yes**, TS: **yes**
- `When I resolve the letter` — Py: **yes**, TS: **yes**

### `providers/laposte/cli.feature`

- `And I have a Porto SDK client initialized` — Py: **yes**, TS: **yes**
- `And I have porto-data available` — Py: **yes**, TS: **yes**
- `And delivery preference is "cheapest"` — Py: **yes**, TS: **yes**
- `And the "data_path" fields should match` — Py: **yes**, TS: **yes**
- `And the products array should contain product with id "lettre_verte"` — Py: **yes**, TS: **yes**
- `And the products array should contain product with id "lettre_verte_suivie"` — Py: **yes**, TS: **yes**
- `And the result should have field "amount" as number` — Py: **yes**, TS: **yes**
- `And the result should have field "currency" with value "EUR"` — Py: **yes**, TS: **yes**
- `And the result should have field "data_path"` — Py: **yes**, TS: **yes**
- `And the result should have field "is_valid" with value true` — Py: **yes**, TS: **yes**
- `And the result should have field "price" as number` — Py: **yes**, TS: **yes**
- `And the result should have field "weight" with value 20` — Py: **yes**, TS: **yes**
- `And the result should have field "zone" with nested "id" "domestic"` — Py: **yes**, TS: **yes**
- `And the result should have field "zone" with nested "id" "world"` — Py: **yes**, TS: **yes**
- `And the result should have field "zone" with value "domestic"` — Py: **yes**, TS: **yes**
- `And the services array should contain service with id "avis_de_reception_national"` — Py: **yes**, TS: **yes**
- `And the services array should contain service with id "option_suivi"` — Py: **yes**, TS: **yes**
- `And the zones array should contain zone with id "domestic"` — Py: **yes**, TS: **yes**
- `And the zones array should contain zone with id "world"` — Py: **yes**, TS: **yes**
- `And the zones array should contain zone with id "zone_1_eu"` — Py: **yes**, TS: **yes**
- `Given product id is "lettre_verte"` — Py: **yes**, TS: **yes**
- `Given provider is "laposte"` — Py: **yes**, TS: **yes**
- `Then the result should be stored for comparison` — Py: **yes**, TS: **yes**
- `Then the result should have array "products"` — Py: **yes**, TS: **yes**
- `Then the result should have array "services"` — Py: **yes**, TS: **yes**
- `Then the result should have array "zones"` — Py: **yes**, TS: **yes**
- `Then the result should have field "product"` — Py: **yes**, TS: **yes**
- `Then the result should have field "product" with nested "id" "lettre_verte"` — Py: **yes**, TS: **yes**
- `Then the result should have field "product" with value "lettre_verte"` — Py: **yes**, TS: **yes**
- `Then the result should have field "provider" with value "laposte"` — Py: **yes**, TS: **yes**
- `Then the results should be identical` — Py: **yes**, TS: **yes**
- `Then the results should have same structure` — Py: **yes**, TS: **yes**
- `When I call CLI config command` — Py: **yes**, TS: **yes**
- `When I call CLI data price command with product "lettre_verte" zone "domestic" weight 20` — Py: **yes**, TS: **yes**
- `When I call CLI data products command` — Py: **yes**, TS: **yes**
- `When I call CLI data services command` — Py: **yes**, TS: **yes**
- `When I call CLI data zones command` — Py: **yes**, TS: **yes**
- `When I call CLI price command with country "FR" weight 20` — Py: **yes**, TS: **yes**
- `When I call CLI price command with country "US" weight 20` — Py: **yes**, TS: **yes**

### `providers/laposte/products.feature`

- `And I have a Porto SDK client initialized` — Py: **yes**, TS: **yes**
- `And I have access to porto-data` — Py: **yes**, TS: **yes**
- `And product options should include "lettre_services_plus"` — Py: **yes**, TS: **yes**
- `And the letter weight is 20 grams` — Py: **yes**, TS: **yes**
- `Given I want to send a letter to country "FR"` — Py: **yes**, TS: **yes**
- `Given provider is "laposte"` — Py: **yes**, TS: **yes**
- `Then product options should include "lettre_verte"` — Py: **yes**, TS: **yes**
- `When I list product options` — Py: **yes**, TS: **yes**

### `providers/laposte/resolution.feature`

- `And I have a Porto SDK client initialized` — Py: **yes**, TS: **yes**
- `And I have access to porto-data` — Py: **yes**, TS: **yes**
- `And I should get zone with id "domestic"` — Py: **yes**, TS: **yes**
- `And delivery preference is "fastest"` — Py: **yes**, TS: **yes**
- `And product id is "lettre_verte"` — Py: **yes**, TS: **yes**
- `And the letter weight is 20 grams` — Py: **yes**, TS: **yes**
- `And the resolution should be valid` — Py: **yes**, TS: **yes**
- `Given I want to send a letter to country "FR"` — Py: **yes**, TS: **yes**
- `Given provider is "laposte"` — Py: **yes**, TS: **yes**
- `Then I should get product with id "lettre_services_plus"` — Py: **yes**, TS: **yes**
- `Then I should get product with id "lettre_verte"` — Py: **yes**, TS: **yes**
- `Then resolution should be product ambiguous` — Py: **yes**, TS: **yes**
- `When I resolve the letter` — Py: **yes**, TS: **yes**

### `providers/swisspost/cli.feature`

- `And I have a Porto SDK client initialized` — Py: **yes**, TS: **yes**
- `And I have porto-data available` — Py: **yes**, TS: **yes**
- `And the "data_path" fields should match` — Py: **yes**, TS: **yes**
- `And the products array should contain product with id "a_post_standardbrief"` — Py: **yes**, TS: **yes**
- `And the products array should contain product with id "b_post_standardbrief"` — Py: **yes**, TS: **yes**
- `And the result should have field "amount" as number` — Py: **yes**, TS: **yes**
- `And the result should have field "currency" with value "CHF"` — Py: **yes**, TS: **yes**
- `And the result should have field "data_path"` — Py: **yes**, TS: **yes**
- `And the result should have field "is_valid" with value true` — Py: **yes**, TS: **yes**
- `And the result should have field "price" as number` — Py: **yes**, TS: **yes**
- `And the result should have field "weight" with value 20` — Py: **yes**, TS: **yes**
- `And the result should have field "zone" with nested "id" "domestic"` — Py: **yes**, TS: **yes**
- `And the result should have field "zone" with nested "id" "world"` — Py: **yes**, TS: **yes**
- `And the result should have field "zone" with value "domestic"` — Py: **yes**, TS: **yes**
- `And the services array should contain service with id "a_mail_plus"` — Py: **yes**, TS: **yes**
- `And the services array should contain service with id "zuschlag_dicke"` — Py: **yes**, TS: **yes**
- `And the zones array should contain zone with id "domestic"` — Py: **yes**, TS: **yes**
- `And the zones array should contain zone with id "world"` — Py: **yes**, TS: **yes**
- `And the zones array should contain zone with id "zone_1_eu"` — Py: **yes**, TS: **yes**
- `Given product id is "a_post_standardbrief"` — Py: **yes**, TS: **yes**
- `Given provider is "swisspost"` — Py: **yes**, TS: **yes**
- `Then the result should be stored for comparison` — Py: **yes**, TS: **yes**
- `Then the result should have array "products"` — Py: **yes**, TS: **yes**
- `Then the result should have array "services"` — Py: **yes**, TS: **yes**
- `Then the result should have array "zones"` — Py: **yes**, TS: **yes**
- `Then the result should have field "product"` — Py: **yes**, TS: **yes**
- `Then the result should have field "product" with nested "id" "a_post_standardbrief"` — Py: **yes**, TS: **yes**
- `Then the result should have field "product" with value "a_post_standardbrief"` — Py: **yes**, TS: **yes**
- `Then the result should have field "provider" with value "swisspost"` — Py: **yes**, TS: **yes**
- `Then the results should be identical` — Py: **yes**, TS: **yes**
- `Then the results should have same structure` — Py: **yes**, TS: **yes**
- `When I call CLI config command` — Py: **yes**, TS: **yes**
- `When I call CLI data price command with product "a_post_standardbrief" zone "domestic" weight 20` — Py: **yes**, TS: **yes**
- `When I call CLI data products command` — Py: **yes**, TS: **yes**
- `When I call CLI data services command` — Py: **yes**, TS: **yes**
- `When I call CLI data zones command` — Py: **yes**, TS: **yes**
- `When I call CLI price command with country "CH" weight 20` — Py: **yes**, TS: **yes**
- `When I call CLI price command with country "US" weight 20` — Py: **yes**, TS: **yes**

### `providers/swisspost/resolution.feature`

- `And I have a Porto SDK client initialized` — Py: **yes**, TS: **yes**
- `And I have access to porto-data` — Py: **yes**, TS: **yes**
- `And I should get weight tier "W0020"` — Py: **yes**, TS: **yes**
- `And I should get zone with id "domestic"` — Py: **yes**, TS: **yes**
- `And the letter weight is 20 grams` — Py: **yes**, TS: **yes**
- `And the resolution should be valid` — Py: **yes**, TS: **yes**
- `Given I want to send a letter to country "CH"` — Py: **yes**, TS: **yes**
- `Given provider is "swisspost"` — Py: **yes**, TS: **yes**
- `Then I should get product with id "a_post_standardbrief"` — Py: **yes**, TS: **yes**
- `When I resolve the letter` — Py: **yes**, TS: **yes**

### `providers/ukrposhta/cli.feature`

- `And I have a Porto SDK client initialized` — Py: **yes**, TS: **yes**
- `And I have porto-data available` — Py: **yes**, TS: **yes**
- `And the "data_path" fields should match` — Py: **yes**, TS: **yes**
- `And the products array should contain product with id "dokument"` — Py: **yes**, TS: **yes**
- `And the products array should contain product with id "lyst_standartnyi"` — Py: **yes**, TS: **yes**
- `And the result should have field "amount" as number` — Py: **yes**, TS: **yes**
- `And the result should have field "currency" with value "UAH"` — Py: **yes**, TS: **yes**
- `And the result should have field "currency" with value "USD"` — Py: **yes**, TS: **yes**
- `And the result should have field "data_path"` — Py: **yes**, TS: **yes**
- `And the result should have field "is_valid" with value true` — Py: **yes**, TS: **yes**
- `And the result should have field "price" as number` — Py: **yes**, TS: **yes**
- `And the result should have field "weight" with value 20` — Py: **yes**, TS: **yes**
- `And the result should have field "zone" with nested "id" "domestic"` — Py: **yes**, TS: **yes**
- `And the result should have field "zone" with nested "id" "world"` — Py: **yes**, TS: **yes**
- `And the result should have field "zone" with value "domestic"` — Py: **yes**, TS: **yes**
- `And the services array should contain service with id "mizhnarodne_zareiestrovane"` — Py: **yes**, TS: **yes**
- `And the services array should contain service with id "paperove_povidomlennia_vruchennia"` — Py: **yes**, TS: **yes**
- `And the zones array should contain zone with id "domestic"` — Py: **yes**, TS: **yes**
- `And the zones array should contain zone with id "world"` — Py: **yes**, TS: **yes**
- `Given provider is "ukrposhta"` — Py: **yes**, TS: **yes**
- `Then the result should be stored for comparison` — Py: **yes**, TS: **yes**
- `Then the result should have array "products"` — Py: **yes**, TS: **yes**
- `Then the result should have array "services"` — Py: **yes**, TS: **yes**
- `Then the result should have array "zones"` — Py: **yes**, TS: **yes**
- `Then the result should have field "product"` — Py: **yes**, TS: **yes**
- `Then the result should have field "product" with nested "id" "lyst_standartnyi"` — Py: **yes**, TS: **yes**
- `Then the result should have field "product" with value "lyst_standartnyi"` — Py: **yes**, TS: **yes**
- `Then the result should have field "provider" with value "ukrposhta"` — Py: **yes**, TS: **yes**
- `Then the results should be identical` — Py: **yes**, TS: **yes**
- `Then the results should have same structure` — Py: **yes**, TS: **yes**
- `When I call CLI config command` — Py: **yes**, TS: **yes**
- `When I call CLI data price command with product "lyst_standartnyi" zone "domestic" weight 20` — Py: **yes**, TS: **yes**
- `When I call CLI data products command` — Py: **yes**, TS: **yes**
- `When I call CLI data services command` — Py: **yes**, TS: **yes**
- `When I call CLI data zones command` — Py: **yes**, TS: **yes**
- `When I call CLI price command with country "UA" weight 20` — Py: **yes**, TS: **yes**
- `When I call CLI price command with country "US" weight 20` — Py: **yes**, TS: **yes**

### `providers/ukrposhta/products.feature`

- `And I have a Porto SDK client initialized` — Py: **yes**, TS: **yes**
- `And I have access to porto-data` — Py: **yes**, TS: **yes**
- `And the letter weight is 500 grams` — Py: **yes**, TS: **yes**
- `Given I want to send a letter to country "UA"` — Py: **yes**, TS: **yes**
- `Given provider is "ukrposhta"` — Py: **yes**, TS: **yes**
- `Then product options should include "dokument"` — Py: **yes**, TS: **yes**
- `When I list product options` — Py: **yes**, TS: **yes**

### `providers/ukrposhta/resolution.feature`

- `And I have a Porto SDK client initialized` — Py: **yes**, TS: **yes**
- `And I have access to porto-data` — Py: **yes**, TS: **yes**
- `And I should get zone with id "domestic"` — Py: **yes**, TS: **yes**
- `And the letter weight is 20 grams` — Py: **yes**, TS: **yes**
- `And the resolution should be valid` — Py: **yes**, TS: **yes**
- `Given I want to send a letter to country "UA"` — Py: **yes**, TS: **yes**
- `Given provider is "ukrposhta"` — Py: **yes**, TS: **yes**
- `Then I should get product with id "lyst_standartnyi"` — Py: **yes**, TS: **yes**
- `When I resolve the letter` — Py: **yes**, TS: **yes**
