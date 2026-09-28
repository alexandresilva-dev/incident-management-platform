from typing import TYPE_CHECKING

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import str_enum
from app.models.enums import AssetType, Criticality
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.vulnerability import Vulnerability


class Asset(TimestampMixin, Base):
    """Ativo (servidor, aplicação, base de dados...) que pode ser afetado por incidentes."""

    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    asset_type: Mapped[AssetType] = mapped_column(str_enum(AssetType))
    criticality: Mapped[Criticality] = mapped_column(
        str_enum(Criticality), default=Criticality.medium
    )
    ip_address: Mapped[str | None] = mapped_column(String(45))
    owner: Mapped[str | None] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)

    vulnerabilities: Mapped[list["Vulnerability"]] = relationship(
        back_populates="asset", passive_deletes=True
    )
