# Incident Management Platform

> **Status: work in progress** — development starts September 2026. This README describes the planned scope; items will be checked off as they are implemented.

Full-stack platform to manage the complete incident lifecycle, applying ITIL incident-management principles to the workflow design.

## Planned scope

- [ ] Incident ingestion and classification
- [ ] Severity-based prioritisation
- [ ] Asset registry
- [ ] Vulnerability tracking
- [ ] State-driven incident workflows
- [ ] Audit trail
- [ ] REST API integration layer
- [ ] Relational data model (PostgreSQL)
- [ ] React front end

## Tech stack

- **Backend:** Python, FastAPI
- **Database:** PostgreSQL
- **Front end:** React
- **Tooling:** Docker, pytest, Git

## Getting started

Requirements: [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Compose v2). Nothing else needs to be installed locally.

```bash
git clone https://github.com/alexandresilva-dev/incident-management-platform.git
cd incident-management-platform

# 1. Create your local configuration and set a real database password
cp .env.example .env

# 2. Build and start PostgreSQL + the API
docker compose up --build
```

The API is then available at:

- Health check: <http://localhost:8000/health>
- Interactive API docs (Swagger UI): <http://localhost:8000/docs>

PostgreSQL is published on `127.0.0.1:5433` (not 5432, to avoid clashing with a local install), in case you want to inspect it with `psql` or a GUI client.

Stop everything with `docker compose down` (add `-v` to also delete the database volume).

> `.env` holds secrets and is git-ignored. Only `.env.example` (placeholders) is committed.

## Project structure

```
backend/
  app/
    api/        HTTP layer: routers, request/response handling
    schemas/    Pydantic models: what the API accepts and returns
    models/     SQLAlchemy models: what is stored in the database
    services/   Business logic (workflow rules, prioritisation)
    db/         Engine, session and declarative base
    config.py   Settings loaded from environment variables
    main.py     FastAPI application
  tests/
frontend/       React application
docker-compose.yml
```

## Author

Alexandre Silva — [GitHub](https://github.com/alexandresilva-dev) · [LinkedIn](https://www.linkedin.com/in/alexandresilva-dev) · [Portfolio](https://alexandresilva-dev.github.io/)
