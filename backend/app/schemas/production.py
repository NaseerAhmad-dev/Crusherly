import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import ProductionEntryStatus, ProductionShift
from app.schemas.common import ORMModel


class ProductionOutputInput(BaseModel):
    product_description: str = Field(min_length=1, max_length=200)
    quantity: Decimal = Field(gt=0)
    unit_id: uuid.UUID


class ProductionEntryCreateRequest(BaseModel):
    organization_unit_id: uuid.UUID | None = None
    production_date: date
    shift: ProductionShift
    raw_material_description: str = Field(min_length=1, max_length=200)
    raw_material_quantity: Decimal = Field(gt=0)
    raw_material_unit_id: uuid.UUID
    remarks: str | None = None
    outputs: list[ProductionOutputInput] = Field(min_length=1)


class ProductionOutputResponse(ORMModel):
    id: uuid.UUID
    product_description: str
    quantity: Decimal
    unit_id: uuid.UUID


class ProductionEntryResponse(ORMModel):
    id: uuid.UUID
    entry_number: str
    status: ProductionEntryStatus
    organization_unit_id: uuid.UUID | None
    production_date: date
    shift: ProductionShift
    raw_material_description: str
    raw_material_quantity: Decimal
    raw_material_unit_id: uuid.UUID
    remarks: str | None
    outputs: list[ProductionOutputResponse]
    created_at: datetime
    updated_at: datetime
