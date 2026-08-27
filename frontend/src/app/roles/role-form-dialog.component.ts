import { Component, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';

import { PermissionService } from '../core/services/permission.service';
import { RoleService } from '../core/services/role.service';
import { Permission, Role } from '../core/models/role.model';
import { ToastService } from '../shared/components/toast/toast.service';

export type RoleFormDialogData = { mode: 'create' } | { mode: 'edit'; role: Role };

interface PermissionGroup {
  module: string;
  permissions: Permission[];
}

/** Create/edit a role and its permission set in one dialog. On edit, both the role's
 * name/description and its permissions are saved (two calls: PATCH then PUT .../permissions —
 * see role.service.ts) since the backend models them as separate operations. */
@Component({
  selector: 'app-role-form-dialog',
  standalone: true,
  imports: [ReactiveFormsModule, MatDialogModule, MatFormFieldModule, MatInputModule, MatCheckboxModule, MatButtonModule],
  templateUrl: './role-form-dialog.component.html',
  styles: [
    `
      .role-form__group {
        margin-bottom: 12px;
        display: flex;
        flex-direction: column;
        gap: 2px;
      }
      .role-form__group h4 {
        margin: 8px 0 4px;
        text-transform: capitalize;
        color: var(--mat-sys-on-surface-variant);
        font-size: 12px;
      }
      .role-form__notice {
        color: var(--app-status-warning);
        font-size: 12px;
      }
    `,
  ],
})
export class RoleFormDialogComponent {
  private readonly fb = inject(FormBuilder);
  private readonly roleService = inject(RoleService);
  private readonly permissionService = inject(PermissionService);
  private readonly toast = inject(ToastService);
  readonly dialogRef = inject(MatDialogRef<RoleFormDialogComponent, boolean>);
  readonly data = inject<RoleFormDialogData>(MAT_DIALOG_DATA);

  readonly isEdit = this.data.mode === 'edit';
  readonly isSystemRole = this.data.mode === 'edit' && this.data.role.is_system;
  readonly saving = signal(false);
  readonly title = computed(() => (this.isEdit ? 'Edit Role' : 'New Role'));

  readonly permissionGroups = signal<PermissionGroup[]>([]);
  readonly selectedCodes = signal<Set<string>>(
    new Set(this.data.mode === 'edit' ? this.data.role.permission_codes : []),
  );

  readonly form = this.fb.nonNullable.group({
    code: [
      { value: this.data.mode === 'edit' ? this.data.role.code : '', disabled: this.isEdit },
      this.isEdit ? [] : [Validators.required, Validators.pattern(/^[A-Z0-9_]+$/)],
    ],
    name: [this.data.mode === 'edit' ? this.data.role.name : '', Validators.required],
    description: [this.data.mode === 'edit' ? (this.data.role.description ?? '') : ''],
  });

  constructor() {
    this.permissionService.list().subscribe((permissions) => {
      const byModule = new Map<string, Permission[]>();
      for (const permission of permissions) {
        const group = byModule.get(permission.module) ?? [];
        group.push(permission);
        byModule.set(permission.module, group);
      }
      this.permissionGroups.set(
        Array.from(byModule.entries())
          .sort(([a], [b]) => a.localeCompare(b))
          .map(([module, perms]) => ({ module, permissions: perms })),
      );
    });
  }

  isSelected(code: string): boolean {
    return this.selectedCodes().has(code);
  }

  toggle(code: string): void {
    const next = new Set(this.selectedCodes());
    if (next.has(code)) {
      next.delete(code);
    } else {
      next.add(code);
    }
    this.selectedCodes.set(next);
  }

  submit(): void {
    if (this.form.invalid || this.saving()) {
      this.form.markAllAsTouched();
      return;
    }
    this.saving.set(true);
    const value = this.form.getRawValue();
    const permissionCodes = Array.from(this.selectedCodes());
    const data = this.data;

    if (data.mode === 'edit') {
      this.roleService.update(data.role.id, { name: value.name, description: value.description || null }).subscribe({
        next: () => {
          this.roleService.updatePermissions(data.role.id, { permission_codes: permissionCodes }).subscribe({
            next: () => {
              this.toast.success('Role updated.');
              this.dialogRef.close(true);
            },
            error: () => this.saving.set(false),
          });
        },
        error: () => this.saving.set(false),
      });
    } else {
      this.roleService
        .create({ code: value.code, name: value.name, description: value.description || null, permission_codes: permissionCodes })
        .subscribe({
          next: () => {
            this.toast.success('Role created.');
            this.dialogRef.close(true);
          },
          error: () => this.saving.set(false),
        });
    }
  }
}
