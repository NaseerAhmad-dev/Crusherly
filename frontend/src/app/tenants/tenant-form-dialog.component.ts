import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';

import { TenantService } from '../core/services/tenant.service';
import { ToastService } from '../shared/components/toast/toast.service';

/** Creates a tenant and its first Tenant Admin user in one step, mirroring
 * app/schemas/tenant.py::TenantCreateRequest — the backend provisions both atomically. */
@Component({
  selector: 'app-tenant-form-dialog',
  standalone: true,
  imports: [ReactiveFormsModule, MatDialogModule, MatFormFieldModule, MatInputModule, MatButtonModule],
  templateUrl: './tenant-form-dialog.component.html',
})
export class TenantFormDialogComponent {
  private readonly fb = inject(FormBuilder);
  private readonly tenantService = inject(TenantService);
  private readonly toast = inject(ToastService);
  readonly dialogRef = inject(MatDialogRef<TenantFormDialogComponent, boolean>);

  readonly saving = signal(false);

  readonly form = this.fb.nonNullable.group({
    name: ['', Validators.required],
    code: ['', Validators.required],
    slug: ['', [Validators.required, Validators.pattern(/^[a-z0-9-]+$/)]],
    timezone: ['Asia/Kolkata', Validators.required],
    currency: ['INR', Validators.required],
    admin_email: ['', [Validators.required, Validators.email]],
    admin_password: ['', [Validators.required, Validators.minLength(8)]],
    admin_first_name: ['', Validators.required],
    admin_last_name: ['', Validators.required],
  });

  submit(): void {
    if (this.form.invalid || this.saving()) {
      this.form.markAllAsTouched();
      return;
    }
    this.saving.set(true);
    this.tenantService.create(this.form.getRawValue()).subscribe({
      next: () => {
        this.toast.success('Tenant created.');
        this.dialogRef.close(true);
      },
      error: () => this.saving.set(false),
    });
  }
}
