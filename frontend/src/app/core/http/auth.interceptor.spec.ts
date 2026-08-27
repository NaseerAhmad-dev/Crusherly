import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { Component } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { firstValueFrom } from 'rxjs';

import { AuthService } from '../auth/auth.service';
import { authInterceptor } from './auth.interceptor';

@Component({ selector: 'app-blank-test', template: '' })
class BlankTestComponent {}

describe('authInterceptor', () => {
  let http: HttpClient;
  let httpMock: HttpTestingController;
  let authService: AuthService;

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([authInterceptor])),
        provideHttpClientTesting(),
        provideRouter([{ path: 'login', component: BlankTestComponent }]),
      ],
    });
    http = TestBed.inject(HttpClient);
    httpMock = TestBed.inject(HttpTestingController);
    authService = TestBed.inject(AuthService);
  });

  afterEach(() => {
    httpMock.verify();
    localStorage.clear();
  });

  it('attaches the bearer token to ordinary requests', () => {
    localStorage.setItem('sc_access_token', 'AT');
    http.get('/api/v1/users').subscribe();
    const req = httpMock.expectOne('/api/v1/users');
    expect(req.request.headers.get('Authorization')).toBe('Bearer AT');
    req.flush({});
  });

  it('does not attach a token to the login request', () => {
    http.post('/api/v1/auth/login', {}).subscribe();
    const req = httpMock.expectOne('/api/v1/auth/login');
    expect(req.request.headers.has('Authorization')).toBe(false);
    req.flush({});
  });

  it('refreshes the token once on a 401 and retries the original request', async () => {
    localStorage.setItem('sc_access_token', 'EXPIRED');
    localStorage.setItem('sc_refresh_token', 'RT');

    const resultPromise = firstValueFrom(http.get('/api/v1/users'));

    httpMock.expectOne('/api/v1/users').flush({ error: 'expired' }, { status: 401, statusText: 'Unauthorized' });

    httpMock.expectOne((req) => req.url.endsWith('/auth/refresh')).flush({
      success: true,
      data: { access_token: 'NEW_AT', refresh_token: 'NEW_RT', token_type: 'bearer', expires_in: 900 },
    });

    const retried = httpMock.expectOne('/api/v1/users');
    expect(retried.request.headers.get('Authorization')).toBe('Bearer NEW_AT');
    retried.flush({ ok: true });

    await resultPromise;
    expect(localStorage.getItem('sc_access_token')).toBe('NEW_AT');
  });

  it('forces the session to expire if the refresh itself fails', async () => {
    localStorage.setItem('sc_access_token', 'EXPIRED');
    localStorage.setItem('sc_refresh_token', 'RT');

    const resultPromise = firstValueFrom(http.get('/api/v1/users')).catch((error: unknown) => error);

    httpMock.expectOne('/api/v1/users').flush({}, { status: 401, statusText: 'Unauthorized' });
    httpMock.expectOne((req) => req.url.endsWith('/auth/refresh')).flush({}, { status: 401, statusText: 'Unauthorized' });

    await resultPromise;
    expect(authService.isAuthenticated()).toBe(false);
    expect(localStorage.getItem('sc_refresh_token')).toBeNull();
  });
});
