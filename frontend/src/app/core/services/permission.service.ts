import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, map } from 'rxjs';

import { environment } from '../../../environments/environment';
import { SuccessResponse } from '../models/common.model';
import { Permission } from '../models/role.model';

@Injectable({ providedIn: 'root' })
export class PermissionService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiBaseUrl}/permissions`;

  list(): Observable<Permission[]> {
    return this.http.get<SuccessResponse<Permission[]>>(this.baseUrl).pipe(map((res) => res.data));
  }
}
