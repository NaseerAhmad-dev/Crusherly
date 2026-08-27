import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { Component } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { firstValueFrom } from 'rxjs';

import { AuthService } from './auth.service';

@Component({ selector: 'app-blank-test', template: '' })
class BlankTestComponent {}

describe('AuthService', () => {
  let service: AuthService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([{ path: 'login', component: BlankTestComponent }]),
      ],
    });
    service = TestBed.inject(AuthService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
    localStorage.clear();
  });

  it('bootstrap resolves to null when no session was ever established', async () => {
    const result = await firstValueFrom(service.bootstrap());
    expect(result).toBeNull();
    expect(service.isAuthenticated()).toBe(false);
  });

  it('login stores the token pair and populates permissions from /auth/me', async () => {
    const loginPromise = firstValueFrom(service.login({ email: 'admin@tenanta.example.com', password: 'x' }));

    httpMock
      .expectOne((req) => req.url.endsWith('/auth/login'))
      .flush({
        success: true,
        data: { access_token: 'AT', refresh_token: 'RT', token_type: 'bearer', expires_in: 900 },
      });
    httpMock.expectOne((req) => req.url.endsWith('/auth/me')).flush({
      success: true,
      data: {
        id: '1',
        tenant_id: 'tenant-a',
        email: 'admin@tenanta.example.com',
        first_name: 'Ada',
        last_name: 'Min',
        is_platform_user: false,
        roles: ['TENANT_ADMIN'],
        permissions: ['users.view', 'users.create'],
      },
    });

    await loginPromise;

    expect(service.isAuthenticated()).toBe(true);
    expect(service.hasPermission('users.view')).toBe(true);
    expect(service.hasPermission('tenants.delete')).toBe(false);
    expect(service.hasAnyPermission(['tenants.delete', 'users.create'])).toBe(true);
    expect(service.hasAllPermissions(['users.view', 'users.create'])).toBe(true);
    expect(service.hasAllPermissions(['users.view', 'tenants.delete'])).toBe(false);
    expect(localStorage.getItem('sc_access_token')).toBe('AT');
  });

  it('logout clears the stored session even if the server call fails', async () => {
    localStorage.setItem('sc_refresh_token', 'RT');

    const logoutPromise = firstValueFrom(service.logout());
    httpMock.expectOne((req) => req.url.endsWith('/auth/logout')).flush('boom', { status: 500, statusText: 'Error' });
    await logoutPromise;

    expect(service.isAuthenticated()).toBe(false);
    expect(localStorage.getItem('sc_refresh_token')).toBeNull();
    expect(localStorage.getItem('sc_access_token')).toBeNull();
  });

  it('forceSessionExpired clears the session (used after a failed token refresh)', () => {
    localStorage.setItem('sc_access_token', 'AT');
    localStorage.setItem('sc_refresh_token', 'RT');

    service.forceSessionExpired();

    expect(service.isAuthenticated()).toBe(false);
    expect(localStorage.getItem('sc_access_token')).toBeNull();
  });
});
