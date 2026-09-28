from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Column, DateTime, ForeignKey, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import str_enum
from app.models.enums import IncidentCategory, IncidentStatus, Priority, Severity
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.asset import Asset
    from app.models.status_history import IncidentStatusHistory
    from app.models.vulnerability import Vulnerability

# Tabelas de associação (muitos-para-muitos). Se um ativo/vulnerabilidade/incidente
# for apagado, só a ligação desaparece (CASCADE), nunca o outro lado.
incident_assets = Table(
    "incident_assets",
    Base.metadata,
    Column("incident_id", ForeignKey("incidents.id", ondelete="CASCADE"), primary_key=True),
    Column("asset_id", ForeignKey("assets.id", ondelete="CASCADE"), primary_key=True),
)

incident_vulnerabilities = Table(
    "incident_vulnerabilities",
    Base.metadata,
    Column("incident_id", ForeignKey("incidents.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "vulnerability_id",
        ForeignKey("vulnerabilities.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Incident(TimestampMixin, Base):
    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[IncidentCategory] = mapped_column(
        str_enum(IncidentCategory), default=IncidentCategory.other
    )
    severity: Mapped[Severity] = mapped_column(str_enum(Severity))
    priority: Mapped[Priority] = mapped_column(str_enum(Priority), default=Priority.P3)
    status: Mapped[IncidentStatus] = mapped_column(
        str_enum(IncidentStatus), default=IncidentStatus.open, index=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    assets: Mapped[list["Asset"]] = relationship(
        secondary=incident_assets, back_populates="incidents"
    )
    vulnerabilities: Mapped[list["Vulnerability"]] = relationship(
        secondary=incident_vulnerabilities, back_populates="incidents"
    )
    history: Mapped[list["IncidentStatusHistory"]] = relationship(
        back_populates="incident", order_by="IncidentStatusHistory.id"
    )
