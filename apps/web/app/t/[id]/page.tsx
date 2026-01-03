"use client";

import { useEffect, useState } from "react";
import { generateSchedule, getErrorMessage, getTournament } from "@/lib/api";
import { useRouter, useParams } from "next/navigation";
import Link from "next/link";


export default function TournamentPage() {
  const router = useRouter();
  const params = useParams();

  const tournamentIdRaw = params?.id;
  const tournamentId =
    typeof tournamentIdRaw === "string" ? tournamentIdRaw : tournamentIdRaw?.[0];

  const [tournamentName, setTournamentName] = useState<string>("Tournament");
  const [isGenerating, setIsGenerating] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      if (!tournamentId) return;
      try {
        const t = await getTournament(tournamentId);
        setTournamentName(t.name);
      } catch {
        // If it fails, we keep a fallback title; not fatal.
      }
    }
    load();
  }, [tournamentId]);

  async function onGenerate() {
    setErrorMsg(null);

    if (!tournamentId) {
      setErrorMsg("Tournament ID missing in URL.");
      return;
    }

    setIsGenerating(true);
    try {
      await generateSchedule(tournamentId);
      router.push(`/t/${tournamentId}/schedule`);
    } catch (e: unknown) {
      const msg = getErrorMessage(e);
      setErrorMsg(msg || "Failed to generate schedule.");
    } finally {
      setIsGenerating(false);
    }
  }

  return (
    <main style={{ maxWidth: 900, margin: "40px auto", padding: 16 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <h1 style={{ fontSize: 28, fontWeight: 700, margin: 0 }}>{tournamentName}</h1>

        <Link
          href="/"
          style={{
            marginLeft: "auto",
            padding: "8px 12px",
            border: "1px solid #ddd",
            borderRadius: 10,
            textDecoration: "none",
            background: "lightgray",
          }}
        >
          ← Back to tournament list
        </Link>
      </div>

      <p style={{ marginTop: 6, opacity: 0.8 }}>
        ID: <code>{tournamentId || "…"}</code>
      </p>

      <div style={{ marginTop: 18, display: "flex", gap: 10 }}>
        <button
          onClick={onGenerate}
          disabled={isGenerating || !tournamentId}
          style={{
            padding: "10px 14px",
            border: "1px solid #ddd",
            borderRadius: 10,
            background: isGenerating ? "#78f3e0ff" : "#c0ddf0ff",
            cursor: isGenerating ? "not-allowed" : "pointer",
          }}
        >
          {isGenerating ? "Generating..." : "Generate Schedule"}
        </button>

        <button
          onClick={() => tournamentId && router.push(`/t/${tournamentId}/schedule`)}
          disabled={!tournamentId}
          style={{
            padding: "10px 14px",
            border: "1px solid #ddd",
            borderRadius: 10,
            background: "#68b1e2ff",
          }}
        >
          View Latest Schedule
        </button>
      </div>

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
    </main>
  );
}
