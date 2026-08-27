import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import MasterDataStatus
from app.schemas.common import ORMModel


class VehicleCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=50, description="Registration number")
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    vehicle_type: str | None = Field(default=None, max_length=50)
    capacity: Decimal | None = Field(default=None, gt=0)
    capacity_unit_id: uuid.UUID | None = None


class VehicleUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    status: MasterDataStatus | None = None
    vehicle_type: str | None = Field(default=None, max_length=50)
    capacity: Decimal | None = Field(default=None, gt=0)
    capacity_unit_id: uuid.UUID | None = None


class VehicleResponse(ORMModel):
    id: uuid.UUID
    code: str
    name: str
    description: str | None
    status: MasterDataStatus
    vehicle_type: str | None
    capacity: Decimal | None
    capacity_unit_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class DriverCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=50, description="License number")
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    phone: str | None = Field(default=None, max_length=30)


class DriverUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    status: MasterDataStatus | None = None
    phone: str | None = Field(default=None, max_length=30)


class DriverResponse(ORMModel):
    id: uuid.UUID
    code: str
    name: str
    description: str | None
    status: MasterDataStatus
    phone: str | None
    created_at: datetime
    updated_at: datetime
