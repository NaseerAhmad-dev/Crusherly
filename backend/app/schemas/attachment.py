import uuid
from datetime import datetime

from app.schemas.common import ORMModel


class AttachmentResponse(ORMModel):
    id: uuid.UUID
    entity_type: str
    entity_id: str
    file_name: str
    content_type: str
    size: int
    uploaded_by: uuid.UUID
    created_at: datetime


class AttachmentDownloadResponse(ORMModel):
    id: uuid.UUID
    file_name: str
    content_type: str
    access_url: str
