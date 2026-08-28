/**
 * Smoke-test Next.js route integration without starting a server.
 */

import { POST } from "./app/api/quote/route";

async function main() {
  const request = new Request("http://localhost:3000/api/quote", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      letterType: "standard",
      countryCode: "DE",
      weight: 20,
    }),
  });

  const response = await POST(request);
  const body = await response.json();
  console.log("Status:", response.status);
  console.log("Body:", body);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
