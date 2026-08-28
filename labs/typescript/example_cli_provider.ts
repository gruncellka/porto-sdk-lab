/**
 * CLI examples with provider support.
 *
 * Demonstrates the new CLI commands:
 *   porto config check [--provider ...]
 *   porto ident --country DE --weight 20 [--provider ...]
 *   porto restrict --country DE [--provider ...]
 *   porto calc --type letter_standard --country DE --weight 20 [--provider ...]
 */

import { execFileSync } from "node:child_process";

function runPorto(args: string[]): unknown {
  const cmd = "pnpm";
  const fullArgs = ["exec", "porto", ...args];
  console.log(`Running: ${cmd} ${fullArgs.join(" ")}`);
  const output = execFileSync(cmd, fullArgs, { encoding: "utf8" });
  return JSON.parse(output);
}

function main(): void {
  try {
    // 1. Config check (default provider)
    console.log("\n--- porto config check ---");
    const config = runPorto(["config", "check", "--json"]) as Record<string, unknown>;
    console.log(JSON.stringify(config, null, 2));

    // 2. Config check with explicit provider
    console.log("\n--- porto config check --provider swisspost ---");
    const configCh = runPorto(["config", "check", "--provider", "swisspost", "--json"]) as Record<
      string,
      unknown
    >;
    console.log(JSON.stringify(configCh, null, 2));

    // 3. Restrict (geo restrictions)
    console.log("\n--- porto restrict ---");
    const restrict = runPorto(["restrict", "--country", "DE", "--json"]) as Record<string, unknown>;
    console.log(JSON.stringify(restrict, null, 2));

    // 4. Restrict with explicit provider
    console.log("\n--- porto restrict --provider swisspost ---");
    const restrictCh = runPorto([
      "restrict",
      "--country",
      "CH",
      "--provider",
      "swisspost",
      "--json",
    ]) as Record<string, unknown>;
    console.log(JSON.stringify(restrictCh, null, 2));

    console.log("\n✅ All CLI commands OK");
  } catch (error) {
    console.error("CLI command failed");
    if (error instanceof Error) {
      console.error(error.message);
    } else {
      console.error(String(error));
    }
    process.exit(1);
  }
}

main();
