import { Component, ElementRef, input, output, viewChild } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-file-upload',
  standalone: true,
  imports: [MatButtonModule, MatIconModule],
  template: `
    <div class="file-upload">
      <input #fileInput type="file" [accept]="accept()" hidden (change)="onFileChange($event)" />
      <button mat-stroked-button type="button" (click)="browse()">
        <mat-icon aria-hidden="true">attach_file</mat-icon>
        Choose file
      </button>
      @if (selectedFileName) {
        <span class="file-upload__name">{{ selectedFileName }}</span>
      }
    </div>
  `,
  styles: [
    `
      .file-upload {
        display: flex;
        align-items: center;
        gap: 12px;
      }
      .file-upload__name {
        font-size: 13px;
        color: var(--mat-sys-on-surface-variant);
      }
    `,
  ],
})
export class FileUploadComponent {
  readonly accept = input('*/*');
  readonly maxSizeMb = input(25);
  readonly fileSelected = output<File>();
  readonly validationError = output<string>();

  private readonly fileInput = viewChild.required<ElementRef<HTMLInputElement>>('fileInput');
  selectedFileName: string | null = null;

  browse(): void {
    this.fileInput().nativeElement.click();
  }

  onFileChange(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    input.value = '';
    if (!file) {
      return;
    }
    if (file.size > this.maxSizeMb() * 1024 * 1024) {
      this.validationError.emit(`File exceeds the ${this.maxSizeMb()}MB limit.`);
      return;
    }
    this.selectedFileName = file.name;
    this.fileSelected.emit(file);
  }
}
