/**
 * Internetmarke order matrix — graph-driven cases with artifact capture.
 */

import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import {
  getInternetmarkeBaseUrl,
  loadInternetmarkeConfig,
} from "../../../sdks/porto-sdk-typescript/src/adapters/deutschepost/internetmarke/index.ts";
import { loadPortoConfigFromEnv } from "../../../sdks/porto-sdk-typescript/src/config.ts";
import {
  PortoClient,
  PortoError,
  ProviderClient,
  type Address,
  type ExecutionParameters,
  type PortoMark,
  type PortoMarkRequest,
} from "../../../sdks/porto-sdk-typescript/src/index.ts";
import { ExecutionBinding } from "../../../sdks/porto-sdk-typescript/src/services/execution-binding.ts";
import { loadLabEnv } from "../../lib/typescript/load_env.ts";
import { saveStampPng } from "../../lib/typescript/internetmarke_stamp_asset.ts";
import { createPortoClient } from "../../lib/typescript/porto_client.ts";
import { probeInternetmarkeAuth } from "../../lib/typescript/internetmarke_auth_diagnostic.ts";
import { isReady } from "../../../sdks/porto-sdk-typescript/src/states.ts";

const __dirname = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(__dirname, "../../..");

loadLabEnv();

const PROVIDER_DEUTSCHEPOST = "deutschepost";
const ADAPTER_INTERNETMARKE = "internetmarke";

const ZONE_COUNTRY: Record<string, string> = {
  domestic: "DE",
  zone_1_eu: "FR",
  zone_2_europe: "UA",
  world: "US",
};

const LICKO_COUNTRIES = ["DE", "UA", "FR", "CH", "US"] as const;

function addressFromFixture(fixtureId: string): Address {
  const raw = JSON.parse(
    readFileSync(
      join(repoRoot, "resources", "porto-features", "porto_features", "fixtures", "addresses", `${fixtureId}.json`),
      "utf8",
    ),
  ) as Record<string, unknown>;
  return {
    name: String(raw.name),
    street: String(raw.street ?? ""),
    houseNumber: String(raw.house_number ?? ""),
    postalCode: String(raw.postal_code),
    locality: String(raw.locality ?? raw.city),
    countryCode: String(raw.country_code),
    regionCode: raw.region_code ? String(raw.region_code) : undefined,
  };
}

function labCountryForZone(zoneId: string): string {
  if (zoneId === "world") {
    const override = (process.env.LAB_WORLD_COUNTRY ?? "").trim().toUpperCase();
    if (override && override in RECIPIENTS && !["DE", "FR", "CH", "UA"].includes(override)) {
      return override;
    }
    return ZONE_COUNTRY.world;
  }
  return ZONE_COUNTRY[zoneId] ?? "DE";
}

const DEFAULT_PROFILES: Record<string, Record<string, unknown>> = {
  canary: { execution: "manual", purchases: true, max_cases: 1 },
  full: { execution: "manual", purchases: true, max_cases: null },
  dry_run: { execution: "auto_ok", purchases: false, max_cases: null },
};

const SENDER: Address = addressFromFixture("origin_DE");
const RECIPIENTS: Record<string, Address> = Object.fromEntries(
  LICKO_COUNTRIES.map((code) => [code, addressFromFixture(`valid_${code}`)]),
);

interface MatrixCase {
  caseId: string;
  productId: string;
  zoneId: string;
  countryCode: string;
  weight: number;
  weightTierId: string;
  serviceIds: string[];
}

interface GeneratedCaseRow {
  case_id: string;
  product_id: string;
  zone_id: string;
  service_ids: string[];
  country_code: string;
  weight: number;
}

function casesJsonPath(): string {
  return join(
    repoRoot,
    "resources",
    "porto-features",
    "porto_features",
    "matrix",
    "cases.generated.json",
  );
}

