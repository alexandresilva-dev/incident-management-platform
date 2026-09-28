from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import User
from app.models.enums import UserRole
from app.security import hash_password, verify_password
from app.services.errors import DuplicateUserError, LastAdminError

MIN_PASSWORD_LENGTH = 12


def normalise_email(email: str) -> str:
    return email.strip().lower()


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == normalise_email(email)))


def create_user(
    db: Session,
    email: str,
    full_name: str,
    password: str,
    role: UserRole = UserRole.analyst,
) -> User:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters long")
    email = normalise_email(email)
    if get_user_by_email(db, email) is not None:
        raise DuplicateUserError(email)

    user = User(
        email=email,
        full_name=full_name.strip(),
        hashed_password=hash_password(password),
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, email: str, password: str) -> User | None:
    """Devolve o utilizador se as credenciais estiverem certas e a conta ativa.

    A verificação da password corre SEMPRE (mesmo se o email não existir), para o
    tempo de resposta não revelar que emails estão registados.
    """
    user = get_user_by_email(db, email)
    password_ok = verify_password(password, user.hashed_password if user else None)
    if user is None or not password_ok or not user.is_active:
        return None
    return user


def list_users(db: Session) -> list[User]:
    return list(db.scalars(select(User).order_by(User.id)))


def _active_admin_count(db: Session) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(User)
            .where(User.role == UserRole.admin, User.is_active)
        )
        or 0
    )


def update_user(db: Session, user: User, changes: dict) -> User:
    """Aplica `changes` (full_name, role, is_active).

    Regra de segurança: nunca se pode ficar sem administradores ativos, senão ninguém
    conseguiria gerir utilizadores. Isto cobre desativar ou despromover o último admin
    (incluindo a própria pessoa).
    """
    was_active_admin = user.role == UserRole.admin and user.is_active
    will_be_active_admin = changes.get("role", user.role) == UserRole.admin and changes.get(
        "is_active", user.is_active
    )
    if was_active_admin and not will_be_active_admin and _active_admin_count(db) <= 1:
        raise LastAdminError

    for field, value in changes.items():
        setattr(user, field, value.strip() if field == "full_name" else value)
    db.commit()
    db.refresh(user)
    return user
