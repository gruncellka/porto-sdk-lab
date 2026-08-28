/**
 * ApiVersionResource check (TypeScript) — mirrors example_api_version_check.py.
 * No credentials required.
 */

import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { getInternetmarkeBaseUrl, loadInternetmarkeConfig } from "@gruncellka/porto-sdk";
import { loadLabEnv } from "../../lib/typescript/load_env.ts";

const __dirname = dirname(fileURLToPath(import.meta.url));
loadLabEnv();

function saveResult(payload: Record<string, unknown>): string {
  const outDir = process.env.OBSERVER_RUN_DIR
    ? join(process.env.OBSERVER_RUN_DIR, "api")
    : join(__dirname, "artifacts", "api");
  mkdirSync(outDir, { recursive: true });
  const ts = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
  const outPath = join(outDir, `api_version_${ts}.json`);
  writeFileSync(outPath, `${JSON.stringify(payload, null, 2)}\n`, "utf8");
  return outPath;
}

async function main(): Promise<number> {
  const im = loadInternetmarkeConfig("deutschepost");
  const baseUrl = getInternetmarkeBaseUrl(im);
  const versionUrl = `${baseUrl}/`;

  console.log("ApiVersionResource check (TS)");
  console.log(`GET ${versionUrl}`);

  let ok = true;
  let result: Record<string, unknown>;
  try {
    const resp = await fetch(versionUrl);
    const text = await resp.text();
    result = { status: resp.status, ok: resp.ok, body_preview: text.slice(0, 2000) };
    ok = resp.ok;
  } catch (error) {
    ok = false;
    result = { error: String(error) };
  }

  const path = saveResult({
    ts: new Date().toISOString(),
    status: ok ? "ok" : "error",
    response_json: result,
  });

  console.log(ok ? "API available" : "API check failed");
  console.log(`Saved: ${path}`);
  return ok ? 0 : 1;
}

main().then((code) => process.exit(code));