function canaryYamlPath(): string {
  return join(
    repoRoot,
    "resources",
    "porto-features",
    "porto_features",
    "matrix",
    "canary.yaml",
  );
}

function loadCanaryCaseIds(): string[] {
  try {
    const text = readFileSync(canaryYamlPath(), "utf8");
    const ids: string[] = [];
    let inList = false;
    for (const line of text.split("\n")) {
      const stripped = line.trim();
      if (stripped === "case_ids:") {
        inList = true;
        continue;
      }
      if (inList && stripped.startsWith("- ")) {
        ids.push(stripped.slice(2).trim());
      } else if (inList && stripped && !stripped.startsWith("#")) {
        break;
      }
    }
    return ids;
  } catch {
    return [];
  }
}

function wireServiceVariants(zoneWire: Record<string, unknown>): string[][] {
  const variants: string[][] = [[]];
  const services = zoneWire.services;
  if (services && typeof services === "object" && services !== null) {
    for (const serviceId of Object.keys(services as Record<string, unknown>).sort()) {
      if ((services as Record<string, unknown>)[serviceId] != null) {
        variants.push([serviceId]);
      }
    }
  }
  return variants;
}

function buildCasesFromWire(
  provider: ProviderClient,
): MatrixCase[] {
  const loader = provider._resolver.dataLoader;
  const graph = loader.resolutionGraph;
  const wire = graph.wire_edges?.internetmarke ?? {};
  const links = graph.links ?? {};
  const cases: MatrixCase[] = [];

  for (const [productId, zones] of Object.entries(wire)) {
    const productLink = (links as Record<string, { zones?: string[]; weight_tiers?: string[] }>)[
      productId
    ];
    const allowedZones = new Set(productLink?.zones ?? []);
    const weightTierId = productLink?.weight_tiers?.[0] ?? "W0020";
    const weight = minWeightForTier(weightTierId, loader);

    for (const [zoneId, zoneWire] of Object.entries(zones)) {
      if (!allowedZones.has(zoneId) || typeof zoneWire !== "object" || zoneWire === null) continue;
      if ((zoneWire as { base?: unknown }).base == null) continue;
      for (const serviceIds of wireServiceVariants(zoneWire as Record<string, unknown>)) {
        cases.push({
          caseId: caseIdFor(PROVIDER_DEUTSCHEPOST, ADAPTER_INTERNETMARKE, productId, zoneId, serviceIds),
          productId,
          zoneId,
          countryCode: labCountryForZone(zoneId),
          weight,
          weightTierId,
          serviceIds,
        });
      }
    }
  }

  return cases.sort((a, b) => a.caseId.localeCompare(b.caseId));
}

function buildCasesFromGeneratedJson(): MatrixCase[] | null {
  try {
    const doc = JSON.parse(readFileSync(casesJsonPath(), "utf8")) as {
      cases?: GeneratedCaseRow[];
    };
    if (!Array.isArray(doc.cases)) return null;
    return doc.cases.map((row) => ({
      caseId: row.case_id,
      productId: row.product_id,
      zoneId: row.zone_id,
      countryCode: row.country_code,
      weight: row.weight,
      weightTierId: "W0020",
      serviceIds: row.service_ids ?? [],
    }));
  } catch {
    return null;
  }
}

function filterCasesForProfile(
  cases: MatrixCase[],
  profileName: string,
  maxCases: number | null,
): MatrixCase[] {
  const profile = loadProfile(profileName);
  if (profileName === "canary") {
    const canaryIds = loadCanaryCaseIds();
    if (canaryIds.length > 0) {
      const allowed = new Set(canaryIds);
      cases = cases.filter((row) => allowed.has(row.caseId));
    }
  }
  const limit = maxCases ?? (profile.max_cases as number | null | undefined);
  return limit != null ? cases.slice(0, Number(limit)) : cases;
}

