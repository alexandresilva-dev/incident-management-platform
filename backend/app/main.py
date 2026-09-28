from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import assets, health, incidents, vulnerabilities
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

app.include_router(health.router)
app.include_router(assets.router)
app.include_router(vulnerabilities.router)
app.include_router(incidents.router)
