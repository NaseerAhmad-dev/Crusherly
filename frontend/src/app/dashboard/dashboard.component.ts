import { Component, computed, inject, signal } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { Observable } from 'rxjs';

import { AuthService } from '../core/auth/auth.service';
import { DashboardService } from '../core/services/dashboard.service';
import { PlatformDashboard, TenantDashboard } from '../core/models/dashboard.model';
import { ErrorStateComponent } from '../shared/components/error-state/error-state.component';
import { LoadingStateComponent } from '../shared/components/loading-state/loading-state.component';

interface DashboardCard {
  label: string;
  value: number | string;
  icon: string;
  tone: 'primary' | 'accent' | 'success';
}

/** Foundation dashboard only (Master Build Specification section 36) — business dashboards
 * (production/sales/inventory/...) are out of scope until Phase 11. */
@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [MatCardModule, MatIconModule, LoadingStateComponent, ErrorStateComponent],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.scss',
})
export class DashboardComponent {
  private readonly auth = inject(AuthService);
  private readonly dashboardService = inject(DashboardService);

  readonly loading = signal(true);
  readonly error = signal(false);
  private readonly platformData = signal<PlatformDashboard | null>(null);
  private readonly tenantData = signal<TenantDashboard | null>(null);

  readonly isPlatformUser = computed(() => this.auth.currentUser()?.is_platform_user ?? false);

  readonly cards = computed<DashboardCard[]>(() => {
    const platform = this.platformData();
    if (platform) {
      return [
        { label: 'Total Tenants', value: platform.total_tenants, icon: 'apartment', tone: 'primary' },
        { label: 'Active Tenants', value: platform.active_tenants, icon: 'check_circle', tone: 'success' },
        { label: 'Total Users', value: platform.total_users, icon: 'group', tone: 'primary' },
        { label: 'System Status', value: platform.system_status, icon: 'monitor_heart', tone: 'accent' },
      ];
    }
    const tenant = this.tenantData();
    if (tenant) {
      return [
        { label: 'Plants', value: tenant.total_plants, icon: 'factory', tone: 'accent' },
        { label: 'Total Users', value: tenant.total_users, icon: 'group', tone: 'primary' },
        { label: 'Active Users', value: tenant.active_users, icon: 'check_circle', tone: 'success' },
      ];
    }
    return [];
  });

  constructor() {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.error.set(false);
    const isPlatform = this.isPlatformUser();
    const request: Observable<PlatformDashboard | TenantDashboard> = isPlatform
      ? this.dashboardService.platform()
      : this.dashboardService.tenant();
    request.subscribe({
      next: (data) => {
        if (isPlatform) {
          this.platformData.set(data as PlatformDashboard);
        } else {
          this.tenantData.set(data as TenantDashboard);
        }
        this.loading.set(false);
      },
      error: () => {
        this.error.set(true);
        this.loading.set(false);
      },
    });
  }
}
