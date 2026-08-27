import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, map } from 'rxjs';

import { environment } from '../../../environments/environment';
import { Page, SuccessResponse } from '../models/common.model';
import { Tenant, TenantCreateRequest, TenantUpdateRequest } from '../models/tenant.model';

@Injectable({ providedIn: 'root' })
export class TenantService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiBaseUrl}/tenants`;

  list(page: number, pageSize: number): Observable<Page<Tenant>> {
    const params = new HttpParams().set('page', page).set('page_size', pageSize);
    return this.http.get<Page<Tenant>>(this.baseUrl, { params });
  }

  get(id: string): Observable<Tenant> {
    return this.http.get<SuccessResponse<Tenant>>(`${this.baseUrl}/${id}`).pipe(map((res) => res.data));
  }

  create(payload: TenantCreateRequest): Observable<Tenant> {
    return this.http.post<SuccessResponse<Tenant>>(this.baseUrl, payload).pipe(map((res) => res.data));
  }

  update(id: string, payload: TenantUpdateRequest): Observable<Tenant> {
    return this.http
      .patch<SuccessResponse<Tenant>>(`${this.baseUrl}/${id}`, payload)
      .pipe(map((res) => res.data));
  }

  suspend(id: string): Observable<Tenant> {
    return this.http
      .post<SuccessResponse<Tenant>>(`${this.baseUrl}/${id}/suspend`, {})
      .pipe(map((res) => res.data));
  }
}
