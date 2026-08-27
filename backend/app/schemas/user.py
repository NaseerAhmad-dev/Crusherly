import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import UserStatus
from app.schemas.common import ORMModel


class UserCreateRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=30)
    tenant_id: uuid.UUID | None = None  # only honored for platform users creating platform users


class UserUpdateRequest(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=30)
    status: UserStatus | None = None


class UserResponse(ORMModel):
    id: uuid.UUID
    tenant_id: uuid.UUID | None
    email: str
    first_name: str
    last_name: str
    phone: str | None
    status: UserStatus
    is_verified: bool
    is_platform_user: bool
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime


class RoleAssignmentRequest(BaseModel):
    role_id: uuid.UUID
    organization_unit_id: uuid.UUID | None = None


class UserRoleResponse(ORMModel):
    id: uuid.UUID
    role_id: uuid.UUID
    role_code: str
    organization_unit_id: uuid.UUID | None
