from fastapi import FastAPI

from app.api import assets, health, vulnerabilities

app = FastAPI(title="Incident Management Platform")

app.include_router(health.router)
app.include_router(assets.router)
app.include_router(vulnerabilities.router)
