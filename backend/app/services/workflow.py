from app.models.enums import IncidentStatus
from app.services.errors import InvalidTransitionError

S = IncidentStatus

# Máquina de estados do ciclo de vida de um incidente (inspirada no ITIL):
#
#   open -> investigating -> mitigated -> resolved -> closed
#                 ^              |            |
#                 +--------------+------------+   (mitigação falhou / reabertura)
#
# Não há saltos (open -> closed é impossível) e `closed` é terminal.
ALLOWED_TRANSITIONS: dict[IncidentStatus, frozenset[IncidentStatus]] = {
    S.open: frozenset({S.investigating}),
    S.investigating: frozenset({S.mitigated}),
    S.mitigated: frozenset({S.resolved, S.investigating}),
    S.resolved: frozenset({S.closed, S.investigating}),
    S.closed: frozenset(),
}


def allowed_transitions(current: IncidentStatus) -> list[IncidentStatus]:
    """Estados para onde se pode ir a partir de `current`, pela ordem do ciclo de vida."""
    return [status for status in IncidentStatus if status in ALLOWED_TRANSITIONS[current]]


def validate_transition(current: IncidentStatus, target: IncidentStatus) -> None:
    if target not in ALLOWED_TRANSITIONS[current]:
        raise InvalidTransitionError(
            current.value, target.value, [s.value for s in allowed_transitions(current)]
        )
