import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, map } from 'rxjs';

import { environment } from '../../../environments/environment';
import { Page, SuccessResponse } from '../models/common.model';
import {
  WeighbridgeTicket,
  WeighbridgeTicketCompleteRequest,
  WeighbridgeTicketCreateRequest,
  WeighbridgeTicketStatus,
} from '../models/weighbridge.model';

@Injectable({ providedIn: 'root' })
export class WeighbridgeService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiBaseUrl}/weighbridge/tickets`;

  list(page: number, pageSize: number, status?: WeighbridgeTicketStatus): Observable<Page<WeighbridgeTicket>> {
    let params = new HttpParams().set('page', page).set('page_size', pageSize);
    if (status) {
      params = params.set('status', status);
    }
    return this.http.get<Page<WeighbridgeTicket>>(this.baseUrl, { params });
  }

  create(payload: WeighbridgeTicketCreateRequest): Observable<WeighbridgeTicket> {
    return this.http
      .post<SuccessResponse<WeighbridgeTicket>>(this.baseUrl, payload)
      .pipe(map((res) => res.data));
  }

  complete(id: string, payload: WeighbridgeTicketCompleteRequest): Observable<WeighbridgeTicket> {
    return this.http
      .post<SuccessResponse<WeighbridgeTicket>>(`${this.baseUrl}/${id}/complete`, payload)
      .pipe(map((res) => res.data));
  }

  cancel(id: string): Observable<WeighbridgeTicket> {
    return this.http
      .post<SuccessResponse<WeighbridgeTicket>>(`${this.baseUrl}/${id}/cancel`, {})
      .pipe(map((res) => res.data));
  }
}
