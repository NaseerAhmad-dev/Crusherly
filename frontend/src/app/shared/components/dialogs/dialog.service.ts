import { ComponentType } from '@angular/cdk/portal';
import { Injectable, inject } from '@angular/core';
import { MatDialog, MatDialogConfig } from '@angular/material/dialog';
import { Observable } from 'rxjs';

/** Thin wrapper over MatDialog used by every "open a form/confirmation in a dialog" case in the
 * app, so components depend on one small, mockable service instead of MatDialog directly. */
@Injectable({ providedIn: 'root' })
export class DialogService {
  private readonly dialog = inject(MatDialog);

  open<TComponent, TData = unknown, TResult = unknown>(
    component: ComponentType<TComponent>,
    data?: TData,
    config: MatDialogConfig = {},
  ): Observable<TResult | undefined> {
    const ref = this.dialog.open(component, { width: '480px', autoFocus: false, data, ...config });
    return ref.afterClosed();
  }
}
