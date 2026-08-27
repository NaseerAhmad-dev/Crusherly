import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';

import { ReferenceService } from '../core/services/reference.service';
import { OrganizationUnit, Unit } from '../core/models/reference.model';
import { WeighbridgeTicketType } from '../core/models/weighbridge.model';
import { WeighbridgeService } from '../core/services/weighbridge.service';
import { ToastService } from '../shared/components/toast/toast.service';

const TICKET_TYPES: WeighbridgeTicketType[] = ['INBOUND', 'OUTBOUND'];

/** First weighment only — the second weighment (and the net weight it produces) is recorded
 * later via `WeighbridgeTicketCompleteDialogComponent`, mirroring the real workflow: a truck is
 * weighed once on arrival and again once its load has been handled. */
@Component({
  selector: 'app-weighbridge-ticket-dialog',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatButtonModule,
  ],
  templateUrl: './weighbridge-ticket-dialog.component.html',
})
export class WeighbridgeTicketDialogComponent {
  private readonly fb = inject(FormBuilder);
  private readonly referenceService = inject(ReferenceService);
  private readonly weighbridgeService = inject(WeighbridgeService);
  private readonly toast = inject(ToastService);
  readonly dialogRef = inject(MatDialogRef<WeighbridgeTicketDialogComponent, boolean>);

  readonly ticketTypes = TICKET_TYPES;
  readonly units = signal<Unit[]>([]);
  readonly organizationUnits = signal<OrganizationUnit[]>([]);
  readonly saving = signal(false);

  readonly form = this.fb.nonNullable.group({
    organization_unit_id: [''],
    unit_id: ['', Validators.required],
    ticket_type: ['INBOUND' as WeighbridgeTicketType, Validators.required],
    vehicle_number: ['', Validators.required],
    driver_name: [''],
    party_name: [''],
    material_description: ['', Validators.required],
    first_weight: ['', [Validators.required, Validators.pattern(/^\d+(\.\d{1,3})?$/)]],
    remarks: [''],
  });

  constructor() {
    this.referenceService.units().subscribe((units) => this.units.set(units));
    this.referenceService.organizationUnits().subscribe((units) => this.organizationUnits.set(units));
  }

  submit(): void {
    if (this.form.invalid || this.saving()) {
      this.form.markAllAsTouched();
      return;
    }
    this.saving.set(true);
    const value = this.form.getRawValue();
    this.weighbridgeService
      .create({
        organization_unit_id: value.organization_unit_id || null,
        unit_id: value.unit_id,
        ticket_type: value.ticket_type,
        vehicle_number: value.vehicle_number,
        driver_name: value.driver_name || null,
        party_name: value.party_name || null,
        material_description: value.material_description,
        first_weight: value.first_weight,
        remarks: value.remarks || null,
      })
      .subscribe({
        next: () => {
          this.toast.success('Weighbridge ticket created.');
          this.dialogRef.close(true);
        },
        error: () => this.saving.set(false),
      });
  }
}
