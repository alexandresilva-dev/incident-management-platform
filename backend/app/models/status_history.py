from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import str_enum
from app.models.enums import IncidentStatus

if TYPE_CHECKING:
    from app.models.incident import Incident


class IncidentStatusHistory(Base):
    """Audit trail: uma linha por cada mudança de estado de um incidente.

    Só se acrescentam linhas, nunca se alteram nem se apagam. O registo de
    criação tem from_status = NULL.
    """

    __tablename__ = "incident_status_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    # RESTRICT: a BD recusa apagar um incidente que tenha histórico, para o
    # audit trail não se perder por acidente.
    incident_id: Mapped[int] = mapped_column(
        ForeignKey("incidents.id", ondelete="RESTRICT"), index=True
    )
    from_status: Mapped[IncidentStatus | None] = mapped_column(str_enum(IncidentStatus))
    to_status: Mapped[IncidentStatus] = mapped_column(str_enum(IncidentStatus))
    # Texto e não FK: o registo deve continuar a dizer quem agiu mesmo que a
    # conta seja apagada mais tarde.
    changed_by: Mapped[str | None] = mapped_column(String(255))
    comment: Mapped[str | None] = mapped_column(Text)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    incident: Mapped["Incident"] = relationship(back_populates="history")
