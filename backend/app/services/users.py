from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User
from app.security import hash_password, verify_password

MIN_PASSWORD_LENGTH = 12


def normalise_email(email: str) -> str:
    return email.strip().lower()


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == normalise_email(email)))


def create_user(db: Session, email: str, full_name: str, password: str) -> User:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters long")
    email = normalise_email(email)
    if get_user_by_email(db, email) is not None:
        raise ValueError(f"A user with email {email} already exists")

    user = User(email=email, full_name=full_name.strip(), hashed_password=hash_password(password))
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
