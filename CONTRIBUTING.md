# Contributing to Porto SDK Lab

Lab is orchestration tooling for both SDKs and shared resources. It is not a publishable SDK package.

- SDKs: `sdks/porto-sdk-python`, `sdks/porto-sdk-typescript`
- Resources (Lab/dev overlays): `resources/porto-data`, `resources/porto-features`
- Runtime SDKs consume **published** porto-data / porto-features (pip/npm). Root `resources/` is for Lab overlays only (`make lab`).

Public-surface comparison lives in [`surface/`](surface/) — see [docs/surface.md](docs/surface.md).

## Setup

```bash
git clone git@github.com:gruncellka/porto-sdk-lab.git --recursive
cd porto-sdk-lab
make                # venv + pre-commit
make health         # submodules + status
make labs-up && make labs-verify && make labs-setup   # Docker labs
```

Lab frameworks track latest stable (FastAPI / Next.js / Node LTS). Core package baselines stay Python `3.13` and TypeScript `5.9.x` — see [docs/labs/framework.md](docs/labs/framework.md).

## Validation

| Level | Command | Scope |
| --- | --- | --- |
| Pre-commit | `make lint` | Lab scripts / tests / surface |
| Lab package lint | `make lint-py` / `make lint-ts` | `labs/python`, `labs/typescript` |
| Required health | `make validate` | all leaf checks |

`make test-all` runs unpaid SDK tests locally and is **not** part of `validate` (SDK repos own package CI).

Before opening a PR: `make validate`.

## Package mode (`lab` / `registry`)

```bash
make lab                       # overlay Lab resource checkouts into both SDK installs
make registry                  # restore published porto-data / porto-features
python scripts/check_registry_deps.py  # manifests must stay registry-clean
```

Committed SDK manifests use **registry semver only**. Overlay mechanics: [docs/labs/resources.md](docs/labs/resources.md), [docs/sdks/dependency.md](docs/sdks/dependency.md).

## Ownership

| Path | Commit where |
| --- | --- |
| `labs/`, `scripts/`, `tests/`, `surface/`, `docs/`, `.github/` | Lab root |
| `sdks/*`, `resources/*` | Inside submodule, then update Lab gitlink |

Keep Lab `docs/` free of dumped OpenAPI, Postman collections, and vendor PDFs. Canonical tariff notes live under `resources/porto-data/docs/providers/`.

## Scripts

- `scripts/*.py` — repository logic and checks
- `scripts/labs/*.sh` — thin Docker orchestration (`setup/`, `run/`, `watch/`, `shell/`, `observers/`; shared helpers in `common.sh`)

## Docker labs

Preserve Docker-first behavior for `labs/` and `scripts/labs/`: reproducible runtime, bind-mounted source, package-style SDK installs (`file:../../sdks/porto-sdk-typescript`, `pip install -e ../../sdks/porto-sdk-python`). Verify with `make labs-up`, `make labs-verify`, `make labs-setup`.

## Submodules

Lab commits **pointers**; submodule repos commit **file changes**. Always **push submodules before Lab**.

```bash
# Inside submodule
git add . && git commit -m "feat: …" && git push

# Then Lab root
git add sdks/porto-sdk-python   # or resources/*
ALLOW_SUBMODULE_POINTER_COMMIT=1 git commit -m "chore: update submodule pointers"
git push
```

| Command | Effect |
| --- | --- |
| `make sm-sync` | Check out Lab-pinned commits (use after pull on other machines) |
| `make sm-sync-remote` | Move to remote default branch tips (only when intentionally updating pins) |
| `make sm-reset-danger` | **DESTRUCTIVE** hard-reset `resources/*` to `origin/main` |

Safe variants: `make sm-sync-safe`, `make sm-sync-remote-safe` (autostash).

Add new submodules only with `git submodule add` (gitlink mode `160000`). Editing `.gitmodules` alone is not enough.

`.gitmodules` uses **HTTPS** so GitHub Actions can clone. For local SSH:

```bash
git config url."git@github.com:".insteadOf "https://github.com/"
```

## Pre-commit

| Config | Scope |
| --- | --- |
| `.pre-commit-config.yaml` | Lab scripts / tests / surface |
| `.pre-commit-config-py-lab.yaml` | Python lab |
| `.pre-commit-config-ts-lab.yaml` | TypeScript lab |

Root hooks exclude `resources/` and `sdks/`. A root guard blocks accidental submodule pointer commits; set `ALLOW_SUBMODULE_POINTER_COMMIT=1` for intentional pointer updates after submodule pushes.

## CI

Push-based workflow [`.github/workflows/validation.yml`](.github/workflows/validation.yml):

```text
lint · lint-py · lint-ts · test · matrix · surface  →  validate
```

`validate` is a pure aggregator — use it as the required branch-protection check. One concurrent run per ref (`cancel-in-progress: true`).

## Credentials and evidence

Copy [`.env.example`](.env.example) → `.env` (gitignored). Fill `PORTO_DEUTSCHEPOST_INTERNETMARKE_*` for paid Internetmarke labs. Never commit `.env`. Paid matrix runs are **manual only — never CI**.

`make check-gitignore` / pre-commit fail if `.env` or nested env files become tracked.

Do not commit `labs/experiments/runs/`, `labs/experiments/latest`, or `labs/**/artifacts/` (stamps, auth JSON, HTTP traces). Commit experiment scripts only — see [`labs/experiments/internetmarke/README.md`](labs/experiments/internetmarke/README.md).

## Useful commands

| Command | Purpose |
| --- | --- |
| `make` / `make setup` | Bootstrap venv + pre-commit |
| `make health` | Submodules + status |
| `make validate` | Required repository health |
| `make sm-sync` | Align to Lab-pinned submodule commits |
| `make sm-sync-remote` | Update pins to remote tips (intentional) |
| `make lab` | Overlay Lab `resources/*` into both SDK installs |
| `make registry` | Restore published porto-data / porto-features in SDK installs |
| `make labs-setup` | Setup labs in Docker |
| `make lint` / `lint-py` / `lint-ts` | Pre-commit hygiene |
| `make test-scripts` | Lab pytest |
| `make clean` | Caches/build artifacts only |
| `make clean-all` | `clean` + remove dependencies |
| `make clean-repos` | **DESTRUCTIVE** remove submodule working trees |
