#!/usr/bin/env node
/**
 * Lab-owned: symlink Lab resource checkouts into an SDK TypeScript node_modules.
 * Usage: node link-typescript.mjs <path-to-porto-sdk-typescript>
 */

import { existsSync, mkdirSync, rmSync, symlinkSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const labRoot = resolve(__dirname, "../..");

const sdkRoot = process.argv[2] ? resolve(process.argv[2]) : null;
if (!sdkRoot) {
    console.error("usage: link-typescript.mjs <sdk-typescript-root>");
    process.exit(1);
}

const LINKS = [
    {
        name: "@gruncellka/porto-data",
        source: join(labRoot, "resources/porto-data"),
    },
    {
        name: "@gruncellka/porto-features",
        source: join(labRoot, "resources/porto-features"),
    },
];

for (const { name, source } of LINKS) {
    if (!existsSync(source)) {
        console.error(`missing ${source}`);
        process.exit(1);
    }
    const scopeDir = join(sdkRoot, "node_modules", "@gruncellka");
    const target = join(scopeDir, name.split("/")[1]);
    mkdirSync(scopeDir, { recursive: true });
    if (existsSync(target)) {
        rmSync(target, { recursive: true, force: true });
    }
    symlinkSync(source, target, "dir");
    console.log(`Linked ${name} -> ${source}`);
}

writeFileSync(join(sdkRoot, "node_modules", ".porto-local-resources"), "1\n");
console.log("TypeScript SDK local resources linked (Lab-owned).");
