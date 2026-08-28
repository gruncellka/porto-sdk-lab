/** Lab-owned HTTP tracing transport. SDK must not import this module. */

import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import type {
    RequestOptions,
    Transport,
} from "../../../sdks/porto-sdk-typescript/src/transport/http-client.ts";
import { redactHeaders, redactPayload, redactText, redactUrl } from "./redaction.ts";

const BODY_LIMIT = 4096;
const BINARY_PREFIXES = ["image/", "audio/", "video/"];
const BINARY_TYPES = new Set([
    "application/pdf",
    "application/zip",
    "application/octet-stream",
    "application/gzip",
]);

let counter = 0;

export type HopRecord = Record<string, unknown>;
export type PersistHop = (hop: HopRecord) => void;

export function tracingEnabled(): boolean {
    return process.env.PORTO_LAB_HTTP_TRACE?.trim() === "1";
}

export function bodiesEnabled(): boolean {
    return process.env.PORTO_LAB_HTTP_TRACE_BODIES?.trim() === "1";
}

function traceDir(): string {
    const explicit = process.env.PORTO_LAB_HTTP_TRACE_DIR;
    if (explicit) return explicit;
    const observer = process.env.OBSERVER_RUN_DIR;
    if (observer) return join(observer, "http");
    return join("artifacts", "http");
}

function label(url: string): string {
    if (url.includes("/user") || url.includes("/authenticate") || url.includes("/auth/")) {
        return "auth";
    }
    if (url.includes("/shoppingcart/png") || url.includes("/shoppingcart/pdf")) {
        return "checkout";
    }
    if (url.includes("/shoppingcart")) {
        return "cart";
    }
    return "http";
}

function bounded(value: unknown): unknown {
    if (typeof value === "string" && value.length > BODY_LIMIT) {
        return value.slice(0, BODY_LIMIT);
    }
    const encoded = JSON.stringify(value);
    if (encoded && encoded.length > BODY_LIMIT) {
        return encoded.slice(0, BODY_LIMIT);
    }
    return value;
}

function isBinary(contentType: string): boolean {
    const lowered = contentType.split(";")[0]?.trim().toLowerCase() ?? "";
    return BINARY_PREFIXES.some((prefix) => lowered.startsWith(prefix)) || BINARY_TYPES.has(lowered);
}

function previewRequestBody(body: string | undefined, includeBodies: boolean): unknown {
    if (!includeBodies || body === undefined) return undefined;
    try {
        return bounded(redactPayload(JSON.parse(body)));
    } catch {
        return bounded(redactText(body));
    }
}

async function previewResponseBody(
    response: Response,
    includeBodies: boolean,
): Promise<unknown> {
    if (!includeBodies) return undefined;
    const contentType = response.headers.get("content-type") ?? "";
    if (isBinary(contentType)) {
        const clone = response.clone();
        const bytes = (await clone.arrayBuffer()).byteLength;
        return { kind: "binary", bytes };
    }
    const clone = response.clone();
    const text = await clone.text();
    try {
        return bounded(redactPayload(JSON.parse(text)));
    } catch {
        return bounded(redactText(text));
    }
}

export function persistHopFile(hop: HopRecord): void {
    const outDir = traceDir();
    mkdirSync(outDir, { recursive: true });
    const seq = Number(hop.seq);
    const hopLabel = String(hop.label);
    const path = join(outDir, `${String(seq).padStart(3, "0")}_${hopLabel}.json`);
    writeFileSync(path, `${JSON.stringify(hop, null, 2)}\n`, "utf8");
}

export class TracingTransport implements Transport {
    constructor(
        private readonly inner: Transport,
        private readonly persist: PersistHop = persistHopFile,
    ) {}

    async request(options: RequestOptions): Promise<Response> {
        const started = Date.now();
        try {
            const response = await this.inner.request(options);
            await this.safePersist(options, response, undefined, Date.now() - started);
            return response;
        } catch (error: unknown) {
            await this.safePersist(
                options,
                undefined,
                error instanceof Error ? error.message : String(error),
                Date.now() - started,
            );
            throw error;
        }
    }

    private async safePersist(
        options: RequestOptions,
        response: Response | undefined,
        error: string | undefined,
        durationMs: number,
    ): Promise<void> {
        try {
            counter += 1;
            const includeBodies = bodiesEnabled();
            const hop: HopRecord = {
                seq: counter,
                label: label(options.url),
                timestamp: new Date().toISOString(),
                duration_ms: durationMs,
                request: {
                    method: options.method,
                    url: redactUrl(options.url),
                    headers: redactHeaders(options.headers),
                },
                response: {
                    status_code: response?.status ?? null,
                    headers: redactHeaders(
                        response ? Object.fromEntries(response.headers.entries()) : undefined,
                    ),
                },
            };
            const requestBody = previewRequestBody(options.body, includeBodies);
            if (requestBody !== undefined) {
                (hop.request as Record<string, unknown>).body = requestBody;
            }
            if (response) {
                const responseBody = await previewResponseBody(response, includeBodies);
                if (responseBody !== undefined) {
                    (hop.response as Record<string, unknown>).body = responseBody;
                }
            }
            if (error !== undefined) {
                hop.error = error;
            }
            this.persist(hop);
        } catch {
            /* tracing must never break the postal request */
        }
    }
}

export function wrapTransport(inner: Transport): Transport {
    return tracingEnabled() ? new TracingTransport(inner) : inner;
}
