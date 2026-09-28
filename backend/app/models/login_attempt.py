from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LoginAttempt(Base):
    """Uma tentativa de login (certa ou errada).

    Serve para limitar tentativas repetidas (ver services/login_throttle.py) e
    como registo de auditoria de autenticação. `email` é o que foi submetido,
    exista ou não uma conta com ele, para o limite não revelar que contas existem.
    """

    __tablename__ = "login_attempts"
    __table_args__ = (
        Index("ix_login_attempts_email_attempted_at", "email", "attempted_at"),
        Index("ix_login_attempts_ip_address_attempted_at", "ip_address", "attempted_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320))
    ip_address: Mapped[str] = mapped_column(String(45))
    success: Mapped[bool] = mapped_column(Boolean)
    attempted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
