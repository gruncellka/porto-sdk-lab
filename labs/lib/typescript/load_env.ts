import { existsSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const libDir = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(libDir, "../../..");
const labRequire = createRequire(
    join(repoRoot, "labs/typescript/package.json"),
);

/** Load repo root `.env` only (shared by Python + TypeScript labs). */
export function loadLabEnv(): void {
    try {
        const config = labRequire("dotenv").config as (options: { path: string }) => void;
        const rootEnv = join(repoRoot, ".env");
        if (existsSync(rootEnv)) {
            config({ path: rootEnv });
        }
    } catch {
        // dotenv is optional.
    }
}
