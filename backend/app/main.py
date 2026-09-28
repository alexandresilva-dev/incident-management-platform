from fastapi import FastAPI

from app.api import assets, health, incidents, vulnerabilities
from app.api.errors import register_exception_handlers

app = FastAPI(title="Incident Management Platform")

register_exception_handlers(app)

app.include_router(health.router)
app.include_router(assets.router)
app.include_router(vulnerabilities.router)
app.include_router(incidents.router)
