# Cross-Repo Context Awareness

## Why this rule exists

This workspace deliberately places multiple repositories side-by-side on disk (this Lab root plus submodules) so that Cursor (and humans) can **read across them** when reasoning about changes. That visibility is the entire point — without it, working on SDKs that share data and features would force constant context-switching between checkouts.

But on-disk co-location is **not** commit coupling. Each repo has its own:

- remote
- branches
- history
- CI/CD
- hooks
- release lifecycle

This rule defines how to use cross-repo visibility for *context* without bleeding concerns between repos.

Downstream **product** repositories (consumer apps) are **not** part of this Lab checkout. Pairing this lab with other repos in an editor is done **outside** this repository (for example a private multi-root workspace); nothing in this repo defines or ships that layout.

## The principle

> **See across, commit within.**

You may read any file in the workspace to inform a change. You may only modify and commit files in the repository that owns them.

## The four repos in this Lab workspace

| On-disk path                       | Repo of record                            | Tracking in this Lab repo        | CI in this Lab repo |
| ---------------------------------- | ----------------------------------------- | -------------------------------- | ------------------- |
| `porto-sdk-lab/` (root)      | `porto-sdk-lab`                     | This repo                        | Yes                 |
| `resources/porto-data/`            | `porto-data`                              | Submodule (gitlink, mode 160000) | Pointer-only        |
| `resources/porto-features/`        | `porto-features`                          | Submodule (gitlink, mode 160000) | Pointer-only        |
| `sdks/porto-sdk-python/`          | `porto-sdk-python`                        | Submodule (gitlink, mode 160000) | Pointer-only        |
| `sdks/porto-sdk-typescript/`     | `porto-sdk-typescript`                    | Submodule (gitlink, mode 160000) | Pointer-only        |

Co-location mechanism:

- **Submodules** (`sdks/*`, `resources/*`) — tracked here as gitlinks (a pinned SHA). Reproducible via `make sm-sync`. See [structure.md](structure.md) and [CONTRIBUTING.md](../../CONTRIBUTING.md).

Submodule visibility gives you on-disk context. It does **not** permit cross-repo commits from this Lab root in a single confused commit.

## What "context awareness" means in practice

When working on a file in repo **A**, you may:

- **Read** files in any other co-located repo to understand types, contracts, data shapes, call sites, BDD scenarios, or downstream consumption.
- **Reference** behavior observed in another repo when justifying a design decision in **A**.
- **Validate** that an API surface in **A** stays ergonomic for known consumers (including apps maintained in **other** repos you have open locally).
- **Trace** a single conceptual flow (e.g. "how a tariff lookup resolves end-to-end") across repos to ground the change.

When working on a file in repo **A**, you must **not**:

- Edit files in any other repo as part of the same change without explicitly switching context to that repo.
- Stage gitlinks (mode `160000`) without intent — every pointer bump is a deliberate commit, guarded by the root pre-commit hook.
- Add paths that belong to **other Git repos** (for example a sibling product clone) into anything **tracked** in this Lab repo.
- Introduce code in repo **A** that only makes sense because of how repo **B** happens to call it today (over-fitting).
- Duplicate code across repos to avoid a package boundary — solve it inside the right repo and consume via its published package.

## How dependencies actually flow

This is the only allowed dependency direction; the AI should reinforce it, not bridge it:

```text
resources/porto-data ──────────┐
                                ├──► sdks/porto-sdk-python ──┐
resources/porto-features ──────┤                              ├──► downstream apps (separate repos;
                                └──► sdks/porto-sdk-typescript ┘   consumed via published npm/pip
                                                                      packages — not submodules here)
```

- Resources do not depend on SDKs.
- SDKs depend on **published** `porto-data` / `porto-features` packages (not on the sibling source folders, except via the explicit lab dev mode documented in `CONTRIBUTING.md`).
- Product apps depend on **published** SDK packages.
- Nothing in this Lab repo depends on a product app's source.

Any suggestion that inverts an arrow (e.g. SDK imports from an app repo, resource imports from SDK source as a shortcut) is wrong and should be flagged.

