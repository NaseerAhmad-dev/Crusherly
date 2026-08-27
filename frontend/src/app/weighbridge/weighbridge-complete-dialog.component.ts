import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';

import { WeighbridgeTicket } from '../core/models/weighbridge.model';
import { WeighbridgeService } from '../core/services/weighbridge.service';
import { ToastService } from '../shared/components/toast/toast.service';

@Component({
  selector: 'app-weighbridge-complete-dialog',
  standalone: true,
  imports: [ReactiveFormsModule, MatDialogModule, MatFormFieldModule, MatInputModule, MatButtonModule],
  templateUrl: './weighbridge-complete-dialog.component.html',
})
export class WeighbridgeCompleteDialogComponent {
  private readonly fb = inject(FormBuilder);
  private readonly weighbridgeService = inject(WeighbridgeService);
  private readonly toast = inject(ToastService);
  readonly dialogRef = inject(MatDialogRef<WeighbridgeCompleteDialogComponent, boolean>);
  readonly ticket = inject<WeighbridgeTicket>(MAT_DIALOG_DATA);

  readonly saving = signal(false);

  readonly form = this.fb.nonNullable.group({
    second_weight: ['', [Validators.required, Validators.pattern(/^\d+(\.\d{1,3})?$/)]],
  });

  submit(): void {
    if (this.form.invalid || this.saving()) {
      this.form.markAllAsTouched();
      return;
    }
    this.saving.set(true);
    this.weighbridgeService.complete(this.ticket.id, this.form.getRawValue()).subscribe({
      next: () => {
        this.toast.success('Ticket completed.');
        this.dialogRef.close(true);
      },
      error: () => this.saving.set(false),
    });
  }
}
