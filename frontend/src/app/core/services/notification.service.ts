import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, map } from 'rxjs';

import { environment } from '../../../environments/environment';
import { Page, SuccessResponse } from '../models/common.model';
import { AppNotification } from '../models/notification.model';

@Injectable({ providedIn: 'root' })
export class NotificationService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiBaseUrl}/notifications`;

  list(page: number, pageSize: number, unreadOnly = false): Observable<Page<AppNotification>> {
    const params = new HttpParams()
      .set('page', page)
      .set('page_size', pageSize)
      .set('unread_only', unreadOnly);
    return this.http.get<Page<AppNotification>>(this.baseUrl, { params });
  }

  markRead(id: string): Observable<AppNotification> {
    return this.http
      .post<SuccessResponse<AppNotification>>(`${this.baseUrl}/${id}/read`, {})
      .pipe(map((res) => res.data));
  }
}
