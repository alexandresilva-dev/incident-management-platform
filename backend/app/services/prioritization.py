from collections.abc import Iterable

from app.models.enums import Criticality, Priority, Severity

# Prioridade base: vem só da severidade do incidente.
_BASE_PRIORITY: dict[Severity, Priority] = {
    Severity.critical: Priority.P1,
    Severity.high: Priority.P2,
    Severity.medium: Priority.P3,
    Severity.low: Priority.P4,
}

# Do mais urgente para o menos urgente.
_URGENCY_ORDER = [Priority.P1, Priority.P2, Priority.P3, Priority.P4]


def _escalate(priority: Priority) -> Priority:
    """Sobe um nível de urgência (P3 -> P2). P1 já é o máximo."""
    index = _URGENCY_ORDER.index(priority)
    return _URGENCY_ORDER[max(index - 1, 0)]


def calculate_priority(severity: Severity, asset_criticalities: Iterable[Criticality]) -> Priority:
    """Prioridade = impacto (severidade) ajustado pela criticidade do negócio.

    Regra: se algum ativo afetado for `critical`, a prioridade sobe um nível.
    Ativos de criticidade `high` ou inferior não alteram a prioridade base.
    """
    priority = _BASE_PRIORITY[severity]
    if Criticality.critical in set(asset_criticalities):
        priority = _escalate(priority)
    return priority
