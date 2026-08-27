import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, switchMap, throwError } from 'rxjs';

import { AuthService } from '../auth/auth.service';

/** Requests to these paths never carry (or need) a bearer token. */
const AUTH_FREE_PATHS = ['/auth/login', '/auth/refresh', '/auth/forgot-password', '/auth/reset-password'];

/**
 * Attaches the bearer access token to every other request, and on a 401 attempts exactly one
 * silent refresh-and-retry before giving up and forcing the user back to /login (Master Build
 * Specification section 8/35). Concurrent 401s share a single in-flight refresh via
 * `AuthService.refreshAccessToken`.
 */
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);
  const isAuthFree = AUTH_FREE_PATHS.some((path) => req.url.includes(path));

  const token = auth.getAccessToken();
  const authedReq = token && !isAuthFree ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } }) : req;

  return next(authedReq).pipe(
    catchError((error: unknown) => {
      if (isAuthFree || !(error instanceof HttpErrorResponse) || error.status !== 401) {
        return throwError(() => error);
      }
      return auth.refreshAccessToken().pipe(
        switchMap((pair) => {
          const retried = req.clone({ setHeaders: { Authorization: `Bearer ${pair.access_token}` } });
          return next(retried);
        }),
        catchError((refreshError: unknown) => {
          auth.forceSessionExpired();
          return throwError(() => refreshError);
        }),
      );
    }),
  );
};
