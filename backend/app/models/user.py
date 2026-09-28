from sqlalchemy import Boolean, String, true
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import str_enum
from app.models.enums import UserRole
from app.models.mixins import TimestampMixin


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Sempre em minúsculas (ver services/users.py): "Ana@x.com" e "ana@x.com" são a mesma conta.
    email: Mapped[str] = mapped_column(String(320), unique=True)
    full_name: Mapped[str] = mapped_column(String(200))
    # Só o hash bcrypt: a password em si nunca é guardada.
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=true())
    # Lido da BD em cada pedido (não vai no token): mudar o papel tem efeito imediato.
    role: Mapped[UserRole] = mapped_column(
        str_enum(UserRole), server_default=UserRole.analyst.value
    )
