"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

import { createTournament, getErrorMessage } from "@/lib/api";

function normName(s: string) {
  return s.trim().toLowerCase().replace(/\s+/g, " ");
}

function findDuplicates(items: { name: string }[]) {
  const seen = new Map<string, number>();
  for (const it of items) {
    const n = normName(it.name);
    if (!n) continue;
    seen.set(n, (seen.get(n) ?? 0) + 1);
  }
  return Array.from(seen.entries())
    .filter(([, count]) => count > 1)
    .map(([name]) => name);
}


function isoFromLocalDatetime(localValue: string): string {
  // localValue is like "2025-12-30T18:00"
  // new Date(localValue) interprets it in local timezone and converts to ISO UTC.
  const d = new Date(localValue);
  return d.toISOString();
}

export default function NewTournamentPage() {
  const router = useRouter();

  const [name, setName] = useState("College Winter Invite");
  const [teamsText, setTeamsText] = useState("Lions\nTigers\nBears\nHawks");
  const [venuesText, setVenuesText] = useState("Main Gym\nAux Gym");

  // Simple “time window builder”: user provides start, end; we store a list
  const [timeWindows, setTimeWindows] = useState<
    { start_ts: string; end_ts: string }[]
  >([]);


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

  async function onCreate() {
    setErrorMsg(null);

    if (!name.trim()) return setErrorMsg("Tournament name is required.");
    if (teams.length < 2) return setErrorMsg("Add at least 2 teams.");
    if (teams.length > 24) return setErrorMsg("Max 24 teams allowed (demo safety limit).");
    if (venues.length < 1) return setErrorMsg("Add at least 1 venue.");
    if (timeWindows.length < 1) return setErrorMsg("Add at least 1 time window.");

    // validation goes RIGHT HERE
    const normalized = (s: string) => s.trim().toLowerCase();
    const teamNames = teams.map(t => normalized(t.name));
    const dupTeams = teamNames.filter((n, i) => teamNames.indexOf(n) !== i);
    if (dupTeams.length) return setErrorMsg(`Duplicate team names not allowed: ${[...new Set(dupTeams)].join(", ")}`);

    const venueNames = venues.map(v => normalized(v.name));
    const dupVenues = venueNames.filter((n, i) => venueNames.indexOf(n) !== i);
    if (dupVenues.length) return setErrorMsg(`Duplicate venue names not allowed: ${[...new Set(dupVenues)].join(", ")}`);

    const now = new Date();

    for (const tw of timeWindows) {
      const s = new Date(tw.start_ts);
      const e = new Date(tw.end_ts);

      if (isNaN(s.getTime()) || isNaN(e.getTime())) {
        return setErrorMsg("Time windows must have valid start/end values.");
      }
      if (s < now) {
        return setErrorMsg("Time windows cannot start in the past.");
      }
      if (e <= s) {
        return setErrorMsg("Time window end must be after start.");
      }
      
      const dupTeams = findDuplicates(teams);
      if (dupTeams.length > 0) {
        return setErrorMsg(`Duplicate team name(s) not allowed: ${dupTeams.join(", ")}`);
      }
  
      const dupVenues = findDuplicates(venues);
      if (dupVenues.length > 0) {
        return setErrorMsg(`Duplicate venue name(s) not allowed: ${dupVenues.join(", ")}`);
      }
    }



    setIsSubmitting(true);
    try {
      const payload = {
        name: name.trim(),
        teams,
        venues,
        time_windows: timeWindows.map((tw) => ({
          start_ts: isoFromLocalDatetime(tw.start_ts),
          end_ts: isoFromLocalDatetime(tw.end_ts),
          venue_id: null,
        })),
      };

      const created = await createTournament(payload);
      router.push(`/t/${created.id}`);
    } catch (e: unknown) {
      const msg = getErrorMessage(e);
      setErrorMsg(msg || "Failed to create tournament.");
    } finally {
      setIsSubmitting(false);
    }
  }


  function toLocalInput(d: Date) {
    const pad = (n: number) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  }

  function addTimeWindow() {
    const now = new Date();
    const start = new Date(now.getTime() + 60 * 60 * 1000); // +1 hour
    const end = new Date(start.getTime() + 60 * 60 * 1000); // +1 hour

    setTimeWindows((prev) => [
      ...prev,
      { start_ts: toLocalInput(start), end_ts: toLocalInput(end) },
    ]);
  }

  function removeTimeWindow(idx: number) {
    setTimeWindows((prev) => prev.filter((_, i) => i !== idx));
  }


  return (
    <main style={{ maxWidth: 980, margin: "40px auto", padding: 16 }}>
      {/* <h1 style={{ fontSize: 28, fontWeight: 700 }}>Create Tournament</h1> */}
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <h1 style={{ fontSize: 28, fontWeight: 700, margin: 0 }}>Create Tournament</h1>
        <Link
          href="/"
          style={{
            marginLeft: "auto",
            padding: "8px 12px",
            border: "1px solid #ddd",
            borderRadius: 10,
            textDecoration: "none",
            background: "LightGray",
          }}
        >
          Go back to Home
        </Link>
      </div>


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

        <section style={{ marginTop: 16 }}>
          <div style={{ fontWeight: 800 }}>Time windows</div>
          <div style={{ fontSize: 13, opacity: 0.8, marginTop: 4 }}>
            Add one or more windows. These define when games can be scheduled.
          </div>

          <button
            type="button"
            onClick={addTimeWindow}
            style={{
              marginTop: 10,
              padding: "8px 12px",
              border: "1px solid #ddd",
              borderRadius: 10,
              background: "lightblue",
            }}
          >
            + Add time window
          </button>

          {timeWindows.length === 0 && (
            <div style={{ marginTop: 10, fontSize: 13, opacity: 0.75 }}>
              No time windows yet.
            </div>
          )}

          {timeWindows.map((tw, idx) => (
            <div
              key={idx}
              style={{
                display: "flex",
                gap: 10,
                marginTop: 12,
                alignItems: "end",
                padding: 10,
                border: "1px solid #eee",
                borderRadius: 12,
              }}
            >
              <div>
                <div style={{ fontSize: 12, opacity: 0.7 }}>Start</div>
                <input
                  type="datetime-local"
                  value={tw.start_ts}
                  onChange={(e) => {
                    const v = e.target.value;
                    setTimeWindows((prev) =>
                      prev.map((x, i) => (i === idx ? { ...x, start_ts: v } : x))
                    );
                  }}
                />
              </div>

              <div>
                <div style={{ fontSize: 12, opacity: 0.7 }}>End</div>
                <input
                  type="datetime-local"
                  value={tw.end_ts}
                  onChange={(e) => {
                    const v = e.target.value;
                    setTimeWindows((prev) =>
                      prev.map((x, i) => (i === idx ? { ...x, end_ts: v } : x))
                    );
                  }}
                />
              </div>

              <button
                type="button"
                onClick={() => removeTimeWindow(idx)}
                style={{
                  padding: "8px 12px",
                  border: "1px solid #ddd",
                  borderRadius: 10,
                  background: "#d50000ff",
                  color: "white"
                }}
              >
                Remove
              </button>
            </div>
          ))}
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
              background: isSubmitting ? "#6fc140ff" : "lightgreen",
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
