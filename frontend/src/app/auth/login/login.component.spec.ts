import { HttpErrorResponse, provideHttpClient } from '@angular/common/http';
import { Component } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';

import { AuthService } from '../../core/auth/auth.service';
import { CurrentUser } from '../../core/models/auth.model';
import { LoginComponent } from './login.component';

@Component({ selector: 'app-blank-test', template: '' })
class BlankTestComponent {}

const FAKE_USER: CurrentUser = {
  id: '1',
  tenant_id: 'tenant-a',
  email: 'admin@tenanta.example.com',
  first_name: 'Ada',
  last_name: 'Min',
  is_platform_user: false,
  roles: ['TENANT_ADMIN'],
  permissions: [],
};

describe('LoginComponent', () => {
  let fixture: ComponentFixture<LoginComponent>;
  let component: LoginComponent;
  let authServiceStub: { login: (payload: unknown) => ReturnType<AuthService['login']> };
  let receivedPayload: unknown;

  beforeEach(async () => {
    receivedPayload = undefined;
    authServiceStub = {
      login: (payload) => {
        receivedPayload = payload;
        return of(FAKE_USER);
      },
    };

    await TestBed.configureTestingModule({
      imports: [LoginComponent],
      providers: [
        provideHttpClient(),
        provideRouter([{ path: 'dashboard', component: BlankTestComponent }]),
        { provide: AuthService, useValue: authServiceStub },
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { queryParamMap: convertToParamMap({}) } },
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(LoginComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('does not call AuthService.login while the form is invalid', () => {
    component.submit();
    expect(receivedPayload).toBeUndefined();
  });

  it('calls AuthService.login with the entered credentials once the form is valid', () => {
    component.form.setValue({ email: 'admin@tenanta.example.com', password: 'secret123' });
    component.submit();
    expect(receivedPayload).toEqual({ email: 'admin@tenanta.example.com', password: 'secret123' });
  });

  it('shows the backend error message inline on failed login', () => {
    authServiceStub.login = () =>
      throwError(
        () =>
          new HttpErrorResponse({
            status: 401,
            error: {
              success: false,
              error: { code: 'UNAUTHORIZED', message: 'Invalid email or password.', request_id: null },
            },
          }),
      );

    component.form.setValue({ email: 'admin@tenanta.example.com', password: 'wrong' });
    component.submit();

    expect(component.errorMessage()).toBe('Invalid email or password.');
    expect(component.submitting()).toBe(false);
  });
});
