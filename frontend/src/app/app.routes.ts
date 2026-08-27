import { Routes } from '@angular/router';

import { authGuard } from './core/guards/auth.guard';
import { permissionGuard } from './core/guards/permission.guard';

export const routes: Routes = [
  {
    path: 'login',
    loadComponent: () => import('./auth/login/login.component').then((m) => m.LoginComponent),
  },
  {
    path: 'forgot-password',
    loadComponent: () =>
      import('./auth/forgot-password/forgot-password.component').then((m) => m.ForgotPasswordComponent),
  },
  {
    path: 'reset-password',
    loadComponent: () =>
      import('./auth/reset-password/reset-password.component').then((m) => m.ResetPasswordComponent),
  },
  {
    path: '',
    loadComponent: () => import('./layout/shell.component').then((m) => m.ShellComponent),
    canActivate: [authGuard],
    children: [
      { path: '', pathMatch: 'full', redirectTo: 'dashboard' },
      {
        path: 'dashboard',
        loadComponent: () => import('./dashboard/dashboard.component').then((m) => m.DashboardComponent),
        canActivate: [permissionGuard('dashboard.view')],
      },
      {
        path: 'users',
        loadComponent: () => import('./users/users-list.component').then((m) => m.UsersListComponent),
        canActivate: [permissionGuard('users.view')],
      },
      {
        path: 'roles',
        loadComponent: () => import('./roles/roles-list.component').then((m) => m.RolesListComponent),
        canActivate: [permissionGuard('roles.view')],
      },
      {
        path: 'tenants',
        loadComponent: () => import('./tenants/tenants-list.component').then((m) => m.TenantsListComponent),
        canActivate: [permissionGuard('tenants.view')],
      },
      {
        path: 'weighbridge',
        loadComponent: () =>
          import('./weighbridge/weighbridge-list.component').then((m) => m.WeighbridgeListComponent),
        canActivate: [permissionGuard('weighbridge.view')],
      },
      {
        path: 'production',
        loadComponent: () =>
          import('./production/production-list.component').then((m) => m.ProductionListComponent),
        canActivate: [permissionGuard('production.view')],
      },
      {
        path: 'audit',
        loadComponent: () => import('./audit/audit-list.component').then((m) => m.AuditListComponent),
        canActivate: [permissionGuard('audit.view')],
      },
      {
        path: 'settings',
        loadComponent: () => import('./settings/settings.component').then((m) => m.SettingsComponent),
        canActivate: [permissionGuard('settings.view')],
      },
    ],
  },
  { path: '**', redirectTo: 'dashboard' },
];
