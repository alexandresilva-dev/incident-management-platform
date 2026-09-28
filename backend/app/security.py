"""Hashing de passwords e tokens JWT. Sem dependências de HTTP nem da BD."""

from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.config import settings

ALGORITHM = "HS256"

# O bcrypt só usa os primeiros 72 bytes da password. Em vez de truncar em
# silêncio (duas passwords longas diferentes ficariam iguais), rejeita-se.
MAX_PASSWORD_BYTES = 72

# Hash de uma password que ninguém conhece. Serve para verify_password gastar o
# mesmo tempo quando o utilizador não existe, para o tempo de resposta não
# revelar que emails estão registados.
_DUMMY_HASH = bcrypt.hashpw(b"not-a-real-password", bcrypt.gensalt())


def hash_password(password: str) -> str:
    encoded = password.encode()
    if len(encoded) > MAX_PASSWORD_BYTES:
        raise ValueError(f"Password must be at most {MAX_PASSWORD_BYTES} bytes long")
    return bcrypt.hashpw(encoded, bcrypt.gensalt()).decode()


def verify_password(password: str, hashed_password: str | None) -> bool:
    """Compara a password com o hash. `hashed_password=None` (utilizador inexistente)
    gasta o mesmo tempo mas devolve sempre False."""
    target = hashed_password.encode() if hashed_password else _DUMMY_HASH
    try:
        matches = bcrypt.checkpw(password.encode(), target)
    except ValueError:  # password com mais de 72 bytes
        return False
    return matches and hashed_password is not None


def create_access_token(subject: str, expires_minutes: int | None = None) -> str:
    now = datetime.now(UTC)
    lifetime = timedelta(minutes=expires_minutes or settings.access_token_expire_minutes)
    payload = {"sub": subject, "iat": now, "exp": now + lifetime}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> str | None:
    """Devolve o `sub` (id do utilizador) de um token válido, ou None se for inválido,
    adulterado ou expirado."""
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            # Fixar o algoritmo impede que um token diga "alg: none" ou troque
            # o algoritmo para contornar a assinatura.
            algorithms=[ALGORITHM],
            options={"require": ["exp", "sub"]},
        )
    except jwt.PyJWTError:
        return None
    subject = payload.get("sub")
    return subject if isinstance(subject, str) else None
