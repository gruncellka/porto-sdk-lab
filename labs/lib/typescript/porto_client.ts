/** Lab PortoClient factory. Injects tracing transport when HTTP trace is enabled. */

import { PortoClient, type PortoConfig } from "../../../sdks/porto-sdk-typescript/src/client.ts";
import { resolveTransport } from "../../../sdks/porto-sdk-typescript/src/config.ts";
import { HttpClient } from "../../../sdks/porto-sdk-typescript/src/transport/http-client.ts";
import { wrapTransport } from "./http_trace.ts";

export function createPortoClient(config: PortoConfig): PortoClient {
  const policy = resolveTransport(config);
  const inner = new HttpClient(policy.timeout, policy.retries);
  return new PortoClient(config, { transport: wrapTransport(inner) });
}
