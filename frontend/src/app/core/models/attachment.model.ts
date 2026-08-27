/** Mirrors backend/app/schemas/attachment.py. */

export interface Attachment {
  id: string;
  entity_type: string;
  entity_id: string;
  file_name: string;
  content_type: string;
  size: number;
  uploaded_by: string;
  created_at: string;
}

export interface AttachmentDownload {
  id: string;
  file_name: string;
  content_type: string;
  access_url: string;
}
