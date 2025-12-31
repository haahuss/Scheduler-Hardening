-- =========================
-- Scheduler-Hardening schema (Phase 0)
-- =========================

-- Needed for gen_random_uuid()
create extension if not exists pgcrypto;

-- -------------------------
-- tournaments
-- -------------------------
create table if not exists tournaments (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  created_at timestamptz not null default now()
);

-- -------------------------
-- teams
-- -------------------------
create table if not exists teams (
  id uuid primary key default gen_random_uuid(),
  tournament_id uuid not null references tournaments(id) on delete cascade,
  name text not null,
  created_at timestamptz not null default now(),
  unique (tournament_id, name)
);

create index if not exists idx_teams_tournament_id on teams(tournament_id);

-- -------------------------
-- venues
-- -------------------------
create table if not exists venues (
  id uuid primary key default gen_random_uuid(),
  tournament_id uuid not null references tournaments(id) on delete cascade,
  name text not null,
  created_at timestamptz not null default now(),
  unique (tournament_id, name)
);

create index if not exists idx_venues_tournament_id on venues(tournament_id);

-- -------------------------
-- time_windows
-- A tournament’s available slots (optionally pinned to a venue)
-- -------------------------
create table if not exists time_windows (
  id uuid primary key default gen_random_uuid(),
  tournament_id uuid not null references tournaments(id) on delete cascade,
  start_ts timestamptz not null,
  end_ts timestamptz not null,
  venue_id uuid null references venues(id) on delete set null,
  created_at timestamptz not null default now(),
  check (end_ts > start_ts)
);

create index if not exists idx_time_windows_tournament_id on time_windows(tournament_id);
create index if not exists idx_time_windows_start_ts on time_windows(start_ts);

-- -------------------------
-- schedule_runs
-- Immutable “runs” (each generate = new row)
-- -------------------------
create table if not exists schedule_runs (
  id uuid primary key default gen_random_uuid(),
  tournament_id uuid not null references tournaments(id) on delete cascade,
  created_at timestamptz not null default now(),

  -- QUEUED | RUNNING | COMPLETE | FAILED
  status text not null,

  -- Hash of the scheduling input so we can compare runs later
  input_hash text not null,

  -- The produced schedule (JSON)
  schedule_json jsonb null,

  -- Metrics and quality indicators (JSON)
  metrics_json jsonb null,

  -- Error details if failed (JSON)
  error_json jsonb null
);

create index if not exists idx_schedule_runs_tournament_id on schedule_runs(tournament_id);
create index if not exists idx_schedule_runs_created_at on schedule_runs(created_at);
