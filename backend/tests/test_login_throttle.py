from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import LoginAttempt, User
from app.services.errors import TooManyLoginAttemptsError
from app.services.login_throttle import (
    RETENTION,
    check_login_allowed,
    record_login_attempt,
)
from tests.conftest import TEST_USER_EMAIL, TEST_USER_PASSWORD

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
WINDOW = timedelta(minutes=settings.login_lockout_window_minutes)
LIMIT = settings.login_max_failures_per_account
IP = "203.0.113.7"


def fail(db: Session, email: str = "ana@example.com", ip: str = IP, at: datetime = NOW) -> None:
    record_login_attempt(db, email, ip, success=False, now=at)


# --- por conta ---------------------------------------------------------------


def test_allows_attempts_below_the_limit(db: Session) -> None:
    for i in range(LIMIT - 1):
        fail(db, at=NOW + timedelta(seconds=i))

    check_login_allowed(db, "ana@example.com", IP, now=NOW + timedelta(minutes=1))  # não levanta


def test_blocks_once_the_limit_is_reached(db: Session) -> None:
    for i in range(LIMIT):
        fail(db, at=NOW + timedelta(seconds=i))

    with pytest.raises(TooManyLoginAttemptsError) as error:
        check_login_allowed(db, "ana@example.com", IP, now=NOW + timedelta(minutes=1))

    assert "Try again in" in str(error.value)


def test_retry_after_counts_down_to_when_the_oldest_failure_leaves_the_window(
    db: Session,
) -> None:
    for i in range(LIMIT):
        fail(db, at=NOW + timedelta(minutes=i))  # falhas às 12:00, 12:01, ...
    now = NOW + timedelta(minutes=LIMIT)  # 12:05

    with pytest.raises(TooManyLoginAttemptsError) as error:
        check_login_allowed(db, "ana@example.com", IP, now=now)

    # A falha das 12:00 sai da janela às 12:15: faltam 10 minutos.
    assert error.value.retry_after_seconds == 10 * 60


def test_unblocks_when_the_failures_age_out_of_the_window(db: Session) -> None:
    for i in range(LIMIT):
        fail(db, at=NOW + timedelta(seconds=i))

    later = NOW + WINDOW + timedelta(minutes=1)

    check_login_allowed(db, "ana@example.com", IP, now=later)  # não levanta


def test_successful_logins_do_not_count(db: Session) -> None:
    for i in range(LIMIT * 2):
        record_login_attempt(
            db, "ana@example.com", IP, success=True, now=NOW + timedelta(seconds=i)
        )

    check_login_allowed(db, "ana@example.com", IP, now=NOW + timedelta(minutes=1))  # não levanta


def test_email_is_normalised_so_case_tricks_do_not_dodge_the_limit(db: Session) -> None:
    variants = ["ana@example.com", "ANA@example.com", "  Ana@Example.com "]
    for i in range(LIMIT):
        fail(db, email=variants[i % 3], at=NOW + timedelta(seconds=i))

    with pytest.raises(TooManyLoginAttemptsError):
        check_login_allowed(db, "AnA@EXAMPLE.com", "198.51.100.1", now=NOW + timedelta(minutes=1))


def test_other_accounts_are_not_affected(db: Session) -> None:
    for i in range(LIMIT):
        fail(db, email="ana@example.com", ip="198.51.100.1", at=NOW + timedelta(seconds=i))

    check_login_allowed(db, "rui@example.com", "198.51.100.2", now=NOW + timedelta(minutes=1))


def test_non_existent_accounts_are_throttled_exactly_like_real_ones(db: Session) -> None:
    """Se só as contas reais fossem bloqueadas, o 429 revelaria que existem."""
    for i in range(LIMIT):
        fail(db, email="ghost-nobody@example.com", at=NOW + timedelta(seconds=i))

    with pytest.raises(TooManyLoginAttemptsError):
        check_login_allowed(db, "ghost-nobody@example.com", IP, now=NOW + timedelta(minutes=1))


# --- por IP ------------------------------------------------------------------


def test_one_ip_spraying_many_accounts_is_blocked(db: Session) -> None:
    ip_limit = settings.login_max_failures_per_ip
    for i in range(ip_limit):
        fail(db, email=f"user{i}@example.com", ip="203.0.113.99", at=NOW + timedelta(seconds=i))

    with pytest.raises(TooManyLoginAttemptsError):
        # nenhuma conta chegou ao limite, mas o IP sim
        check_login_allowed(
            db, "someone-new@example.com", "203.0.113.99", now=NOW + timedelta(minutes=1)
        )
    check_login_allowed(
        db, "someone-new@example.com", "203.0.113.100", now=NOW + timedelta(minutes=1)
    )


# --- registo -----------------------------------------------------------------


def test_old_attempts_are_purged(db: Session) -> None:
    fail(db, at=NOW - RETENTION - timedelta(hours=1))
    fail(db, at=NOW - timedelta(hours=1))

    fail(db, at=NOW)  # esta gravação limpa as antigas

    assert db.scalar(select(func.count()).select_from(LoginAttempt)) == 2


def test_very_long_emails_are_stored_truncated(db: Session) -> None:
    record_login_attempt(db, "a" * 1000 + "@example.com", IP, success=False, now=NOW)

    stored = db.scalar(select(LoginAttempt.email))
    assert len(stored) == 320


# --- pela API ------------------------------------------------------------------


def login(client: TestClient, email: str, password: str):
    return client.post("/auth/login", data={"username": email, "password": password})


def test_login_endpoint_locks_after_repeated_failures(
    anonymous_client: TestClient, test_user: User
) -> None:
    for _ in range(LIMIT):
        assert login(anonymous_client, TEST_USER_EMAIL, "wrong-password-value").status_code == 401

    blocked = login(anonymous_client, TEST_USER_EMAIL, "wrong-password-value")

    assert blocked.status_code == 429
    assert int(blocked.headers["retry-after"]) > 0
    assert "Try again in" in blocked.json()["detail"]


def test_correct_password_is_also_refused_while_locked(
    anonymous_client: TestClient, test_user: User
) -> None:
    """Se a password certa passasse durante o bloqueio, o atacante continuava a adivinhar."""
    for _ in range(LIMIT):
        login(anonymous_client, TEST_USER_EMAIL, "wrong-password-value")

    assert login(anonymous_client, TEST_USER_EMAIL, TEST_USER_PASSWORD).status_code == 429


def test_login_endpoint_locks_unknown_emails_too(anonymous_client: TestClient) -> None:
    for _ in range(LIMIT):
        login(anonymous_client, "ghost@example.com", "whatever-password")

    assert login(anonymous_client, "ghost@example.com", "whatever-password").status_code == 429


def test_failures_below_the_limit_do_not_block_a_correct_login(
    anonymous_client: TestClient, test_user: User
) -> None:
    for _ in range(LIMIT - 1):
        login(anonymous_client, TEST_USER_EMAIL, "wrong-password-value")

    assert login(anonymous_client, TEST_USER_EMAIL, TEST_USER_PASSWORD).status_code == 200


def test_every_attempt_is_recorded(
    anonymous_client: TestClient, test_user: User, db: Session
) -> None:
    login(anonymous_client, TEST_USER_EMAIL, "wrong-password-value")
    login(anonymous_client, TEST_USER_EMAIL, TEST_USER_PASSWORD)

    attempts = db.scalars(select(LoginAttempt).order_by(LoginAttempt.id)).all()

    assert [a.success for a in attempts] == [False, True]
    assert all(a.email == TEST_USER_EMAIL and a.ip_address for a in attempts)
