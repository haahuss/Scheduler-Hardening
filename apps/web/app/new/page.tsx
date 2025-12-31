"use client";

import { useMemo, useState } from "react";
import { createTournament } from "@/lib/api";
import { useRouter } from "next/navigation";

function isoFromLocalDatetime(localValue: string): string {
  // localValue is like "2025-12-30T18:00"
  // new Date(localValue) interprets it in local timezone and converts to ISO UTC.
  const d = new Date(localValue);
  return d.toISOString();
}

export default function NewTournamentPage() {
  const router = useRouter();

  const [name, setName] = useState("San Jose Winter Invite");
  const [teamsText, setTeamsText] = useState("Lions\nTigers\nBears\nHawks");
  const [venuesText, setVenuesText] = useState("Main Gym\nAux Gym");

  // Simple “time window builder”: user provides start, end; we store a list
  const [twStart, setTwStart] = useState("2025-12-31T10:00");
  const [twEnd, setTwEnd] = useState("2025-12-31T11:00");
  const [timeWindows, setTimeWindows] = useState<
    { start_local: string; end_local: string }[]
  >([
    { start_local: "2025-12-31T10:00", end_local: "2025-12-31T11:00" },
    { start_local: "2025-12-31T11:00", end_local: "2025-12-31T12:00" },
    { start_local: "2025-12-31T12:00", end_local: "2025-12-31T13:00" },
    { start_local: "2025-12-31T13:00", end_local: "2025-12-31T14:00" },
  ]);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const teams = useMemo(
    () =>
      teamsText
        .split("\n")
        .map((s) => s.trim())
        .filter(Boolean)
        .map((name) => ({ name })),
    [teamsText]
  );

  const venues = useMemo(
    () =>
      venuesText
        .split("\n")
        .map((s) => s.trim())
        .filter(Boolean)
        .map((name) => ({ name })),
    [venuesText]
  );

  async function onAddTimeWindow() {
    setTimeWindows((prev) => [...prev, { start_local: twStart, end_local: twEnd }]);
  }

  async function onCreate() {
    setErrorMsg(null);

    if (!name.trim()) return setErrorMsg("Tournament name is required.");
    if (teams.length < 2) return setErrorMsg("Add at least 2 teams.");
    if (venues.length < 1) return setErrorMsg("Add at least 1 venue.");
    if (timeWindows.length < 1) return setErrorMsg("Add at least 1 time window.");

    setIsSubmitting(true);
    try {
      const payload = {
        name: name.trim(),
        teams,
        venues,
        time_windows: timeWindows.map((tw) => ({
          start_ts: isoFromLocalDatetime(tw.start_local),
          end_ts: isoFromLocalDatetime(tw.end_local),
          venue_id: null, // Phase 0: not pinning windows to venues yet
        })),
      };

      const created = await createTournament(payload);
      router.push(`/t/${created.id}`);
    } catch (e: any) {
      setErrorMsg(e?.message || "Failed to create tournament.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main style={{ maxWidth: 980, margin: "40px auto", padding: 16 }}>
      <h1 style={{ fontSize: 28, fontWeight: 700 }}>Create Tournament</h1>

      <div style={{ marginTop: 18, display: "grid", gap: 14 }}>
        <label style={{ display: "grid", gap: 6 }}>
          <span style={{ fontWeight: 600 }}>Tournament name</span>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            style={{ padding: 10, border: "1px solid #ddd", borderRadius: 10 }}
          />
        </label>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
          <label style={{ display: "grid", gap: 6 }}>
            <span style={{ fontWeight: 600 }}>Teams (one per line)</span>
            <textarea
              value={teamsText}
              onChange={(e) => setTeamsText(e.target.value)}
              rows={8}
              style={{ padding: 10, border: "1px solid #ddd", borderRadius: 10 }}
            />
          </label>

          <label style={{ display: "grid", gap: 6 }}>
            <span style={{ fontWeight: 600 }}>Venues (one per line)</span>
            <textarea
              value={venuesText}
              onChange={(e) => setVenuesText(e.target.value)}
              rows={8}
              style={{ padding: 10, border: "1px solid #ddd", borderRadius: 10 }}
            />
          </label>
        </div>

        <section style={{ marginTop: 8 }}>
          <div style={{ display: "flex", alignItems: "baseline", gap: 12 }}>
            <h2 style={{ fontSize: 18, fontWeight: 700 }}>Time windows</h2>
            <span style={{ fontSize: 13, opacity: 0.8 }}>
              (Phase 0: global windows, not venue-specific)
            </span>
          </div>

          <div style={{ marginTop: 10, display: "flex", gap: 10, flexWrap: "wrap" }}>
            <label style={{ display: "grid", gap: 6 }}>
              <span style={{ fontWeight: 600 }}>Start</span>
              <input
                type="datetime-local"
                value={twStart}
                onChange={(e) => setTwStart(e.target.value)}
                style={{ padding: 10, border: "1px solid #ddd", borderRadius: 10 }}
              />
            </label>

            <label style={{ display: "grid", gap: 6 }}>
              <span style={{ fontWeight: 600 }}>End</span>
              <input
                type="datetime-local"
                value={twEnd}
                onChange={(e) => setTwEnd(e.target.value)}
                style={{ padding: 10, border: "1px solid #ddd", borderRadius: 10 }}
              />
            </label>

            <button
              type="button"
              onClick={onAddTimeWindow}
              style={{
                alignSelf: "end",
                padding: "10px 14px",
                border: "1px solid #ddd",
                borderRadius: 10,
                background: "white",
              }}
            >
              + Add time window
            </button>
          </div>

          <div style={{ marginTop: 12, border: "1px solid #eee", borderRadius: 12 }}>
            <div style={{ padding: 12, fontSize: 13, opacity: 0.8 }}>
              Current windows ({timeWindows.length})
            </div>
            <ul style={{ margin: 0, padding: "0 12px 12px 28px" }}>
              {timeWindows.map((tw, idx) => (
                <li key={idx} style={{ padding: "4px 0" }}>
                  {tw.start_local} → {tw.end_local}
                </li>
              ))}
            </ul>
          </div>
        </section>

        {errorMsg && (
          <div
            style={{
              marginTop: 8,
              padding: 12,
              border: "1px solid #f3c2c2",
              background: "#fff7f7",
              borderRadius: 12,
            }}
          >
            <b>Error:</b> {errorMsg}
          </div>
        )}

        <div style={{ marginTop: 10, display: "flex", gap: 10 }}>
          <button
            onClick={onCreate}
            disabled={isSubmitting}
            style={{
              padding: "10px 14px",
              border: "1px solid #ddd",
              borderRadius: 10,
              background: isSubmitting ? "#f5f5f5" : "white",
              cursor: isSubmitting ? "not-allowed" : "pointer",
            }}
          >
            {isSubmitting ? "Creating..." : "Create tournament"}
          </button>
        </div>
      </div>
    </main>
  );
}
