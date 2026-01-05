# Scheduler-Hardening (DevSecOps Project)

A small tournament scheduler app built to demonstrate **secure-by-default engineering**: CI quality gates, row-level data isolation, adversarial testing, and production hardening.

## What this project does
Create a tournament (teams, venues, time windows) and generate a schedule. The scheduler attempts to produce a valid schedule; if constraints make it infeasible, it returns a “best effort” draft plus integrity/fairness metrics.

---

## Project Demo

[Demo Video for the Scheduler Application](https://drive.google.com/file/d/1w3PAoJGjhQ1vQjQeJtUbdM8C06viz1en/view?usp=sharing)

<img width="1536" height="1024" alt="image" src="https://github.com/user-attachments/assets/4eaf056b-eb72-4f28-83f5-c85d3a3fa296" />

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

## Manual tests with scripts/*

Basic API health check and List Tournaments
```
$ ./api_health_basic.sh

{
  "status": "ok"
}
[
  {
    "id": "79bd35f1-e605-46d2-a924-52a5d0944e57",
    "name": "A tourney",
    "created_at": "2026-01-05T11:13:27.686454Z"
  },
  {
    "id": "8042354a-3913-4cb1-8b54-5bab74817949",
    "name": "A tourney",
    "created_at": "2026-01-05T11:13:20.322085Z"
  }
]
```

Rate Limit Test (rate limit after 60 requests)
```
$ ./rate_limit_test.py

✅ rate limit triggered at request 61
Body: {"detail":"Rate limit exceeded. Try again later."}
```

Creating Tournament with too many teams. (24 Max allowed)
```
$ ./payload_size_hardening.py

status: 400
body: {"detail":"Max 24 teams allowed."}
```

RLS Isolation: User A can read A tournaments but User B cannot.
```
$ ./rls_isolation.sh

[
  {
    "id": "8042354a-3913-4cb1-8b54-5bab74817949",
    "name": "A tourney",
    "created_at": "2026-01-05T11:13:20.322085Z"
  }
]
```


---

## Project structure (high level)
| Directory |  Description |
|--------|-----------|
| apps/web/ | Next.js UI |
| apps/api/ | FastAPI backend |
| infra/ | docker compose + schema/SQL (orgs, RLS, app role, audit log) |
| .github/workflows/ | CI pipelines |

