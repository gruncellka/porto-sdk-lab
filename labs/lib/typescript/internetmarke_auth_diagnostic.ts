/** Shared Internetmarke auth classification for lab preflight scripts.
 *
 * Lab consumes Internetmarke adapter mapper output only. It must not re-parse
 * provider body text to invent PORTO_* codes. Direction is always:
 *
 *   adapter mapper → PORTO_* (+ diagnosticReason + providerError) → Lab
 */

import {
  DIAG_INVALID_PORTOKASSE_CREDENTIALS,
  DIAG_PENDING_PORTOKASSE_APPROVAL,
  DIAG_UNKNOWN_CHANNEL,
  InternetmarkeAuthEndpoint,
  internetmarkeAuthErrorDetails,
  mapInternetmarkeAuthHttpError,
  type InternetmarkeAuthErrorInfo,
} from "../../../sdks/porto-sdk-typescript/src/adapters/deutschepost/internetmarke/auth-errors.ts";
import { PortoErrorCode } from "../../../sdks/porto-sdk-typescript/src/errors.ts";

export type AuthDiagnostic = {
  status: string;
  hint: string;
  blocking_stage: string;
  next_steps: string[];
  app_status: number | null;
  user_status: number | null;
  app_body_preview: string;
  user_body_preview: string;
  sdk_error_code: string | null;
  diagnostic_reason: string | null;
  provider_error: Record<string, unknown> | null;
};

function providerError(info: InternetmarkeAuthErrorInfo): Record<string, unknown> {
  const details = internetmarkeAuthErrorDetails(info);
  const bag = details.provider_error;
  return bag && typeof bag === "object" && !Array.isArray(bag)
    ? { ...(bag as Record<string, unknown>) }
    : {};
}

function nextStepsFor(bag: Record<string, unknown>): string[] {
  const stage = bag.stage;
  const reason = bag.reason;
  if (stage === "dhl_developer_app") {
    const steps = [
      "Open DHL Developer Portal → your app → confirm approval for Post & Parcel Germany / Internetmarke.",
      "Verify PORTO_DEUTSCHEPOST_INTERNETMARKE_API_KEY and _API_SECRET.",
      "Re-run gate check (no purchase required).",
    ];
    if (reason === DIAG_UNKNOWN_CHANNEL) {
      steps.unshift(
        "Replace stale/Wing-mapped developer-app credentials — DHL reported unknown channel for this app.",
      );
    }
    return steps;
  }
  if (stage === "portokasse_linkage") {
    return [
      "Log in to Portokasse → Meine Daten → Geschäftsanwendungen.",
      "Approve the business application (Freigabe).",
      "Re-run gate check (no purchase required).",
    ];
  }
  if (stage === "portokasse_credentials") {
    return [
      "Verify PORTO_DEUTSCHEPOST_INTERNETMARKE_USERNAME and _PASSWORD.",
      "Re-run gate check.",
    ];
  }
  return ["Inspect saved JSON provider_error / body_preview."];
}

function diagnosticFromError(
  info: InternetmarkeAuthErrorInfo,
  appStatus: number | null,
  userStatus: number | null,
  appBody: string,
  userBody: string,
): AuthDiagnostic {
  const bag = providerError(info);
  const reason = typeof bag.reason === "string" ? bag.reason : "unknown";
  return {
    status: reason,
    hint: typeof bag.hint === "string" ? bag.hint : "",
    blocking_stage: typeof bag.stage === "string" ? bag.stage : "unknown",
    next_steps: nextStepsFor(bag),
    app_status: appStatus,
    user_status: userStatus,
    app_body_preview: appBody.slice(0, 2000),
    user_body_preview: userBody.slice(0, 4000),
    sdk_error_code: String(info.code),
    diagnostic_reason: reason,
    provider_error: bag,
  };
}

