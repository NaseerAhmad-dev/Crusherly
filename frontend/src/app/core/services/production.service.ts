import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, map } from 'rxjs';

import { environment } from '../../../environments/environment';
import { Page, SuccessResponse } from '../models/common.model';
import {
  ProductionEntry,
  ProductionEntryCreateRequest,
  ProductionEntryStatus,
} from '../models/production.model';

@Injectable({ providedIn: 'root' })
export class ProductionService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiBaseUrl}/production/entries`;

  list(
    page: number,
    pageSize: number,
    status?: ProductionEntryStatus,
  ): Observable<Page<ProductionEntry>> {
    let params = new HttpParams().set('page', page).set('page_size', pageSize);
    if (status) {
      params = params.set('status', status);
    }
    return this.http.get<Page<ProductionEntry>>(this.baseUrl, { params });
  }

  create(payload: ProductionEntryCreateRequest): Observable<ProductionEntry> {
    return this.http
      .post<SuccessResponse<ProductionEntry>>(this.baseUrl, payload)
      .pipe(map((res) => res.data));
  }

  submit(id: string): Observable<ProductionEntry> {
    return this.http
      .post<SuccessResponse<ProductionEntry>>(`${this.baseUrl}/${id}/submit`, {})
      .pipe(map((res) => res.data));
  }

  cancel(id: string): Observable<ProductionEntry> {
    return this.http
      .post<SuccessResponse<ProductionEntry>>(`${this.baseUrl}/${id}/cancel`, {})
      .pipe(map((res) => res.data));
  }
}
