from enum import Enum

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.orm import InstrumentedAttribute, Session

from app.models import Asset, Incident, Vulnerability
from app.models.enums import (
    Criticality,
    IncidentStatus,
    Priority,
    Severity,
    VulnerabilityStatus,
)
from app.schemas.dashboard import (
    AssetStats,
    DashboardSummary,
    IncidentStats,
    VulnerabilityStats,
)


def _count_by(
    db: Session,
    column: InstrumentedAttribute,
    enum_cls: type[Enum],
    where: ColumnElement[bool] | None = None,
) -> dict:
    """Contagem por valor do enum, com TODOS os valores presentes (0 se não houver)."""
    stmt = select(column, func.count()).group_by(column)
    if where is not None:
        stmt = stmt.where(where)
    rows = dict(db.execute(stmt).tuples().all())
    return {member: rows.get(member, 0) for member in enum_cls}


def _count_all(db: Session, model: type) -> int:
    return db.scalar(select(func.count()).select_from(model)) or 0


def build_dashboard_summary(db: Session) -> DashboardSummary:
    incidents_by_status = _count_by(db, Incident.status, IncidentStatus)
    is_active = Incident.status != IncidentStatus.closed

    return DashboardSummary(
        incidents=IncidentStats(
            total=sum(incidents_by_status.values()),
            active=sum(
                count
                for status, count in incidents_by_status.items()
                if status != IncidentStatus.closed
            ),
            by_status=incidents_by_status,
            active_by_severity=_count_by(db, Incident.severity, Severity, where=is_active),
            active_by_priority=_count_by(db, Incident.priority, Priority, where=is_active),
        ),
        assets=AssetStats(
            total=_count_all(db, Asset),
            by_criticality=_count_by(db, Asset.criticality, Criticality),
        ),
        vulnerabilities=VulnerabilityStats(
            total=_count_all(db, Vulnerability),
            by_status=_count_by(db, Vulnerability.status, VulnerabilityStatus),
            by_severity=_count_by(db, Vulnerability.severity, Severity),
        ),
    )
