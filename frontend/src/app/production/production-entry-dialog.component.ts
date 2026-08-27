import { Component, inject, signal } from '@angular/core';
import { FormArray, FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';

import { ReferenceService } from '../core/services/reference.service';
import { OrganizationUnit, Unit } from '../core/models/reference.model';
import { ProductionShift } from '../core/models/production.model';
import { ProductionService } from '../core/services/production.service';
import { ToastService } from '../shared/components/toast/toast.service';

const SHIFTS: ProductionShift[] = ['DAY', 'NIGHT'];
const QUANTITY_PATTERN = /^\d+(\.\d{1,3})?$/;

/** One shift's crushing run: the raw material consumed plus however many graded products it
 * produced — `outputs` is a FormArray because a real run is almost never a single product. */
@Component({
  selector: 'app-production-entry-dialog',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatIconModule,
    MatButtonModule,
  ],
  templateUrl: './production-entry-dialog.component.html',
  styleUrl: './production-entry-dialog.component.scss',
})
export class ProductionEntryDialogComponent {
  private readonly fb = inject(FormBuilder);
  private readonly referenceService = inject(ReferenceService);
  private readonly productionService = inject(ProductionService);
  private readonly toast = inject(ToastService);
  readonly dialogRef = inject(MatDialogRef<ProductionEntryDialogComponent, boolean>);

  readonly shifts = SHIFTS;
  readonly units = signal<Unit[]>([]);
  readonly organizationUnits = signal<OrganizationUnit[]>([]);
  readonly saving = signal(false);

  readonly form = this.fb.nonNullable.group({
    organization_unit_id: [''],
    production_date: [new Date().toISOString().slice(0, 10), Validators.required],
    shift: ['DAY' as ProductionShift, Validators.required],
    raw_material_description: ['', Validators.required],
    raw_material_quantity: ['', [Validators.required, Validators.pattern(QUANTITY_PATTERN)]],
    raw_material_unit_id: ['', Validators.required],
    remarks: [''],
    outputs: this.fb.array([this.newOutputGroup()]),
  });

  get outputs(): FormArray {
    return this.form.controls.outputs;
  }

  constructor() {
    this.referenceService.units().subscribe((units) => this.units.set(units));
    this.referenceService.organizationUnits().subscribe((units) => this.organizationUnits.set(units));
  }

  private newOutputGroup() {
    return this.fb.nonNullable.group({
      product_description: ['', Validators.required],
      quantity: ['', [Validators.required, Validators.pattern(QUANTITY_PATTERN)]],
      unit_id: ['', Validators.required],
    });
  }

  addOutput(): void {
    this.outputs.push(this.newOutputGroup());
  }

  removeOutput(index: number): void {
    if (this.outputs.length > 1) {
      this.outputs.removeAt(index);
    }
  }

  submit(): void {
    if (this.form.invalid || this.saving()) {
      this.form.markAllAsTouched();
      return;
    }
    this.saving.set(true);
    const value = this.form.getRawValue();
    this.productionService
      .create({
        organization_unit_id: value.organization_unit_id || null,
        production_date: value.production_date,
        shift: value.shift,
        raw_material_description: value.raw_material_description,
        raw_material_quantity: value.raw_material_quantity,
        raw_material_unit_id: value.raw_material_unit_id,
        remarks: value.remarks || null,
        outputs: value.outputs,
      })
      .subscribe({
        next: () => {
          this.toast.success('Production entry created.');
          this.dialogRef.close(true);
        },
        error: () => this.saving.set(false),
      });
  }
}
