import itertools

import pytest

from app.models.enums import IncidentStatus
from app.services.errors import InvalidTransitionError
from app.services.workflow import allowed_transitions, validate_transition

S = IncidentStatus

# Escrito à mão e independente da implementação: é a "especificação" do workflow.
VALID = {
    (S.open, S.investigating),
    (S.investigating, S.mitigated),
    (S.mitigated, S.resolved),
    (S.mitigated, S.investigating),  # mitigação falhou
    (S.resolved, S.closed),
    (S.resolved, S.investigating),  # reabertura
}


@pytest.mark.parametrize(("current", "target"), sorted(VALID))
def test_valid_transitions_are_accepted(current: IncidentStatus, target: IncidentStatus) -> None:
    validate_transition(current, target)  # não levanta


@pytest.mark.parametrize(
    ("current", "target"),
    [pair for pair in itertools.product(S, S) if pair not in VALID],
)
def test_every_other_transition_is_rejected(current: IncidentStatus, target: IncidentStatus) -> None:
    with pytest.raises(InvalidTransitionError):
        validate_transition(current, target)


def test_cannot_skip_straight_from_open_to_closed() -> None:
    with pytest.raises(InvalidTransitionError) as exc_info:
        validate_transition(S.open, S.closed)

    assert exc_info.value.allowed == ["investigating"]
    assert "open" in str(exc_info.value) and "closed" in str(exc_info.value)


def test_closed_is_terminal() -> None:
    assert allowed_transitions(S.closed) == []
    for target in S:
        with pytest.raises(InvalidTransitionError):
            validate_transition(S.closed, target)


def test_a_status_cannot_transition_to_itself() -> None:
    for status in S:
        with pytest.raises(InvalidTransitionError):
            validate_transition(status, status)


def test_allowed_transitions_follow_lifecycle_order() -> None:
    assert allowed_transitions(S.open) == [S.investigating]
    assert allowed_transitions(S.mitigated) == [S.investigating, S.resolved]
    assert allowed_transitions(S.resolved) == [S.investigating, S.closed]


def test_every_status_is_covered_by_the_table() -> None:
    from app.services.workflow import ALLOWED_TRANSITIONS

    assert set(ALLOWED_TRANSITIONS) == set(S)
