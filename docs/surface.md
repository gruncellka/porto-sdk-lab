# Surface tool

Lab-internal tool for **public API shape** extract, normalize, and cross-SDK parity checks.

## Scope

| Concern | Owner |
| --- | --- |
| Behavioral contracts (Gherkin) | porto-features |
| Public export allow/deny policy | `surface/contract/contract.yaml` |
| Observed SDK exports | `surface/extract/` |
| Parity report | `surface/artifacts/report.json` |

`surface/` is not a publishable package and not the normative behavioral contract.

## Commands

```bash
make surface           # write python.json, typescript.json, report.json (+ optional report.md)
make surface-check     # same pipeline; exit non-zero when report has errors (CI)
make surface-structure # optional full declaration stubs under surface/artifacts/structure/
```

Requires SDK submodules at pinned commits. TypeDoc runs from `surface/node_modules` for TypeScript extract.

## Artifacts

Generated output is **local/CI only** — never commit extracts, reports, or structure stubs.

| Path | Lifecycle |
| --- | --- |
| `surface/artifacts/python.json` | Generated; gitignored |
| `surface/artifacts/typescript.json` | Generated; gitignored |
| `surface/artifacts/report.json` | Generated; gitignored |
| `surface/artifacts/report.md` | Optional human view; gitignored |
| `surface/artifacts/structure/` | Optional stubs from `make surface-structure`; gitignored |
| `surface/node_modules/` | TypeDoc install; gitignored |
| `surface/contract/*.yaml` | Authored policy; tracked |
| `surface/package.json` + lock | Tooling deps for CI `npm ci`; tracked |

## Related docs

- [adr.md](adr.md)
- [sdks/public.md](sdks/public.md) — cross-language public API reference
- [sdks/parity.md](sdks/parity.md) — BDD step parity (separate from surface extract)
