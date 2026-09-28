from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import DbSession, get_or_404
from app.models import Asset, Vulnerability
from app.models.enums import Severity, VulnerabilityStatus
from app.schemas.vulnerability import (
    VulnerabilityCreate,
    VulnerabilityRead,
    VulnerabilityUpdate,
)
from app.services.vulnerability import severity_from_cvss

router = APIRouter(prefix="/vulnerabilities", tags=["vulnerabilities"])


def _ensure_asset_exists(db: Session, asset_id: int | None) -> None:
    """Uma referência a um ativo inexistente é erro do cliente (422), não da BD."""
    if asset_id is not None and db.get(Asset, asset_id) is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"asset_id {asset_id} does not exist",
        )


@router.post("", response_model=VulnerabilityRead, status_code=status.HTTP_201_CREATED)
def create_vulnerability(payload: VulnerabilityCreate, db: DbSession) -> Vulnerability:
    _ensure_asset_exists(db, payload.asset_id)
    data = payload.model_dump()
    if data["severity"] is None:
        data["severity"] = severity_from_cvss(data["cvss_score"])
    vulnerability = Vulnerability(**data)
    db.add(vulnerability)
    db.commit()
    db.refresh(vulnerability)
    return vulnerability


@router.get("", response_model=list[VulnerabilityRead])
def list_vulnerabilities(
    db: DbSession,
    severity: Severity | None = None,
    status_: Annotated[VulnerabilityStatus | None, Query(alias="status")] = None,
    asset_id: int | None = None,
    cve_id: str | None = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[Vulnerability]:
    stmt = select(Vulnerability).order_by(Vulnerability.id)
    if severity is not None:
        stmt = stmt.where(Vulnerability.severity == severity)
    if status_ is not None:
        stmt = stmt.where(Vulnerability.status == status_)
    if asset_id is not None:
        stmt = stmt.where(Vulnerability.asset_id == asset_id)
    if cve_id:
        stmt = stmt.where(Vulnerability.cve_id == cve_id.upper())
    return list(db.scalars(stmt.offset(skip).limit(limit)))


@router.get("/{vulnerability_id}", response_model=VulnerabilityRead)
def get_vulnerability(vulnerability_id: int, db: DbSession) -> Vulnerability:
    return get_or_404(db, Vulnerability, vulnerability_id)


@router.patch("/{vulnerability_id}", response_model=VulnerabilityRead)
def update_vulnerability(
    vulnerability_id: int, payload: VulnerabilityUpdate, db: DbSession
) -> Vulnerability:
    vulnerability = get_or_404(db, Vulnerability, vulnerability_id)
    changes = payload.model_dump(exclude_unset=True)
    _ensure_asset_exists(db, changes.get("asset_id"))
    for field, value in changes.items():
        setattr(vulnerability, field, value)
    db.commit()
    db.refresh(vulnerability)
    return vulnerability


@router.delete("/{vulnerability_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vulnerability(vulnerability_id: int, db: DbSession) -> Response:
    vulnerability = get_or_404(db, Vulnerability, vulnerability_id)
    db.delete(vulnerability)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
