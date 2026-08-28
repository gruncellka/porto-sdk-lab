# Porto SDK — known gaps

Non-blocking leftovers. Not required for public API stability.

## Adapter DTO

Internetmarke maps stamp/label onto voucher layout internally. That mapping stays in the adapter. Do not promote `FRANKING_ZONE` / `ADDRESS_ZONE` / `voucherLayout` to the public SDK.

## Folder symmetry

Python and TypeScript **package** layouts are not identical. Do not reshape `porto_sdk/` / `src/` just to match folders. Public names and error codes are the contract.

**Test** taxonomy must match: [testing.md](testing.md). Architecture invariants use the same names in both SDKs.

## Config helpers

Provider runtime / wire config helpers are uneven across languages. Leave them until a consumer needs a shared config façade.

## Catalog `mark_type` on products

Some catalog rows still carry `mark_type`. Resolved `Porto.mark_type` / `markType` comes from the bound mark profile. Do not teach consumers to read the product-row duplicate.

## Surface polish

Language-shaped diffs (snake vs camel, Pydantic vs Zod, sync vs Promise on catalog `price`) are expected. Do not expand allow-lists to hide a public-name split. `mark` is async in both languages.

## Secondary providers

Deutsche Post Internetmarke is the paid execution wire exercised here. Other providers stay behind the same `Porto` → `mark` contract; they are not a second public model.
