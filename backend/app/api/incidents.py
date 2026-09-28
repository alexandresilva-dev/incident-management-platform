from enum import StrEnum
from typing import Annotated

from fastapi import APIRouter, Query, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession, get_or_404
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


class IncidentSort(StrEnum):
    newest = "newest"
    priority = "priority"  # P1 primeiro; a igualdade desfaz-se pelos mais recentes


@router.post(
    "",
    response_model=IncidentRead,
    status_code=status.HTTP_201_CREATED,
    responses={422: {"description": "Invalid input or unknown asset/vulnerability ids"}},
)
def create_incident(payload: IncidentCreate, db: DbSession, current_user: CurrentUser) -> Incident:
    """Register an incident. It starts as `open`; the priority is calculated automatically
    and the creation is the first entry of the audit trail."""
    return incident_service.create_incident(db, payload, actor=current_user.email)


@router.get("", response_model=list[IncidentSummary])
def list_incidents(
    db: DbSession,
    status_: Annotated[IncidentStatus | None, Query(alias="status")] = None,
    severity: Severity | None = None,
    priority: Priority | None = None,
    category: IncidentCategory | None = None,
    asset_id: Annotated[
        int | None, Query(description="Only incidents affecting this asset")
    ] = None,
    q: Annotated[str | None, Query(description="Case-insensitive search in the title")] = None,
    sort: IncidentSort = IncidentSort.newest,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[Incident]:
    """List incidents (lightweight summaries), newest first by default. Filter by status,
    severity, priority, category, affected asset or title; sort by `priority` to get P1 first."""
    if sort == IncidentSort.priority:
        stmt = select(Incident).order_by(Incident.priority, Incident.id.desc())
    else:
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


@router.get(
    "/{incident_id}",
    response_model=IncidentRead,
    responses={404: {"description": "Incident not found"}},
)
def get_incident(incident_id: int, db: DbSession) -> Incident:
    """Full incident, with its assets, vulnerabilities and the transitions allowed right now."""
    return get_or_404(db, Incident, incident_id)


@router.patch(
    "/{incident_id}",
    response_model=IncidentRead,
    responses={
        404: {"description": "Incident not found"},
        409: {"description": "The incident is closed and can no longer be modified"},
        422: {"description": "Invalid input or unknown asset/vulnerability ids"},
    },
)
def update_incident(incident_id: int, payload: IncidentUpdate, db: DbSession) -> Incident:
    """Partial update. The status cannot be changed here (use transitions) and the
    priority is recalculated when the severity or the linked assets change."""
    incident = get_or_404(db, Incident, incident_id)
    return incident_service.update_incident(db, incident, payload)


@router.post(
    "/{incident_id}/transitions",
    response_model=IncidentRead,
    responses={
        404: {"description": "Incident not found"},
        409: {
            "description": "Transition not allowed by the workflow",
            "content": {
                "application/json": {
                    "example": {
                        "detail": (
                            "Cannot move incident from 'open' to 'closed'. Allowed: investigating"
                        ),
                        "allowed_transitions": ["investigating"],
                    }
                }
            },
        },
    },
)
def transition_incident(
    incident_id: int, payload: TransitionRequest, db: DbSession, current_user: CurrentUser
) -> Incident:
    """Muda o estado do incidente. Só são aceites as transições do workflow."""
    incident = get_or_404(db, Incident, incident_id, for_update=True)
    return incident_service.transition_incident(
        db, incident, payload.to_status, comment=payload.comment, actor=current_user.email
    )


@router.get(
    "/{incident_id}/history",
    response_model=list[StatusHistoryRead],
    responses={404: {"description": "Incident not found"}},
)
def get_incident_history(incident_id: int, db: DbSession) -> list[IncidentStatusHistory]:
    """Audit trail: todas as mudanças de estado, da mais antiga para a mais recente."""
    get_or_404(db, Incident, incident_id)
    stmt = (
        select(IncidentStatusHistory)
        .where(IncidentStatusHistory.incident_id == incident_id)
        .order_by(IncidentStatusHistory.id)
    )
    return list(db.scalars(stmt))
