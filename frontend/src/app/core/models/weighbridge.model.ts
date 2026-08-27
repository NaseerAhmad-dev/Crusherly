/** Mirrors backend/app/schemas/weighbridge.py and app/models/enums.py's weighbridge enums. */

export type WeighbridgeTicketType = 'INBOUND' | 'OUTBOUND';
export type WeighbridgeTicketStatus = 'OPEN' | 'COMPLETED' | 'CANCELLED';

export interface WeighbridgeTicket {
  id: string;
  ticket_number: string;
  ticket_type: WeighbridgeTicketType;
  status: WeighbridgeTicketStatus;
  organization_unit_id: string | null;
  unit_id: string;
  vehicle_number: string;
  driver_name: string | null;
  party_name: string | null;
  material_description: string;
  first_weight: string;
  first_weighed_at: string;
  second_weight: string | null;
  second_weighed_at: string | null;
  net_weight: string | null;
  remarks: string | null;
  created_at: string;
  updated_at: string;
}

export interface WeighbridgeTicketCreateRequest {
  organization_unit_id: string | null;
  unit_id: string;
  ticket_type: WeighbridgeTicketType;
  vehicle_number: string;
  driver_name?: string | null;
  party_name?: string | null;
  material_description: string;
  first_weight: string;
  remarks?: string | null;
}

export interface WeighbridgeTicketCompleteRequest {
  second_weight: string;
}
