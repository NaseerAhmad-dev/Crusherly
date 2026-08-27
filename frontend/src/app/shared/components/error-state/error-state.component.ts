import { Component, input, output } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-error-state',
  standalone: true,
  imports: [MatButtonModule, MatIconModule],
  template: `
    <div class="error-state">
      <mat-icon aria-hidden="true">error_outline</mat-icon>
      <p>{{ message() }}</p>
      @if (retryable()) {
        <button mat-stroked-button type="button" (click)="retry.emit()">Retry</button>
      }
    </div>
  `,
  styles: [
    `
      .error-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 8px;
        padding: 48px 24px;
        color: var(--app-status-danger);
        text-align: center;
      }
      .error-state mat-icon {
        font-size: 32px;
        width: 32px;
        height: 32px;
      }
    `,
  ],
})
export class ErrorStateComponent {
  readonly message = input('Something went wrong.');
  readonly retryable = input(true);
  readonly retry = output<void>();
}
