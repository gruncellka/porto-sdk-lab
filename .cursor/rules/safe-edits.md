# Safe vs Submodule Edits

## Why this matters in this repo

- The Lab root orchestrates SDK and resource **submodules** only.
- `sdks/*` are primary SDK repos; `resources/*` are shared dev/lab inputs.
- Committing in the wrong repo creates broken pointers, missing commits, and pull failures for teammates.

The general principle ("see across, commit within") is documented in [cross-repo.md](cross-repo.md). This rule is the operational checklist.

## Safe to Edit in Lab Root

Commit directly in this repo for:

- `labs/`
- `scripts/`
- `tests/`
- `docs/`
- `surface/`
- `.github/`
- `.cursor/`
- root config files (Makefile, pyproject.toml, tsconfig.json, etc.)

## Must Be Committed Inside Submodule

Files under any of these paths belong to a separate repo and must be committed *inside* that submodule, then optionally pointer-bumped in the Lab repo:

- `sdks/porto-sdk-python/`
- `sdks/porto-sdk-typescript/`
- `resources/porto-data/`
- `resources/porto-features/`

## Practical Rule

- File changed in this repo → commit here.
- File changed in a submodule → commit in the submodule (push it first), then optionally bump the Lab pointer.

## Why visibility ≠ commit boundary

You may have **more than one Git repo** open in the IDE (for example via a multi-root workspace that also includes a product app). That is intentional for context. It does **not** mean any commit from the Lab root can include files that belong to another repo. The repo that owns the file is determined by its path (see table in [cross-repo.md](cross-repo.md)), not by where your shell is `cd`-ed.

## Common Mistakes

- Committing from Lab root and expecting submodule file changes to be included.
- Pushing Lab pointer commit before pushing submodule commit.
- Running `sm-reset-danger` without understanding it performs `reset --hard` + `clean -fd` in resource submodules.
- Treating `ALLOW_SUBMODULE_POINTER_COMMIT` as a Make command (it is a one-commit env-var bypass for the root pre-commit pointer guard).
- Proposing to add a **product** repository as a submodule of the Lab, or to wire Lab CI to a private app repo.
- Adding a workspace-level config file (`.env`, top-level `package.json`, etc.) that tries to coordinate the Lab with unrelated repos. Each Git repository owns its own config.
