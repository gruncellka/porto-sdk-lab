export default function HomePage() {
  return (
    <main
      style={{
        fontFamily: "sans-serif",
        maxWidth: 720,
        margin: "40px auto",
        padding: "0 16px",
      }}
    >
      <h1>Porto SDK TypeScript Lab (Next.js)</h1>
      <p>
        This lab validates SDK integration in a real Next.js runtime. Use{" "}
        <code>POST /api/quote</code> to run a resolver quote through the SDK.
      </p>
      <pre style={{ background: "#f4f4f4", padding: 12, borderRadius: 6 }}>
        {`curl -X POST http://localhost:3000/api/quote \\
  -H "Content-Type: application/json" \\
  -d '{"letterType":"standard","countryCode":"DE","weight":20}'`}
      </pre>
    </main>
  );
}
