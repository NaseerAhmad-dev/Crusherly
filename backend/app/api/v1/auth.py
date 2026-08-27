from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.auth import (
    CurrentUserResponse,
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    ResetPasswordRequest,
    TokenPairResponse,
)
from app.schemas.common import MessageResponse, SuccessResponse
from app.security.dependencies import require_authenticated_user
from app.security.security_context import SecurityContext
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=SuccessResponse[TokenPairResponse])
async def login(payload: LoginRequest, request: Request, session: AsyncSession = Depends(get_db)):
    _user, token_pair = await auth_service.login(
        session, email=payload.email, password=payload.password, request=request
    )
    return SuccessResponse(
        data=TokenPairResponse(
            access_token=token_pair.access_token,
            refresh_token=token_pair.refresh_token,
            expires_in=token_pair.expires_in,
        )
    )


@router.post("/refresh", response_model=SuccessResponse[TokenPairResponse])
async def refresh(
    payload: RefreshRequest, request: Request, session: AsyncSession = Depends(get_db)
):
    token_pair = await auth_service.refresh(
        session, refresh_token=payload.refresh_token, request=request
    )
    return SuccessResponse(
        data=TokenPairResponse(
            access_token=token_pair.access_token,
            refresh_token=token_pair.refresh_token,
            expires_in=token_pair.expires_in,
        )
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(payload: LogoutRequest, session: AsyncSession = Depends(get_db)):
    await auth_service.logout(session, refresh_token=payload.refresh_token)
    return MessageResponse(message="Logged out.")


@router.get("/me", response_model=SuccessResponse[CurrentUserResponse])
async def me(context: SecurityContext = Depends(require_authenticated_user)):
    return SuccessResponse(
        data=CurrentUserResponse(
            id=context.user.id,
            tenant_id=context.tenant_id,
            email=context.user.email,
            first_name=context.user.first_name,
            last_name=context.user.last_name,
            is_platform_user=context.is_platform_user,
            roles=sorted(context.role_codes),
            permissions=sorted(context.permission_codes),
        )
    )


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(payload: ForgotPasswordRequest, session: AsyncSession = Depends(get_db)):
    await auth_service.request_password_reset(session, email=payload.email)
    return MessageResponse(
        message="If an account exists for this email, a reset link has been sent."
    )


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(payload: ResetPasswordRequest, session: AsyncSession = Depends(get_db)):
    await auth_service.reset_password(
        session, token=payload.token, new_password=payload.new_password
    )
    return MessageResponse(message="Password has been reset.")
