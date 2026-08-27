import { Component, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

import { AuthService } from '../core/auth/auth.service';
import { TenantService } from '../core/services/tenant.service';
import { Tenant } from '../core/models/tenant.model';
import { ConfirmationService } from '../shared/components/confirmation/confirmation.service';
import { DataTableColumn, DataTableComponent } from '../shared/components/data-table/data-table.component';
import { DialogService } from '../shared/components/dialogs/dialog.service';
import { PageChangeEvent, PaginationComponent } from '../shared/components/pagination/pagination.component';
import { StatusBadgeComponent } from '../shared/components/status-badge/status-badge.component';
import { ToastService } from '../shared/components/toast/toast.service';
import { TenantFormDialogComponent } from './tenant-form-dialog.component';

const COLUMNS: DataTableColumn[] = [
  { key: 'name', label: 'Name' },
  { key: 'code', label: 'Code' },
  { key: 'status', label: 'Status' },
  { key: 'timezone', label: 'Timezone' },
  { key: 'currency', label: 'Currency' },
];

@Component({
  selector: 'app-tenants-list',
  standalone: true,
  imports: [MatButtonModule, MatIconModule, DataTableComponent, PaginationComponent, StatusBadgeComponent],
  templateUrl: './tenants-list.component.html',
})
export class TenantsListComponent {
  private readonly tenantService = inject(TenantService);
  private readonly dialogService = inject(DialogService);
  private readonly confirmationService = inject(ConfirmationService);
  private readonly toast = inject(ToastService);
  readonly auth = inject(AuthService);

  readonly columns = COLUMNS;
  readonly rows = signal<Tenant[]>([]);
  readonly totalItems = signal(0);
  readonly loading = signal(true);
  readonly page = signal(1);
  readonly pageSize = signal(20);

  constructor() {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.tenantService.list(this.page(), this.pageSize()).subscribe({
      next: (result) => {
        this.rows.set(result.data);
        this.totalItems.set(result.meta.total_items);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  onPageChange(event: PageChangeEvent): void {
    this.page.set(event.page);
    this.pageSize.set(event.pageSize);
    this.load();
  }

  openCreateDialog(): void {
    this.dialogService
      .open<TenantFormDialogComponent, undefined, boolean>(TenantFormDialogComponent, undefined, {
        width: '520px',
      })
      .subscribe((saved) => {
        if (saved) {
          this.load();
        }
      });
  }

  suspend(tenant: Tenant): void {
    if (tenant.status === 'SUSPENDED') {
      return;
    }
    this.confirmationService
      .confirm({
        title: 'Suspend tenant',
        message: `Suspend "${tenant.name}"? Its users will no longer be able to sign in.`,
        confirmLabel: 'Suspend',
        destructive: true,
      })
      .subscribe((confirmed) => {
        if (!confirmed) {
          return;
        }
        this.tenantService.suspend(tenant.id).subscribe(() => {
          this.toast.success('Tenant suspended.');
          this.load();
        });
      });
  }
}
