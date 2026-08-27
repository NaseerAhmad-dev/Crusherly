import { HttpClient, HttpContext } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { Observable, catchError, finalize, map, of, shareReplay, switchMap, tap, throwError } from 'rxjs';

import { environment } from '../../../environments/environment';
import { CurrentUser, LoginRequest, TokenPair } from '../models/auth.model';
import { MessageResponse, SuccessResponse } from '../models/common.model';

const ACCESS_TOKEN_KEY = 'sc_access_token';
const REFRESH_TOKEN_KEY = 'sc_refresh_token';

/**
 * The single source of truth for "who is logged in and what can they do" on the frontend.
 * Every guard, interceptor, and permission check goes through this service rather than reading
 * localStorage or decoding the token directly (Master Build Specification section 35 — frontend
 * authorization is for UX only, the backend remains the security boundary; `currentUser` is
 * always populated from `/auth/me`, never inferred from the JWT payload).
 */
@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);
  private readonly baseUrl = `${environment.apiBaseUrl}/auth`;

  private readonly _currentUser = signal<CurrentUser | null>(null);
  readonly currentUser = this._currentUser.asReadonly();
  readonly isAuthenticated = computed(() => this._currentUser() !== null);

  private refreshInFlight$: Observable<TokenPair> | null = null;

  /** Called once at app startup (see app.config.ts) so a page refresh doesn't lose the session. */
  bootstrap(): Observable<CurrentUser | null> {
    if (!this.getRefreshToken()) {
      return of(null);
    }
    return this.loadCurrentUser().pipe(catchError(() => of(this.clearSession())));
  }

  login(payload: LoginRequest, context?: HttpContext): Observable<CurrentUser> {
    return this.http.post<SuccessResponse<TokenPair>>(`${this.baseUrl}/login`, payload, { context }).pipe(
      tap((res) => this.storeTokens(res.data)),
      switchMap(() => this.loadCurrentUser()),
    );
  }

  logout(): Observable<void> {
    const refreshToken = this.getRefreshToken();
    if (!refreshToken) {
      this.clearSession();
      return of(undefined);
    }
    return this.http.post<MessageResponse>(`${this.baseUrl}/logout`, { refresh_token: refreshToken }).pipe(
      map(() => undefined),
      catchError(() => of(undefined)),
      tap(() => this.clearSession()),
    );
  }

  /** Used by the auth HTTP interceptor to transparently retry a request after a 401. */
  refreshAccessToken(): Observable<TokenPair> {
    if (this.refreshInFlight$) {
      return this.refreshInFlight$;
    }
    const refreshToken = this.getRefreshToken();
    if (!refreshToken) {
      return throwError(() => new Error('No refresh token available.'));
    }
    this.refreshInFlight$ = this.http
      .post<SuccessResponse<TokenPair>>(`${this.baseUrl}/refresh`, { refresh_token: refreshToken })
      .pipe(
        map((res) => res.data),
        tap((pair) => this.storeTokens(pair)),
        shareReplay(1),
        finalize(() => {
          this.refreshInFlight$ = null;
        }),
      );
    return this.refreshInFlight$;
  }

  loadCurrentUser(): Observable<CurrentUser> {
    return this.http
      .get<SuccessResponse<CurrentUser>>(`${this.baseUrl}/me`)
      .pipe(
        map((res) => res.data),
        tap((user) => this._currentUser.set(user)),
      );
  }

  forgotPassword(email: string, context?: HttpContext): Observable<MessageResponse> {
    return this.http.post<MessageResponse>(`${this.baseUrl}/forgot-password`, { email }, { context });
  }

  resetPassword(token: string, newPassword: string, context?: HttpContext): Observable<MessageResponse> {
    return this.http.post<MessageResponse>(
      `${this.baseUrl}/reset-password`,
      { token, new_password: newPassword },
      { context },
    );
  }

  hasPermission(code: string): boolean {
    return this._currentUser()?.permissions.includes(code) ?? false;
  }

  hasAnyPermission(codes: string[]): boolean {
    return codes.length === 0 || codes.some((code) => this.hasPermission(code));
  }

  hasAllPermissions(codes: string[]): boolean {
    return codes.every((code) => this.hasPermission(code));
  }

  getAccessToken(): string | null {
    return localStorage.getItem(ACCESS_TOKEN_KEY);
  }

  getRefreshToken(): string | null {
    return localStorage.getItem(REFRESH_TOKEN_KEY);
  }

  /** Called by the auth interceptor when a token refresh itself fails (session truly expired). */
  forceSessionExpired(): void {
    this.clearSession();
    this.router.navigate(['/login'], { queryParams: { sessionExpired: true } });
  }

  private storeTokens(pair: TokenPair): void {
    localStorage.setItem(ACCESS_TOKEN_KEY, pair.access_token);
    localStorage.setItem(REFRESH_TOKEN_KEY, pair.refresh_token);
  }

  private clearSession(): null {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    this._currentUser.set(null);
    return null;
  }
}
