from fastapi import APIRouter, Query, status
from sqlalchemy import select

from app.api.deps import DbSession, get_or_404
from app.models import Incident, IncidentStatusHistory, incident_assets
from app.models.enums import IncidentCategory, IncidentStatus, Priority, Severity
from app.schemas.incident import (
    IncidentCreate,
    IncidentRead,
    IncidentSummary,
    IncidentUpdate,
    TransitionRequest,
)
from app.schemas.status_history import StatusHistoryRead
from app.services import incidents as incident_service

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.post("", response_model=IncidentRead, status_code=status.HTTP_201_CREATED)
def create_incident(payload: IncidentCreate, db: DbSession) -> Incident:
    return incident_service.create_incident(db, payload)


@router.get("", response_model=list[IncidentSummary])
def list_incidents(
    db: DbSession,
    status_: IncidentStatus | None = Query(default=None, alias="status"),
    severity: Severity | None = None,
    priority: Priority | None = None,
    category: IncidentCategory | None = None,
    asset_id: int | None = Query(default=None, description="Only incidents affecting this asset"),
    q: str | None = Query(default=None, description="Case-insensitive search in the title"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[Incident]:
    stmt = select(Incident).order_by(Incident.id.desc())
    if status_ is not None:
        stmt = stmt.where(Incident.status == status_)
    if severity is not None:
        stmt = stmt.where(Incident.severity == severity)
    if priority is not None:
        stmt = stmt.where(Incident.priority == priority)
    if category is not None:
        stmt = stmt.where(Incident.category == category)
    if asset_id is not None:
        stmt = stmt.where(
            Incident.id.in_(
                select(incident_assets.c.incident_id).where(incident_assets.c.asset_id == asset_id)
            )
        )
    if q:
        stmt = stmt.where(Incident.title.icontains(q, autoescape=True))
    return list(db.scalars(stmt.offset(skip).limit(limit)))


@router.get("/{incident_id}", response_model=IncidentRead)
def get_incident(incident_id: int, db: DbSession) -> Incident:
    return get_or_404(db, Incident, incident_id)


@router.patch("/{incident_id}", response_model=IncidentRead)
def update_incident(incident_id: int, payload: IncidentUpdate, db: DbSession) -> Incident:
    incident = get_or_404(db, Incident, incident_id)
    return incident_service.update_incident(db, incident, payload)


@router.post("/{incident_id}/transitions", response_model=IncidentRead)
def transition_incident(incident_id: int, payload: TransitionRequest, db: DbSession) -> Incident:
    """Muda o estado do incidente. Só são aceites as transições do workflow."""
    incident = get_or_404(db, Incident, incident_id, for_update=True)
    return incident_service.transition_incident(
        db, incident, payload.to_status, comment=payload.comment
    )


@router.get("/{incident_id}/history", response_model=list[StatusHistoryRead])
def get_incident_history(incident_id: int, db: DbSession) -> list[IncidentStatusHistory]:
    """Audit trail: todas as mudanças de estado, da mais antiga para a mais recente."""
    get_or_404(db, Incident, incident_id)
    stmt = (
        select(IncidentStatusHistory)
        .where(IncidentStatusHistory.incident_id == incident_id)
        .order_by(IncidentStatusHistory.id)
    )
    return list(db.scalars(stmt))
