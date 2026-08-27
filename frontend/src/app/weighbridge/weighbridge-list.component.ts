import { Component, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

import { AuthService } from '../core/auth/auth.service';
import { WeighbridgeTicket } from '../core/models/weighbridge.model';
import { WeighbridgeService } from '../core/services/weighbridge.service';
import { ConfirmationService } from '../shared/components/confirmation/confirmation.service';
import { DataTableColumn, DataTableComponent } from '../shared/components/data-table/data-table.component';
import { DialogService } from '../shared/components/dialogs/dialog.service';
import { PageChangeEvent, PaginationComponent } from '../shared/components/pagination/pagination.component';
import { StatusBadgeComponent } from '../shared/components/status-badge/status-badge.component';
import { ToastService } from '../shared/components/toast/toast.service';
import { WeighbridgeCompleteDialogComponent } from './weighbridge-complete-dialog.component';
import { WeighbridgeTicketDialogComponent } from './weighbridge-ticket-dialog.component';

const COLUMNS: DataTableColumn[] = [
  { key: 'ticket_number', label: 'Ticket #' },
  { key: 'ticket_type', label: 'Type' },
  { key: 'vehicle_number', label: 'Vehicle' },
  { key: 'material_description', label: 'Material' },
  { key: 'first_weight', label: 'First Wt.' },
  { key: 'net_weight', label: 'Net Wt.' },
  { key: 'status', label: 'Status' },
];

@Component({
  selector: 'app-weighbridge-list',
  standalone: true,
  imports: [MatButtonModule, MatIconModule, DataTableComponent, PaginationComponent, StatusBadgeComponent],
  templateUrl: './weighbridge-list.component.html',
})
export class WeighbridgeListComponent {
  private readonly weighbridgeService = inject(WeighbridgeService);
  private readonly dialogService = inject(DialogService);
  private readonly confirmationService = inject(ConfirmationService);
  private readonly toast = inject(ToastService);
  readonly auth = inject(AuthService);

  readonly columns = COLUMNS;
  readonly rows = signal<WeighbridgeTicket[]>([]);
  readonly totalItems = signal(0);
  readonly loading = signal(true);
  readonly page = signal(1);
  readonly pageSize = signal(20);

  constructor() {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.weighbridgeService.list(this.page(), this.pageSize()).subscribe({
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
      .open<WeighbridgeTicketDialogComponent, undefined, boolean>(WeighbridgeTicketDialogComponent, undefined, {
        width: '520px',
      })
      .subscribe((saved) => {
        if (saved) {
          this.load();
        }
      });
  }

  openCompleteDialog(ticket: WeighbridgeTicket): void {
    this.dialogService
      .open<WeighbridgeCompleteDialogComponent, WeighbridgeTicket, boolean>(
        WeighbridgeCompleteDialogComponent,
        ticket,
        { width: '420px' },
      )
      .subscribe((saved) => {
        if (saved) {
          this.load();
        }
      });
  }

  cancel(ticket: WeighbridgeTicket): void {
    this.confirmationService
      .confirm({
        title: 'Cancel ticket',
        message: `Cancel ticket ${ticket.ticket_number}? This cannot be undone.`,
        confirmLabel: 'Cancel ticket',
        destructive: true,
      })
      .subscribe((confirmed) => {
        if (!confirmed) {
          return;
        }
        this.weighbridgeService.cancel(ticket.id).subscribe(() => {
          this.toast.success('Ticket cancelled.');
          this.load();
        });
      });
  }
}
