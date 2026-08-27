import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, map } from 'rxjs';

import { environment } from '../../../environments/environment';
import { MessageResponse, Page, SuccessResponse } from '../models/common.model';
import {
  RoleAssignmentRequest,
  User,
  UserCreateRequest,
  UserRoleAssignment,
  UserUpdateRequest,
} from '../models/user.model';

@Injectable({ providedIn: 'root' })
export class UserService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiBaseUrl}/users`;

  list(page: number, pageSize: number, search?: string): Observable<Page<User>> {
    let params = new HttpParams().set('page', page).set('page_size', pageSize);
    if (search) {
      params = params.set('search', search);
    }
    return this.http.get<Page<User>>(this.baseUrl, { params });
  }

  get(id: string): Observable<User> {
    return this.http.get<SuccessResponse<User>>(`${this.baseUrl}/${id}`).pipe(map((res) => res.data));
  }

  create(payload: UserCreateRequest): Observable<User> {
    return this.http.post<SuccessResponse<User>>(this.baseUrl, payload).pipe(map((res) => res.data));
  }

  update(id: string, payload: UserUpdateRequest): Observable<User> {
    return this.http
      .patch<SuccessResponse<User>>(`${this.baseUrl}/${id}`, payload)
      .pipe(map((res) => res.data));
  }

  deactivate(id: string): Observable<MessageResponse> {
    return this.http.delete<MessageResponse>(`${this.baseUrl}/${id}`);
  }

  assignRole(id: string, payload: RoleAssignmentRequest): Observable<UserRoleAssignment> {
    return this.http
      .post<SuccessResponse<UserRoleAssignment>>(`${this.baseUrl}/${id}/role-assignments`, payload)
      .pipe(map((res) => res.data));
  }
}
