/** Mirrors backend/app/schemas/notification.py and app/models/enums.py::NotificationChannel. */

export type NotificationChannel = 'IN_APP' | 'EMAIL' | 'SMS' | 'PUSH' | 'WHATSAPP';

export interface AppNotification {
  id: string;
  channel: NotificationChannel;
  title: string;
  body: string;
  entity_type: string | null;
  entity_id: string | null;
  is_read: boolean;
  read_at: string | null;
  created_at: string;
}
