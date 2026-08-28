# Lab Observer Experiments

Unified documentation for the external lab observer: context, architecture, operation, and artifact format.

## Context

Labs are used for SDK integration experiments:

- `labs/python`
- `labs/typescript`

The observer captures run behavior without adding logging throughout business code.

## Current Output Location

Observer runs now write to:

- `labs/experiments/runs/<run_id>/`
- `labs/experiments/latest` (symlink)

Legacy historical runs may still exist under `labs/artifacts/`.

## Purpose

The observer provides an MVP-level execution trace for lab scripts:

- process lifecycle
- stdout/stderr
- exit code
- run summary
- lightweight timeline (`process.jsonl`)

## Design Direction (MVP-first)

### Build now

1. `observer-runner`
   - wraps existing lab command
   - creates `run_id`
   - executes process and tracks lifecycle
2. `artifact-writer`
   - writes run files under `labs/experiments/runs/<run_id>/`
   - updates `labs/experiments/latest`
3. `redaction`
   - masks sensitive output
4. core outputs
   - `summary.json`
   - `stdout.log`
   - `stderr.log`
   - `process.jsonl`

### Defer

- sidecar proxy
- mandatory typed telemetry layer
- domain-level event schemas
- heavier retention/encryption infrastructure

### Lab HTTP trace (shipped)

Set `PORTO_LAB_HTTP_TRACE=1` (automatic for `make labs-internetmarke-*`). Lab wraps the default SDK `HttpClient` with a Lab-owned tracing transport and writes redacted JSON per hop under `$OBSERVER_RUN_DIR/http/` (or `PORTO_LAB_HTTP_TRACE_DIR`). The published SDK has no observer API. See [`labs/experiments/internetmarke/README.md`](../../labs/experiments/internetmarke/README.md).

## Components

### Observer runner

File: `scripts/labs/observers/runner.py`

Responsibilities:

- create run directory (`run_id`)
- execute target command from repo root
- stream stdout/stderr to console and files
- write process events
- finalize summary
- update `labs/experiments/latest`

### Wrappers

- `scripts/labs/observers/py.sh`
- `scripts/labs/observers/ts.sh`

### Make entry points

- `make labs-observe-py SCRIPT=example_basic.py`
- `make labs-observe-ts SCRIPT=example_basic.ts`

## Runtime Flow

1. wrapper calls `runner.py`
2. observer creates `labs/experiments/runs/<run_id>/`
3. observer starts target command
4. each output line is redacted, written to logs, and appended to `process.jsonl`
5. observer writes `summary.json`
6. observer updates `labs/experiments/latest`

## Run ID and Summary

Run id format:

- `YYYYMMDD-HHMMSS-<rand3hex>`

`summary.json` includes:

- run identifiers and timestamps
- status (`passed` / `failed` / `failed_to_start`)
- exit code and duration
- command and cwd
- observer metadata (`observer_version`, `sdk_language`, `script`, `git_commit`)

## Process Events

`process.jsonl` emits:

- `run_started`
- `process_started`
- `process_output`
- `process_exit`
- `run_finished`
- `run_failed_to_start`

## Retention

Observer keeps the last N runs (default `30`):

- override: `OBSERVER_KEEP_LAST_RUNS=50`
- disable pruning: `OBSERVER_KEEP_LAST_RUNS=0`

## Security Notes

Redaction currently covers common secret patterns (passwords, tokens, authorization values, bearer fragments). This is practical MVP redaction, not full DLP.

## Usage

Run:

```bash
make labs-observe-py SCRIPT=example_basic.py
make labs-observe-ts SCRIPT=example_basic.ts
```

Inspect latest:

```bash
jq . labs/experiments/latest/summary.json
tail -n 80 labs/experiments/latest/stdout.log
tail -n 80 labs/experiments/latest/stderr.log
cat labs/experiments/latest/process.jsonl | jq
```

Retention examples:

```bash
OBSERVER_KEEP_LAST_RUNS=50 make labs-observe-py SCRIPT=example_basic.py
OBSERVER_KEEP_LAST_RUNS=0 make labs-observe-ts SCRIPT=example_basic.ts
```
