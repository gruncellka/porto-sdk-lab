# Naming

Shortest unambiguous name in its scope. One word by default. Two words when each word carries meaning. Public API stays self-explanatory outside its module.

`make naming` scans both SDK source trees. Three-word definitions print a warning. Four or more words, and a filename that repeats a parent directory word, fail unless they are already in [`scripts/naming-baseline.txt`](../scripts/naming-baseline.txt) or the definition is marked `naming: ok`.

Wire values, JSON keys, error codes, and database columns are not renamed for style.

## Applied (internal)

| Old | New | Why |
|---|---|---|
| `DEUTSCHEPOST_SHIPMENT_STATUS_MAP` and the other provider `*_STATUS_MAP` constants | `MAP` | The file is already `adapters/<provider>/tracking/status_map`. Call sites alias it (`MAP as deutschepost`). |
| `DeutschePostShipmentTrackingAdapter` | `Adapter` | The file is `adapters/deutschepost/tracking/shipment`. The registry imports it as `Shipment`. |
| `snapshot_from_payload` / `snapshotFromPayload` | `snapshot` | Used only inside that shipment module. |

`status_map.py` / `status-map.ts` stays. Two words, and neither word repeats `deutschepost` or `tracking`.

## Left as-is

| Name | Class | Why it stays |
|---|---|---|
| `PortoStatus`, `TrackingStatus`, `TrackingEvent`, `ProviderClient`, `providerRaw` | public | Each word distinguishes a concept. Not shortened to `Status` or `Raw`. |
| `map_native_status` | internal | `map` alone collides with `map_event`. `native` is the carrier code. |
| `sanitize_provider_payload` | internal | Call sites are outside the module, so the words say what is stripped. |
| `PORTO_*` error codes | public wire | Documented identifiers. |
| `get_price_by_product_zone_weight_tier` and the other data-loader verbs | public | Renaming is an SDK compatibility change, not a local cleanup. |
| `porto_data_loader.py`, `schema_validator.py`, and their TypeScript twins | module path | The filename repeats `data` or `validator`. Changing it moves imports across the public loader. |
| Test function names | tests | They state the behavior. The checker does not scan tests. |
