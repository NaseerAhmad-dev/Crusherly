import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { firstValueFrom } from 'rxjs';

import { ToastService } from '../../shared/components/toast/toast.service';
import { SILENT_ERROR_CONTEXT, errorInterceptor } from './error.interceptor';

describe('errorInterceptor', () => {
  let http: HttpClient;
  let httpMock: HttpTestingController;
  const toastCalls: string[] = [];

  beforeEach(() => {
    toastCalls.length = 0;
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([errorInterceptor])),
        provideHttpClientTesting(),
        { provide: ToastService, useValue: { error: (message: string) => toastCalls.push(message) } },
      ],
    });
    http = TestBed.inject(HttpClient);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('toasts the backend error message for an unhandled error', async () => {
    const promise = firstValueFrom(http.get('/api/v1/users')).catch((error: unknown) => error);
    httpMock
      .expectOne('/api/v1/users')
      .flush(
        { success: false, error: { code: 'FORBIDDEN', message: 'Nope.', request_id: 'r1' } },
        { status: 403, statusText: 'Forbidden' },
      );
    await promise;
    expect(toastCalls).toEqual(['Nope.']);
  });

  it('does not toast when the request opts out via SILENT_ERROR_CONTEXT', async () => {
    const promise = firstValueFrom(
      http.get('/api/v1/auth/login', { context: SILENT_ERROR_CONTEXT }),
    ).catch((error: unknown) => error);
    httpMock.expectOne('/api/v1/auth/login').flush({}, { status: 422, statusText: 'Unprocessable' });
    await promise;
    expect(toastCalls).toEqual([]);
  });
});
