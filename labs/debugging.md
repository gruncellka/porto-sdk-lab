# Debugging Porto SDK from the monorepo (TypeScript & Python)

Paths below are from the **repo root** (`porto-sdk-lab`). Dependency model: [docs/sdks/dependency.md](../docs/sdks/dependency.md).

## Shared: catalog root (`PORTO_DATA_PATH`)

`PORTO_DATA_PATH` is the **catalog root** (directory with `mappings.json`), not the porto-data git repo root. Optional when the installed `gruncellka-porto-data` / `@gruncellka/porto-data` package already resolves.

```bash
export PORTO_DATA_PATH="$PWD/resources/porto-data/porto_data"
```

Use the same value in **Run and Debug → env** (see `.vscode/launch.json`).

---

## TypeScript CLI (`porto`)

### Important

- The CLI binary is built in **`sdks/porto-sdk-typescript`**, not in `labs/typescript` (that lab runs **Next.js** only).
- Run **`pnpm build`** in the SDK folder first so `dist/cli.js` exists.

### Terminal (no editor)

```bash
cd sdks/porto-sdk-typescript
pnpm build
export PORTO_DATA_PATH="$PWD/../../resources/porto-data/porto_data"   # optional
node dist/cli.js restrict --country UA --json
```

**Node inspector**

- `node --inspect dist/cli.js …` — debug protocol on; process runs (good for breakpoints after attach).
- `node --inspect-brk dist/cli.js …` — **pauses on the first line** until you attach (Chrome `chrome://inspect` or Cursor). No JSON on stdout until you **Continue**.

### Cursor / VS Code

Use **Run and Debug** and pick **“Porto TS: restrict (dist)”** (or calc / custom `args` in `.vscode/launch.json`).

Before first run: `cd sdks/porto-sdk-typescript && pnpm build`.

**Breakpoints:** e.g. `src/cli/commands.ts` (`cmdRestrict`), `src/services/restriction.service.ts`, `src/data/entities/restrictions.ts`, `src/data/loader.ts` (`limits` / `restrictions` branches).

**If breakpoints never hit:** the CLI is a **single bundled** `dist/cli.js` (tsup). The launch configs set `outFiles` so the debugger loads `cli.js.map` and maps lines back to `src/**/*.ts`. Re-run **`pnpm build`** after changing source so `dist` matches your editor. Put breakpoints on **executable lines** (first line inside `checkRestrictions`, e.g. `const normalizedCountryCode = …`), not only on multi-line function headers—the binder sometimes skips the parameter lines. **`getData()` is not used** on the `restrict` code path (`RestrictionService` → `PortoDataLoader.checkRestrictions` → `RestrictionsLoader.checkRestrictions`), so a breakpoint there will not run for `porto restrict`.

### From a TypeScript lab folder

If you only opened `labs/typescript`, either open the **monorepo root** in Cursor so `launch.json` applies, or run the commands above from a terminal with `cd` to `sdks/porto-sdk-typescript`.

---

## Python CLI (`porto`)

### One-time: editable install + venv

```bash
cd sdks/porto-sdk-python
python3.13 -m venv venv
source venv/bin/activate
pip install -e .
export PORTO_DATA_PATH="$PWD/../../resources/porto-data/porto_data"   # optional
```

### Terminal

```bash
porto restrict --country UA --json
```

Equivalent (useful for debugging / consistent argv):

```bash
python -m porto_sdk.cli restrict --country UA --json
```

### Cursor / VS Code

Use **“Porto Python: restrict (module)”** in Run and Debug.  
Requires **Python extension** + interpreter = `sdks/porto-sdk-python/venv/bin/python` (adjust if your venv path differs).

**Breakpoints:** e.g. `porto_sdk/cli/_commands.py`, `porto_sdk/services/restriction_service.py`, `porto_sdk/data/entities/restrictions.py`.

### Python lab (`labs/python`)

After `setup.sh` / `source venv/bin/activate`, the same `porto` or `python -m porto_sdk.cli` works if the editable SDK install points at `../../sdks/porto-sdk-python`.

---

## Quick reference

| Goal | TypeScript | Python |
|------|------------|--------|
| Build CLI | `cd sdks/porto-sdk-typescript && pnpm build` | `pip install -e sdks/porto-sdk-python` |
| Run restrict JSON | `node dist/cli.js restrict --country UA --json` | `porto restrict --country UA --json` |
| Inspect (no pause at start) | `node --inspect dist/cli.js …` | debugpy / launch config |
| Pause at start | `node --inspect-brk dist/cli.js …` | set breakpoint in IDE |

The `porto` console script resolves to `porto_sdk.cli:main`. **`python -m porto_sdk.cli`** uses `porto_sdk/cli/__main__.py` and the same argv.
