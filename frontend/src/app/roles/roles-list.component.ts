import { Component, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

import { AuthService } from '../core/auth/auth.service';
import { RoleService } from '../core/services/role.service';
import { Role } from '../core/models/role.model';
import { ConfirmationService } from '../shared/components/confirmation/confirmation.service';
import { DataTableColumn, DataTableComponent } from '../shared/components/data-table/data-table.component';
import { DialogService } from '../shared/components/dialogs/dialog.service';
import { ToastService } from '../shared/components/toast/toast.service';
import { RoleFormDialogComponent, RoleFormDialogData } from './role-form-dialog.component';

const COLUMNS: DataTableColumn[] = [
  { key: 'name', label: 'Name' },
  { key: 'code', label: 'Code' },
  { key: 'description', label: 'Description' },
  { key: 'permission_count', label: 'Permissions' },
  { key: 'kind', label: 'Type' },
];

@Component({
  selector: 'app-roles-list',
  standalone: true,
  imports: [MatButtonModule, MatIconModule, DataTableComponent],
  templateUrl: './roles-list.component.html',
})
export class RolesListComponent {
  private readonly roleService = inject(RoleService);
  private readonly dialogService = inject(DialogService);
  private readonly confirmationService = inject(ConfirmationService);
  private readonly toast = inject(ToastService);
  readonly auth = inject(AuthService);

  readonly columns = COLUMNS;
  readonly rows = signal<(Role & { permission_count: number; kind: string })[]>([]);
  readonly loading = signal(true);

  constructor() {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.roleService.list().subscribe({
      next: (roles) => {
        this.rows.set(
          roles.map((role) => ({
            ...role,
            permission_count: role.permission_codes.length,
            kind: role.is_system ? 'System' : 'Custom',
          })),
        );
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  openCreateDialog(): void {
    this.openDialog({ mode: 'create' });
  }

  openEditDialog(role: Role): void {
    this.openDialog({ mode: 'edit', role });
  }

  delete(role: Role): void {
    if (role.is_system) {
      return;
    }
    this.confirmationService
      .confirm({
        title: 'Delete role',
        message: `Delete the "${role.name}" role? Users holding it will lose its permissions.`,
        confirmLabel: 'Delete',
        destructive: true,
      })
      .subscribe((confirmed) => {
        if (!confirmed) {
          return;
        }
        this.roleService.delete(role.id).subscribe(() => {
          this.toast.success('Role deleted.');
          this.load();
        });
      });
  }

  private openDialog(data: RoleFormDialogData): void {
    this.dialogService
      .open<RoleFormDialogComponent, RoleFormDialogData, boolean>(RoleFormDialogComponent, data, {
        width: '560px',
      })
      .subscribe((saved) => {
        if (saved) {
          this.load();
        }
      });
  }
}
