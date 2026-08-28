/**
 * Portokasse linkage diagnostic (TypeScript) — no stamp order, no charge.
 */

import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import {
  getInternetmarkeBaseUrl,
  loadInternetmarkeConfig,
} from "../../../sdks/porto-sdk-typescript/src/index.ts";
import {
  exitCodeForAuthStatus,
  probeInternetmarkeAuth,
} from "../../lib/typescript/internetmarke_auth_diagnostic.ts";
import { loadLabEnv } from "../../lib/typescript/load_env.ts";

const __dirname = dirname(fileURLToPath(import.meta.url));
loadLabEnv();

function mask(value: string | undefined): string {
  if (!value) return "MISSING";
  if (value.length <= 6) return "***";
  return `${value.slice(0, 3)}...${value.slice(-3)}`;
}

function saveResult(payload: Record<string, unknown>): string {
  const outDir = process.env.OBSERVER_RUN_DIR
    ? join(process.env.OBSERVER_RUN_DIR, "auth")
    : join(__dirname, "artifacts", "auth");
  mkdirSync(outDir, { recursive: true });
  const ts = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
  const outPath = join(outDir, `portokasse_link_check_${ts}.json`);
  writeFileSync(outPath, `${JSON.stringify(payload, null, 2)}\n`, "utf8");
  return outPath;
}

async function main(): Promise<number> {
  const im = loadInternetmarkeConfig("deutschepost");
  const creds = im?.credentials ?? {};
  const baseUrl = getInternetmarkeBaseUrl(im);

  console.log("Portokasse linkage diagnostic (TS)");
  console.log(`DHL API key: ${mask(creds.dhl_api_key)}`);
  console.log(`Portokasse user: ${mask(creds.username)}`);

  const auth = await probeInternetmarkeAuth({
    baseUrl,
    username: creds.username,
    password: creds.password,
    apiKey: creds.dhl_api_key,
    apiSecret: creds.dhl_api_secret,
  });

  const path = saveResult({
    ts: new Date().toISOString(),
    ...auth,
    checks: {
      app_auth: {
        endpoint: `${baseUrl.replace(/\/$/, "")}/auth/token`,
        status_code: auth.app_status,
        body_preview: auth.app_body_preview,
      },
      user_auth: {
        endpoint: `${baseUrl.replace(/\/$/, "")}/user/authenticate`,
        status_code: auth.user_status,
        body_preview: auth.user_body_preview,
      },
    },
  });

  console.log(`status: ${auth.status}`);
  console.log(`blocking_stage: ${auth.blocking_stage}`);
  console.log(`hint: ${auth.hint}`);
  if (auth.next_steps.length > 0) {
    console.log("next_steps:");
    for (const step of auth.next_steps) {
      console.log(`  - ${step}`);
    }
  }
  console.log(`saved: ${path}`);
  return exitCodeForAuthStatus(auth.status);
}

main().then((code) => process.exit(code));
