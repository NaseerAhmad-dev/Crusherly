import { Component, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';

import { UserService } from '../core/services/user.service';
import { User, UserStatus } from '../core/models/user.model';
import { ToastService } from '../shared/components/toast/toast.service';

export type UserFormDialogData = { mode: 'create' } | { mode: 'edit'; user: User };

const STATUSES: UserStatus[] = ['ACTIVE', 'INACTIVE', 'LOCKED'];

/** One form shape for both create and edit — email/password only render (and validate) in
 * create mode, status only renders in edit mode — rather than a union-typed FormGroup, which
 * would make the template's `form.controls.x` bindings awkward to type-check. */
@Component({
  selector: 'app-user-form-dialog',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatButtonModule,
  ],
  templateUrl: './user-form-dialog.component.html',
})
export class UserFormDialogComponent {
  private readonly fb = inject(FormBuilder);
  private readonly userService = inject(UserService);
  private readonly toast = inject(ToastService);
  readonly dialogRef = inject(MatDialogRef<UserFormDialogComponent, boolean>);
  readonly data = inject<UserFormDialogData>(MAT_DIALOG_DATA);

  readonly statuses = STATUSES;
  readonly isEdit = this.data.mode === 'edit';
  readonly saving = signal(false);
  readonly title = computed(() => (this.isEdit ? 'Edit User' : 'New User'));

  readonly form = this.fb.nonNullable.group({
    email: [
      { value: this.data.mode === 'edit' ? this.data.user.email : '', disabled: this.isEdit },
      this.isEdit ? [] : [Validators.required, Validators.email],
    ],
    password: ['', this.isEdit ? [] : [Validators.required, Validators.minLength(8)]],
    first_name: [this.data.mode === 'edit' ? this.data.user.first_name : '', Validators.required],
    last_name: [this.data.mode === 'edit' ? this.data.user.last_name : '', Validators.required],
    phone: [this.data.mode === 'edit' ? (this.data.user.phone ?? '') : ''],
    status: [this.data.mode === 'edit' ? this.data.user.status : ('ACTIVE' as UserStatus)],
  });

  submit(): void {
    if (this.form.invalid || this.saving()) {
      this.form.markAllAsTouched();
      return;
    }
    this.saving.set(true);
    const value = this.form.getRawValue();

    const request =
      this.data.mode === 'edit'
        ? this.userService.update(this.data.user.id, {
            first_name: value.first_name,
            last_name: value.last_name,
            phone: value.phone || null,
            status: value.status,
          })
        : this.userService.create({
            email: value.email,
            password: value.password,
            first_name: value.first_name,
            last_name: value.last_name,
            phone: value.phone || null,
          });

    request.subscribe({
      next: () => {
        this.toast.success(this.isEdit ? 'User updated.' : 'User created.');
        this.dialogRef.close(true);
      },
      error: () => this.saving.set(false),
    });
  }
}
