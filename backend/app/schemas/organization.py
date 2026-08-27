import uuid

from app.models.enums import OrganizationUnitType
from app.schemas.common import ORMModel


class OrganizationUnitResponse(ORMModel):
    id: uuid.UUID
    name: str
    code: str
    unit_type: OrganizationUnitType
    parent_id: uuid.UUID | None
