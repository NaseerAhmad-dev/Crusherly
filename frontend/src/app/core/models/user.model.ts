/** Mirrors backend/app/schemas/user.py and app/models/enums.py::UserStatus. */

export type UserStatus = 'ACTIVE' | 'INACTIVE' | 'LOCKED';

export interface User {
  id: string;
  tenant_id: string | null;
  email: string;
  first_name: string;
  last_name: string;
  phone: string | null;
  status: UserStatus;
  is_verified: boolean;
  is_platform_user: boolean;
  last_login_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface UserCreateRequest {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  phone?: string | null;
  tenant_id?: string | null;
}

export interface UserUpdateRequest {
  first_name?: string;
  last_name?: string;
  phone?: string | null;
  status?: UserStatus;
}

export interface RoleAssignmentRequest {
  role_id: string;
  organization_unit_id?: string | null;
}

export interface UserRoleAssignment {
  id: string;
  role_id: string;
  role_code: string;
  organization_unit_id: string | null;
}
