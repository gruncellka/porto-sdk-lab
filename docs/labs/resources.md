# Lab package overlays (`lab` / `registry`)

**Architecture:** Committed SDK manifests always use **registry semver**. Lab wiring swaps the **installed package instance** in venv / `node_modules` without changing manifests. Production integrators use pip/npm only — see [../sdks/dependency.md](../sdks/dependency.md).

Disk nouns `sdks/` and `resources/` stay; Make verbs are **`lab`** (local checkouts) and **`registry`** (published). SDKs do **not** detect Lab topology. Overlays are Lab-owned and invoked from the Lab root only. This repo does not wire consumer apps.

## Apply / restore

From Lab root:

```bash
make lab
```

```bash
make registry
```

## What runs

| SDK | Overlay | Restore |
| --- | --- | --- |
| Python | `scripts/lab/overlay-python.sh` → `pip install -e` Lab `resources/*` into SDK `.venv` | `restore-python.sh` |
| TypeScript | `scripts/lab/link-typescript.mjs` → symlink into SDK `node_modules` | `unlink-typescript.mjs` |

Docker lab setup (`labs/typescript/setup.sh`) calls the Lab link script with an absolute path to the SDK checkout.

## Guards

Each SDK: `make registry` (pre-commit + CI). Lab: `python scripts/check_registry_deps.py` runs both SDKs’ `make registry`.
