from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import IncidentCategory, IncidentStatus, Priority, Severity
from app.schemas.asset import AssetRead
from app.schemas.vulnerability import VulnerabilityRead

_NOT_NULLABLE = ("title", "category", "severity", "asset_ids", "vulnerability_ids")


class IncidentCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=300, examples=["Suspicious logins on VPN gateway"])
    description: str | None = None
    category: IncidentCategory = IncidentCategory.other
    severity: Severity
    asset_ids: list[int] = Field(default_factory=list, max_length=100)
    vulnerability_ids: list[int] = Field(default_factory=list, max_length=100)


class IncidentUpdate(BaseModel):
    """Atualização parcial. O estado NÃO se altera aqui: usa-se o endpoint de
    transições, que valida a state machine e regista o audit trail."""

    model_config = ConfigDict(str_strip_whitespace=True)

    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = None
    category: IncidentCategory | None = None
    severity: Severity | None = None
    asset_ids: list[int] | None = Field(default=None, max_length=100)
    vulnerability_ids: list[int] | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def _reject_null_for_required_fields(self) -> "IncidentUpdate":
        for field in _NOT_NULLABLE:
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class IncidentSummary(BaseModel):
    """Versão leve, usada nas listagens (sem ativos/vulnerabilidades aninhados)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    category: IncidentCategory
    severity: Severity
    priority: Priority
    status: IncidentStatus
    resolved_at: datetime | None
    closed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class IncidentRead(IncidentSummary):
    assets: list[AssetRead]
    vulnerabilities: list[VulnerabilityRead]
