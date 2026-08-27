/** Mirrors backend/app/schemas/tenant.py and app/models/enums.py::TenantStatus. */

export type TenantStatus = 'ACTIVE' | 'SUSPENDED' | 'INACTIVE';

export interface Tenant {
  id: string;
  name: string;
  code: string;
  slug: string;
  status: TenantStatus;
  timezone: string;
  currency: string;
  created_at: string;
  updated_at: string;
}

export interface TenantCreateRequest {
  name: string;
  code: string;
  slug: string;
  timezone: string;
  currency: string;
  admin_email: string;
  admin_password: string;
  admin_first_name: string;
  admin_last_name: string;
}

export interface TenantUpdateRequest {
  name?: string;
  timezone?: string;
  currency?: string;
}
