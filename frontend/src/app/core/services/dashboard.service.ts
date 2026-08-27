import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, map } from 'rxjs';

import { environment } from '../../../environments/environment';
import { SuccessResponse } from '../models/common.model';
import { PlatformDashboard, TenantDashboard } from '../models/dashboard.model';

@Injectable({ providedIn: 'root' })
export class DashboardService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiBaseUrl}/dashboard`;

  platform(): Observable<PlatformDashboard> {
    return this.http
      .get<SuccessResponse<PlatformDashboard>>(`${this.baseUrl}/platform`)
      .pipe(map((res) => res.data));
  }

  tenant(): Observable<TenantDashboard> {
    return this.http
      .get<SuccessResponse<TenantDashboard>>(`${this.baseUrl}/tenant`)
      .pipe(map((res) => res.data));
  }
}
