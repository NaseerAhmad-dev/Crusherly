import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';

import { SettingService } from '../core/services/setting.service';
import { ToastService } from '../shared/components/toast/toast.service';

/** Known tenant-configurable settings keys (Master Build Specification section 23). Any other
 * key can still be edited by typing it in — this list is a convenience, not a restriction. */
const KNOWN_KEYS = [
  'currency',
  'timezone',
  'date_format',
  'weight_unit',
  'tax_configuration',
  'document_numbering',
  'approval_limits',
  'notification_preferences',
];

@Component({
  selector: 'app-settings',
  standalone: true,
  imports: [ReactiveFormsModule, MatFormFieldModule, MatInputModule, MatSelectModule, MatButtonModule],
  templateUrl: './settings.component.html',
  styleUrl: './settings.component.scss',
})
export class SettingsComponent {
  private readonly fb = inject(FormBuilder);
  private readonly settingService = inject(SettingService);
  private readonly toast = inject(ToastService);

  readonly knownKeys = KNOWN_KEYS;
  readonly loading = signal(false);
  readonly saving = signal(false);
  readonly loaded = signal(false);
  readonly jsonError = signal<string | null>(null);

  readonly keyControl = this.fb.nonNullable.control('', Validators.required);
  readonly valueForm = this.fb.nonNullable.group({
    value: ['', Validators.required],
  });

  load(): void {
    const key = this.keyControl.value.trim();
    if (!key) {
      return;
    }
    this.loading.set(true);
    this.loaded.set(false);
    this.settingService.get(key).subscribe({
      next: (value) => {
        this.valueForm.controls.value.setValue(JSON.stringify(value ?? null, null, 2));
        this.loaded.set(true);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  save(): void {
    const key = this.keyControl.value.trim();
    if (!key || this.valueForm.invalid) {
      return;
    }
    this.jsonError.set(null);

    let parsed: unknown;
    try {
      parsed = JSON.parse(this.valueForm.getRawValue().value);
    } catch {
      this.jsonError.set('Value must be valid JSON (e.g. "INR", 42, or {"a": 1}).');
      return;
    }

    this.saving.set(true);
    this.settingService.upsert({ key, value: parsed }).subscribe({
      next: () => {
        this.toast.success('Setting saved.');
        this.saving.set(false);
      },
      error: () => this.saving.set(false),
    });
  }
}
