from pydantic import BaseModel


class PlatformDashboardResponse(BaseModel):
    total_tenants: int
    active_tenants: int
    total_users: int
    system_status: str


class TenantDashboardResponse(BaseModel):
    total_plants: int
    total_users: int
    active_users: int
