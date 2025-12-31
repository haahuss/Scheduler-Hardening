"use client";

import { useEffect, useMemo, useState } from "react";
import { getLatestRun } from "@/lib/api";
import { useRouter, useParams } from "next/navigation";

export default function SchedulePage() {
  const router = useRouter();
  const params = useParams();

  const tournamentIdRaw = params?.id;
  const tournamentId =
    typeof tournamentIdRaw === "string" ? tournamentIdRaw : tournamentIdRaw?.[0];

  const [loading, setLoading] = useState(true);
  const [run, setRun] = useState<any>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  async function load() {
    setErrorMsg(null);

    if (!tournamentId) {
      setErrorMsg("Tournament ID missing in URL.");
      setLoading(false);
      return;
    }

    setLoading(true);
    try {
      const r = await getLatestRun(tournamentId);
      setRun(r);
    } catch (e: any) {
      setErrorMsg(e?.message || "Failed to load schedule.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tournamentId]);

  const games = useMemo(() => run?.schedule_json?.games || [], [run]);

  return (
    <main style={{ maxWidth: 1100, margin: "40px auto", padding: 16 }}>
      <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
        <h1 style={{ fontSize: 28, fontWeight: 700 }}>Latest Schedule</h1>

        <button
          onClick={() => tournamentId && router.push(`/t/${tournamentId}`)}
          disabled={!tournamentId}
          style={{
            marginLeft: "auto",
            padding: "8px 12px",
            border: "1px solid #ddd",
            borderRadius: 10,
            background: "white",
          }}
        >
          ← Back
        </button>

        <button
          onClick={load}
          style={{
            padding: "8px 12px",
            border: "1px solid #ddd",
            borderRadius: 10,
            background: "white",
          }}
        >
          Refresh
        </button>
      </div>

      <p style={{ marginTop: 6, opacity: 0.8 }}>
        Tournament: <code>{tournamentId || "…"}</code>
      </p>

      {loading && <div style={{ marginTop: 18 }}>Loading…</div>}

      {errorMsg && (
        <div
          style={{
            marginTop: 14,
            padding: 12,
            border: "1px solid #f3c2c2",
            background: "#fff7f7",
            borderRadius: 12,
          }}
        >
          <b>Error:</b> {errorMsg}
        </div>
      )}

      {!loading && run && (
        <>
          <section
            style={{
              marginTop: 18,
              padding: 14,
              border: "1px solid #eee",
              borderRadius: 14,
            }}
          >
            <div style={{ display: "flex", gap: 14, flexWrap: "wrap" }}>
              <div>
                <div style={{ fontSize: 12, opacity: 0.7 }}>Status</div>
                <div style={{ fontWeight: 700 }}>{run.status}</div>
              </div>
              <div>
                <div style={{ fontSize: 12, opacity: 0.7 }}>Run ID</div>
                <div style={{ fontFamily: "monospace" }}>{run.id}</div>
              </div>
              <div>
                <div style={{ fontSize: 12, opacity: 0.7 }}>Created</div>
                <div>{new Date(run.created_at).toLocaleString()}</div>
              </div>
            </div>

            <div style={{ marginTop: 10 }}>
              <div style={{ fontSize: 12, opacity: 0.7 }}>Metrics</div>
              <pre
                style={{
                  marginTop: 6,
                  padding: 10,
                  background: "#fafafa",
                  border: "1px solid #eee",
                  borderRadius: 12,
                  overflowX: "auto",
                }}
              >
                {JSON.stringify(run.metrics_json || {}, null, 2)}
              </pre>
            </div>
          </section>

          <section style={{ marginTop: 18 }}>
            <h2 style={{ fontSize: 18, fontWeight: 700 }}>
              Games ({games.length})
            </h2>

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
                    <th style={{ textAlign: "left", padding: 10, borderBottom: "1px solid #eee" }}>#</th>
                    <th style={{ textAlign: "left", padding: 10, borderBottom: "1px solid #eee" }}>Home</th>
                    <th style={{ textAlign: "left", padding: 10, borderBottom: "1px solid #eee" }}>Away</th>
                    <th style={{ textAlign: "left", padding: 10, borderBottom: "1px solid #eee" }}>Start</th>
                    <th style={{ textAlign: "left", padding: 10, borderBottom: "1px solid #eee" }}>End</th>
                    <th style={{ textAlign: "left", padding: 10, borderBottom: "1px solid #eee" }}>Venue</th>
                  </tr>
                </thead>
                <tbody>
                  {games.map((g: any) => (
                    <tr key={g.game_no}>
                      <td style={{ padding: 10, borderBottom: "1px solid #f1f1f1" }}>{g.game_no}</td>
                      <td style={{ padding: 10, borderBottom: "1px solid #f1f1f1", fontFamily: "monospace" }}>
                        {g.home_team_id}
                      </td>
                      <td style={{ padding: 10, borderBottom: "1px solid #f1f1f1", fontFamily: "monospace" }}>
                        {g.away_team_id}
                      </td>
                      <td style={{ padding: 10, borderBottom: "1px solid #f1f1f1" }}>
                        {new Date(g.start_ts).toLocaleString()}
                      </td>
                      <td style={{ padding: 10, borderBottom: "1px solid #f1f1f1" }}>
                        {new Date(g.end_ts).toLocaleString()}
                      </td>
                      <td style={{ padding: 10, borderBottom: "1px solid #f1f1f1", fontFamily: "monospace" }}>
                        {g.venue_id}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </main>
  );
}
