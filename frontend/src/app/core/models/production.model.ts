/** Mirrors backend/app/schemas/production.py and app/models/enums.py's production enums. */

export type ProductionShift = 'DAY' | 'NIGHT';
export type ProductionEntryStatus = 'DRAFT' | 'SUBMITTED' | 'CANCELLED';

export interface ProductionOutput {
  id: string;
  product_description: string;
  quantity: string;
  unit_id: string;
}

export interface ProductionEntry {
  id: string;
  entry_number: string;
  status: ProductionEntryStatus;
  organization_unit_id: string | null;
  production_date: string;
  shift: ProductionShift;
  raw_material_description: string;
  raw_material_quantity: string;
  raw_material_unit_id: string;
  remarks: string | null;
  outputs: ProductionOutput[];
  created_at: string;
  updated_at: string;
}

export interface ProductionOutputInput {
  product_description: string;
  quantity: string;
  unit_id: string;
}

export interface ProductionEntryCreateRequest {
  organization_unit_id: string | null;
  production_date: string;
  shift: ProductionShift;
  raw_material_description: string;
  raw_material_quantity: string;
  raw_material_unit_id: string;
  remarks?: string | null;
  outputs: ProductionOutputInput[];
}
