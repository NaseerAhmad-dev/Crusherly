import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, map } from 'rxjs';

import { environment } from '../../../environments/environment';
import { SuccessResponse } from '../models/common.model';
import { Setting, SettingUpsertRequest } from '../models/setting.model';

@Injectable({ providedIn: 'root' })
export class SettingService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiBaseUrl}/settings`;

  get(key: string, organizationUnitId?: string, module?: string): Observable<unknown> {
    let params = new HttpParams();
    if (organizationUnitId) {
      params = params.set('organization_unit_id', organizationUnitId);
    }
    if (module) {
      params = params.set('module', module);
    }
    return this.http
      .get<SuccessResponse<{ key: string; value: unknown }>>(`${this.baseUrl}/${key}`, { params })
      .pipe(map((res) => res.data.value));
  }

  upsert(payload: SettingUpsertRequest): Observable<Setting> {
    return this.http.put<SuccessResponse<Setting>>(this.baseUrl, payload).pipe(map((res) => res.data));
  }
}
