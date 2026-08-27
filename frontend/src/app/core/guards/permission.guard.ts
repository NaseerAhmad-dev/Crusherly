import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

import { AuthService } from '../auth/auth.service';

/**
 * Route guard factory: `canActivate: [permissionGuard('users.view')]`.
 * Grants access if the user holds ANY of the given permission codes at any scope (RBAC-only —
 * per-resource scope checks happen server-side; see Master Build Specification section 10/35).
 */
export function permissionGuard(...codes: string[]): CanActivateFn {
  return () => {
    const auth = inject(AuthService);
    const router = inject(Router);

    if (auth.hasAnyPermission(codes)) {
      return true;
    }
    return router.createUrlTree(['/dashboard']);
  };
}
