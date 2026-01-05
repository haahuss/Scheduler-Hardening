-- =========================
-- Audit log
-- =========================

create table if not exists audit_log (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),

  org_id uuid not null references orgs(id) on delete cascade,
  user_id uuid not null,

  action text not null,
  entity_type text not null,
  entity_id uuid null,

  meta jsonb not null default '{}'::jsonb
);

create index if not exists audit_log_org_created_idx on audit_log (org_id, created_at desc);

alter table audit_log enable row level security;

drop policy if exists audit_log_isolation on audit_log;

create policy audit_log_isolation
on audit_log
for all
using (
  exists (
    select 1
    from org_members m
    where m.org_id = audit_log.org_id
      and m.user_id = (current_setting('app.user_id', true))::uuid
  )
)
with check (
  exists (
    select 1
    from org_members m
    where m.org_id = audit_log.org_id
      and m.user_id = (current_setting('app.user_id', true))::uuid
  )
);
