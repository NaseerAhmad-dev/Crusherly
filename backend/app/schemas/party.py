import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import MasterDataStatus
from app.schemas.common import ORMModel


class PartyCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    contact_name: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=30)
    email: str | None = Field(default=None, max_length=320)
    address: str | None = Field(default=None, max_length=500)
    tax_id: str | None = Field(default=None, max_length=50)


class PartyUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    status: MasterDataStatus | None = None
    contact_name: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=30)
    email: str | None = Field(default=None, max_length=320)
    address: str | None = Field(default=None, max_length=500)
    tax_id: str | None = Field(default=None, max_length=50)


class PartyResponse(ORMModel):
    id: uuid.UUID
    code: str
    name: str
    description: str | None
    status: MasterDataStatus
    contact_name: str | None
    phone: str | None
    email: str | None
    address: str | None
    tax_id: str | None
    created_at: datetime
    updated_at: datetime
