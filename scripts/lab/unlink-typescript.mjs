#!/usr/bin/env node
/**
 * Lab-owned: remove local resource symlinks and restore registry packages.
 * Usage: node unlink-typescript.mjs <path-to-porto-sdk-typescript>
 */

import { spawnSync } from "node:child_process";
import { existsSync, lstatSync, rmSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const sdkRoot = process.argv[2] ? resolve(process.argv[2]) : null;
if (!sdkRoot) {
    console.error("usage: unlink-typescript.mjs <sdk-typescript-root>");
    process.exit(1);
}

for (const pkg of ["porto-data", "porto-features"]) {
    const target = join(sdkRoot, "node_modules", "@gruncellka", pkg);
    if (!existsSync(target)) continue;
    if (lstatSync(target).isSymbolicLink()) {
        rmSync(target, { force: true });
        console.log(`Removed symlink ${target}`);
    }
}

if (process.env.PORTO_LAB_SKIP_INSTALL === "1") {
    rmSync(join(sdkRoot, "node_modules", ".porto-lab"), { force: true });
    console.log("TypeScript SDK lab marker cleared (pnpm install skipped).");
    process.exit(0);
}

const install = spawnSync("pnpm", ["install", "--frozen-lockfile"], {
    cwd: sdkRoot,
    stdio: "inherit",
    shell: process.platform === "win32",
});
if (install.status !== 0) {
    process.exit(install.status ?? 1);
}

rmSync(join(sdkRoot, "node_modules", ".porto-lab"), { force: true });
console.log("TypeScript SDK registry packages restored.");
