"""Importar todos os modelos aqui garante que ficam registados em Base.metadata
(o Alembic precisa disso para os ver)."""

from app.models.asset import Asset
from app.models.incident import Incident, incident_assets, incident_vulnerabilities
from app.models.status_history import IncidentStatusHistory
from app.models.vulnerability import Vulnerability

__all__ = [
    "Asset",
    "Incident",
    "IncidentStatusHistory",
    "Vulnerability",
    "incident_assets",
    "incident_vulnerabilities",
]
