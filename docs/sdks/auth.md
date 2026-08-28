# Authentication and Registration Architecture

This document aligns with [architecture.md](./architecture.md) and is the
single source for:

- Internetmarke authentication model
- Credential setup and runtime expectations
- App registration guidance
- Auth decision notes and open validation questions

## Scope and Direction

- API transport: REST API via DHL Developer Portal
- Authentication: two-level model (integrator app + customer Portokasse)
- SDK role: accept runtime credentials and perform request auth/signing
- Backend role: secure credential storage and tenant isolation

## Two-Level Authentication Model

### Level 1 - App-Level Credentials

- Source: `developer.dhl.com`
- Type: API key + API secret
- Identity scope: integrator application
- Tenant scope: shared across tenants for a given environment

### Level 2 - Customer-Level Portokasse Credentials (BYO)

- Source: customer's Portokasse account
- Type: username/email + password
- Identity scope: customer's wallet and authorization context
- Tenant scope: per tenant

### Freigabe Clarification

Freigabe is an authorization grant and does not replace customer credentials for API
authentication in the supported flow.

### Portokasse Freigabe (Geschäftsanwendungen) — observed behavior

When the SDK (or lab gate check) first authenticates against a Portokasse that has not
yet approved the integrator app, Deutsche Post responds as follows.

| Step | What happens |
|------|----------------|
| **API call** | `POST {base_url}/user` with `grant_type`, `client_id`, `client_secret`, `username`, `password` (official Internetmarke auth path used by Porto SDK) |
| **HTTP response** | `401` with `title: genericUserAuthenticationError` and `detail` containing *"application is not authorized by user"* |
| **SDK error** | `PortoErrorCode.PROVIDER_LINKAGE_PENDING` |
| **SDK `details`** | `auth_stage: portokasse_linkage`, `user_action: portokasse_geschaeftsanwendungen_freigabe`, `triggers_portokasse_freigabe_email: true` |
| **Provider email** | Portokasse user receives *"Es liegt eine neue Freigabe-Anfrage für Sie vor"* naming the partner app (e.g. `porto_sdk`) and Portokasse ID; user must approve under **Meine Daten → Geschäftsanwendungen** |

References:

- [DHL Internetmarke API (DE)](https://developer.dhl.com/api-reference/deutsche-post-internetmarke-post-paket-deutschland?lang=de) — documents HTTP 401 until Freigabe on token retrieval
- [Deutsche Post API FAQ](https://www.deutschepost.de/de/i/internetmarke-porto-drucken/haeufige-fragen/api-anbindung.html) — Geschäftsanwendungen Freigabe workflow

**Licko / Porto product mapping (recommended):**

- Map `PROVIDER_LINKAGE_PENDING` to a user-facing operational hint: approve the app in Portokasse (not a credential typo, not DHL developer portal).
- Check `details.user_action === portokasse_geschaeftsanwendungen_freigabe` for stable UI routing without parsing provider JSON.
- Do **not** retry purchases automatically; wait for user Freigabe then re-run auth.

**Distinct from DHL developer app denial:** `PROVIDER_AUTH_DENIED` is for integrator app/key issues at the DHL Developer Portal. Freigabe is a separate Portokasse-user step after DHL app approval.

## Runtime Credential Setup

Typical environment variables for integration testing:

```bash
# Level 1: App-level credentials (integrator identity)
PORTO_DEUTSCHEPOST_INTERNETMARKE_API_KEY=your-api-key
PORTO_DEUTSCHEPOST_INTERNETMARKE_API_SECRET=your-api-secret
PORTO_DEUTSCHEPOST_INTERNETMARKE_BASE_URL=https://api-eu.dhl.com/post/de/shipping/im/v1

# Level 2: Customer-level credentials (tenant identity)
PORTO_DEUTSCHEPOST_INTERNETMARKE_USERNAME=customer-portokasse@example.com
PORTO_DEUTSCHEPOST_INTERNETMARKE_PASSWORD=customer-password
```

Base URLs:

- Production: `https://api-eu.dhl.com/post/de/shipping/im/v1`
- Sandbox: `https://api-sandbox.dhl.com/post/de/shipping/im/v1`

## Authentication Flow

1. Backend resolves app credentials (level 1) for environment
2. Backend resolves customer credentials (level 2) for tenant
3. Backend passes runtime config to SDK
4. SDK authenticates/signs requests as required by provider APIs
5. Provider validates and executes operation (for example, stamp generation)

## Responsibility Split

SDK responsibilities:

- Accept runtime auth config
- Execute auth/signing logic and token handling
- Map provider auth failures into stable SDK error model
- Preserve raw provider payload for troubleshooting

Backend/consumer responsibilities:

- Store app credentials securely
- Store customer credentials securely per tenant
- Enforce tenant isolation
- Rotate credentials and handle incident response

SDK must not own long-term credential storage. Callers pass credentials in `PortoConfig.integrations` per request; the SDK authenticates, executes, and discards the in-memory client when the call ends.

## Unified error mapping (consumer-facing)

| User situation | Unified `PortoErrorCode` |
|----------------|--------------------------|
| Wrong Portokasse password | `PROVIDER_AUTH_FAILED` |
| Freigabe not granted | `PROVIDER_LINKAGE_PENDING` |
| Integrator DHL app/key rejected | `PROVIDER_AUTH_DENIED` |
| Wallet too low for mark execution | `PORTO_WALLET_INSUFFICIENT` |
| Capability not in manifest | `PORTO_CAPABILITY_UNSUPPORTED` |

Branch on unified `PORTO_*` codes only. See [architecture.md](architecture.md) (error normalization) and [gaps.md](gaps.md).

## App Registration (DHL Developer Portal)

Register application and environments so credentials can be issued and managed.

Recommended metadata:

- Application name: your product name as registered with the operator
- Production domain: your production app origin (for example `app.example.com`)
- Test/staging domain: your non-production app origin (for example `staging.example.com`)

Suggested flow:

1. Create/access organization and account on [DHL Developer Portal](https://developer.dhl.com)
2. Create Internetmarke REST app registration
3. Register production/test domains as requested
4. Receive and store app credentials per environment
5. Validate rotation and recovery procedures in backend

## Operational Checklist

- [ ] Developer Portal registration is active
- [ ] Production and test environment metadata are documented
- [ ] App credentials are stored in secure backend infrastructure
- [ ] Tenant credential handling is encrypted and isolated
- [ ] Auth failure logging maps to stable SDK errors
- [ ] Integration smoke test passes in production and sandbox

## Decision Notes

- Two-level authentication remains the baseline design
- No ID-only or OAuth-only replacement flow is assumed for final behavior
- Any provider-auth model change requires explicit doc and implementation update

## Open Validation Questions

Review periodically against DHL documentation/support:

- Is any token-only replacement flow officially supported?
- Has Freigabe behavior changed in production policy?
- Have app/customer credential requirements changed?
- Are separate app registrations required for test and production?

## Related Docs

- [SDK Architecture](./architecture.md)
- [Lab Framework Policy](../labs/framework.md)
- [Contributing Guide](../../CONTRIBUTING.md)
