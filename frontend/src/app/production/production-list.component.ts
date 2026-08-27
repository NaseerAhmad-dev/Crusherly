import { Component, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

import { AuthService } from '../core/auth/auth.service';
import { ProductionEntry } from '../core/models/production.model';
import { ProductionService } from '../core/services/production.service';
import { ConfirmationService } from '../shared/components/confirmation/confirmation.service';
import { DataTableColumn, DataTableComponent } from '../shared/components/data-table/data-table.component';
import { DialogService } from '../shared/components/dialogs/dialog.service';
import { PageChangeEvent, PaginationComponent } from '../shared/components/pagination/pagination.component';
import { StatusBadgeComponent } from '../shared/components/status-badge/status-badge.component';
import { ToastService } from '../shared/components/toast/toast.service';
import { ProductionEntryDialogComponent } from './production-entry-dialog.component';

const COLUMNS: DataTableColumn[] = [
  { key: 'entry_number', label: 'Entry #' },
  { key: 'production_date', label: 'Date' },
  { key: 'shift', label: 'Shift' },
  { key: 'raw_material_description', label: 'Raw Material' },
  { key: 'outputs', label: 'Outputs' },
  { key: 'status', label: 'Status' },
];

@Component({
  selector: 'app-production-list',
  standalone: true,
  imports: [MatButtonModule, MatIconModule, DataTableComponent, PaginationComponent, StatusBadgeComponent],
  templateUrl: './production-list.component.html',
})
export class ProductionListComponent {
  private readonly productionService = inject(ProductionService);
  private readonly dialogService = inject(DialogService);
  private readonly confirmationService = inject(ConfirmationService);
  private readonly toast = inject(ToastService);
  readonly auth = inject(AuthService);

  readonly columns = COLUMNS;
  readonly rows = signal<ProductionEntry[]>([]);
  readonly totalItems = signal(0);
  readonly loading = signal(true);
  readonly page = signal(1);
  readonly pageSize = signal(20);

  constructor() {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.productionService.list(this.page(), this.pageSize()).subscribe({
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

  outputsSummary(entry: ProductionEntry): string {
    return entry.outputs.map((o) => `${o.product_description}: ${o.quantity}`).join(', ');
  }

  openCreateDialog(): void {
    this.dialogService
      .open<ProductionEntryDialogComponent, undefined, boolean>(ProductionEntryDialogComponent, undefined, {
        width: '640px',
      })
      .subscribe((saved) => {
        if (saved) {
          this.load();
        }
      });
  }

  submit(entry: ProductionEntry): void {
    this.productionService.submit(entry.id).subscribe(() => {
      this.toast.success('Entry submitted.');
      this.load();
    });
  }

  cancel(entry: ProductionEntry): void {
    this.confirmationService
      .confirm({
        title: 'Cancel entry',
        message: `Cancel production entry ${entry.entry_number}? This cannot be undone.`,
        confirmLabel: 'Cancel entry',
        destructive: true,
      })
      .subscribe((confirmed) => {
        if (!confirmed) {
          return;
        }
        this.productionService.cancel(entry.id).subscribe(() => {
          this.toast.success('Entry cancelled.');
          this.load();
        });
      });
  }
}
