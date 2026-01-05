// apps/web/lib/api.ts


export type TournamentListItem = {
  id: string;
  name: string;
  status?: string;
  created_at?: string; // ✅ add this
};

export type IntegrityViolation = {
  type: string;
  severity?: string;
  message?: string;
  explain?: string;

  team_id?: string;
  team_name?: string;
  venue_id?: string;
  venue_name?: string;

  rest_minutes?: number;
  min_rest_minutes?: number;

  games?: Game[];
  [key: string]: unknown;
};

export type TopOffender = {
  team_name: string;
  count: number;
};

export type Game = {
  game_no?: number;
  start_ts: string;
  end_ts: string;

  home_team_id?: string;
  home_team_name?: string;
  away_team_id?: string;
  away_team_name?: string;

  venue_id?: string;
  venue_name?: string;

  vs?: string;
  matchup?: string;

  [key: string]: unknown;
};


export type TournamentOut = {
  id: string;
  name: string;
};

export type MetricsJson = {
  integrity?: {
    status?: string;
    violations_total?: number;
    violations?: IntegrityViolation[];
  };
  fairness?: {
    score?: number;
    back_to_back_total?: number;
    top_offenders?: TopOffender[];
  };
};


export type ScheduleRun = {
  id?: string;
  status?: string;
  created_at?: string;
  schedule_json?: { games?: Game[] };
  metrics_json?: MetricsJson;
  error_json?: { guidance?: string[] };
};


type ApiErrorBody = {
  detail?: unknown;
  message?: unknown;
};

export type Tournament = {
  id: string;
  name: string;
  status?: string;
};

export function getTournament(tournamentId: string): Promise<Tournament> {
  // Most likely REST shape:
  return requestJson<Tournament>(`/api/tournaments/${tournamentId}`);
}


export function getErrorMessage(err: unknown): string {
  if (err instanceof Error) return err.message;
  if (typeof err === "string") return err;
  return "Unexpected error";
}

function getDevUserId(): string {
  // During SSR/build, window/localStorage isn't available
  if (typeof window === "undefined") return "00000000-0000-0000-0000-000000000000";

  const key = "dev_user_id";
  let id = window.localStorage.getItem(key);
  if (!id) {
    id = crypto.randomUUID();
    window.localStorage.setItem(key, id);
  }
  return id;
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);

  // ✅ local identity header (dev/demo)
  headers.set("X-User-Id", getDevUserId());

  const res = await fetch(path, { ...init, headers });

  if (!res.ok) {
    let body: ApiErrorBody | undefined;
    try {
      body = (await res.json()) as ApiErrorBody;
    } catch {}

    const msg =
      (typeof body?.detail === "string" ? body.detail : undefined) ||
      (typeof body?.message === "string" ? body.message : undefined) ||
      `Request failed: ${res.status} ${res.statusText}`;

    throw new Error(msg);
  }

  return (await res.json()) as T;
}


// ✅ API helpers your pages should import and use

export function listTournaments(): Promise<TournamentListItem[]> {
  return requestJson<TournamentListItem[]>("/api/tournaments");
}

export function createTournament(payload: Record<string, unknown>): Promise<TournamentOut> {
  return requestJson<TournamentOut>("/api/tournaments", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function generateSchedule(tournamentId: string): Promise<{ ok: boolean }> {
  return requestJson<{ ok: boolean }>(`/api/tournaments/${tournamentId}/generate`, {
    method: "POST",
  });
}

export function getLatestRun(tournamentId: string): Promise<ScheduleRun> {
  return requestJson<ScheduleRun>(`/api/tournaments/${tournamentId}/latest-run`);
}
