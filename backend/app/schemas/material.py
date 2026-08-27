import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import MasterDataStatus
from app.schemas.common import ORMModel


class MaterialCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    category_id: uuid.UUID | None = None
    default_unit_id: uuid.UUID | None = None


class MaterialUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    status: MasterDataStatus | None = None
    category_id: uuid.UUID | None = None
    default_unit_id: uuid.UUID | None = None


class MaterialResponse(ORMModel):
    id: uuid.UUID
    code: str
    name: str
    description: str | None
    status: MasterDataStatus
    category_id: uuid.UUID | None
    default_unit_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class ProductCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    category_id: uuid.UUID | None = None
    default_unit_id: uuid.UUID | None = None


class ProductUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    status: MasterDataStatus | None = None
    category_id: uuid.UUID | None = None
    default_unit_id: uuid.UUID | None = None


class ProductResponse(ORMModel):
    id: uuid.UUID
    code: str
    name: str
    description: str | None
    status: MasterDataStatus
    category_id: uuid.UUID | None
    default_unit_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
