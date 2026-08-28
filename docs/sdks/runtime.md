# Dual runtime — identical PortoClient, two data loaders

**Purpose:** Document why TypeScript ships `@gruncellka/porto-sdk` and `@gruncellka/porto-sdk/browser`, how that relates to Python `gruncellka-porto-sdk`, and how integrators avoid cross-SDK drift.

**Status:** Active — June 2026.

**See also:** [api.md](api.md) (public contract), [dependency.md](dependency.md) (manifest vs config vs discovery), [architecture.md](architecture.md) §6 (data layer), Licko [`porto-sdk-integration.md`](../../../licko-app/docs/reference/porto-sdk-integration.md) (vend/sync).

---

## 1. Doctrine

**porto-data is JSON input for the SDK — not an app integration surface.**

```text
porto-data (JSON)  →  SDK loaders + entity processing  →  typed PortoClient subservices
                              ↑
                    Apps import SDK only (never raw porto-data JSON)
```

Python and TypeScript implement the **same** `PortoClient` subservices ([api.md](api.md)). Only **language** and **how porto-data is loaded at runtime** differ.

**Dependency vs config:** Declare `gruncellka-porto-data` / `@gruncellka/porto-data` in the manifest (version contract). Optionally set `data_path` / `PORTO_DATA_PATH` to choose a catalog instance. Auto-discovery when unset is a convenience — see [dependency.md](dependency.md).

| Layer | Role | Who touches it |
|-------|------|----------------|
| **porto-data** | Canonical postal JSON | **SDK build/load only** |
| **SDK** | Process JSON → typed API | Licko + Porto |
| **Apps** | Call `envelopes.list()`, etc. | Never parse `envelopes.json` |

---

## 2. TypeScript package exports

Same `PortoClient` class — not a reduced “lite” API:

| Export | Runtime | porto-data access |
|--------|---------|-------------------|
| `@gruncellka/porto-sdk` | Node / SSR / CLI / tooling | Filesystem (`PortoDataLoader`, `data_path` or package discovery) |
| `@gruncellka/porto-sdk/browser` | Browser (and any environment without `fs`) | **Embedded catalog** — JSON baked at SDK **build time** |

```typescript
// Node
import { PortoClient } from '@gruncellka/porto-sdk'

// Browser — same PortoClient, embedded bundle injected by default
import { PortoClient } from '@gruncellka/porto-sdk/browser'

const client = new PortoClient({ provider: 'deutschepost' })
client.envelopes.list()
```

Implementation: `src/browser.ts` injects `embeddedFiles` from `src/browser/embedded-porto-data.ts`, which imports catalog JSON from the installed `@gruncellka/porto-data` package.

Internal loader path: `PortoDataLoader.fromEmbedded()` uses the same entity processing as the filesystem loader ([`src/data/loader.ts`](../../sdks/porto-sdk-typescript/src/data/loader.ts)).

---

## 3. Python — no separate `/browser` entry

Python runs on servers with filesystem access. One entry:

```python
from porto_sdk import PortoClient, PortoConfig

client = PortoClient(PortoConfig(
    data_path="/path/to/porto_data",
    provider="deutschepost",
))
client.envelopes.list()
```

There is **no** Python `/browser` export today. The browser TS entry is the **client-runtime equivalent** of `data_path` + disk — not a different SDK design.

Optional future: `PortoClient.from_embedded(mapping)` in Python for tests/parity — same in-memory path as TS, not required for production server use.

---

## 4. Why `/browser` exists (not “a second SDK”)

Browsers cannot read `porto_data/**/*.json` from disk. Options:

| Approach | Tradeoff |
|----------|----------|
| **HTTP catalog only** (Licko → Porto → Python SDK) | Extra latency, Porto must be up, adapter can drift from SDK — **not on compose hot path** |
| **Raw porto-data in the frontend** | Forbidden — apps must not parse JSON bundles |
| **Embedded catalog in TS SDK** ✓ | Same SDK pipeline, synchronous catalog reads, no secrets in bundle |

The `/browser` entry is a **common pattern**: same library API, runtime-specific data transport (embed vs `fs`). Match, estimate, and stamp flows stay on the **server** (Python SDK + secrets).

---

## 5. Tier usage (Licko vs Porto) — not an SDK split

Both SDKs **implement** all subservices. Integrators **choose which to call** by runtime policy:

| Subservice | In both SDKs? | Licko browser (compose) | Porto server (typical) |
|------------|---------------|-------------------------|-------------------------|
| `provider.options` / `resolve` / `price` | Yes | **Yes** — product picker + tariff preview | Optional dev HTTP only |
| `envelopes` | Yes | **Yes** — catalog, identify, layout | Optional dev HTTP |
| `providers` / jurisdictions / restrictions | Yes | **Yes** | **Yes** |
| `provider.mark` / Internetmarke | Yes (same adapter in Py + TS) | **Not invoked** — no spend in browser | **Yes** — server-side execution only |

---

## 6. Avoiding Python ↔ TypeScript drift

**Not drift (expected):**

- TS `/browser` vs PY `data_path`
- `camelCase` vs `snake_case`

**Real drift (prevent):**

- Different subservice shapes or return fields
- Different loader/entity logic between SDKs
- Apps or HTTP handlers duplicating catalog facts
- Vend sync from different Lab commits

**Gates** ([api.md §8–§10](api.md)):

1. **porto-features** BDD scenarios define inputs/outputs before new public methods ship
2. Both SDK CIs green before release or Licko vend sync
3. Same **porto-data** revision feeds embed script (TS) and `data_path` (PY)
4. Parity tests — e.g. TS `tests/client/browser.test.ts`: DE envelopes DL/C5/dimensions; window via `geometry("C5", "DE")`

Licko vend (outside this repo):

```bash
make sync-porto-sdk-py   # porto/vendor/ — Python + porto_data
make sync-porto-sdk-ts   # packages/porto-sdk-typescript/ — built @gruncellka/porto-sdk
```

Run both from the **same Lab commit** and note the SHA in the PR.

---

## 7. Build and test (TypeScript)

```bash
cd sdks/porto-sdk-typescript
pnpm run build          # tsup (index + browser + cli)
pnpm exec vitest run src/browser.test.ts
```

The browser entry imports catalog JSON from the installed `@gruncellka/porto-data` package at build time. Local Lab work overlays that package via a `node_modules` symlink — same imports. Browser apps never import `@gruncellka/porto-data` themselves.

Browser bundle: `platform: 'browser'`, Node built-ins shimmed, `ajv`/`zod` inlined — safe for Next.js client components.

---

## 8. Anti-goals

| Do not | Do instead |
|--------|------------|
| Expose raw porto-data paths or JSON to apps | `PortoClient` subservices only |
| Treat `/browser` as a separate product API | Same `PortoClient`; different internal loader |
| Duplicate envelope catalog in UI or HTTP | `envelopes.list()` |
| Ship TS browser without porto-features parity | Scenario-first, both SDKs green |

---

*Dual runtime — Porto SDK Lab — June 2026.*
