from fastapi import APIRouter, status

from app.api.deps import DbSession, get_or_404
from app.models import User
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.services import users as user_service

# Todo este router é só para administradores (ver main.py).
router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserRead])
def list_users(db: DbSession) -> list[User]:
    """List all users."""
    return user_service.list_users(db)


@router.post(
    "",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {"description": "A user with this email already exists"},
        422: {"description": "Invalid email or a password shorter than 12 characters"},
    },
)
def create_user(payload: UserCreate, db: DbSession) -> User:
    """Create a user. There is no public sign-up: accounts are created by administrators."""
    return user_service.create_user(
        db, payload.email, payload.full_name, payload.password, role=payload.role
    )


@router.patch(
    "/{user_id}",
    response_model=UserRead,
    responses={
        404: {"description": "User not found"},
        409: {"description": "Would leave the application without an active administrator"},
    },
)
def update_user(user_id: int, payload: UserUpdate, db: DbSession) -> User:
    """Change a user's name or role, or activate/deactivate the account.

    Users are deactivated rather than deleted so the audit trail keeps making sense.
    A deactivated user loses access immediately, even with an unexpired token.
    The last active administrator cannot be demoted or deactivated.
    """
    user = get_or_404(db, User, user_id)
    return user_service.update_user(db, user, payload.model_dump(exclude_unset=True))
