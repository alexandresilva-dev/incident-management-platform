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
