import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import WeighbridgeTicketStatus, WeighbridgeTicketType
from app.schemas.common import ORMModel


class WeighbridgeTicketCreateRequest(BaseModel):
    organization_unit_id: uuid.UUID | None = None
    unit_id: uuid.UUID
    ticket_type: WeighbridgeTicketType
    vehicle_number: str = Field(min_length=1, max_length=20)
    driver_name: str | None = Field(default=None, max_length=100)
    party_name: str | None = Field(default=None, max_length=200)
    material_description: str = Field(min_length=1, max_length=200)
    first_weight: Decimal = Field(gt=0)
    remarks: str | None = None


class WeighbridgeTicketCompleteRequest(BaseModel):
    second_weight: Decimal = Field(gt=0)


class WeighbridgeTicketResponse(ORMModel):
    id: uuid.UUID
    ticket_number: str
    ticket_type: WeighbridgeTicketType
    status: WeighbridgeTicketStatus
    organization_unit_id: uuid.UUID | None
    unit_id: uuid.UUID
    vehicle_number: str
    driver_name: str | None
    party_name: str | None
    material_description: str
    first_weight: Decimal
    first_weighed_at: datetime
    second_weight: Decimal | None
    second_weighed_at: datetime | None
    net_weight: Decimal | None
    remarks: str | None
    created_at: datetime
    updated_at: datetime
