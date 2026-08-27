/** Mirrors backend/app/schemas/auth.py. */

export interface LoginRequest {
  email: string;
  password: string;
}

export interface ForgotPasswordRequest {
  email: string;
}

export interface ResetPasswordRequest {
  token: string;
  new_password: string;
}

export interface CurrentUser {
  id: string;
  tenant_id: string | null;
  email: string;
  first_name: string;
  last_name: string;
  is_platform_user: boolean;
  roles: string[];
  permissions: string[];
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}
