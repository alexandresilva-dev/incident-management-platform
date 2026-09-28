from fastapi import FastAPI

from app.api import health

app = FastAPI(title="Incident Management Platform")

app.include_router(health.router)
