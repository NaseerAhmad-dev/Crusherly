"""Generic master-data lifecycle: list/get/create/update/deactivate, tenant-scoped, with a
code-uniqueness check on create and an audit event on every write.

This is deliberately not scope-based (unlike `weighbridge_service`/`production_service`) — the
master spec calls master data "tenant-aware and scope-aware *where appropriate*", and a tenant's
material/customer/vehicle list is ordinary reference data any authenticated tenant user with the
right permission can manage, not something that needs per-plant authorization. If a specific
master-data entity later needs plant-level scoping, that entity's router/service can layer
`authorization_service.authorize()` on top of this — nothing here forecloses it.

One `MasterDataService(...)` instance per entity (see `app/services/material_service.py`), each
supplying its own model, repository, resource-type label, and audit actions.
"""

import uuid
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models.enums import MasterDataStatus
from app.repositories.master_data_repository import MasterDataRepository
from app.security.security_context import SecurityContext
from app.services import audit_service

ModelT = TypeVar("ModelT")


@dataclass(frozen=True)
class MasterDataAuditActions:
    created: str
    updated: str
    deactivated: str


class MasterDataService(Generic[ModelT]):
    def __init__(
        self,
        *,
        model: type[ModelT],
        repository: MasterDataRepository[ModelT],
        resource_type: str,
        audit_actions: MasterDataAuditActions,
    ):
        self.model = model
        self.repository = repository
        self.resource_type = resource_type
        self.audit_actions = audit_actions

    async def list(
        self,
        session: AsyncSession,
        context: SecurityContext,
        page: int,
        page_size: int,
        search: str | None,
    ) -> tuple[list[ModelT], int]:
        if context.tenant_id is None:
            raise ForbiddenError(f"Platform users must access {self.resource_type} data through a tenant.")
        return await self.repository.list_in_tenant(
            session, context.tenant_id, offset=(page - 1) * page_size, limit=page_size, search=search
        )

    async def get(self, session: AsyncSession, context: SecurityContext, item_id: uuid.UUID) -> ModelT:
        if context.tenant_id is None:
            raise ForbiddenError(f"Platform users must access {self.resource_type} data through a tenant.")
        item = await self.repository.get_by_id_in_tenant(session, item_id, context.tenant_id)
        if item is None:
            raise NotFoundError(f"{self.resource_type.replace('_', ' ').title()} not found.")
        return item

    async def create(
        self,
        session: AsyncSession,
        context: SecurityContext,
        payload: BaseModel,
        request: Request | None,
    ) -> ModelT:
        if context.tenant_id is None:
            raise ForbiddenError(f"Platform users must access {self.resource_type} data through a tenant.")

        existing = await self.repository.get_by_code_in_tenant(session, payload.code, context.tenant_id)
        if existing is not None:
            raise ConflictError(f"A {self.resource_type.replace('_', ' ')} with this code already exists.")

        instance = self.model(
            tenant_id=context.tenant_id, created_by=context.user.id, **payload.model_dump()
        )
        self.repository.add(session, instance)
        await session.flush()

        await audit_service.record(
            session,
            action=self.audit_actions.created,
            resource_type=self.resource_type,
            resource_id=str(instance.id),
            tenant_id=context.tenant_id,
            user_id=context.user.id,
            new_data=payload.model_dump(mode="json"),
            request=request,
        )
        await session.commit()
        return instance

    async def update(
        self,
        session: AsyncSession,
        context: SecurityContext,
        item_id: uuid.UUID,
        payload: BaseModel,
        request: Request | None,
    ) -> ModelT:
        instance = await self.get(session, context, item_id)
        update_data: dict[str, Any] = payload.model_dump(exclude_unset=True)
        old_data = {key: getattr(instance, key) for key in update_data}

        for key, value in update_data.items():
            setattr(instance, key, value)
        instance.updated_by = context.user.id

        await session.flush()
        await audit_service.record(
            session,
            action=self.audit_actions.updated,
            resource_type=self.resource_type,
            resource_id=str(instance.id),
            tenant_id=context.tenant_id,
            user_id=context.user.id,
            old_data={k: str(v) for k, v in old_data.items()},
            new_data={k: str(v) for k, v in update_data.items()},
            request=request,
        )
        await session.commit()
        return instance

    async def deactivate(
        self,
        session: AsyncSession,
        context: SecurityContext,
        item_id: uuid.UUID,
        request: Request | None,
    ) -> ModelT:
        instance = await self.get(session, context, item_id)
        if instance.status == MasterDataStatus.INACTIVE:
            raise ConflictError(f"This {self.resource_type.replace('_', ' ')} is already inactive.")

        instance.status = MasterDataStatus.INACTIVE
        instance.updated_by = context.user.id
        await session.flush()

        await audit_service.record(
            session,
            action=self.audit_actions.deactivated,
            resource_type=self.resource_type,
            resource_id=str(instance.id),
            tenant_id=context.tenant_id,
            user_id=context.user.id,
            request=request,
        )
        await session.commit()
        return instance
