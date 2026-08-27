import { TestBed } from '@angular/core/testing';
import { ActivatedRouteSnapshot, Router, RouterStateSnapshot, UrlTree, provideRouter } from '@angular/router';

import { AuthService } from '../auth/auth.service';
import { permissionGuard } from './permission.guard';

describe('permissionGuard', () => {
  let permissions: string[];

  beforeEach(() => {
    permissions = [];
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        {
          provide: AuthService,
          useValue: { hasAnyPermission: (codes: string[]) => codes.some((c) => permissions.includes(c)) },
        },
      ],
    });
  });

  it('allows navigation when the user holds the required permission', () => {
    permissions = ['users.view'];
    const result = TestBed.runInInjectionContext(() =>
      permissionGuard('users.view')({} as ActivatedRouteSnapshot, {} as RouterStateSnapshot),
    );
    expect(result).toBe(true);
  });

  it('redirects to /dashboard when the user lacks every required permission', () => {
    const result = TestBed.runInInjectionContext(() =>
      permissionGuard('tenants.view')({} as ActivatedRouteSnapshot, {} as RouterStateSnapshot),
    ) as UrlTree;

    const router = TestBed.inject(Router);
    expect(router.serializeUrl(result)).toBe('/dashboard');
  });

  it('grants access if the user holds ANY of several required permissions', () => {
    permissions = ['roles.view'];
    const result = TestBed.runInInjectionContext(() =>
      permissionGuard('users.view', 'roles.view')({} as ActivatedRouteSnapshot, {} as RouterStateSnapshot),
    );
    expect(result).toBe(true);
  });
});
