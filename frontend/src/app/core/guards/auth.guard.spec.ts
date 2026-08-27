import { TestBed } from '@angular/core/testing';
import { ActivatedRouteSnapshot, Router, RouterStateSnapshot, UrlTree, provideRouter } from '@angular/router';

import { AuthService } from '../auth/auth.service';
import { authGuard } from './auth.guard';

describe('authGuard', () => {
  let isAuthenticated: boolean;

  beforeEach(() => {
    isAuthenticated = false;
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        { provide: AuthService, useValue: { isAuthenticated: () => isAuthenticated } },
      ],
    });
  });

  it('allows navigation when a session is active', () => {
    isAuthenticated = true;
    const result = TestBed.runInInjectionContext(() =>
      authGuard({} as ActivatedRouteSnapshot, { url: '/dashboard' } as RouterStateSnapshot),
    );
    expect(result).toBe(true);
  });

  it('redirects to /login with returnUrl when no session is active', () => {
    const result = TestBed.runInInjectionContext(() =>
      authGuard({} as ActivatedRouteSnapshot, { url: '/users' } as RouterStateSnapshot),
    ) as UrlTree;

    const router = TestBed.inject(Router);
    const serialized = router.serializeUrl(result);
    expect(serialized).toContain('/login');
    expect(serialized).toContain('returnUrl=%2Fusers');
  });
});
