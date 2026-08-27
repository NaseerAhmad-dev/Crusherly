"""Shared API response envelopes: pagination, list wrappers, generic success."""

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PageMeta(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int


class Page[T](BaseModel):
    success: bool = True
    data: list[T]
    meta: PageMeta


class PaginationParams(BaseModel):
    page: int = 1
    page_size: int = 20

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


class SuccessResponse[T](BaseModel):
    success: bool = True
    data: T


class MessageResponse(BaseModel):
    success: bool = True
    message: str
