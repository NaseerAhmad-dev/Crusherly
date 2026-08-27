import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import TenantStatus
from app.schemas.common import ORMModel


class TenantCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    code: str = Field(min_length=1, max_length=50)
    slug: str = Field(min_length=1, max_length=80, pattern=r"^[a-z0-9-]+$")
    timezone: str = "Asia/Kolkata"
    currency: str = "INR"
    admin_email: str
    admin_password: str = Field(min_length=8, max_length=128)
    admin_first_name: str = Field(min_length=1, max_length=100)
    admin_last_name: str = Field(min_length=1, max_length=100)


class TenantUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    timezone: str | None = None
    currency: str | None = None


class TenantResponse(ORMModel):
    id: uuid.UUID
    name: str
    code: str
    slug: str
    status: TenantStatus
    timezone: str
    currency: str
    created_at: datetime
    updated_at: datetime
