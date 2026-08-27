import { Component, computed, input } from '@angular/core';

type BadgeTone = 'success' | 'warning' | 'danger' | 'info' | 'neutral';

const TONE_BY_STATUS: Record<string, BadgeTone> = {
  ACTIVE: 'success',
  APPROVED: 'success',
  COMPLETED: 'success',
  SUBMITTED: 'info',
  OPEN: 'info',
  DRAFT: 'neutral',
  SUSPENDED: 'warning',
  INACTIVE: 'neutral',
  CANCELLED: 'neutral',
  CLOSED: 'neutral',
  LOCKED: 'danger',
  REJECTED: 'danger',
};

/** Colour-coded status chip. Add new status values to TONE_BY_STATUS as later phases introduce
 * them — unknown values fall back to a neutral tone rather than erroring. */
@Component({
  selector: 'app-status-badge',
  standalone: true,
  template: `<span class="status-badge" [class]="'status-badge--' + tone()">{{ status() }}</span>`,
  styles: [
    `
      .status-badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
        letter-spacing: 0.02em;
      }
      .status-badge--success {
        background: var(--app-status-success-bg);
        color: var(--app-status-success);
      }
      .status-badge--warning {
        background: var(--app-status-warning-bg);
        color: var(--app-status-warning);
      }
      .status-badge--danger {
        background: var(--app-status-danger-bg);
        color: var(--app-status-danger);
      }
      .status-badge--info {
        background: var(--app-status-info-bg);
        color: var(--app-status-info);
      }
      .status-badge--neutral {
        background: var(--app-status-neutral-bg);
        color: var(--app-status-neutral);
      }
    `,
  ],
})
export class StatusBadgeComponent {
  readonly status = input.required<string>();
  readonly tone = computed<BadgeTone>(() => TONE_BY_STATUS[this.status()] ?? 'neutral');
}
