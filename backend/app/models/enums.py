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
