# Porto SDK Lab

[![validation](https://github.com/gruncellka/porto-sdk-lab/actions/workflows/validation.yml/badge.svg)](https://github.com/gruncellka/porto-sdk-lab/actions/workflows/validation.yml)
[![codecov](https://codecov.io/gh/gruncellka/porto-sdk-lab/graph/badge.svg)](https://codecov.io/gh/gruncellka/porto-sdk-lab)

Development workspace for coordinating the Porto SDK ecosystem: Python and TypeScript SDKs, porto-data, and porto-features at pinned submodule commits.

This repository is **orchestration tooling**, not a publishable SDK package.

## What Lab owns

| Concern | Location |
| --- | --- |
| Submodule pin alignment | `make sm-sync`, `scripts/sync.py` |
| Public-surface extract/compare | `surface/`, `make surface-check` |
| Matrix drift at ecosystem boundary | `matrix/`, `scripts/matrix-*-sync.py` |
| Docker labs and paid experiments | `labs/`, `make labs-*` |
| Lab workspace tests | `tests/`, `surface/tests/` |
| Cross-SDK coordination docs | `docs/sdks/` |
| Architectural decisions | `docs/adr.md` |

## What Lab does not own

| Concern | Owner |
| --- | --- |
| SDK implementation, validation, publish | `sdks/porto-sdk-python`, `sdks/porto-sdk-typescript` |
| Postal catalog JSON and schemas | `resources/porto-data` |
| Behavioral Gherkin contracts | `resources/porto-features` |

SDKs consume porto-data and porto-features via **published npm/pip packages** at runtime. Lab `resources/` submodules are for development and local overlay only (`make local-resources`).

## Submodule topology

```text
porto-sdk-lab/
├── resources/porto-data
├── resources/porto-features
├── sdks/porto-sdk-python
└── sdks/porto-sdk-typescript
```

Commit file changes in the owning repository. Lab commits **pointer updates** only. Push submodules before pushing Lab.

## Quick start

```bash
git clone git@github.com:gruncellka/porto-sdk-lab.git --recursive
cd porto-sdk-lab
make                # venv + pre-commit hooks
make health         # submodules + status
make validate       # required repository checks
```

## Commands

```bash
make help              # grouped target list
make validate          # all required checks (CI gate locally)
make lint              # pre-commit hygiene only
make test-scripts      # Lab pytest (scripts + surface)
make surface-check     # public API parity across SDKs
make test-all          # optional: SDK unit + BDD (not in validate)
make labs-up           # Docker lab containers
make labs-setup        # setup labs inside Docker
```

## Porto ecosystem

- [porto-sdk-python](https://github.com/gruncellka/porto-sdk-python) — Python SDK
- [porto-sdk-typescript](https://github.com/gruncellka/porto-sdk-typescript) — TypeScript SDK
- [porto-data](https://github.com/gruncellka/porto-data) — postal catalog data
- [porto-features](https://github.com/gruncellka/porto-features) — BDD contracts

---

🔳 gruncellka
