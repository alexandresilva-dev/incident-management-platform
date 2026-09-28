from collections.abc import Sequence
from datetime import UTC, datetime
from typing import TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import Asset, Incident, IncidentStatusHistory, Vulnerability
from app.models.enums import IncidentStatus
from app.schemas.incident import IncidentCreate, IncidentUpdate
from app.services.errors import IncidentClosedError, UnknownReferenceError
from app.services.workflow import validate_transition

ModelT = TypeVar("ModelT", bound=Base)


def _load_all(db: Session, model: type[ModelT], ids: Sequence[int], kind: str) -> list[ModelT]:
    """Carrega os objetos com estes ids; se algum não existir, é erro do cliente."""
    unique_ids = list(dict.fromkeys(ids))
    if not unique_ids:
        return []
    found = {obj.id: obj for obj in db.scalars(select(model).where(model.id.in_(unique_ids)))}
    missing = [i for i in unique_ids if i not in found]
    if missing:
        raise UnknownReferenceError(kind, missing)
    return [found[i] for i in unique_ids]


def create_incident(db: Session, payload: IncidentCreate, actor: str | None = None) -> Incident:
    incident = Incident(
        title=payload.title,
        description=payload.description,
        category=payload.category,
        severity=payload.severity,
        status=IncidentStatus.open,
        assets=_load_all(db, Asset, payload.asset_ids, "asset"),
        vulnerabilities=_load_all(db, Vulnerability, payload.vulnerability_ids, "vulnerability"),
    )
    # Todo o incidente nasce com um registo de audit trail (sem estado anterior).
    incident.history.append(
        IncidentStatusHistory(
            from_status=None,
            to_status=IncidentStatus.open,
            changed_by=actor,
            comment="Incident created",
        )
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)
    return incident


def update_incident(db: Session, incident: Incident, payload: IncidentUpdate) -> Incident:
    if incident.status == IncidentStatus.closed:
        raise IncidentClosedError(incident.id)

    changes = payload.model_dump(exclude_unset=True)

    # Resolver as referências antes de alterar seja o que for: se falhar, nada muda.
    if "asset_ids" in changes:
        incident.assets = _load_all(db, Asset, changes.pop("asset_ids"), "asset")
    if "vulnerability_ids" in changes:
        incident.vulnerabilities = _load_all(
            db, Vulnerability, changes.pop("vulnerability_ids"), "vulnerability"
        )
    for field, value in changes.items():
        setattr(incident, field, value)

    db.commit()
    db.refresh(incident)
    return incident


def transition_incident(
    db: Session,
    incident: Incident,
    target: IncidentStatus,
    comment: str | None = None,
    actor: str | None = None,
) -> Incident:
    """Move o incidente para `target` se o workflow o permitir, e regista o audit trail.

    O chamador deve ter carregado o incidente com FOR UPDATE, para que dois
    pedidos simultâneos não validem contra o mesmo estado antigo.
    """
    previous = incident.status
    validate_transition(previous, target)  # levanta InvalidTransitionError

    now = datetime.now(UTC)
    incident.status = target
    if target == IncidentStatus.resolved:
        incident.resolved_at = now
    elif target == IncidentStatus.closed:
        incident.closed_at = now
    elif previous == IncidentStatus.resolved:
        incident.resolved_at = None  # reabertura: deixou de estar resolvido

    incident.history.append(
        IncidentStatusHistory(
            from_status=previous, to_status=target, changed_by=actor, comment=comment
        )
    )
    db.commit()
    db.refresh(incident)
    return incident
