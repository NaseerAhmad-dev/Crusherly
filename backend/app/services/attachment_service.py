"""Attachment upload/download/delete, enforcing tenant isolation, size limits, and a permission
gate on delete per Master Build Specification sections 21 and 39.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.core.config import get_settings
from app.core.exceptions import NotFoundError, ValidationAppError
from app.models.attachment import Attachment
from app.repositories import attachment_repository
from app.security.security_context import SecurityContext
from app.services import audit_service, storage_service

settings = get_settings()

_MAX_BYTES = settings.max_upload_size_mb * 1024 * 1024


async def upload(
    session: AsyncSession,
    context: SecurityContext,
    *,
    entity_type: str,
    entity_id: str,
    file_name: str,
    content_type: str,
    content: bytes,
    request: Request | None,
) -> Attachment:
    if context.tenant_id is None:
        raise ValidationAppError("Attachments require a tenant context.")
    if len(content) > _MAX_BYTES:
        raise ValidationAppError(
            f"File exceeds the maximum upload size of {settings.max_upload_size_mb}MB."
        )

    storage_key = storage_service.build_storage_key(
        context.tenant_id, entity_type, entity_id, file_name
    )
    provider = storage_service.get_storage_provider()
    await provider.upload(storage_key, content, content_type)

    attachment = Attachment(
        tenant_id=context.tenant_id,
        entity_type=entity_type,
        entity_id=entity_id,
        file_name=file_name,
        content_type=content_type,
        size=len(content),
        storage_key=storage_key,
        uploaded_by=context.user.id,
    )
    attachment_repository.add(session, attachment)
    await session.flush()

    await audit_service.record(
        session,
        action="DOCUMENT_UPLOADED",
        resource_type="attachment",
        resource_id=str(attachment.id),
        tenant_id=context.tenant_id,
        user_id=context.user.id,
        new_data={"file_name": file_name, "entity_type": entity_type, "entity_id": entity_id},
        request=request,
    )
    await session.commit()
    return attachment


async def list_for_entity(
    session: AsyncSession, context: SecurityContext, entity_type: str, entity_id: str
) -> list[Attachment]:
    if context.tenant_id is None:
        raise ValidationAppError("Attachments require a tenant context.")
    return await attachment_repository.list_for_entity(
        session, context.tenant_id, entity_type, entity_id
    )


async def get_download_url(
    session: AsyncSession, context: SecurityContext, attachment_id: uuid.UUID
) -> tuple[Attachment, str]:
    attachment = await _get_owned(session, context, attachment_id)
    provider = storage_service.get_storage_provider()
    url = await provider.generate_access_url(attachment.storage_key)
    return attachment, url


async def delete(
    session: AsyncSession,
    context: SecurityContext,
    attachment_id: uuid.UUID,
    request: Request | None,
) -> None:
    attachment = await _get_owned(session, context, attachment_id)
    provider = storage_service.get_storage_provider()
    await provider.delete(attachment.storage_key)

    await audit_service.record(
        session,
        action="DOCUMENT_DELETED",
        resource_type="attachment",
        resource_id=str(attachment.id),
        tenant_id=context.tenant_id,
        user_id=context.user.id,
        old_data={"file_name": attachment.file_name},
        request=request,
    )
    await attachment_repository.delete(session, attachment)
    await session.commit()


async def _get_owned(
    session: AsyncSession, context: SecurityContext, attachment_id: uuid.UUID
) -> Attachment:
    if context.tenant_id is None:
        raise ValidationAppError("Attachments require a tenant context.")
    attachment = await attachment_repository.get_by_id_in_tenant(
        session, attachment_id, context.tenant_id
    )
    if attachment is None:
        raise NotFoundError("Attachment not found.")
    return attachment
