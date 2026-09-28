from sqlalchemy.orm import Session

from app.models import Asset
from app.models.enums import IncidentStatus
from app.schemas.asset import AssetUpdate
from app.services.incidents import reprioritise_open_incidents


def update_asset(db: Session, asset: Asset, payload: AssetUpdate) -> Asset:
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(asset, field, value)

    # A criticidade do ativo entra no cálculo da prioridade dos incidentes.
    if "criticality" in changes:
        reprioritise_open_incidents(asset.incidents)

    db.commit()
    db.refresh(asset)
    return asset


def delete_asset(db: Session, asset: Asset) -> None:
    # Os incidentes abertos deixam de ter este ativo, por isso a prioridade
    # tem de ser recalculada sem ele. Os fechados só perdem a ligação (na BD).
    open_incidents = [i for i in asset.incidents if i.status != IncidentStatus.closed]
    for incident in open_incidents:
        incident.assets.remove(asset)
    reprioritise_open_incidents(open_incidents)

    db.delete(asset)
    db.commit()
