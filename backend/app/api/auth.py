from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import CurrentUser, DbSession
from app.schemas.user import Token, UserRead
from app.security import create_access_token
from app.services.login_throttle import check_login_allowed, record_login_attempt
from app.services.users import authenticate

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=Token,
    responses={
        401: {"description": "Incorrect email or password"},
        429: {
            "description": (
                "Too many failed attempts for this account or IP address. "
                "The Retry-After header says how many seconds to wait."
            )
        },
    },
)
def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()], request: Request, db: DbSession
) -> Token:
    """Exchange email + password for an access token (`username` is the email).

    Repeated failures are throttled per account and per IP address (429). The error
    message is the same whether or not the email exists, so it does not reveal
    which accounts exist.
    """
    # Nota: atrás de um proxy reverso, request.client é o IP do proxy. Não se confia
    # em X-Forwarded-For por omissão porque qualquer cliente o pode falsificar.
    ip_address = request.client.host if request.client else "unknown"
    check_login_allowed(db, form.username, ip_address)

    user = authenticate(db, form.username, form.password)
    record_login_attempt(db, form.username, ip_address, success=user is not None)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(access_token=create_access_token(str(user.id)))


@router.get(
    "/me",
    response_model=UserRead,
    responses={401: {"description": "Missing, invalid or expired token"}},
)
def read_current_user(current_user: CurrentUser) -> UserRead:
    """O utilizador a que pertence o token."""
    return current_user
