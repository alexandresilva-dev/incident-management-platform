from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import assets, auth, dashboard, health, incidents, users, vulnerabilities
from app.api.deps import get_current_user, require_admin
from app.api.errors import register_exception_handlers
from app.config import settings

DESCRIPTION = """
REST API of an incident management platform inspired by **ITIL** incident management.

## Authentication
All endpoints except `/health` and `/auth/login` need a bearer token.
Log in with `POST /auth/login` (form fields `username` = email and `password`),
then send `Authorization: Bearer <token>`. In this page, use the **Authorize** button.
Tokens expire after `ACCESS_TOKEN_EXPIRE_MINUTES` (60 by default).

## Incident workflow
`open → investigating → mitigated → resolved → closed`

Two steps go back: a failed mitigation returns to `investigating`, and a resolved
incident can be reopened to `investigating`. States cannot be skipped and `closed` is final.
The status is changed only through `POST /incidents/{id}/transitions`; every change is
recorded in the audit trail (`GET /incidents/{id}/history`).

## Priority
Derived from the severity (critical=P1 … low=P4) and escalated one level when an
affected asset is `critical`. It is never set directly.

## Roles
`analyst` works on incidents, assets and vulnerabilities. `admin` can also delete assets
and vulnerabilities and manage users (`/users`). Failing this returns 403.

## Errors
| Status | Meaning |
|--------|---------|
| 401 | Missing, invalid or expired token |
| 403 | Authenticated, but the role is not allowed to do this |
| 404 | Resource not found |
| 409 | Conflicts with the current state (invalid transition, closed incident, duplicate user) |
| 422 | Invalid input, or a reference to an id that does not exist |
| 429 | Too many failed login attempts; see the `Retry-After` header |
"""

TAGS_METADATA = [
    {"name": "auth", "description": "Obtain a token and inspect the current user."},
    {
        "name": "incidents",
        "description": "Incident lifecycle: create, classify, prioritise, transition and audit.",
    },
    {"name": "assets", "description": "Registry of the assets that incidents can affect."},
    {
        "name": "vulnerabilities",
        "description": "Known vulnerabilities (CVE / CVSS) and their remediation status.",
    },
    {"name": "dashboard", "description": "Aggregated counts for the dashboard."},
    {"name": "users", "description": "User management. Administrators only."},
    {"name": "health", "description": "Liveness and database connectivity. Public."},
]

app = FastAPI(
    title="Incident Management Platform",
    version="0.1.0",
    description=DESCRIPTION,
    openapi_tags=TAGS_METADATA,
)

# Só as origens configuradas (nunca "*"), para que outros sites não possam
# chamar a API a partir do browser de um utilizador.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

register_exception_handlers(app)

# Públicos: /health (monitorização) e /auth (onde se obtém o token).
app.include_router(health.router)
app.include_router(auth.router)

# Todo o resto exige um token válido.
protected = [Depends(get_current_user)]
unauthorized = {401: {"description": "Missing, invalid or expired token"}}
app.include_router(assets.router, dependencies=protected, responses=unauthorized)
app.include_router(vulnerabilities.router, dependencies=protected, responses=unauthorized)
app.include_router(incidents.router, dependencies=protected, responses=unauthorized)
app.include_router(dashboard.router, dependencies=protected, responses=unauthorized)
app.include_router(
    users.router,
    dependencies=[Depends(require_admin)],
    responses={**unauthorized, 403: {"description": "Administrator role required"}},
)
