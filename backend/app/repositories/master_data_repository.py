"""Generic tenant-scoped CRUD queries for any `CodedMasterDataMixin` + `TenantScopedMixin` model.

One `MasterDataRepository(Model)` instance per entity (see `app/repositories/material_repository.py`
for an example) — instances are stateless, holding only a reference to the model class, so a single
module-level instance is safe to share across requests. This exists so adding a new master-data
entity means instantiating this class, not writing another near-identical set of `select()`
statements (the master spec explicitly warns against duplicating CRUD architecture).
"""

import uuid
from typing import Generic, TypeVar

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

ModelT = TypeVar("ModelT")


class MasterDataRepository(Generic[ModelT]):
    def __init__(self, model: type[ModelT]):
        self.model = model

    def add(self, session: AsyncSession, instance: ModelT) -> None:
        session.add(instance)

    async def get_by_id_in_tenant(
        self, session: AsyncSession, item_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> ModelT | None:
        result = await session.execute(
            select(self.model).where(self.model.id == item_id, self.model.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_by_code_in_tenant(
        self, session: AsyncSession, code: str, tenant_id: uuid.UUID
    ) -> ModelT | None:
        result = await session.execute(
            select(self.model).where(self.model.code == code, self.model.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def list_in_tenant(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        *,
        offset: int,
        limit: int,
        search: str | None = None,
    ) -> tuple[list[ModelT], int]:
        conditions = [self.model.tenant_id == tenant_id]
        if search:
            like = f"%{search}%"
            conditions.append(or_(self.model.code.ilike(like), self.model.name.ilike(like)))

        count_result = await session.execute(
            select(func.count()).select_from(self.model).where(*conditions)
        )
        total = count_result.scalar_one()

        result = await session.execute(
            select(self.model).where(*conditions).order_by(self.model.name).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), total
