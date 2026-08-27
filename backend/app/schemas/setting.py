import uuid
from typing import Any

from pydantic import BaseModel

from app.schemas.common import ORMModel


class SettingUpsertRequest(BaseModel):
    key: str
    value: Any
    organization_unit_id: uuid.UUID | None = None
    module: str | None = None


class SettingResponse(ORMModel):
    id: uuid.UUID
    tenant_id: uuid.UUID | None
    organization_unit_id: uuid.UUID | None
    module: str | None
    key: str
    value: Any
