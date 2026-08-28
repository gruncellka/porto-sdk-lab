# Porto SDK Lab Bugbot Rules

## Scope

- This file defines repo-level review rules for Bugbot.
- Keep findings focused on safety, correctness, and cross-SDK compatibility.
- `resources/porto-data` and `resources/porto-features` are shared resource submodules used by both SDK labs:
  - `sdks/porto-sdk-python`
  - `sdks/porto-sdk-typescript`
- **Scope is this repository only.** Do not produce findings that depend on, or prescribe coupling with, codebases that are not part of this repo's tracked tree (for example a consumer app opened in a separate multi-root workspace). Product repos have their own review processes.

## Rule format

- Use explicit, actionable findings.
- Use blocking bugs for safety/correctness risks.
- Use non-blocking bugs for maintainability or coordination risks.

## Rules

### 1) Missing tests for script/library changes (blocking)

If a PR modifies `{scripts/**/*.py, lib/**/*.py}` and there are no changes in `tests/**`, then:

- Add a blocking Bug titled `Missing tests for script or library changes`.
- Body: `This PR changes workspace logic but does not update tests. Add or update tests in tests/ (for example tests/test_sync.py).`
- Apply label `quality`.

### 2) Destructive Make target lost safety guards (blocking)

If a PR modifies the `Makefile` target `sm-reset-danger`, require all of the following:

- visible destructive warning text
- interactive confirmation prompt
- explicit cancel/abort path

If any guard is removed or weakened:

- Add a blocking Bug titled `Destructive reset flow lost safety guard`.
- Body: `sm-reset-danger must remain clearly interactive and easy to abort. Restore warning, prompt, and cancellation behavior.`
- Apply labels `safety`, `cli`.

### 3) New destructive git commands in automation (blocking)

If a PR adds `git reset --hard` or `git clean -fd` in `scripts/**/*.py` or `scripts/**/*.sh`, then:

- Add a blocking Bug titled `Potentially destructive git command added`.
- Body: `Avoid hard reset/clean in automation unless there is an explicit user-confirmed safety flow with clear warnings.`
- Apply labels `safety`, `git`.

Exception:

- Do not report the existing guarded flow in `Makefile` target `sm-reset-danger`.

### 4) subprocess.run must have clear failure handling (blocking)

For new `subprocess.run(...)` calls in `{scripts/**/*.py, lib/**/*.py}`, require either:

- `check=True`, or
- explicit non-zero `returncode` handling.

If neither exists:

- Add a blocking Bug titled `subprocess.run without clear error handling`.
- Body: `New subprocess invocation can fail silently. Use check=True or explicit returncode handling with clear behavior.`
- Apply labels `reliability`, `python`.

### 5) sync.py changes need focused tests (non-blocking)

If `scripts/sync.py` changes and `tests/test_sync.py` does not, then:

- Add a non-blocking Bug titled `sync.py changed without matching test update`.
- Body: `Add or confirm focused coverage for no-op behavior (.git/.gitmodules missing), --autostash stash/restore flow, and root/nested status output behavior.`
- Apply label `regression-risk`.

### 6) Shared resource pin change needs cross-SDK validation (blocking)

If submodule pointers for `resources/porto-data` or `resources/porto-features` change, require at least one signal of cross-SDK validation:

- both SDK areas changed (`sdks/porto-sdk-python/**` and `sdks/porto-sdk-typescript/**`), or
- verification evidence in changed docs (for example `README*`, `docs/**`) describing checks for both SDK labs.

If no signal exists:

- Add a blocking Bug titled `Shared resource pin changed without cross-SDK validation`.
- Body: `This PR updates shared resource submodules used by both SDK labs. Add evidence that both Python and TypeScript lab flows were validated.`
- Apply labels `integration`, `quality`.

### 7) Single SDK pin update should be intentional (non-blocking)

If exactly one SDK submodule pointer changes (`sdks/porto-sdk-python` xor `sdks/porto-sdk-typescript`), then:

- Add a non-blocking Bug titled `Single SDK pin updated`.
- Body: `Confirm this one-sided SDK pin update is intentional and note expected compatibility with shared resources.`
- Apply label `integration`.

### 8) TODO/FIXME must be tracked (non-blocking)

If changed code includes `TODO` or `FIXME` without an issue reference like `#123` or `ABC-123`, then:

- Add a non-blocking Bug titled `Untracked TODO/FIXME comment`.
- Body: `Link TODO/FIXME to a tracked issue (for example TODO(#123): ...) or remove it.`
- Apply label `maintainability`.

### 9) SDK must respect porto-data integrations vs wire split (blocking)

If a PR changes SDK execution wiring (`sdks/porto-sdk-python/**`, `sdks/porto-sdk-typescript/**`, or `labs/**` that resolves checkout codes) and:

- reads **`productCode`** or zone wire tables from **`execution.json`** instead of **`graph.edges.wire`**, or
- treats **`execution.json`** billing/execution methods as if they lived on **`graph.json`**, or
- bundles a truncated integration manifest missing **`adapter`** / **`billing`** / **`execution`** shape from porto-data:

- Add a blocking Bug titled `SDK conflates integration manifest with wire tables`.
- Body: `porto-data: execution.json = wire + billing/execution methods; graph.edges.wire = productCode tables. SDK loaders must resolve wire from graph and gate execution from execution manifest. See resources/porto-data/docs/identity.md and BUGBOT rules 33–34.`
- Apply labels `integration`, `architecture`, `consistency`.

### 10) Mark fetch helpers must use catalog calibrations, not hardcoded geometry (non-blocking)

If a PR adds mark download / normalization (`fetch_mark_bytes`, `fetchMarkBytes`, stamp IO) and hardcodes provider checkout dimensions instead of reading **`marks.calibrations[]`** (or documented provider tables in **`docs/providers/<id>.md`**):

- Add a non-blocking Bug titled `Mark geometry hardcoded instead of catalog calibrations`.
- Body: `Measured checkout sizes belong in porto-data marks.calibrations; SDK/labs should load calibration facts from bundled porto-data, not duplicate mm/px tables in code.`
- Apply labels `maintainability`, `consistency`.
