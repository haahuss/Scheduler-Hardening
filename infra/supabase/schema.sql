-- =========================
-- Scheduler-Hardening schema (MVP)
-- =========================

-- Needed for gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- -------------------------
-- tournaments
-- -------------------------
CREATE TABLE IF NOT EXISTS tournaments (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- -------------------------
-- teams
-- -------------------------
CREATE TABLE IF NOT EXISTS teams (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tournament_id uuid NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
  name text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tournament_id, name)
);
CREATE INDEX IF NOT EXISTS idx_teams_tournament_id ON teams(tournament_id);

-- -------------------------
-- venues
-- -------------------------
CREATE TABLE IF NOT EXISTS venues (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tournament_id uuid NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
  name text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tournament_id, name)
);
CREATE INDEX IF NOT EXISTS idx_venues_tournament_id ON venues(tournament_id);

-- -------------------------
-- time_windows
-- A tournament’s available slots (optionally pinned to a venue)
-- -------------------------
CREATE TABLE IF NOT EXISTS time_windows (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tournament_id uuid NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
  start_ts timestamptz NOT NULL,
  end_ts timestamptz NOT NULL,
  venue_id uuid NULL REFERENCES venues(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (end_ts > start_ts)
);
CREATE INDEX IF NOT EXISTS idx_time_windows_tournament_id ON time_windows(tournament_id);
CREATE INDEX IF NOT EXISTS idx_time_windows_start_ts ON time_windows(start_ts);

-- -------------------------
-- schedule_runs
-- Immutable “runs” (each generate = new row)
-- -------------------------
CREATE TABLE IF NOT EXISTS schedule_runs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tournament_id uuid NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
  created_at timestamptz NOT NULL DEFAULT now(),

  -- SUCCESS | FAILED
  status text NOT NULL,

  -- Hash of inputs (teams/venues/windows) for regression + reproducibility
  input_hash text NOT NULL,

  -- Generated schedule
  schedule_json jsonb NULL,

  -- Metrics: integrity/fairness/etc.
  metrics_json jsonb NULL,

  -- Failure guidance (capacity/constraints), if any
  error_json jsonb NULL
);

CREATE INDEX IF NOT EXISTS idx_schedule_runs_tournament_id ON schedule_runs(tournament_id);
CREATE INDEX IF NOT EXISTS idx_schedule_runs_created_at ON schedule_runs(created_at);
