import { Component, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

import { AuthService } from '../core/auth/auth.service';
import { UserService } from '../core/services/user.service';
import { User } from '../core/models/user.model';
import { ConfirmationService } from '../shared/components/confirmation/confirmation.service';
import { DataTableColumn, DataTableComponent } from '../shared/components/data-table/data-table.component';
import { DialogService } from '../shared/components/dialogs/dialog.service';
import { PaginationComponent, PageChangeEvent } from '../shared/components/pagination/pagination.component';
import { SearchBoxComponent } from '../shared/components/search/search-box.component';
import { StatusBadgeComponent } from '../shared/components/status-badge/status-badge.component';
import { ToastService } from '../shared/components/toast/toast.service';
import { UserFormDialogComponent, UserFormDialogData } from './user-form-dialog.component';

const COLUMNS: DataTableColumn[] = [
  { key: 'name', label: 'Name' },
  { key: 'email', label: 'Email' },
  { key: 'status', label: 'Status' },
  { key: 'last_login_at', label: 'Last Login' },
];

@Component({
  selector: 'app-users-list',
  standalone: true,
  imports: [
    MatButtonModule,
    MatIconModule,
    DataTableComponent,
    PaginationComponent,
    SearchBoxComponent,
    StatusBadgeComponent,
  ],
  templateUrl: './users-list.component.html',
})
export class UsersListComponent {
  private readonly userService = inject(UserService);
  private readonly dialogService = inject(DialogService);
  private readonly confirmationService = inject(ConfirmationService);
  private readonly toast = inject(ToastService);
  readonly auth = inject(AuthService);

  readonly columns = COLUMNS;
  readonly rows = signal<(User & { name: string })[]>([]);
  readonly totalItems = signal(0);
  readonly loading = signal(true);
  readonly page = signal(1);
  readonly pageSize = signal(20);
  private search = '';

  constructor() {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.userService.list(this.page(), this.pageSize(), this.search || undefined).subscribe({
      next: (result) => {
        this.rows.set(result.data.map((user) => ({ ...user, name: `${user.first_name} ${user.last_name}` })));
        this.totalItems.set(result.meta.total_items);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  onSearch(term: string): void {
    this.search = term;
    this.page.set(1);
    this.load();
  }

  onPageChange(event: PageChangeEvent): void {
    this.page.set(event.page);
    this.pageSize.set(event.pageSize);
    this.load();
  }

  openCreateDialog(): void {
    this.openDialog({ mode: 'create' });
  }

  openEditDialog(user: User): void {
    this.openDialog({ mode: 'edit', user });
  }

  deactivate(user: User): void {
    this.confirmationService
      .confirm({
        title: 'Deactivate user',
        message: `Deactivate ${user.email}? They will no longer be able to sign in.`,
        confirmLabel: 'Deactivate',
        destructive: true,
      })
      .subscribe((confirmed) => {
        if (!confirmed) {
          return;
        }
        this.userService.deactivate(user.id).subscribe(() => {
          this.toast.success('User deactivated.');
          this.load();
        });
      });
  }

  private openDialog(data: UserFormDialogData): void {
    this.dialogService
      .open<UserFormDialogComponent, UserFormDialogData, boolean>(UserFormDialogComponent, data, {
        width: '480px',
      })
      .subscribe((saved) => {
        if (saved) {
          this.load();
        }
      });
  }
}
