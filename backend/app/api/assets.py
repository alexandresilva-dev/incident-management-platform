from fastapi import APIRouter, Query, Response, status
from sqlalchemy import select

from app.api.deps import DbSession, get_or_404
from app.models import Asset
from app.models.enums import AssetType, Criticality
from app.schemas.asset import AssetCreate, AssetRead, AssetUpdate

router = APIRouter(prefix="/assets", tags=["assets"])


@router.post("", response_model=AssetRead, status_code=status.HTTP_201_CREATED)
def create_asset(payload: AssetCreate, db: DbSession) -> Asset:
    asset = Asset(**payload.model_dump())
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


@router.get("", response_model=list[AssetRead])
def list_assets(
    db: DbSession,
    asset_type: AssetType | None = None,
    criticality: Criticality | None = None,
    q: str | None = Query(default=None, description="Case-insensitive search in the name"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[Asset]:
    stmt = select(Asset).order_by(Asset.id)
    if asset_type is not None:
        stmt = stmt.where(Asset.asset_type == asset_type)
    if criticality is not None:
        stmt = stmt.where(Asset.criticality == criticality)
    if q:
        stmt = stmt.where(Asset.name.icontains(q, autoescape=True))
    return list(db.scalars(stmt.offset(skip).limit(limit)))


@router.get("/{asset_id}", response_model=AssetRead)
def get_asset(asset_id: int, db: DbSession) -> Asset:
    return get_or_404(db, Asset, asset_id)


@router.patch("/{asset_id}", response_model=AssetRead)
def update_asset(asset_id: int, payload: AssetUpdate, db: DbSession) -> Asset:
    asset = get_or_404(db, Asset, asset_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(asset, field, value)
    db.commit()
    db.refresh(asset)
    return asset


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_asset(asset_id: int, db: DbSession) -> Response:
    asset = get_or_404(db, Asset, asset_id)
    db.delete(asset)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
