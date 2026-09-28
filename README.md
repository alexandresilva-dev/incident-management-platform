# Incident Management Platform

Full-stack platform to manage the complete incident lifecycle, applying ITIL incident-management principles to the workflow design: incidents are classified, prioritised, investigated through a controlled state machine and fully audited.

## Features

- [x] Incident ingestion and classification (category, severity)
- [x] Severity-based prioritisation, adjusted by the criticality of the affected assets
- [x] Asset registry
- [x] Vulnerability tracking (CVE, CVSS, remediation status)
- [x] State-driven incident workflow (`open → investigating → mitigated → resolved → closed`)
- [x] Audit trail of every status change
- [x] REST API with generated OpenAPI documentation
- [x] Relational data model with versioned migrations (PostgreSQL + Alembic)
- [x] React front end (dashboard, incident list, detail and creation)

## Tech stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2, Pydantic v2, Alembic
- **Database:** PostgreSQL 16
- **Front end:** React 19, TypeScript (strict), Vite
- **Tooling:** Docker Compose, pytest, Vitest, Git

## How it works

### Workflow

```
open ──▶ investigating ──▶ mitigated ──▶ resolved ──▶ closed
              ▲                │             │
              └────────────────┴─────────────┘   (mitigation failed / reopened)
```

Skipping states is impossible (`open → closed` is rejected with `409`) and `closed` is final: a closed incident is read-only. Every transition is recorded in the audit trail with the previous status, the new status, a comment and a timestamp.

### Prioritisation

The priority (`P1`–`P4`) is derived, never set by hand:

| Severity | Base priority |
|----------|---------------|
| critical | P1 |
| high     | P2 |
| medium   | P3 |
| low      | P4 |

If any affected asset is `critical`, the priority escalates one level (capped at P1). It is recalculated when the severity or the linked assets change, and when a linked asset's criticality changes; closed incidents keep their priority.

### Design decisions

- **Layered backend.** `api/` (HTTP) → `services/` (business rules) → `models/` (persistence). The state machine and the prioritisation are pure functions with exhaustive unit tests, independent of HTTP and the database.
- **The database enforces the important rules too.** CVSS is constrained to 0–10 with a `CHECK`, and `ON DELETE RESTRICT` makes it impossible to delete an incident that has an audit trail. Incidents are deliberately not deletable through the API.
- **Concurrency-safe transitions.** The incident row is locked (`SELECT … FOR UPDATE`) during a transition, so two simultaneous requests cannot both validate against the same old state.
- **Tests run on real PostgreSQL** (a separate `<db>_test` database, each test rolled back) rather than SQLite, so database behaviour is actually exercised.
- **The UI does not duplicate rules.** Transition buttons are rendered from the `allowed_transitions` field the API returns.
- **Secrets stay out of Git.** Configuration comes from environment variables; only `.env.example` is committed, CORS origins are an explicit allow-list and the containers run as unprivileged users.

## Getting started

Requirements: [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Compose v2). Nothing else needs to be installed locally.

```bash
git clone https://github.com/alexandresilva-dev/incident-management-platform.git
cd incident-management-platform

# 1. Create your local configuration and set a real database password
cp .env.example .env

# 2. Build and start PostgreSQL, the API and the front end
docker compose up --build

# 3. (optional) Load demo data: assets, vulnerabilities and incidents at several stages
docker compose exec api python -m scripts.seed
```

| Service | URL |
|---------|-----|
| Front end | <http://localhost:5173> |
| API docs (Swagger UI) | <http://localhost:8000/docs> |
| Health check | <http://localhost:8000/health> |
| PostgreSQL | `127.0.0.1:5433` (not 5432, to avoid clashing with a local install) |

Migrations are applied automatically when the API container starts. Stop everything with `docker compose down` (add `-v` to also delete the database volume).

> `.env` holds secrets and is git-ignored. Only `.env.example` (placeholders) is committed. After changing front-end dependencies run `docker compose up --build --renew-anon-volumes`.

## Running the tests

```bash
docker compose exec api pytest            # backend (uses a separate test database)
docker compose exec frontend npm test     # front end
docker compose exec frontend npm run lint
```

## API overview

| Resource | Endpoints |
|----------|-----------|
| Incidents | `GET/POST /incidents` · `GET/PATCH /incidents/{id}` · `POST /incidents/{id}/transitions` · `GET /incidents/{id}/history` |
| Assets | `GET/POST /assets` · `GET/PATCH/DELETE /assets/{id}` |
| Vulnerabilities | `GET/POST /vulnerabilities` · `GET/PATCH/DELETE /vulnerabilities/{id}` |
| Dashboard | `GET /dashboard/summary` |
| Health | `GET /health` |

Lists support filtering and `skip`/`limit` pagination; incidents can also be sorted by priority. The full, interactive reference is at `/docs`.

## Project structure

```
backend/
  app/
    api/        HTTP layer: routers, request/response handling, error mapping
    schemas/    Pydantic models: what the API accepts and returns
    models/     SQLAlchemy models: what is stored in the database
    services/   Business logic (workflow, prioritisation, CVSS bands, dashboard)
    db/         Engine, session and declarative base
    config.py   Settings loaded from environment variables
  alembic/      Database migrations
  scripts/      Demo data seed
  tests/
frontend/
  src/
    api/        Typed API client
    pages/      Dashboard, incident list / detail / creation
    components/ Layout, badges, charts
docker-compose.yml
```

## Author

Alexandre Silva — [GitHub](https://github.com/alexandresilva-dev) · [LinkedIn](https://www.linkedin.com/in/alexandresilva-dev) · [Portfolio](https://alexandresilva-dev.github.io/)
