from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import get_db
from app.models import User
from app.models.enums import UserRole
from app.security import decode_access_token

# Alias para não repetir Depends(get_db) em todos os endpoints.
DbSession = Annotated[Session, Depends(get_db)]

# tokenUrl aponta para o login: é o que faz o botão "Authorize" do Swagger funcionar.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: DbSession) -> User:
    """Autentica o pedido a partir do token Bearer; 401 se for inválido ou expirado."""
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    subject = decode_access_token(token)
    if subject is None or not subject.isdigit():
        raise unauthorized
    user = db.get(User, int(subject))
    # Um utilizador desativado ou apagado perde o acesso mesmo com um token ainda válido.
    if user is None or not user.is_active:
        raise unauthorized
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_or_404[ModelT: Base](
    db: Session, model: type[ModelT], object_id: int, *, for_update: bool = False
) -> ModelT:
    """Devolve o objeto ou 404. `for_update` bloqueia a linha até ao fim da transação."""
    obj = db.get(model, object_id, with_for_update=for_update)
    if obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{model.__name__} {object_id} not found",
        )
    return obj


def require_admin(current_user: CurrentUser) -> User:
    """Só administradores. Corre depois da autenticação (401 antes de 403)."""
    if current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Administrator role required"
        )
    return current_user


AdminUser = Annotated[User, Depends(require_admin)]
