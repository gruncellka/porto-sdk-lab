# Labs

Docker-first sandboxes for running and observing SDK behavior.

## Ownership

| Path | Role |
| --- | --- |
| `labs/lib/python/` | Shared Python helpers (`matrix`, `mark_measure`, HTTP trace, auth diagnostics) |
| `labs/lib/typescript/` | Shared TypeScript helpers (same concerns, TS implementations) |
| `labs/python/` | FastAPI lab runtime + `example_*.py` |
| `labs/typescript/` | Next.js lab runtime + `example_*.ts` |
| `labs/experiments/` | Paid Internetmarke matrix scripts (source only; runs/artifacts gitignored) |
| `scripts/labs/` | Orchestration (`up`, `run`, `watch`, `shell`) — not library code |

Helpers live under `labs/lib/{python,typescript}`. Do not copy them into lab homes.

## Quick start

```bash
make labs-up
make labs-verify
make labs-setup

make labs-run-py SCRIPT=example_fastapi_integration.py
make labs-run-ts SCRIPT=example_nextjs_integration.ts

make labs-watch-py SCRIPT=example_fastapi_integration.py
make labs-watch-ts SCRIPT=example_nextjs_integration.ts

make labs-shell-py
make labs-shell-ts
```

Paid Internetmarke matrix (never CI):

```bash
make labs-internetmarke-canary
make labs-internetmarke-full
make labs-internetmarke-py PROFILE=dry_run
```

See [`experiments/internetmarke/README.md`](experiments/internetmarke/README.md) and [`docs/labs/boundaries.md`](../docs/labs/boundaries.md).

Inside lab shells:

```bash
# Python (FastAPI)
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# TypeScript (Next.js)
pnpm run dev
```

```bash
make labs-down
make labs-clean
```

## Credentials

Repo root `.env` only (shared). Template: [`.env.example`](../.env.example).

```bash
cp .env.example .env
```

## Notes

- Labs are not part of release CI/CD.
- Online/API tests may incur costs.
- TypeScript lab uses `pnpm` (Corepack + pnpm@10) and Node.js 22.
