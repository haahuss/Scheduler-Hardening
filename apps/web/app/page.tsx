// apps/web/app/page.tsx
import Link from "next/link";

export default function HomePage() {
  return (
    <main style={{ maxWidth: 900, margin: "40px auto", padding: 16 }}>
      <h1 style={{ fontSize: 32, fontWeight: 700 }}>Scheduler Hardening</h1>
      <p style={{ marginTop: 8, fontSize: 16, lineHeight: 1.5 }}>
        Build a tournament schedule and validate it with integrity checks (later phases).
        Phase 0: create tournament → generate schedule → view results.
      </p>

      <div style={{ marginTop: 24 }}>
        <Link
          href="/new"
          style={{
            display: "inline-block",
            padding: "10px 14px",
            border: "1px solid #ddd",
            borderRadius: 10,
            textDecoration: "none",
          }}
        >
          + Create Tournament
        </Link>
      </div>

      <div style={{ marginTop: 24, fontSize: 13, opacity: 0.8 }}>
        API: {process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"}
      </div>
    </main>
  );
}
