from typing import Annotated, TypeVar

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import get_db

# Alias para não repetir Depends(get_db) em todos os endpoints.
DbSession = Annotated[Session, Depends(get_db)]

ModelT = TypeVar("ModelT", bound=Base)


def get_or_404(db: Session, model: type[ModelT], object_id: int) -> ModelT:
    obj = db.get(model, object_id)
    if obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{model.__name__} {object_id} not found",
        )
    return obj
