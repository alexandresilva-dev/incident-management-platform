from typing import Annotated

from fastapi import APIRouter, Query, Response, status
from sqlalchemy import select

from app.api.deps import DbSession, get_or_404
from app.models import Asset
from app.models.enums import AssetType, Criticality
from app.schemas.asset import AssetCreate, AssetRead, AssetUpdate
from app.services import assets as asset_service

router = APIRouter(prefix="/assets", tags=["assets"])


@router.post("", response_model=AssetRead, status_code=status.HTTP_201_CREATED)
def create_asset(payload: AssetCreate, db: DbSession) -> Asset:
    """Register an asset. `ip_address` must be a valid IPv4/IPv6 address."""
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
    q: Annotated[str | None, Query(description="Case-insensitive search in the name")] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[Asset]:
    """List assets, filtered by type or criticality or searched by name (case-insensitive)."""
    stmt = select(Asset).order_by(Asset.id)
    if asset_type is not None:
        stmt = stmt.where(Asset.asset_type == asset_type)
    if criticality is not None:
        stmt = stmt.where(Asset.criticality == criticality)
    if q:
        stmt = stmt.where(Asset.name.icontains(q, autoescape=True))
    return list(db.scalars(stmt.offset(skip).limit(limit)))


@router.get(
    "/{asset_id}", response_model=AssetRead, responses={404: {"description": "Asset not found"}}
)
def get_asset(asset_id: int, db: DbSession) -> Asset:
    """Get one asset."""
    return get_or_404(db, Asset, asset_id)


@router.patch(
    "/{asset_id}", response_model=AssetRead, responses={404: {"description": "Asset not found"}}
)
def update_asset(asset_id: int, payload: AssetUpdate, db: DbSession) -> Asset:
    """Partial update. Changing the criticality recalculates the priority of the open
    incidents that affect this asset."""
    asset = get_or_404(db, Asset, asset_id)
    return asset_service.update_asset(db, asset, payload)


@router.delete(
    "/{asset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"description": "Asset not found"}},
)
def delete_asset(asset_id: int, db: DbSession) -> Response:
    """Delete an asset. Its vulnerabilities are kept (without an asset) and open incidents
    are re-prioritised without it; closed incidents keep their priority."""
    asset = get_or_404(db, Asset, asset_id)
    asset_service.delete_asset(db, asset)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
