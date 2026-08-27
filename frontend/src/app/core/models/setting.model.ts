/** Mirrors backend/app/schemas/setting.py. */

export interface Setting {
  id: string;
  tenant_id: string | null;
  organization_unit_id: string | null;
  module: string | null;
  key: string;
  value: unknown;
}

export interface SettingUpsertRequest {
  key: string;
  value: unknown;
  organization_unit_id?: string | null;
  module?: string | null;
}
