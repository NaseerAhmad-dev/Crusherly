import uuid

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class RoleCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=50, pattern=r"^[A-Z0-9_]+$")
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)
    permission_codes: list[str] = Field(default_factory=list)


class RoleUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)


class RolePermissionsUpdateRequest(BaseModel):
    permission_codes: list[str]


class RoleResponse(ORMModel):
    id: uuid.UUID
    tenant_id: uuid.UUID | None
    code: str
    name: str
    description: str | None
    is_system: bool
    permission_codes: list[str] = Field(default_factory=list)


class PermissionResponse(ORMModel):
    id: uuid.UUID
    code: str
    description: str | None
    module: str
