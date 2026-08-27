import { HttpContext, HttpContextToken, HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, throwError } from 'rxjs';

import { ToastService } from '../../shared/components/toast/toast.service';
import { ErrorResponse } from '../models/common.model';

/** Set on a request's HttpContext to suppress the automatic toast (e.g. the login form, which
 * shows the same error inline and would otherwise duplicate it). */
export const SKIP_ERROR_TOAST = new HttpContextToken<boolean>(() => false);

/** Convenience context for the common case of "this request's error is rendered inline by the
 * calling component, don't also toast it" — used by the unauthenticated auth forms. */
export const SILENT_ERROR_CONTEXT = new HttpContext().set(SKIP_ERROR_TOAST, true);

/** Surfaces every other API error as a toast, using the standard error envelope
 * (Master Build Specification section 33) when present. */
export const errorInterceptor: HttpInterceptorFn = (req, next) => {
  const toast = inject(ToastService);

  return next(req).pipe(
    catchError((error: unknown) => {
      if (!req.context.get(SKIP_ERROR_TOAST) && error instanceof HttpErrorResponse) {
        toast.error(extractMessage(error));
      }
      return throwError(() => error);
    }),
  );
};

function extractMessage(error: HttpErrorResponse): string {
  const body = error.error as Partial<ErrorResponse> | null;
  if (body && body.success === false && body.error?.message) {
    return body.error.message;
  }
  if (error.status === 0) {
    return 'Unable to reach the server. Check your connection and try again.';
  }
  return `Request failed (${error.status}).`;
}
