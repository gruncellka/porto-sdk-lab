/** Lab-only Internetmarke API root probe (not a PortoClient method). */

export async function health(baseUrl: string): Promise<Record<string, unknown>> {
  const url = `${baseUrl.replace(/\/$/, "")}/`;
  const response = await fetch(url);
  const text = await response.text();
  if (!response.ok) {
    throw new Error(`Internetmarke API unavailable: ${response.status} GET ${url}`);
  }
  try {
    return JSON.parse(text) as Record<string, unknown>;
  } catch {
    return { text: text.slice(0, 2000) };
  }
}