export function classifyInternetmarkeAuth(args: {
  appStatus: number | null;
  userStatus: number | null;
  appBody?: string;
  userBody?: string;
}): AuthDiagnostic {
  const appBody = args.appBody ?? "";
  const userBody = args.userBody ?? "";

  if (args.userStatus === 200) {
    return {
      status: "connected",
      hint: "App + Portokasse auth succeeded. Safe to run canary/full matrix.",
      blocking_stage: "none",
      next_steps: [],
      app_status: args.appStatus,
      user_status: args.userStatus,
      app_body_preview: appBody.slice(0, 2000),
      user_body_preview: userBody.slice(0, 4000),
      sdk_error_code: null,
      diagnostic_reason: null,
      provider_error: null,
    };
  }

  if (args.appStatus !== 200) {
    const info = mapInternetmarkeAuthHttpError(args.appStatus ?? 0, appBody, {
      endpoint: InternetmarkeAuthEndpoint.DHL_APP_TOKEN,
    });
    return diagnosticFromError(info, args.appStatus, args.userStatus, appBody, userBody);
  }

  const info = mapInternetmarkeAuthHttpError(args.userStatus ?? 0, userBody, {
    endpoint: InternetmarkeAuthEndpoint.PORTOKASSE_USER,
    appTokenObtained: true,
  });
  return diagnosticFromError(info, args.appStatus, args.userStatus, appBody, userBody);
}

export function exitCodeForAuthStatus(status: string): number {
  if (status === "connected") return 0;
  if (
    status === DIAG_UNKNOWN_CHANNEL ||
    status === DIAG_PENDING_PORTOKASSE_APPROVAL
  ) {
    return 1;
  }
  return 2;
}

export async function probeInternetmarkeAuth(args: {
  baseUrl: string;
  username?: string;
  password?: string;
  apiKey?: string;
  apiSecret?: string;
}): Promise<AuthDiagnostic> {
  const missing = [
    ["PORTO_DEUTSCHEPOST_INTERNETMARKE_API_KEY", args.apiKey],
    ["PORTO_DEUTSCHEPOST_INTERNETMARKE_API_SECRET", args.apiSecret],
    ["PORTO_DEUTSCHEPOST_INTERNETMARKE_USERNAME", args.username],
    ["PORTO_DEUTSCHEPOST_INTERNETMARKE_PASSWORD", args.password],
  ]
    .filter(([, val]) => !val)
    .map(([name]) => name);

  if (missing.length > 0) {
    return {
      status: "missing_credentials",
      hint: `Missing env vars: ${missing.join(", ")}`,
      blocking_stage: "configuration",
      next_steps: ["Copy .env.example → .env at repo root and fill Internetmarke values."],
      app_status: null,
      user_status: null,
      app_body_preview: "",
      user_body_preview: "",
      sdk_error_code: null,
      diagnostic_reason: null,
      provider_error: null,
    };
  }

  const root = args.baseUrl.replace(/\/$/, "");
  const body = new URLSearchParams({
    grant_type: "client_credentials",
    client_id: args.apiKey!,
    client_secret: args.apiSecret!,
    username: args.username!,
    password: args.password!,
  });

  // Prefer combined /user (production purchase path). Keep the first mapper
  // result — do not reclassify as DHL_APP_TOKEN (avoids DENIED→FAILED downgrade).
  const combinedResp = await fetch(`${root}/user`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  const combinedBody = (await combinedResp.text()).slice(0, 4000);

  if (combinedResp.ok) {
    return {
      status: "connected",
      hint: "App + Portokasse auth succeeded. Safe to run canary/full matrix.",
      blocking_stage: "none",
      next_steps: [],
      app_status: 200,
      user_status: 200,
      app_body_preview: "",
      user_body_preview: combinedBody.slice(0, 2000),
      sdk_error_code: null,
      diagnostic_reason: null,
      provider_error: null,
    };
  }

  const info = mapInternetmarkeAuthHttpError(combinedResp.status, combinedBody, {
    endpoint: InternetmarkeAuthEndpoint.COMBINED_USER,
  });

  if (
    providerError(info).stage === "portokasse_linkage" ||
    providerError(info).stage === "portokasse_credentials"
  ) {
    return diagnosticFromError(info, 200, combinedResp.status, "", combinedBody);
  }

  return diagnosticFromError(info, combinedResp.status, null, combinedBody, "");
}

export {
  DIAG_INVALID_PORTOKASSE_CREDENTIALS,
  DIAG_PENDING_PORTOKASSE_APPROVAL,
  DIAG_UNKNOWN_CHANNEL,
  PortoErrorCode,
};
