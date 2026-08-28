/**
 * Simple CLI smoke script for the current TypeScript SDK.
 *
 * Runs:
 *   pnpm exec porto config check --json
 */

import { execFileSync } from "node:child_process";

function main(): void {
  const cmd = "pnpm";
  const args = ["exec", "porto", "config", "check", "--json"];
  console.log(`Running: ${cmd} ${args.join(" ")}`);

  try {
    const output = execFileSync(cmd, args, { encoding: "utf8" });
    const payload = JSON.parse(output);
    console.log("CLI OK");
    console.log(JSON.stringify(payload, null, 2));
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
