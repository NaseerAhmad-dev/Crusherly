import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, map } from 'rxjs';

import { environment } from '../../../environments/environment';
import { Attachment, AttachmentDownload } from '../models/attachment.model';
import { MessageResponse, SuccessResponse } from '../models/common.model';

@Injectable({ providedIn: 'root' })
export class AttachmentService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiBaseUrl}/attachments`;

  upload(entityType: string, entityId: string, file: File): Observable<Attachment> {
    const formData = new FormData();
    formData.append('entity_type', entityType);
    formData.append('entity_id', entityId);
    formData.append('file', file);
    return this.http
      .post<SuccessResponse<Attachment>>(this.baseUrl, formData)
      .pipe(map((res) => res.data));
  }

  listForEntity(entityType: string, entityId: string): Observable<Attachment[]> {
    const params = new HttpParams().set('entity_type', entityType).set('entity_id', entityId);
    return this.http
      .get<SuccessResponse<Attachment[]>>(this.baseUrl, { params })
      .pipe(map((res) => res.data));
  }

  getDownloadUrl(id: string): Observable<AttachmentDownload> {
    return this.http
      .get<SuccessResponse<AttachmentDownload>>(`${this.baseUrl}/${id}/download`)
      .pipe(map((res) => res.data));
  }

  delete(id: string): Observable<MessageResponse> {
    return this.http.delete<MessageResponse>(`${this.baseUrl}/${id}`);
  }
}
