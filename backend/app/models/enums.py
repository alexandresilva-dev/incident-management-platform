from enum import StrEnum


class AssetType(StrEnum):
    server = "server"
    workstation = "workstation"
    network_device = "network_device"
    application = "application"
    database = "database"
    cloud_service = "cloud_service"
    other = "other"


class Criticality(StrEnum):
    """Importância de um ativo para o negócio."""

    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class Severity(StrEnum):
    """Gravidade de um incidente ou de uma vulnerabilidade."""

    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class VulnerabilityStatus(StrEnum):
    open = "open"
    mitigated = "mitigated"
    patched = "patched"
    accepted = "accepted"  # risco aceite formalmente, sem correção


class IncidentStatus(StrEnum):
    """Estados do ciclo de vida (as transições válidas estão em services/)."""

    open = "open"
    investigating = "investigating"
    mitigated = "mitigated"
    resolved = "resolved"
    closed = "closed"


class IncidentCategory(StrEnum):
    malware = "malware"
    phishing = "phishing"
    unauthorized_access = "unauthorized_access"
    data_breach = "data_breach"
    denial_of_service = "denial_of_service"
    misconfiguration = "misconfiguration"
    other = "other"


class Priority(StrEnum):
    """P1 é a mais urgente. Derivada da severidade e da criticidade dos ativos."""

    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"
