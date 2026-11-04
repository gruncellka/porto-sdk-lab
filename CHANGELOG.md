# Changelog

[Unreleased]

## 0.2.0 - 2026-11-04

### Added

- Public surface records `PortoStatus`, carrier event time, sanitized `provider_raw`, and purchased feature kinds.
- `PROOF_FEATURE_KINDS` is the proof subset. `tracking` is not in that set.
- Naming check for new SDK definitions.

### Changed

- `ProviderCapabilities` is `mark`, `track`, and `wallet`.
- Deutsche Post live tracking is the `shipment` wire with a base URL. Internetmarke does not poll.

## 0.1.0 - 2026-08-29

Initial release
