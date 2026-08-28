/** Shared redaction helpers for lab artifacts and HTTP traces. */

const SENSITIVE_KEYS = new Set([
    "password",
    "passwd",
    "token",
    "authorization",
    "api_key",
    "api_secret",
    "api-key",
    "x-api-key",
    "client_secret",
    "client_id",
    "access_token",
    "refresh_token",
    "cookie",
    "set-cookie",
    "username",
    "partner_id",
    "signature",
    "secret",
    "portokasse",
    "application_id",
    "account_id",
    "account_number",
    "app_secret",
    "private_key",
]);

const SENSITIVE_FRAGMENTS = [
    "password",
    "passwd",
    "secret",
    "token",
    "authorization",
    "cookie",
    "apikey",
    "apisecret",
];

const SECRET_KV_PATTERN =
    /\b(password|passwd|secret|token|api[_-]?key|client[_-]?secret)\b\s*([:=])\s*([^\s,;]+)/gi;

function normalizedKey(key: string): string {
    return key.toLowerCase().replace(/[^a-z0-9]/g, "");
}

const SENSITIVE_NORMALIZED = new Set([...SENSITIVE_KEYS].map(normalizedKey));

export function isSensitiveKey(key: string): boolean {
    const normalized = normalizedKey(key);
    if (SENSITIVE_NORMALIZED.has(normalized)) return true;
    return SENSITIVE_FRAGMENTS.some((fragment) => normalized.includes(fragment));
}

export function redactHeaders(headers: Record<string, string> | undefined): Record<string, string> {
    if (!headers) return {};
    const out: Record<string, string> = {};
    for (const [key, value] of Object.entries(headers)) {
        out[key] = isSensitiveKey(key) ? "[REDACTED]" : value;
    }
    return out;
}

export function redactPayload<T>(payload: T): T {
    if (payload === null || payload === undefined) return payload;
    if (Array.isArray(payload)) {
        return payload.map((item) => redactPayload(item)) as T;
    }
    if (typeof payload === "object") {
        const out: Record<string, unknown> = {};
        for (const [key, value] of Object.entries(payload as Record<string, unknown>)) {
            out[key] = isSensitiveKey(key) ? "[REDACTED]" : redactPayload(value);
        }
        return out as T;
    }
    return payload;
}

export function redactText(text: string): string {
    return text.replace(SECRET_KV_PATTERN, (_match, name: string, separator: string) => {
        return `${name}${separator}[REDACTED]`;
    });
}

export function redactUrl(url: string): string {
    try {
        const parsed = new URL(url);
        for (const key of [...parsed.searchParams.keys()]) {
            if (isSensitiveKey(key)) {
                parsed.searchParams.set(key, "[REDACTED]");
            }
        }
        return parsed.toString();
    } catch {
        return url;
    }
}
