import uuid
from datetime import datetime

from app.models.enums import NotificationChannel
from app.schemas.common import ORMModel


class NotificationResponse(ORMModel):
    id: uuid.UUID
    channel: NotificationChannel
    title: str
    body: str
    entity_type: str | None
    entity_id: str | None
    is_read: bool
    read_at: datetime | None
    created_at: datetime
