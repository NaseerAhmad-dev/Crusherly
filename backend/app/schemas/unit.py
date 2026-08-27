import uuid

from app.schemas.common import ORMModel


class UnitResponse(ORMModel):
    id: uuid.UUID
    category_id: uuid.UUID
    code: str
    name: str
    symbol: str
