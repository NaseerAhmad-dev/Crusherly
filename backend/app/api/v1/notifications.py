import math
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.common import Page, PageMeta, SuccessResponse
from app.schemas.notification import NotificationResponse
from app.security.dependencies import require_authenticated_user
from app.security.security_context import SecurityContext
from app.services import notification_service

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=Page[NotificationResponse])
async def list_my_notifications(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    unread_only: bool = Query(default=False),
    context: SecurityContext = Depends(require_authenticated_user),
    session: AsyncSession = Depends(get_db),
):
    notifications, total = await notification_service.list_for_user(
        session, context.user.id, page, page_size, unread_only
    )
    return Page(
        data=[NotificationResponse.model_validate(n) for n in notifications],
        meta=PageMeta(
            page=page,
            page_size=page_size,
            total_items=total,
            total_pages=max(1, math.ceil(total / page_size)),
        ),
    )


@router.post("/{notification_id}/read", response_model=SuccessResponse[NotificationResponse])
async def mark_notification_read(
    notification_id: uuid.UUID,
    context: SecurityContext = Depends(require_authenticated_user),
    session: AsyncSession = Depends(get_db),
):
    notification = await notification_service.mark_read(session, context.user.id, notification_id)
    return SuccessResponse(data=NotificationResponse.model_validate(notification))
