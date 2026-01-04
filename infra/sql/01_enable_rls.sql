ALTER TABLE tournaments   ENABLE ROW LEVEL SECURITY;
ALTER TABLE teams         ENABLE ROW LEVEL SECURITY;
ALTER TABLE venues        ENABLE ROW LEVEL SECURITY;
ALTER TABLE schedule_runs ENABLE ROW LEVEL SECURITY;

ALTER TABLE tournaments   FORCE ROW LEVEL SECURITY;
ALTER TABLE teams         FORCE ROW LEVEL SECURITY;
ALTER TABLE venues        FORCE ROW LEVEL SECURITY;
ALTER TABLE schedule_runs FORCE ROW LEVEL SECURITY;


DROP POLICY IF EXISTS tournaments_isolation ON tournaments;
CREATE POLICY tournaments_isolation ON tournaments
FOR ALL
USING (
  EXISTS (
    SELECT 1 FROM org_members m
    WHERE m.org_id = tournaments.org_id
      AND m.user_id = NULLIF(current_setting('app.user_id', true), '')::uuid
  )
)
WITH CHECK (
  EXISTS (
    SELECT 1 FROM org_members m
    WHERE m.org_id = tournaments.org_id
      AND m.user_id = NULLIF(current_setting('app.user_id', true), '')::uuid
  )
);

DROP POLICY IF EXISTS teams_isolation ON teams;
CREATE POLICY teams_isolation ON teams
FOR ALL
USING (
  EXISTS (
    SELECT 1 FROM org_members m
    WHERE m.org_id = teams.org_id
      AND m.user_id = NULLIF(current_setting('app.user_id', true), '')::uuid
  )
)
WITH CHECK (
  EXISTS (
    SELECT 1 FROM org_members m
    WHERE m.org_id = teams.org_id
      AND m.user_id = NULLIF(current_setting('app.user_id', true), '')::uuid
  )
);

DROP POLICY IF EXISTS venues_isolation ON venues;
CREATE POLICY venues_isolation ON venues
FOR ALL
USING (
  EXISTS (
    SELECT 1 FROM org_members m
    WHERE m.org_id = venues.org_id
      AND m.user_id = NULLIF(current_setting('app.user_id', true), '')::uuid
  )
)
WITH CHECK (
  EXISTS (
    SELECT 1 FROM org_members m
    WHERE m.org_id = venues.org_id
      AND m.user_id = NULLIF(current_setting('app.user_id', true), '')::uuid
  )
);

DROP POLICY IF EXISTS schedule_runs_isolation ON schedule_runs;
CREATE POLICY schedule_runs_isolation ON schedule_runs
FOR ALL
USING (
  EXISTS (
    SELECT 1 FROM org_members m
    WHERE m.org_id = schedule_runs.org_id
      AND m.user_id = NULLIF(current_setting('app.user_id', true), '')::uuid
  )
)
WITH CHECK (
  EXISTS (
    SELECT 1 FROM org_members m
    WHERE m.org_id = schedule_runs.org_id
      AND m.user_id = NULLIF(current_setting('app.user_id', true), '')::uuid
  )
);
