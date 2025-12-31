"use client";

import { useState } from "react";
import { generateSchedule } from "@/lib/api";
import { useRouter, useParams } from "next/navigation";

export default function TournamentPage() {
  const router = useRouter();
  const params = useParams();

  // In App Router, useParams() returns Record<string, string | string[]>
  const tournamentIdRaw = params?.id;
  const tournamentId =
    typeof tournamentIdRaw === "string" ? tournamentIdRaw : tournamentIdRaw?.[0];

  const [isGenerating, setIsGenerating] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

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
    } catch (e: any) {
      setErrorMsg(e?.message || "Failed to generate schedule.");
    } finally {
      setIsGenerating(false);
    }
  }

  return (
    <main style={{ maxWidth: 900, margin: "40px auto", padding: 16 }}>
      <h1 style={{ fontSize: 28, fontWeight: 700 }}>Tournament</h1>

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
            background: isGenerating ? "#f5f5f5" : "white",
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
            background: "white",
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
