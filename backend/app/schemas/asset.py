import ipaddress
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import AssetType, Criticality

# Campos que não aceitam null (mesmo num PATCH): a coluna na BD é NOT NULL.
_NOT_NULLABLE = ("name", "asset_type", "criticality")


def _validate_ip(value: str | None) -> str | None:
    if value is None:
        return None
    try:
        return str(ipaddress.ip_address(value))
    except ValueError:
        raise ValueError("must be a valid IPv4 or IPv6 address") from None


class AssetCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=200, examples=["srv-web-01"])
    asset_type: AssetType
    criticality: Criticality = Criticality.medium
    ip_address: str | None = Field(default=None, examples=["10.0.0.15"])
    owner: str | None = Field(default=None, max_length=200, examples=["Infrastructure team"])
    description: str | None = None

    _check_ip = field_validator("ip_address")(_validate_ip)


class AssetUpdate(BaseModel):
    """Atualização parcial (PATCH): só os campos enviados são alterados."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=200)
    asset_type: AssetType | None = None
    criticality: Criticality | None = None
    ip_address: str | None = None
    owner: str | None = Field(default=None, max_length=200)
    description: str | None = None

    _check_ip = field_validator("ip_address")(_validate_ip)

    @model_validator(mode="after")
    def _reject_null_for_required_fields(self) -> "AssetUpdate":
        for field in _NOT_NULLABLE:
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class AssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    asset_type: AssetType
    criticality: Criticality
    ip_address: str | None
    owner: str | None
    description: str | None
    created_at: datetime
    updated_at: datetime
