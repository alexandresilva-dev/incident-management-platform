import pytest

from app.models.enums import Criticality, Priority, Severity
from app.services.prioritization import calculate_priority

P1, P2, P3, P4 = Priority.P1, Priority.P2, Priority.P3, Priority.P4


@pytest.mark.parametrize(
    ("severity", "expected"),
    [(Severity.critical, P1), (Severity.high, P2), (Severity.medium, P3), (Severity.low, P4)],
)
def test_priority_without_assets_comes_from_severity(severity, expected) -> None:
    assert calculate_priority(severity, []) == expected


@pytest.mark.parametrize(
    ("severity", "expected"),
    [
        (Severity.critical, P1),  # já é o máximo: não passa de P1
        (Severity.high, P1),
        (Severity.medium, P2),
        (Severity.low, P3),
    ],
)
def test_critical_asset_escalates_one_level(severity, expected) -> None:
    assert calculate_priority(severity, [Criticality.critical]) == expected


@pytest.mark.parametrize("criticality", [Criticality.low, Criticality.medium, Criticality.high])
def test_non_critical_assets_do_not_escalate(criticality) -> None:
    assert calculate_priority(Severity.medium, [criticality]) == P3


def test_only_one_critical_asset_is_needed_and_escalation_does_not_stack() -> None:
    assets = [Criticality.low, Criticality.critical, Criticality.critical, Criticality.critical]

    assert calculate_priority(Severity.low, assets) == P3  # um nível, não três


def test_accepts_any_iterable() -> None:
    assert calculate_priority(Severity.medium, (c for c in [Criticality.critical])) == P2
