"""Limite de tentativas de login falhadas (proteção contra adivinhar passwords).

Duas barreiras, ambas numa janela deslizante:
- por conta: `login_max_failures_per_account` falhas para o mesmo email;
- por IP:    `login_max_failures_per_ip` falhas vindas do mesmo endereço.

Aplicam-se ao email SUBMETIDO, exista ou não uma conta com ele. Assim o pedido
"bloqueado" é igual para emails reais e inventados e não revela que contas existem.
As tentativas ficam na base de dados (e não em memória) para sobreviverem a
reinícios e funcionarem com vários processos.
"""

import math
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import InstrumentedAttribute, Session

from app.config import settings
from app.models import LoginAttempt
from app.services.errors import TooManyLoginAttemptsError
from app.services.users import normalise_email

# Quanto tempo se guardam as tentativas (só a janela do bloqueio importa; o resto é histórico).
RETENTION = timedelta(hours=24)
_MAX_EMAIL_LENGTH = 320


def _failure_times(
    db: Session, column: InstrumentedAttribute, value: str, since: datetime
) -> list[datetime]:
    stmt = (
        select(LoginAttempt.attempted_at)
        .where(column == value, LoginAttempt.success.is_(False), LoginAttempt.attempted_at >= since)
        .order_by(LoginAttempt.attempted_at)
    )
    return list(db.scalars(stmt))


def _retry_after_seconds(
    failures: list[datetime], limit: int, window: timedelta, now: datetime
) -> int:
    """Segundos até se poder voltar a tentar (0 se já se pode)."""
    if len(failures) < limit:
        return 0
    # Enquanto houver `limit` falhas na janela está bloqueado. Desbloqueia quando a
    # mais antiga dessas `limit` sair da janela.
    unlock_at = failures[-limit] + window
    return max(1, math.ceil((unlock_at - now).total_seconds()))


def check_login_allowed(
    db: Session, email: str, ip_address: str, now: datetime | None = None
) -> None:
    """Levanta TooManyLoginAttemptsError se este email ou este IP estiver bloqueado."""
    now = now or datetime.now(UTC)
    window = timedelta(minutes=settings.login_lockout_window_minutes)
    since = now - window
    email = normalise_email(email)[:_MAX_EMAIL_LENGTH]

    waits = [
        _retry_after_seconds(
            _failure_times(db, LoginAttempt.email, email, since),
            settings.login_max_failures_per_account,
            window,
            now,
        ),
        _retry_after_seconds(
            _failure_times(db, LoginAttempt.ip_address, ip_address, since),
            settings.login_max_failures_per_ip,
            window,
            now,
        ),
    ]
    if any(waits):
        raise TooManyLoginAttemptsError(max(waits))


def record_login_attempt(
    db: Session, email: str, ip_address: str, success: bool, now: datetime | None = None
) -> None:
    now = now or datetime.now(UTC)
    db.add(
        LoginAttempt(
            email=normalise_email(email)[:_MAX_EMAIL_LENGTH],
            ip_address=ip_address,
            success=success,
            attempted_at=now,
        )
    )
    # Limpeza oportunista para a tabela não crescer indefinidamente.
    db.execute(delete(LoginAttempt).where(LoginAttempt.attempted_at < now - RETENTION))
    db.commit()
