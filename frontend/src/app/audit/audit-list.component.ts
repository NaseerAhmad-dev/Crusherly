import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';

import { AuditService } from '../core/services/audit.service';
import { AuditEvent } from '../core/models/audit.model';
import { DataTableColumn, DataTableComponent } from '../shared/components/data-table/data-table.component';
import { FilterBarComponent } from '../shared/components/filters/filter-bar.component';
import { PageChangeEvent, PaginationComponent } from '../shared/components/pagination/pagination.component';

const COLUMNS: DataTableColumn[] = [
  { key: 'timestamp', label: 'When' },
  { key: 'action', label: 'Action' },
  { key: 'resource_type', label: 'Resource' },
  { key: 'resource_id', label: 'Resource ID' },
  { key: 'user_id', label: 'User' },
];

/** Read-only view over the append-only audit trail (Master Build Specification section 15) —
 * tenant-scoped users see their tenant's events, platform users see the platform-wide trail,
 * exactly as GET /api/v1/audit already partitions server-side. */
@Component({
  selector: 'app-audit-list',
  standalone: true,
  imports: [ReactiveFormsModule, MatFormFieldModule, MatInputModule, MatButtonModule, DataTableComponent, FilterBarComponent, PaginationComponent],
  templateUrl: './audit-list.component.html',
  styles: [
    `
      .audit-filters {
        display: flex;
        align-items: center;
        gap: 12px;
      }
    `,
  ],
})
export class AuditListComponent {
  private readonly auditService = inject(AuditService);
  private readonly fb = inject(FormBuilder);

  readonly columns = COLUMNS;
  readonly rows = signal<AuditEvent[]>([]);
  readonly totalItems = signal(0);
  readonly loading = signal(true);
  readonly page = signal(1);
  readonly pageSize = signal(20);

  readonly filterForm = this.fb.nonNullable.group({
    action: [''],
    resource_type: [''],
  });

  constructor() {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    const { action, resource_type } = this.filterForm.getRawValue();
    this.auditService
      .list(this.page(), this.pageSize(), {
        action: action || undefined,
        resource_type: resource_type || undefined,
      })
      .subscribe({
        next: (result) => {
          this.rows.set(result.data);
          this.totalItems.set(result.meta.total_items);
          this.loading.set(false);
        },
        error: () => this.loading.set(false),
      });
  }

  applyFilters(): void {
    this.page.set(1);
    this.load();
  }

  onPageChange(event: PageChangeEvent): void {
    this.page.set(event.page);
    this.pageSize.set(event.pageSize);
    this.load();
  }
}
