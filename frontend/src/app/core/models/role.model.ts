/** Mirrors backend/app/schemas/role.py. */

export interface Role {
  id: string;
  tenant_id: string | null;
  code: string;
  name: string;
  description: string | null;
  is_system: boolean;
  permission_codes: string[];
}

export interface Permission {
  id: string;
  code: string;
  description: string | null;
  module: string;
}

export interface RoleCreateRequest {
  code: string;
  name: string;
  description?: string | null;
  permission_codes: string[];
}

export interface RoleUpdateRequest {
  name?: string;
  description?: string | null;
}

export interface RolePermissionsUpdateRequest {
  permission_codes: string[];
}
