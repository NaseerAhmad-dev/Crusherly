"""Generic request/response shapes for the simplest master-data entities — the ones with no
fields beyond `code`/`name`/`description`/`status` (see `app/models/base.py::CodedMasterDataMixin`).
Richer entities (Material, Customer, Supplier, Vehicle, Driver, ...) define their own schemas
that extend this shape with entity-specific fields instead of reusing these directly.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import MasterDataStatus
from app.schemas.common import ORMModel


class MasterDataCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None


class MasterDataUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    status: MasterDataStatus | None = None


class MasterDataResponse(ORMModel):
    id: uuid.UUID
    code: str
    name: str
    description: str | None
    status: MasterDataStatus
    created_at: datetime
    updated_at: datetime
