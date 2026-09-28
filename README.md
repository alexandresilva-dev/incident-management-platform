# Incident Management Platform

[![CI](https://github.com/alexandresilva-dev/incident-management-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/alexandresilva-dev/incident-management-platform/actions/workflows/ci.yml)

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
- [x] JWT authentication; the audit trail records who made each change
- [x] CI on every push (lint, migrations, tests, builds)

## Tech stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2, Pydantic v2, Alembic, PyJWT, bcrypt
- **Database:** PostgreSQL 16
- **Front end:** React 19, TypeScript (strict), Vite
- **Tooling:** Docker Compose, pytest, Vitest, ruff, oxlint, GitHub Actions, Git

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
- **Secrets stay out of Git.** Configuration comes from environment variables; only `.env.example` is committed. The app refuses to start without a strong `SECRET_KEY`.
- **Authentication is enforced by default and tested as such.** A test walks the OpenAPI schema and fails if any non-public route answers without a token, so a forgotten dependency on a new endpoint is caught.

## Getting started

Requirements: [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Compose v2). Nothing else needs to be installed locally.

```bash
git clone https://github.com/alexandresilva-dev/incident-management-platform.git
cd incident-management-platform

# 1. Create your local configuration
cp .env.example .env
#    then edit .env and set:
#      POSTGRES_PASSWORD  a real password for the database
#      SECRET_KEY         a random value:  openssl rand -hex 32
#    (the API refuses to start with the placeholder SECRET_KEY)

# 2. Build and start PostgreSQL, the API and the front end
docker compose up --build

# 3. Load demo data (assets, vulnerabilities, incidents at several stages)
#    and a demo user taken from SEED_USER_EMAIL / SEED_USER_PASSWORD in .env
docker compose exec api python -m scripts.seed
```

Open <http://localhost:5173> and sign in with the demo user. Those credentials come from `.env.example` and are for **local demos only**.

There is no public sign-up. Create real users from the command line (the password is prompted, so it never appears in your shell history):

```bash
docker compose exec api python -m scripts.create_user ana@company.com "Ana Silva"
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
docker compose exec api ruff check .      # backend lint (and: ruff format --check .)
docker compose exec frontend npm test     # front end
docker compose exec frontend npm run lint
```

The same checks run in GitHub Actions on every push (see `.github/workflows/ci.yml`), plus `alembic upgrade head` on an empty database and `alembic check`, which fails if the models and the migrations drift apart.

## API overview

| Resource | Endpoints |
|----------|-----------|
| Incidents | `GET/POST /incidents` · `GET/PATCH /incidents/{id}` · `POST /incidents/{id}/transitions` · `GET /incidents/{id}/history` |
| Assets | `GET/POST /assets` · `GET/PATCH/DELETE /assets/{id}` |
| Vulnerabilities | `GET/POST /vulnerabilities` · `GET/PATCH/DELETE /vulnerabilities/{id}` |
| Dashboard | `GET /dashboard/summary` |
| Auth | `POST /auth/login` · `GET /auth/me` |
| Health | `GET /health` (public) |

All endpoints except `/health` and `/auth/login` require `Authorization: Bearer <token>`. Lists support filtering and `skip`/`limit` pagination; incidents can also be sorted by priority. The full, interactive reference is at `/docs`.

## Security

Implemented:

- Passwords are hashed with **bcrypt** (salted); passwords over bcrypt's 72-byte limit are rejected rather than silently truncated, and a minimum length of 12 is enforced.
- Login answers identically for a wrong password and an unknown email, and does the same amount of hashing work in both cases, so neither the message nor the timing reveals which emails exist.
- **JWT** access tokens with an expiry; the accepted algorithm is pinned and `exp`/`sub` are required (tests cover expired, tampered, wrongly signed and `alg: none` tokens). A deactivated or deleted user loses access even with an unexpired token.
- No public registration; users are created by an administrator script.
- CORS is an explicit allow-list (never `*`), containers run as unprivileged users, and GitHub Actions use minimal permissions with actions pinned by commit SHA.

Known limitations (deliberately out of scope, and what I would do next):

- No rate limiting or lockout on `/auth/login` (add e.g. per-IP/per-account throttling).
- No refresh tokens or server-side token revocation; tokens are valid until they expire.
- The token is kept in `localStorage`, which is exposed to XSS; `HttpOnly` cookies would be more robust but need a CSRF strategy.
- A single user role: every authenticated user can do everything (add role-based access control).
- The Docker setup is for development (hot reload, published ports); a production deployment would need TLS termination and a production front-end image.

## Project structure

```
backend/
  app/
    api/        HTTP layer: routers, request/response handling, error mapping
    schemas/    Pydantic models: what the API accepts and returns
    models/     SQLAlchemy models: what is stored in the database
    services/   Business logic (workflow, prioritisation, CVSS bands, dashboard)
    db/         Engine, session and declarative base
    security.py Password hashing and JWT helpers
    config.py   Settings loaded from environment variables
  alembic/      Database migrations
  scripts/      Demo data seed and user creation
  tests/
frontend/
  src/
    api/        Typed API client
    pages/      Dashboard, incident list / detail / creation
    auth/       Session handling (token storage, context)
    components/ Layout, route guard, badges, charts
.github/workflows/  CI pipeline
docker-compose.yml
```

## Author

Alexandre Silva — [GitHub](https://github.com/alexandresilva-dev) · [LinkedIn](https://www.linkedin.com/in/alexandresilva-dev) · [Portfolio](https://alexandresilva-dev.github.io/)
