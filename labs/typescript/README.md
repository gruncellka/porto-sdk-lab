# Porto SDK TypeScript Lab (Next.js)

TypeScript integration lab using Next.js with Docker runtime isolation.

## Setup

From repo root:

```bash
make labs-up
make labs-setup-ts
```

This runs `setup.sh` inside the `lab-ts` container and installs:

- local SDK package via `file:../../sdks/porto-sdk-typescript`
- lab dependencies (Next.js, React, TypeScript, tsx, etc.)
- local `.env` template when missing

## Run CLI smoke script

From repo root:

```bash
make labs-run-ts SCRIPT=example_basic.ts
```

`example_basic.ts` executes:

```bash
pnpm exec porto config check --json
```

## CLI with providers

The SDK CLI supports `--provider` for multi-provider workflows (deutschepost, swisspost):

```bash
# Config check
pnpm exec porto config check --json

# Calc price (default: deutschepost)
pnpm exec porto calc --type standard --country DE --weight 20 --json

# Calc with explicit provider
pnpm exec porto calc --type standard --country CH --weight 20 --provider swisspost --json

# Letter type detection
pnpm exec porto ident --country DE --weight 20 --json

# Geo restrictions
pnpm exec porto restrict --country DE --json
```

Run the full CLI provider example:

```bash
make labs-run-ts SCRIPT=example_cli_provider.ts
# or: pnpm run example:cli-provider
```

Run with external observer artifacts:

```bash
make labs-observe-ts SCRIPT=example_basic.ts
```

## Run Next.js app in container shell

```bash
make labs-shell-ts
```

Then inside container:

```bash
corepack enable && corepack prepare pnpm@10 --activate
./setup.sh
pnpm run dev
```

## Watch mode (script reruns)

```bash
make labs-watch-ts SCRIPT=example_nextjs_integration.ts
```

Watch mode starts SDK build watch and reruns the selected script on changes.

## Credentials

Use repo root `.env` only (see [`../../.env.example`](../../.env.example)).

```bash
PORTO_DEUTSCHEPOST_INTERNETMARKE_USERNAME=your-portokasse-username
PORTO_DEUTSCHEPOST_INTERNETMARKE_PASSWORD=your-portokasse-password
PORTO_DEUTSCHEPOST_INTERNETMARKE_API_KEY=your-api-key
PORTO_DEUTSCHEPOST_INTERNETMARKE_API_SECRET=your-api-secret
```

Credentials are optional for offline/pre-calculation scenarios. See [docs/sdks/config.md](../../docs/sdks/config.md).
