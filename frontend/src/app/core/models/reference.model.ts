/** Read-only master/reference data used to populate pickers on business-module forms. */

export interface Unit {
  id: string;
  category_id: string;
  code: string;
  name: string;
  symbol: string;
}

export type OrganizationUnitType = 'BUSINESS_UNIT' | 'PLANT' | 'SITE' | 'DEPARTMENT';

export interface OrganizationUnit {
  id: string;
  name: string;
  code: string;
  unit_type: OrganizationUnitType;
  parent_id: string | null;
}
