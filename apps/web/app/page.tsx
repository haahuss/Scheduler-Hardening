"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { listTournaments } from "@/lib/api";

export default function HomePage() {
  const [items, setItems] = useState<
    { id: string; name: string; created_at: string }[]
  >([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  async function load() {
    setErr(null);
    setLoading(true);
    try {
      const data = await listTournaments();
      setItems(data);
    } catch (e: any) {
      setErr(e?.message || "Failed to load tournaments");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <main style={{ maxWidth: 900, margin: "40px auto", padding: 16 }}>
      <div style={{ display: "flex", alignItems: "baseline", gap: 12 }}>
        <h1 style={{ fontSize: 32, fontWeight: 700 }}>Scheduler Hardening</h1>
        <span style={{ fontSize: 13, opacity: 0.7 }}>
          Phase 1: Integrity + Explainability
        </span>
      </div>

      <p style={{ marginTop: 8, fontSize: 16, lineHeight: 1.5 }}>
        Create tournaments, generate schedules, and (next) validate them with integrity checks.
      </p>

      <div style={{ marginTop: 18, display: "flex", gap: 10 }}>
        <Link
          href="/new"
          style={{
            display: "inline-block",
            padding: "10px 14px",
            border: "1px solid #ddd",
            borderRadius: 10,
            textDecoration: "none",
            background: "lightgreen"
          }}
        >
          + Create Tournament
        </Link>

        <button
          onClick={load}
          style={{
            padding: "10px 14px",
            border: "1px solid #ddd",
            borderRadius: 10,
            background: "lightyellow",
          }}
        >
          Refresh
        </button>
      </div>

      <section style={{ marginTop: 22 }}>
        <h2 style={{ fontSize: 18, fontWeight: 700 }}>Recent tournaments</h2>

        {loading && <div style={{ marginTop: 10 }}>Loading…</div>}

        {err && (
          <div
            style={{
              marginTop: 10,
              padding: 12,
              border: "1px solid #f3c2c2",
              background: "#fff7f7",
              borderRadius: 12,
            }}
          >
            <b>Error:</b> {err}
          </div>
        )}

        {!loading && !err && items.length === 0 && (
          <div style={{ marginTop: 10, opacity: 0.8 }}>
            No tournaments yet. Create one to get started.
          </div>
        )}

        {!loading && !err && items.length > 0 && (
          <div
            style={{
              marginTop: 10,
              border: "1px solid #eee",
              borderRadius: 14,
              overflow: "hidden",
            }}
          >
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead style={{ background: "#fafafa" }}>
                <tr>
                  <th style={{ textAlign: "left", padding: 10, borderBottom: "1px solid #eee" }}>
                    Tournament
                  </th>
                  <th style={{ textAlign: "left", padding: 10, borderBottom: "1px solid #eee" }}>
                    Created
                  </th>
                  <th style={{ textAlign: "left", padding: 10, borderBottom: "1px solid #eee" }}>
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {items.map((t) => (
                  <tr key={t.id}>
                    <td style={{ padding: 10, borderBottom: "1px solid #f1f1f1" }}>
                      <div style={{ fontWeight: 700 }}>{t.name}</div>
                      <div style={{ fontSize: 12, opacity: 0.7 }}>
                        <code>{t.id}</code>
                      </div>
                    </td>
                    <td style={{ padding: 10, borderBottom: "1px solid #f1f1f1" }}>
                      {new Date(t.created_at).toLocaleString()}
                    </td>
                    <td style={{ padding: 10, borderBottom: "1px solid #f1f1f1" }}>
                      <Link
                        href={`/t/${t.id}`}
                        style={{
                          display: "inline-block",
                          padding: "8px 12px",
                          border: "1px solid #ddd",
                          borderRadius: 10,
                          textDecoration: "none",
                          background: "#c4eef7aa"
                        }}
                      >
                        Open
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  );
}
