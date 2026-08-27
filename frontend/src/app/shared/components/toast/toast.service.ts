import { Injectable, inject } from '@angular/core';
import { MatSnackBar } from '@angular/material/snack-bar';

/** Thin wrapper over MatSnackBar so the rest of the app depends on one small interface. */
@Injectable({ providedIn: 'root' })
export class ToastService {
  private readonly snackBar = inject(MatSnackBar);

  success(message: string): void {
    this.show(message, 'toast-success');
  }

  error(message: string): void {
    this.show(message, 'toast-error', 6000);
  }

  info(message: string): void {
    this.show(message, 'toast-info');
  }

  private show(message: string, panelClass: string, durationMs = 4000): void {
    this.snackBar.open(message, 'Dismiss', {
      duration: durationMs,
      panelClass,
      horizontalPosition: 'end',
      verticalPosition: 'top',
    });
  }
}
