import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, map } from 'rxjs';

import { environment } from '../../../environments/environment';
import { SuccessResponse } from '../models/common.model';
import { OrganizationUnit, Unit } from '../models/reference.model';

/** Read-only lookups for pickers on business-module forms (which unit, which plant, ...). */
@Injectable({ providedIn: 'root' })
export class ReferenceService {
  private readonly http = inject(HttpClient);

  units(): Observable<Unit[]> {
    return this.http
      .get<SuccessResponse<Unit[]>>(`${environment.apiBaseUrl}/units`)
      .pipe(map((res) => res.data));
  }

  organizationUnits(): Observable<OrganizationUnit[]> {
    return this.http
      .get<SuccessResponse<OrganizationUnit[]>>(`${environment.apiBaseUrl}/organization-units`)
      .pipe(map((res) => res.data));
  }
}
