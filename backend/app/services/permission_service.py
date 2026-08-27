from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rbac import Permission
from app.repositories import permission_repository


async def list_permissions(session: AsyncSession) -> list[Permission]:
    return await permission_repository.list_all(session)
