# Lab Sandbox Framework and Compatibility Policy

## Purpose

This lab is a compatibility sandbox, not a production application baseline.

The goal is to continuously validate SDK integration in realistic modern frameworks while keeping core package support targets stable and explicit.

## Frameworks used in the lab

- `labs/typescript`: Next.js (latest stable)
- `labs/python`: FastAPI (latest stable)
- Node.js runtime in lab: current LTS / stable line

Shared helpers live under `labs/lib/python/` and `labs/lib/typescript/` (import from lab homes and experiments; do not copy). Orchestration stays in `scripts/labs/`.

## Why these frameworks

1. Real-world ecosystem coverage
   - Next.js represents a modern React + TypeScript stack.
   - FastAPI represents a modern Python API stack.
2. Early compatibility detection
   - Running against latest stable framework releases helps detect API, dependency, and runtime breakages early.
3. Reference integrations
   - Labs act as practical examples of SDK usage in common app architectures.
4. Controlled experimentation
   - New framework/runtime features can be tested without changing production support promises.
5. Clear separation of concerns
   - Labs optimize for forward-compatibility discovery.
   - Core packages optimize for reliability and predictable support.

## Versioning and compatibility strategy

### 1) Lab environment policy

Lab tracks modern framework versions for compatibility validation:

- Next.js: latest stable
- FastAPI: latest stable
- Node.js: current LTS / stable runtime

### 2) Core package baseline policy

Core packages are developed against a stable support baseline:

- `resources/porto-data`
- `resources/porto-features`
- `sdks/porto-sdk-typescript`
- `sdks/porto-sdk-python`

Baseline targets:

- Python: `3.13`
- TypeScript: `5.9.x`

### 3) Governance rule

- Lab compatibility checks do not automatically redefine official package support baselines.
- Baseline versions change only by explicit, intentional decision.
- Production stability has priority over bleeding-edge adoption.

## CI expectations

Use two validation layers:

1. Stable baseline validation
   - Python SDK validated on Python `3.13`
   - TypeScript SDK validated with TypeScript `5.9.x`
2. Forward-compatibility validation
   - SDK integration tested in lab apps with latest stable Next.js and FastAPI

## Principle to keep explicit

A successful run in latest Next.js or FastAPI means "currently compatible in the lab", not "official baseline changed".

## Local resources development rule

For active development in this monorepo, use local resource packages from `resources/` instead of published package registries.

See [resources.md](./resources.md).

## Watch mode

`make labs-watch-py` / `make labs-watch-ts` rerun integration scripts when lab, SDK, or resource overlay paths change. After editing porto-data under `resources/`, restart TypeScript watch or run an SDK build once — symlinked npm packages may not trigger `build --watch` automatically.
