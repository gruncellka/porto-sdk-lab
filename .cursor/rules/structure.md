# Repository Structure

## Main Project Idea

- This repo is a coordination workspace for two SDKs (Python and TypeScript) that should stay behaviorally aligned.
- `sdks/` contains the SDK repositories as submodules (primary product code).
- `resources/` contains shared data/features submodules used for Lab/dev workflows and cross-SDK validation.
- SDKs consume published `porto-data` / `porto-features` packages; they do not vendor root `resources/` folders.

## Why we put multiple repos in one workspace

The workspace gives the AI (and humans) **on-disk visibility across all relevant repositories at once**, so reasoning about a change can be grounded in:

- the SDK source (`sdks/*`)
- the shared data and BDD scenarios (`resources/*`)
- this repo's labs/scripts/tests/docs

Visibility is not commit coupling. Each repo retains its own commit boundary, hooks, CI, and release lifecycle. The full principle is documented in [cross-repo.md](cross-repo.md). Read that rule before suggesting any change that spans more than one of the layouts below.

Consumer applications are **separate repositories** and are **not** part of this checkout. If someone opens this lab beside other repos in their editor, that is their local layout only — not a subdirectory of this repo.

## Core Facts

- Root submodules: `resources/porto-data`, `resources/porto-features`, `sdks/porto-sdk-python`, `sdks/porto-sdk-typescript`
- SDKs have no nested `resources/` submodules
- SDKs consume package dependencies:
  - TypeScript: `@gruncellka/porto-data`, `@gruncellka/porto-features`
  - Python: `gruncellka-porto-data`, `gruncellka-porto-features`

## Layout

```text
porto-sdk-lab/             ← this repo (own commits: labs/scripts/tests/docs/.github/.cursor/configs)
├── resources/
│   ├── porto-data/              ← submodule (shared data, dev/lab)
│   └── porto-features/          ← submodule (shared BDD features, dev/lab)
├── sdks/
│   ├── porto-sdk-python/        ← submodule (Python SDK)
│   └── porto-sdk-typescript/     ← submodule (TypeScript SDK)
├── surface/                     ← internal drift/parity tool (not a product SDK)
│   ├── contract/                ← authored expect baseline (YAML)
│   │   ├── contract.yaml
│   │   ├── schema.yaml
│   │   └── difference.yml       ← intentional cross-SDK differences
│   ├── extract/                 ← language observation (+ normalize/filter helpers)
│   ├── artifacts/               ← generated run output (gitignored; JSON-first)
│   │   ├── python.json
│   │   ├── typescript.json
│   │   ├── report.json          ← primary machine result
│   │   └── report.md            ← optional human view from report.json
│   └── tests/                   ← tests of the instrument
├── labs/                        ← part of this repo
├── scripts/                     ← part of this repo
├── tests/                       ← part of this repo
└── docs/                        ← part of this repo
```

## Editing Guidance

- Edit and commit in this repo: `labs/`, `scripts/`, `tests/`, `docs/`, `surface/`, root config files.
- Edit and commit inside submodules: anything under `sdks/` and `resources/`.
- Treat submodule pointer changes as behavior-relevant changes, especially when `resources/*` pins move.
- For any change that *appears* to span more than one of the on-disk layouts above, consult [cross-repo.md](cross-repo.md) and decompose it per repo before editing.

## Rules in this folder

- [structure.md](structure.md) — this file. Repo layout and where things live.
- [safe-edits.md](safe-edits.md) — what is safe to edit/commit from this repo vs from submodules.
- [CONTRIBUTING.md](../../CONTRIBUTING.md) — submodule commit/push order, sync commands, pointer guard.
- [cross-repo.md](cross-repo.md) — how to use cross-repo visibility for context **without** coupling concerns. Read this before any multi-repo task.
- [doc-naming.mdc](doc-naming.mdc) — lowercase markdown file names (one word preferred).
- [lab.mdc](lab.mdc) — Lab resource lock, validation gates, heavy fail-closed.
- SDK Cursor rules (`sdk.mdc`, `contribution.mdc`) live in each SDK repo, not here.
