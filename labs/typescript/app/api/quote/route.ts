import { createPortoClient } from "../../../../lib/typescript/porto_client.ts";

export const runtime = "nodejs";

type QuoteRequest = {
  countryCode?: string;
  weight?: number;
};

const providerId = process.env.PORTO_PROVIDER ?? "deutschepost";
const client = createPortoClient({ providers: { [providerId]: {} } });

export async function POST(request: Request): Promise<Response> {
  let body: QuoteRequest = {};
  try {
    body = (await request.json()) as QuoteRequest;
  } catch {
    // Keep defaults when body is missing or invalid JSON.
  }

  const countryCode = (body.countryCode ?? "DE").toUpperCase();
  const weight = body.weight ?? 20;

  try {
    const resolved = await client.provider(providerId).resolve({
      countryCode,
      weight,
    });

    return Response.json({
      framework: "nextjs",
      productId: resolved.product.id,
      zoneId: resolved.zone.id,
      basePriceCents: resolved.basePrice,
      currency: resolved.currency,
      isValid: resolved.isValid,
    });
  } catch (error) {
    return Response.json(
      { error: error instanceof Error ? error.message : "Unknown error" },
      { status: 400 }
    );
  }
}
