"use client";

import { useEffect, useMemo, useState } from "react";
import { getLatestRun, getTournament } from "@/lib/api";
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
  const [tournamentName, setTournamentName] = useState<string>("Tournament");


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

  useEffect(() => {
  async function loadTournamentName() {
    if (!tournamentId) return;
    try {
      const t = await getTournament(tournamentId);
      setTournamentName(t.name);
    } catch {
      // Not fatal; keep fallback label.
    }
  }
  loadTournamentName();
}, [tournamentId]);


  const games = useMemo(() => run?.schedule_json?.games || [], [run]);

  const groupedViolations = useMemo(() => {
    const vs = run?.metrics_json?.integrity?.violations || [];
    const map = new Map<string, any>();

    for (const v of vs) {
      const entityKey = v.team_id ? `team:${v.team_id}` : v.venue_id ? `venue:${v.venue_id}` : "none";
      const key = `${v.type}|${entityKey}`;

      if (!map.has(key)) {
        // games_map will dedupe by game_no
        const gamesMap = new Map<number, any>();

        if (Array.isArray(v.games)) {
          for (const g of v.games) {
            if (typeof g?.game_no === "number") gamesMap.set(g.game_no, g);
          }
        }

        map.set(key, {
          ...v,
          count: 1,          // number of pairwise conflicts grouped
          games_map: gamesMap,
        });
      } else {
        const existing = map.get(key);
        existing.count += 1;

        if (Array.isArray(v.games)) {
          for (const g of v.games) {
            if (typeof g?.game_no === "number") {
              existing.games_map.set(g.game_no, g);
            }
          }
        }
      }
    }

    // Convert games_map -> games (deduped + sorted)
    const grouped = Array.from(map.values()).map((v) => {
      const uniqueGames = Array.from(v.games_map.values()).sort(
        (a: any, b: any) => (a.game_no ?? 0) - (b.game_no ?? 0)
      );

      return {
        ...v,
        games: uniqueGames,
        unique_games_count: uniqueGames.length,
      };
    });

    return grouped;
  }, [run]);

  function groupGamesByTimeslot(games: any[]) {
    const map = new Map<string, any[]>();

    for (const g of games || []) {
      const key = `${g.start_ts}|${g.end_ts}`;
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(g);
    }

    // Sort groups by start time, and games by game_no
    const groups = Array.from(map.entries())
      .map(([key, list]) => {
        const [start_ts, end_ts] = key.split("|");
        const sorted = [...list].sort((a, b) => (a.game_no ?? 0) - (b.game_no ?? 0));
        return { start_ts, end_ts, games: sorted };
      })
      .sort((a, b) => new Date(a.start_ts).getTime() - new Date(b.start_ts).getTime());

    return groups;
  }




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
        Tournament: <b>{tournamentName}</b>{" "}
        <span style={{ fontSize: 12, opacity: 0.7 }}>
          (<code>{tournamentId || "…"}</code>)
        </span>
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

            <details style={{ marginTop: 10 }}>
              <summary style={{ cursor: "pointer", fontSize: 13, opacity: 0.85 }}>
                Developer metrics (JSON)
              </summary>

              <pre
                style={{
                  marginTop: 10,
                  padding: 10,
                  background: "#fafafa",
                  border: "1px solid #eee",
                  borderRadius: 12,
                  overflowX: "auto",
                  maxHeight: 240,          // prevents huge vertical bloat
                  overflowY: "auto",
                }}
              >
                {JSON.stringify(run.metrics_json || {}, null, 2)}
              </pre>
            </details>
            
          </section>

          <div style={{ marginTop: 14 }}>
            <h2 style={{ fontSize: 18, fontWeight: 700 }}>Schedule Health</h2>

            <div
              style={{
                marginTop: 10,
                padding: 14,
                border: "1px solid #eee",
                borderRadius: 14,
                background: "#fcfcfc",
              }}
            >
              <div style={{ display: "flex", gap: 18, flexWrap: "wrap" }}>
                <div>
                  <div style={{ fontSize: 12, opacity: 0.7 }}>Integrity</div>
                  <div style={{ fontWeight: 700 }}>
                    {run.metrics_json?.integrity?.status || "Not enabled yet (Phase 1)"}
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: 12, opacity: 0.7 }}>Violations</div>
                  <div style={{ fontWeight: 700 }}>
                    {run.metrics_json?.integrity?.violations_total ?? 0}
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: 12, opacity: 0.7 }}>Fairness</div>
                  <div style={{ fontWeight: 700 }}>
                    {typeof run.metrics_json?.fairness?.score === "number"
                      ? `${run.metrics_json.fairness.score}/100`
                      : "Coming next"}
                  </div>
                </div>
              </div>
              
              {typeof run.metrics_json?.fairness?.score === "number" && (
                <div style={{ marginTop: 10, fontSize: 13, opacity: 0.85, lineHeight: 1.5 }}>
                  Fairness is scored on a <b>0–100</b> scale. Higher is better. The score penalizes
                  back-to-back games and uneven rest distribution across teams.
                </div>
              )}

              {run.metrics_json?.fairness && (
                <div style={{ marginTop: 10, fontSize: 13 }}>
                  {typeof run.metrics_json.fairness.back_to_back_total === "number" && (
                    <div>
                      Back-to-backs: <b>{run.metrics_json.fairness.back_to_back_total}</b>
                    </div>
                  )}

                  {Array.isArray(run.metrics_json.fairness.top_offenders) &&
                    run.metrics_json.fairness.top_offenders.length > 0 && (
                      <div style={{ marginTop: 6 }}>
                        <div style={{ fontWeight: 700 }}>Top offenders</div>
                        <ul style={{ margin: 0, paddingLeft: 18 }}>
                          {run.metrics_json.fairness.top_offenders.slice(0, 3).map((o: any, i: number) => (
                            <li key={i}>
                              {o.team_name}: {o.count}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                </div>
              )}


              <div style={{ marginTop: 10, fontSize: 13, opacity: 0.85, lineHeight: 1.5 }}>
                In Phase 1, we’ll compute invariant checks (no double-bookings, venue conflicts, rest rules)
                and show “why” explanations for any warnings. This panel will light up automatically once
                the metrics are added to the API.
              </div>
            </div>
          </div>
          

          {run.metrics_json?.integrity?.violations?.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <h3 style={{ fontSize: 15, fontWeight: 700 }}>Why it failed (Top 5 Issues)</h3>
              <div style={{ fontSize: 12, opacity: 0.7, marginTop: 4 }}>
                Showing top issues. Total violations detected: {run.metrics_json?.integrity?.violations_total ?? 0}.
              </div>

              <div style={{ marginTop: 8, display: "grid", gap: 10 }}>
                {groupedViolations.slice(0, 5).map((v: any, idx: number) => (
                  <div
                    key={idx}
                    style={{
                      padding: 12,
                      border: "1px solid #f1d0d0",
                      background: "#fff7f7",
                      borderRadius: 12,
                    }}
                  >
                    <div style={{ fontWeight: 700 }}>
                      {v.type} — {v.severity}
                      {typeof v.unique_games_count === "number"
                        ? ` (conflicting games: ${v.unique_games_count})`
                        : ""}
                      {v.team_name ? ` (Team: ${v.team_name})` : ""}
                      {v.venue_name ? ` (Venue: ${v.venue_name})` : ""}
                    </div>
                    <div style={{ marginTop: 6 }}>{v.message}</div>
                    <div style={{ marginTop: 6, fontSize: 13, opacity: 0.85 }}>
                      {v.explain}
                    </div>

                    {/* REST_VIOLATION extra details */}
                    {v.type === "REST_VIOLATION" && typeof v.rest_minutes === "number" && (
                      <div
                        style={{
                          marginTop: 10,
                          padding: 10,
                          border: "1px solid #eee",
                          background: "white",
                          borderRadius: 12,
                          fontSize: 13,
                        }}
                      >
                        <div>
                          Rest time: <b>{v.rest_minutes} min</b>{" "}
                          <span style={{ opacity: 0.75 }}>
                            (minimum required: {v.min_rest_minutes} min)
                          </span>
                        </div>
                        <div style={{ marginTop: 6, opacity: 0.9 }}>
                          This team is scheduled too tightly between these games.
                        </div>
                      </div>
                    )}


                    {Array.isArray(v.games) && v.games.length > 0 && (
                      <div style={{ marginTop: 10, fontSize: 13 }}>
                        <div style={{ fontWeight: 700, marginBottom: 6 }}>Conflicts by time slot</div>

                        {groupGamesByTimeslot(v.games).map((grp, idx) => (
                          <div key={idx} style={{ marginBottom: 10 }}>
                            <div style={{ fontWeight: 700, marginBottom: 4 }}>
                              {new Date(grp.start_ts).toLocaleString()} → {new Date(grp.end_ts).toLocaleString()}
                            </div>

                            <ul style={{ margin: 0, paddingLeft: 18 }}>
                              {grp.games.map((g: any, i: number) => (
                                <li key={i} style={{ marginBottom: 4 }}>
                                  <b>Game #{g.game_no}</b>
                                  {g.vs ? ` — vs ${g.vs}` : ""}
                                  {g.matchup ? ` — ${g.matchup}` : ""}
                                  {" "}
                                  — {new Date(g.start_ts).toLocaleString()} → {new Date(g.end_ts).toLocaleString()}
                                  {" "}
                                  {g.venue_name ? `@ ${g.venue_name}` : g.venue_id ? `@ ${g.venue_id}` : ""}
                                </li>
                              ))}
                            </ul>
                          </div>
                        ))}
                      </div>
                    )}


                  </div>
                ))}
              </div>
            </div>
          )}


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
                        {g.home_team_name || g.home_team_id}
                      </td>
                      <td style={{ padding: 10, borderBottom: "1px solid #f1f1f1", fontFamily: "monospace" }}>
                        {g.away_team_name || g.away_team_id}
                      </td>
                      <td style={{ padding: 10, borderBottom: "1px solid #f1f1f1" }}>
                        {new Date(g.start_ts).toLocaleString()}
                      </td>
                      <td style={{ padding: 10, borderBottom: "1px solid #f1f1f1" }}>
                        {new Date(g.end_ts).toLocaleString()}
                      </td>
                      <td style={{ padding: 10, borderBottom: "1px solid #f1f1f1", fontFamily: "monospace" }}>
                        {g.venue_name || g.venue_id}
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
