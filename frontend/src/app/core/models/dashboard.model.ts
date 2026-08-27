/** Mirrors backend/app/schemas/dashboard.py. */

export interface PlatformDashboard {
  total_tenants: number;
  active_tenants: number;
  total_users: number;
  system_status: string;
}

export interface TenantDashboard {
  total_plants: number;
  total_users: number;
  active_users: number;
}
