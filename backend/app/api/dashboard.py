from fastapi import APIRouter

from app.api.deps import DbSession
from app.schemas.dashboard import DashboardSummary
from app.services.dashboard import build_dashboard_summary

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(db: DbSession) -> DashboardSummary:
    """Contagens agregadas de incidentes, ativos e vulnerabilidades para o dashboard."""
    return build_dashboard_summary(db)
