from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import assets, auth, dashboard, health, incidents, vulnerabilities
from app.api.deps import get_current_user
from app.api.errors import register_exception_handlers
from app.config import settings

app = FastAPI(title="Incident Management Platform")

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
app.include_router(assets.router, dependencies=protected)
app.include_router(vulnerabilities.router, dependencies=protected)
app.include_router(incidents.router, dependencies=protected)
app.include_router(dashboard.router, dependencies=protected)
