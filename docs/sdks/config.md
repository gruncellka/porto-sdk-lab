# Porto SDK Configuration

## Architecture Principle

**SDK truth** = `PortoConfig` + porto-data
**CLI convenience** = `~/.porto/config.json` (optional overlay, CLI-only)

The JSON config file is **not** part of core SDK design. It exists only for CLI developer convenience and local persistence.

---

## Canonical `PortoConfig` shape

- `providers.<id>.wires` — per-provider execution wires (no root `provider`, no root `wires`)
- `data` — optional path to the porto-data catalog root (not `data_path` / `dataPath` on config)
- `transport.timeout` — seconds (not milliseconds)
- `transport.retries`
- `cache`, `features`, `strict_data_validation` / `strictDataValidation`

There is no public default provider field. `client.provider(id)` always takes an explicit id.

Loader/registry **parameters** named `data_path` / `dataPath` still mean the filesystem path to porto-data. That is not the config field.

---

## Config Precedence (CLI)

When the CLI loads config, merge order is (later overwrites earlier):

1. **Base:** Environment variables (`PortoConfig.from_env()` / internal CLI env overlay)
2. **Overlay:** `~/.porto/config.json` (when file exists)
3. **Override:** Explicit CLI flags (e.g. `--provider deutschepost`)

The SDK itself **only** knows:

- Environment variables (via the env loaders)
- Explicit config object passed to `PortoClient(config)`

The file overlay exists **only in the CLI shell**. Core SDK has no file I/O for config. Env is converted at loaders only; `HttpClient` does not read env.

---

## Environment Variables

### General

| Variable | Description |
|----------|-------------|
| `PORTO_PROVIDER` | Selects which provider id the CLI / env loader puts in `providers` |
| `PORTO_DATA_PATH` | Sets `data` (catalog root containing `mappings.json`) |
| `PORTO_TIMEOUT_SECONDS` | HTTP timeout in **seconds** |
| `PORTO_RETRIES` | Retry count |

There is no `PORTO_TIMEOUT_MS` alias.

### Provider-specific (adapter bootstrap)

**Naming rule:** `PORTO_<PROVIDER>_<WIRE>_<FIELD>` (all uppercase)

These are read by adapter bootstrap (not generic `PortoConfig`).

#### Deutsche Post / Internetmarke

| Variable | Description |
|----------|-------------|
| `PORTO_DEUTSCHEPOST_INTERNETMARKE_BASE_URL` | API base URL |
| `PORTO_DEUTSCHEPOST_INTERNETMARKE_USERNAME` | Portokasse username |
| `PORTO_DEUTSCHEPOST_INTERNETMARKE_PASSWORD` | Portokasse password |
| `PORTO_DEUTSCHEPOST_INTERNETMARKE_API_KEY` | Integrator (DHL Developer Portal) API key |
| `PORTO_DEUTSCHEPOST_INTERNETMARKE_API_SECRET` | Integrator (DHL Developer Portal) API secret |
| `PORTO_DEUTSCHEPOST_INTERNETMARKE_PARTNER_ID` | Partner ID |

#### Swiss Post / WebStamp

| Variable | Description |
|----------|-------------|
| `PORTO_SWISSPOST_WEBSTAMP_BASE_URL` | API base URL |
| `PORTO_SWISSPOST_WEBSTAMP_USERNAME` | Username |
| `PORTO_SWISSPOST_WEBSTAMP_PASSWORD` | Password |
| `PORTO_SWISSPOST_WEBSTAMP_CUSTOMER_ID` | Customer ID |
| `PORTO_SWISSPOST_WEBSTAMP_APPLICATION_ID` | Application ID |

---

## CLI Config File

- **Path:** `~/.porto/config.json`
- **Scope:** CLI-only. Not used by SDK when constructing `PortoClient(config)` directly.

```json
{
  "default_provider": "deutschepost",
  "providers": {
    "deutschepost": {
      "wires": {
        "internetmarke": {
          "base_url": "https://api-eu.dhl.com/post/de/shipping/im/v1",
          "credentials": {
            "username": "...",
            "password": "...",
            "dhl_api_key": "...",
            "dhl_api_secret": "...",
            "partner_id": "..."
          }
        }
      }
    }
  }
}
```

`porto auth login` accepts registry keys `--partner-id`, `--customer-id`, `--application-id` (plus Deutsche Post-only `--dhl-api-key` / `--dhl-api-secret`).
