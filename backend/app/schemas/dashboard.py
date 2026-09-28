from pydantic import BaseModel

from app.models.enums import (
    Criticality,
    IncidentStatus,
    Priority,
    Severity,
    VulnerabilityStatus,
)


class IncidentStats(BaseModel):
    total: int
    active: int  # tudo o que ainda não está closed
    by_status: dict[IncidentStatus, int]  # todos os incidentes
    active_by_severity: dict[Severity, int]  # só os que ainda não estão closed
    active_by_priority: dict[Priority, int]


class AssetStats(BaseModel):
    total: int
    by_criticality: dict[Criticality, int]


class VulnerabilityStats(BaseModel):
    total: int
    by_status: dict[VulnerabilityStatus, int]
    by_severity: dict[Severity, int]


class DashboardSummary(BaseModel):
    incidents: IncidentStats
    assets: AssetStats
    vulnerabilities: VulnerabilityStats
