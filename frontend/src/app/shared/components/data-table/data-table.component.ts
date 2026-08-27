import { NgTemplateOutlet } from '@angular/common';
import { Component, TemplateRef, contentChild, input, output } from '@angular/core';
import { MatSortModule, Sort } from '@angular/material/sort';
import { MatTableModule } from '@angular/material/table';

import { EmptyStateComponent } from '../empty-state/empty-state.component';
import { LoadingStateComponent } from '../loading-state/loading-state.component';

export interface DataTableColumn {
  key: string;
  label: string;
  sortable?: boolean;
}

/**
 * Generic reusable table used by every list screen (users/roles/tenants/audit/...).
 *
 * Custom cell rendering (e.g. a StatusBadge) is supplied by the consumer via a `#cell` template;
 * a trailing actions column is supplied via a `#actions` template. Loading/empty states are
 * handled here so feature screens don't each reimplement them.
 *
 * Usage:
 * ```html
 * <app-data-table [columns]="columns" [rows]="rows()" [loading]="loading()">
 *   <ng-template #cell let-row let-column="column">
 *     @if (column === 'status') { <app-status-badge [status]="row.status" /> }
 *     @else { {{ row[column] }} }
 *   </ng-template>
 *   <ng-template #actions let-row>
 *     <button mat-icon-button (click)="edit(row)"><mat-icon>edit</mat-icon></button>
 *   </ng-template>
 * </app-data-table>
 * ```
 */
@Component({
  selector: 'app-data-table',
  standalone: true,
  imports: [NgTemplateOutlet, MatTableModule, MatSortModule, LoadingStateComponent, EmptyStateComponent],
  templateUrl: './data-table.component.html',
  styles: [
    `
      .data-table {
        width: 100%;
      }
      .data-table__row {
        cursor: pointer;
      }
      .data-table__row:hover {
        background: var(--mat-sys-surface-container-highest);
      }
    `,
  ],
})
export class DataTableComponent<T extends object> {
  readonly columns = input.required<DataTableColumn[]>();
  readonly rows = input<T[]>([]);
  readonly loading = input(false);
  readonly emptyMessage = input('No records found.');

  readonly sortChange = output<Sort>();
  readonly rowClick = output<T>();

  readonly cellTemplate = contentChild<TemplateRef<{ $implicit: T; column: string }>>('cell');
  readonly actionsTemplate = contentChild<TemplateRef<{ $implicit: T }>>('actions');

  get displayedColumns(): string[] {
    const keys = this.columns().map((column) => column.key);
    return this.actionsTemplate() ? [...keys, 'actions'] : keys;
  }

  onSort(sort: Sort): void {
    this.sortChange.emit(sort);
  }
}