function buildCases(
  provider: ProviderClient,
  profileName: string,
  maxCases: number | null,
): MatrixCase[] {
  const fromJson = buildCasesFromGeneratedJson();
  const cases = fromJson ?? buildCasesFromWire(provider);
  return filterCasesForProfile(cases, profileName, maxCases);
}

function loadProfile(name: string): Record<string, unknown> {
  const profile = { ...DEFAULT_PROFILES[name] ?? DEFAULT_PROFILES.canary };
  const path = join(__dirname, "matrix_profiles.yaml");
  try {
    const text = readFileSync(path, "utf8");
    let section: string | null = null;
    for (const line of text.split("\n")) {
      const stripped = line.trim();
      if (!stripped || stripped.startsWith("#")) continue;
      if (stripped.endsWith(":") && !stripped.startsWith("-")) {
        section = stripped.slice(0, -1);
        continue;
      }
      if (section === name && stripped.includes(":")) {
        const [key, raw] = stripped.split(":", 2);
        const value = raw.trim();
        if (value === "null") profile[key.trim()] = null;
        else if (value === "true") profile[key.trim()] = true;
        else if (value === "false") profile[key.trim()] = false;
        else if (/^\d+$/.test(value)) profile[key.trim()] = Number(value);
        else profile[key.trim()] = value.replace(/^["']|["']$/g, "");
      }
    }
  } catch {
    /* use defaults */
  }
  return profile;
}

function minWeightForTier(tierId: string, loader: ProviderClient["_resolver"]["dataLoader"]): number {
  const tiers = [...loader.getAllWeightTiers()].sort((a, b) => a.max_weight - b.max_weight);
  let prevMax = 0;
  for (const tier of tiers) {
    if (tier.id === tierId) {
      return prevMax ? prevMax + 1 : 1;
    }
    prevMax = tier.max_weight;
  }
  return 1;
}

function caseIdFor(
  provider: string,
  adapter: string,
  productId: string,
  zoneId: string,
  serviceIds: string[] = [],
): string {
  return [provider, adapter, productId, zoneId, ...serviceIds].join(".");
}

function runDir(): string {
  return process.env.OBSERVER_RUN_DIR ?? join(__dirname, "artifacts", "local");
}

function writeJson(path: string, payload: unknown): void {
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, `${JSON.stringify(payload, null, 2)}\n`, "utf8");
}

function portoErrorPayload(error: PortoError): Record<string, unknown> {
  return {
    code: error.code,
    message: error.message,
    statusCode: error.statusCode,
    upstreamCode: error.upstreamCode,
    details: error.details,
    provider: error.provider,
    wire: error.wire,
  };
}

function buildClient(): PortoClient {
  const portoConfig = loadPortoConfigFromEnv();
  const data = portoConfig.data ?? join(repoRoot, "resources", "porto-data", "porto_data");
  const im = loadInternetmarkeConfig(PROVIDER_DEUTSCHEPOST);
  const current = portoConfig.providers?.[PROVIDER_DEUTSCHEPOST] ?? {};
  const wires = { ...(current.wires ?? {}) };
  if (im) wires.internetmarke = im;
  return createPortoClient({
    ...portoConfig,
    data,
    providers: {
      ...(portoConfig.providers ?? {}),
      [PROVIDER_DEUTSCHEPOST]: { wires },
    },
  });
}

function boundProvider(client: PortoClient): ProviderClient {
  return client.provider(PROVIDER_DEUTSCHEPOST);
}

type VoucherLayout = "ADDRESS_ZONE" | "FRANKING_ZONE";

/** Internetmarke `voucherLayout` wire token — not a Porto type, not SDK execution input. */
function voucherLayoutFor(profile: Record<string, unknown>): VoucherLayout {
  const raw = String(process.env.VOUCHER_LAYOUT ?? profile.voucher_layout ?? "FRANKING_ZONE");
  if (raw !== "ADDRESS_ZONE" && raw !== "FRANKING_ZONE") {
    throw new Error(`Unsupported Internetmarke voucherLayout: ${raw}`);
  }
  return raw;
}

async function runPreflight(client: PortoClient, out: string, dryRun: boolean): Promise<boolean> {
  const preflightDir = join(out, "cases", "_preflight");
  mkdirSync(preflightDir, { recursive: true });

  const apiPayload: Record<string, unknown> = {
    status: "skipped",
    note: "use lab diagnostic for API version checks",
  };
  const apiOk = true;

  let authPayload: Record<string, unknown> = { status: "skipped" };
  let authOk = true;

  if (dryRun) {
    authPayload = { status: "skipped_dry_run", blocking_stage: "none" };
  } else {
    const im = loadInternetmarkeConfig(PROVIDER_DEUTSCHEPOST);
    const creds = im?.credentials ?? {};
    const auth = await probeInternetmarkeAuth({
      baseUrl: getInternetmarkeBaseUrl(im),
      username: creds.username,
      password: creds.password,
      apiKey: creds.dhl_api_key,
      apiSecret: creds.dhl_api_secret,
    });
    authOk = auth.status === "connected";
    authPayload = { ...auth };
    const provider = boundProvider(client);
    if (authOk && isReady(provider.capabilities().wallet)) {
      try {
        const wallet = await provider.wallet.balance();
        authPayload.wallet_balance_cents = wallet.balanceCents;
        authPayload.wallet_source = "provider.wallet.balance";
        console.log(`Portokasse wallet: €${(wallet.balanceCents / 100).toFixed(2)}`);
      } catch (error) {
        authPayload.wallet_error = String(error);
        if (error instanceof PortoError) {
          authPayload.wallet_error_code = error.code;
        }
      }
    }
  }

  writeJson(join(preflightDir, "auth.json"), {
    ts: new Date().toISOString(),
    api_version: apiPayload,
    auth: authPayload,
  });
  return apiOk && authOk;
}

async function runCase(
  client: PortoClient,
  matrixCase: MatrixCase,
  dryRun: boolean,
  out: string,
  _voucherLayout: VoucherLayout,
): Promise<{ ok: boolean; spend: number }> {
  const caseDir = join(out, "cases", matrixCase.caseId);
  mkdirSync(caseDir, { recursive: true });

  const provider = boundProvider(client);
  const loader = provider._resolver.dataLoader;
  const recipient = RECIPIENTS[matrixCase.countryCode] ?? RECIPIENTS.DE;
  const serviceIds = matrixCase.serviceIds.length > 0 ? matrixCase.serviceIds : undefined;
  const services = serviceIds?.map((serviceId) => {
    const row = loader.getService(serviceId);
    if (row == null) {
      throw new Error(`Unknown service ${serviceId}`);
    }
    return row.kind;
  });

  const resolved = await provider.resolve({
    countryCode: matrixCase.countryCode,
    weight: matrixCase.weight,
    productId: matrixCase.productId,
    serviceIds,
    services,
  });

  const wireCode = new ExecutionBinding(loader).resolveWireCode({
    wire: "internetmarke",
    productId: matrixCase.productId,
    zoneId: matrixCase.zoneId,
    serviceIds: matrixCase.serviceIds.length > 0 ? matrixCase.serviceIds : null,
  });

  const expectedLayout: VoucherLayout =
    resolved.markType === "label" ? "ADDRESS_ZONE" : "FRANKING_ZONE";

  const request: PortoMarkRequest = {
    porto: resolved,
    sender: SENDER,
    recipient,
    idempotency: `lab-${matrixCase.caseId}-${Date.now()}`,
  };
  const prepared = await provider._prepare(request);
  writeJson(join(caseDir, "sdk_input.json"), {
    case_id: matrixCase.caseId,
    product_id: matrixCase.productId,
    zone_id: matrixCase.zoneId,
    service_ids: matrixCase.serviceIds,
    wire_code: wireCode,
    voucher_layout: expectedLayout,
    weight: matrixCase.weight,
    request,
    prepared,
  });

  if (dryRun) {
    writeJson(join(caseDir, "sdk_output.json"), {
      dry_run: true,
      wire_code: wireCode,
      price_cents: resolved.amount,
    });
    return { ok: true, spend: 0 };
  }

  try {
    const marked = await provider.mark(request, {} as ExecutionParameters);
    const mark = (Array.isArray(marked) ? marked[0] : marked) as PortoMark;
    writeJson(join(caseDir, "sdk_output.json"), mark);
    const spend = mark.amount ?? resolved.amount;
    if (mark.content?.startsWith("http")) {
      try {
        await saveStampPng(mark.content, join(caseDir, "stamp.png"));
      } catch {
        /* ignore download errors */
      }
    }
    return { ok: true, spend };
  } catch (error) {
    if (error instanceof PortoError) {
      writeJson(join(caseDir, "error.json"), portoErrorPayload(error));
    } else {
      writeJson(join(caseDir, "error.json"), { error: String(error) });
    }
    return { ok: false, spend: 0 };
  }
}

async function main(): Promise<number> {
  const profileName = process.env.PROFILE ?? "canary";
  const profile = loadProfile(profileName);
  const dryRun = process.env.DRY_RUN === "1" || !profile.purchases;
  const voucherLayout = voucherLayoutFor(profile);
  const out = runDir();
  mkdirSync(out, { recursive: true });

  const client = buildClient();
  const provider = boundProvider(client);
  const maxCases = process.env.MAX_CASES ? Number(process.env.MAX_CASES) : null;
  const cases = buildCases(provider, profileName, maxCases);

  console.log(
    `Profile: ${profileName} | cases: ${cases.length} | dry_run: ${dryRun} | voucher_layout: ${voucherLayout}`,
  );

  const preflightOk = await runPreflight(client, out, dryRun);
  if (!preflightOk && !dryRun) {
    console.log("Preflight failed — see cases/_preflight/auth.json");
    writeJson(join(out, "metadata.json"), {
      provider: "deutschepost",
      integration: "internetmarke",
      profile: profileName,
      voucher_layout: voucherLayout,
      dry_run: dryRun,
      sdk_language: "typescript",
      cases_total: cases.length,
      cases_passed: 0,
      cases_failed: 0,
      estimated_spend_cents: 0,
      preflight_ok: false,
    });
    return 1;
  }

  let passed = 0;
  let failed = 0;
  let spend = 0;

  for (const [index, matrixCase] of cases.entries()) {
    console.log(`[${index + 1}/${cases.length}] ${matrixCase.caseId}`);
    try {
      const result = await runCase(client, matrixCase, dryRun, out, voucherLayout);
      if (result.ok) {
        passed += 1;
        spend += result.spend;
      } else {
        failed += 1;
      }
    } catch (error) {
      const caseDir = join(out, "cases", matrixCase.caseId);
      mkdirSync(caseDir, { recursive: true });
      if (error instanceof PortoError) {
        writeJson(join(caseDir, "error.json"), portoErrorPayload(error));
      } else {
        writeJson(join(caseDir, "error.json"), { error: String(error) });
      }
      failed += 1;
    }
  }

  writeJson(join(out, "metadata.json"), {
    provider: "deutschepost",
    integration: "internetmarke",
    profile: profileName,
    voucher_layout: voucherLayout,
    dry_run: dryRun,
    sdk_language: "typescript",
    cases_total: cases.length,
    cases_passed: passed,
    cases_failed: failed,
    estimated_spend_cents: spend,
    preflight_ok: preflightOk,
    finished_at: new Date().toISOString(),
  });

  console.log(`Done: passed=${passed} failed=${failed} spend_cents=${spend}`);
  return failed === 0 ? 0 : 1;
}

main().then((code) => process.exit(code));
