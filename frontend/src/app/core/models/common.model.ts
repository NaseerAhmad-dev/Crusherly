/**
 * Mirrors backend/app/schemas/common.py — every API response uses one of these envelopes.
 *
 * Field names are kept snake_case to match the wire format exactly (the backend has no
 * camelCase conversion layer) rather than introducing a mapping layer for its own sake.
 */

export interface PageMeta {
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
}

export interface Page<T> {
  success: true;
  data: T[];
  meta: PageMeta;
}

export interface SuccessResponse<T> {
  success: true;
  data: T;
}

export interface MessageResponse {
  success: true;
  message: string;
}

export interface ApiErrorBody {
  code: string;
  message: string;
  request_id: string | null;
}

export interface ErrorResponse {
  success: false;
  error: ApiErrorBody;
  details?: unknown;
}
