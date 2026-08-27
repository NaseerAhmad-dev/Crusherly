import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, map } from 'rxjs';

import { environment } from '../../../environments/environment';
import { MessageResponse, SuccessResponse } from '../models/common.model';
import {
  Role,
  RoleCreateRequest,
  RolePermissionsUpdateRequest,
  RoleUpdateRequest,
} from '../models/role.model';

@Injectable({ providedIn: 'root' })
export class RoleService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiBaseUrl}/roles`;

  list(): Observable<Role[]> {
    return this.http.get<SuccessResponse<Role[]>>(this.baseUrl).pipe(map((res) => res.data));
  }

  get(id: string): Observable<Role> {
    return this.http.get<SuccessResponse<Role>>(`${this.baseUrl}/${id}`).pipe(map((res) => res.data));
  }

  create(payload: RoleCreateRequest): Observable<Role> {
    return this.http.post<SuccessResponse<Role>>(this.baseUrl, payload).pipe(map((res) => res.data));
  }

  update(id: string, payload: RoleUpdateRequest): Observable<Role> {
    return this.http
      .patch<SuccessResponse<Role>>(`${this.baseUrl}/${id}`, payload)
      .pipe(map((res) => res.data));
  }

  updatePermissions(id: string, payload: RolePermissionsUpdateRequest): Observable<Role> {
    return this.http
      .put<SuccessResponse<Role>>(`${this.baseUrl}/${id}/permissions`, payload)
      .pipe(map((res) => res.data));
  }

  delete(id: string): Observable<MessageResponse> {
    return this.http.delete<MessageResponse>(`${this.baseUrl}/${id}`);
  }
}