## Registry dependency contract (SDK submodules)

Committed SDK manifests must stay **registry-clean** — semver ranges only; no `file:../../resources/...` or `workspace:` links.

- **Python SDK:** `pyproject.toml` — checked by `scripts/check_registry.py` (`make registry`).
- **TypeScript SDK:** `package.json` + `pnpm-lock.yaml` — checked by `scripts/check_registry.py` (`make registry`).
- **Lab orchestrator:** [`scripts/check_registry_deps.py`](../scripts/check_registry_deps.py) runs `make registry` in both SDK checkouts.
- **Lab dev wiring:** Lab root `make lab` (venv editable installs + node_modules symlinks — never committed `file:` specs).
- **Guards:** pre-commit hook `registry`, CI `validate` jobs, and publish smoke tests in both SDK repos.

See [`docs/labs/resources.md`](../docs/labs/resources.md) and [`docs/sdks/dependency.md`](../docs/sdks/dependency.md).

## Where to commit (decision table)

| Files touched are under …       | Commit in …                              | Then in Lab root …                                                |
| ------------------------------- | ---------------------------------------- | ----------------------------------------------------------------- |
| `labs/`, `scripts/`, `tests/`, `docs/`, `.github/`, `.cursor/`, root config | This Lab repo               | Done.                                                              |
| `sdks/porto-sdk-python/**`      | Submodule repo (`porto-sdk-python`)       | Optionally bump pointer (`ALLOW_SUBMODULE_POINTER_COMMIT=1`).      |
| `sdks/porto-sdk-typescript/**`  | Submodule repo (`porto-sdk-typescript`)   | Optionally bump pointer (`ALLOW_SUBMODULE_POINTER_COMMIT=1`).  |
| `resources/porto-data/**`       | Submodule repo (`porto-data`)             | Optionally bump pointer (with cross-SDK validation evidence).      |
| `resources/porto-features/**`   | Submodule repo (`porto-features`)         | Optionally bump pointer (with cross-SDK validation evidence).      |

## How to reason about a multi-file task

If a task touches files across two or more of the repos above, break it down:

1. Identify which repo owns each touched file (use the table above).
2. Plan one focused change per owning repo.
3. Apply changes repo-by-repo. Commit each repo independently in the correct order:
   1. Submodule(s) first → push.
   2. Lab repo pointer bump (if intentional) → push.
4. Never bundle cross-repo edits into one logical commit from the wrong root.

If steps 1–4 reveal that you'd need to introduce a coupling (cross-repo import, shared config in this repo that reaches into a product app, CI job spanning private and public repos) — **stop and flag**. The right fix is almost always to push the shared concept into the appropriate **published** package, not to wire repos together at the workspace level.

## Anti-patterns (do not propose these)

- "Add a workspace-level `.env` that all repos share." → Each repo owns its own env.
- "Create a top-level `package.json` / `pyproject.toml` that depends on workspace-relative paths into the submodules." → SDKs ship as published packages; consumers use those.
- "Add a private product repo as a submodule of the Lab." → Rejected; pollutes public-bound history and CI. Use a private meta-repo + multi-root workspace instead.
- "Run a product app's tests from the Lab repo's CI." → Out of scope; each product has its own CI.
- "Add a Makefile target `lint-everything` that descends into submodules and arbitrary sibling folders." → Each repo runs its own hooks/tests. Root `make lint` deliberately excludes submodule contents.
- "Import a utility from an app repo into the SDK to avoid duplication." → Wrong direction. Put it in the SDK (or porto-data); apps consume via the package.
- "Symlink files between repos to share code." → Same problem as imports, plus tooling confusion.

## Quick check before suggesting a change

Before proposing any edit, the assistant should be able to answer:

1. **Which repo owns each touched file?**
2. **Is the proposed change a commit boundary violation?** (e.g., staging files from more than one repo as one commit from this root)
3. **Does the change preserve the dependency direction?** (resources → SDKs → published consumers)
4. **Does anything product-specific leak into tracked Lab files** in a way that should live only in the app repo?

If any answer is uncomfortable, slow down and rework the suggestion before editing.
