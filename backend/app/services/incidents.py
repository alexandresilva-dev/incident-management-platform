from collections.abc import Sequence
from typing import TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import Asset, Incident, IncidentStatusHistory, Vulnerability
from app.models.enums import IncidentStatus
from app.schemas.incident import IncidentCreate, IncidentUpdate
from app.services.errors import UnknownReferenceError

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
