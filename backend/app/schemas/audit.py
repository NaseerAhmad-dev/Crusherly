import uuid
from datetime import datetime
from typing import Any

from app.schemas.common import ORMModel


class AuditEventResponse(ORMModel):
    id: uuid.UUID
    tenant_id: uuid.UUID | None
    user_id: uuid.UUID | None
    action: str
    resource_type: str
    resource_id: str | None
    old_data: dict[str, Any] | None
    new_data: dict[str, Any] | None
    ip_address: str | None
    user_agent: str | None
    request_id: str | None
    timestamp: datetime
