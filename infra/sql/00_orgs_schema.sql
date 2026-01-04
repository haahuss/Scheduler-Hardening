CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS orgs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS org_members (
  org_id uuid NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
  user_id uuid NOT NULL,
  role text NOT NULL DEFAULT 'member',
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (org_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_org_members_user_id ON org_members(user_id);

-- Add org_id to your tenant tables
ALTER TABLE tournaments   ADD COLUMN IF NOT EXISTS org_id uuid;
ALTER TABLE teams         ADD COLUMN IF NOT EXISTS org_id uuid;
ALTER TABLE venues        ADD COLUMN IF NOT EXISTS org_id uuid;
ALTER TABLE schedule_runs ADD COLUMN IF NOT EXISTS org_id uuid;

-- Backfill into a default org
DO $$
DECLARE
  default_org uuid;
BEGIN
  SELECT id INTO default_org FROM orgs ORDER BY created_at LIMIT 1;
  IF default_org IS NULL THEN
    INSERT INTO orgs(name) VALUES ('Default Org') RETURNING id INTO default_org;
  END IF;

  UPDATE tournaments   SET org_id = default_org WHERE org_id IS NULL;
  UPDATE teams         SET org_id = default_org WHERE org_id IS NULL;
  UPDATE venues        SET org_id = default_org WHERE org_id IS NULL;
  UPDATE schedule_runs SET org_id = default_org WHERE org_id IS NULL;
END $$;

ALTER TABLE tournaments   ALTER COLUMN org_id SET NOT NULL;
ALTER TABLE teams         ALTER COLUMN org_id SET NOT NULL;
ALTER TABLE venues        ALTER COLUMN org_id SET NOT NULL;
ALTER TABLE schedule_runs ALTER COLUMN org_id SET NOT NULL;
