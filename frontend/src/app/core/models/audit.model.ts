/** Mirrors backend/app/schemas/audit.py. */

export interface AuditEvent {
  id: string;
  tenant_id: string | null;
  user_id: string | null;
  action: string;
  resource_type: string;
  resource_id: string | null;
  old_data: Record<string, unknown> | null;
  new_data: Record<string, unknown> | null;
  ip_address: string | null;
  user_agent: string | null;
  request_id: string | null;
  timestamp: string;
}

export interface AuditEventFilters {
  action?: string;
  resource_type?: string;
  user_id?: string;
  date_from?: string;
  date_to?: string;
}
