# Porto SDK Python Lab (FastAPI)

Python integration lab using FastAPI with Docker runtime isolation.

## Setup

From repo root:

```bash
make labs-up
make labs-setup-py
```

This runs `setup.sh` inside the `lab-py` container and installs:

- local editable SDK (`pip install -e ../../sdks/porto-sdk-python`)
- lab dependencies (FastAPI, Uvicorn, HTTPX, python-dotenv)
- local `.env` template when missing

## Run CLI smoke script

From repo root:

```bash
make labs-run-py SCRIPT=example_basic.py
```

`example_basic.py` executes:

```bash
porto config check --json
```

## CLI with providers

The SDK CLI supports `--provider` for multi-provider workflows (deutschepost, swisspost):

```bash
# Config check
porto config check --json

# Calc price (default: deutschepost)
porto calc --type standard --country DE --weight 20 --json

# Calc with explicit provider
porto calc --type standard --country CH --weight 20 --provider swisspost --json

# Letter type detection
porto ident --country DE --weight 20 --json

# Geo restrictions
porto restrict --country DE --json
```

Run the full CLI provider example:

```bash
make labs-run-py SCRIPT=example_cli_provider.py
```

Run with external observer artifacts:

```bash
make labs-observe-py SCRIPT=example_basic.py
```

## Run FastAPI app in container shell

```bash
make labs-shell-py
```

Then inside container:

```bash
./setup.sh
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Watch mode (script reruns)

```bash
make labs-watch-py SCRIPT=example_fastapi_integration.py
```

## Credentials

Use repo root `.env` only (see [`../../.env.example`](../../.env.example)).

```bash
PORTO_DEUTSCHEPOST_INTERNETMARKE_USERNAME=your-portokasse-username
PORTO_DEUTSCHEPOST_INTERNETMARKE_PASSWORD=your-portokasse-password
PORTO_DEUTSCHEPOST_INTERNETMARKE_API_KEY=your-api-key
PORTO_DEUTSCHEPOST_INTERNETMARKE_API_SECRET=your-api-secret
```

Credentials are optional for offline/pre-calculation scenarios. See [docs/sdks/config.md](../../docs/sdks/config.md).
