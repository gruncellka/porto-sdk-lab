# Architectural decisions

Small records for **durable boundaries** where the rule alone is not enough — a reader needs to know *why* the boundary exists and what breaks if it is violated.

## Gate

Create an entry here only when all of the following hold:

1. The decision is architectural (ownership, dependency direction, tool scope).
2. Violating it would cause real cross-repo or consumer harm.
3. Reference docs alone would lose the rationale within a year.

Otherwise document the fact in [`stack.md`](stack.md), [`surface.md`](surface.md), [`labs/`](labs/), or SDK submodule docs.

---

## Lab orchestrates ecosystem repositories externally

**Status:** accepted

### Context

Porto SDK, porto-data, and porto-features ship as independent packages with their own CI, versioning, and publish workflows. Contributors still need a workspace to pin compatible commits, run cross-language checks, and execute paid provider experiments without coupling product runtime to that workspace.

### Decision

**Porto SDK Lab** coordinates submodules and cross-repo verification. It may invoke SDK and resource commands, compare generated outputs, and run matrix sync at the ecosystem boundary.

**Package repositories do not depend on Lab.** SDKs consume porto-data and porto-features via published npm/pip packages at runtime. Lab-only overlays (`make local-resources`) never run on SDK publish CI.

Dependency direction:

```text
porto-data → porto-features → SDK (Python/TypeScript) → Lab (orchestration only)
```

### Consequences

- Submodule pointer commits belong in Lab; file changes belong in the owning repo.
- Lab CI validates Lab-owned scripts, matrix drift, and surface parity — not full SDK BDD (SDK repos validate themselves).
- Removing Lab must not break SDK installs from PyPI/npm.

See also [`stack.md`](stack.md).

---

## Public surface comparison tool

**Status:** accepted

### Context

Python and TypeScript SDKs must expose the same public API shape. Behavioral contracts live in porto-features (Gherkin). Type and export drift still needs a separate, static comparison that catches accidental exports and shape mismatches before release.

A former `porto-sdk-contract` handbook renderer was retired. The Lab needs a small internal tool, not a second product or normative behavioral contract.

### Decision

Keep the tool named **`surface/`** in Lab. It:

1. **Extracts** observable public exports from both SDKs.
2. **Normalizes** snake_case / camelCase where appropriate.
3. **Compares** against policy in `surface/contract/` (allow/deny lists and intentional differences).
4. **Reports** drift in `surface/artifacts/report.json`.

`surface/contract/` is **comparison policy**, not the behavioral SoT (porto-features owns that). The word *contract* inside `surface/` does not rename the project.

CI runs `make surface-check`. Generated artifacts are gitignored except directory placeholders.

### Consequences

- Do not revive `porto-sdk-contract` as a product.
- Do not move surface extraction into SDK repos — comparison is a Lab cross-repo concern.
- `surface-structure` remains an optional diagnostic for full declaration stubs.

See [`surface.md`](surface.md).
