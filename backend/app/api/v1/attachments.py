import uuid

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.attachment import AttachmentDownloadResponse, AttachmentResponse
from app.schemas.common import MessageResponse, SuccessResponse
from app.security.dependencies import require_permission
from app.security.security_context import SecurityContext
from app.services import attachment_service

router = APIRouter(prefix="/attachments", tags=["documents"])


@router.post("", response_model=SuccessResponse[AttachmentResponse], status_code=201)
async def upload_attachment(
    request: Request,
    entity_type: str = Form(...),
    entity_id: str = Form(...),
    file: UploadFile = File(...),
    context: SecurityContext = Depends(require_permission("documents.upload")),
    session: AsyncSession = Depends(get_db),
):
    content = await file.read()
    attachment = await attachment_service.upload(
        session,
        context,
        entity_type=entity_type,
        entity_id=entity_id,
        file_name=file.filename or "unnamed",
        content_type=file.content_type or "application/octet-stream",
        content=content,
        request=request,
    )
    return SuccessResponse(data=AttachmentResponse.model_validate(attachment))


@router.get("", response_model=SuccessResponse[list[AttachmentResponse]])
async def list_attachments(
    entity_type: str = Query(...),
    entity_id: str = Query(...),
    context: SecurityContext = Depends(require_permission("documents.view")),
    session: AsyncSession = Depends(get_db),
):
    attachments = await attachment_service.list_for_entity(session, context, entity_type, entity_id)
    return SuccessResponse(data=[AttachmentResponse.model_validate(a) for a in attachments])


@router.get("/{attachment_id}/download", response_model=SuccessResponse[AttachmentDownloadResponse])
async def download_attachment(
    attachment_id: uuid.UUID,
    context: SecurityContext = Depends(require_permission("documents.view")),
    session: AsyncSession = Depends(get_db),
):
    attachment, url = await attachment_service.get_download_url(session, context, attachment_id)
    return SuccessResponse(
        data=AttachmentDownloadResponse(
            id=attachment.id,
            file_name=attachment.file_name,
            content_type=attachment.content_type,
            access_url=url,
        )
    )


@router.delete("/{attachment_id}", response_model=MessageResponse)
async def delete_attachment(
    attachment_id: uuid.UUID,
    request: Request,
    context: SecurityContext = Depends(require_permission("documents.delete")),
    session: AsyncSession = Depends(get_db),
):
    await attachment_service.delete(session, context, attachment_id, request)
    return MessageResponse(message="Attachment deleted.")
