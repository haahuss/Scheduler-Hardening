# Scheduler-Hardening (DevSecOps Project)

A small tournament scheduler app built to demonstrate **secure-by-default engineering**: CI quality gates, row-level data isolation, adversarial testing, and production hardening.

## What this project does
Create a tournament (teams, venues, time windows) and generate a schedule. The scheduler attempts to produce a valid schedule; if constraints make it infeasible, it returns a “best effort” draft plus integrity/fairness metrics.

---

## Project Demo


---

## 🛡️ Security Features 

1. **CI gates** : tests + lint + SAST + secrets + deps + container scan (block merges on HIGH/CRITICAL). 
2. **Postgres RLS** : multi-tenant isolation (org/user boundary enforced by DB).
3. **Adversarial harness** : property-based fuzz + regression snapshots.
4. **Production hardening** : input caps, request size limits, rate limiting, audit logging.

## 🛠️ Tech Stack

| Tech        | Description                               |
| ----------- | ----------------------------------------- |
| **Web**     | Next.js (TypeScript)                      |
| **API**     | FastAPI (Python)                          |
| **DB**      | Postgres                                  |
| **Infra**   | Docker Compose + Makefile                 |
| **CI**      | GitHub Actions                            |
| **Testing** | Pytest + Hypothesis (fuzz/property tests) |


---

## Quickstart


### Run the app from the repo root
```bash
make up
```

**Open:**  
Web: http://localhost:3000  
API: http://localhost:8000/health  

### Stop everything
```bash
make down
```

### Reset all data
```bash
make clean
```
This removes volumes, so Postgres data is deleted.

### To inspect audit events:
```bash
docker compose -f infra/docker-compose.yml exec -T postgres \
  psql -U scheduler -d scheduler \
  -c "select created_at, action, entity_type, entity_id, user_id from audit_log order by created_at desc limit 20;"

```

---

## Project structure (high level)
| Directory |  Description |
|--------|-----------|
| apps/web/ | Next.js UI |
| apps/api/ | FastAPI backend |
| infra/ | docker compose + schema/SQL (orgs, RLS, app role, audit log) |
| .github/workflows/ | CI pipelines |

