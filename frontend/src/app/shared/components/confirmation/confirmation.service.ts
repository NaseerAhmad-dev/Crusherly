import { Injectable, inject } from '@angular/core';
import { Observable, map } from 'rxjs';

import { DialogService } from '../dialogs/dialog.service';
import { ConfirmationDialogComponent, ConfirmationDialogData } from './confirmation-dialog.component';

/** `confirmationService.confirm({...}).subscribe(confirmed => ...)` — the reusable
 * "are you sure?" prompt used before destructive actions (deactivate user, delete role, ...). */
@Injectable({ providedIn: 'root' })
export class ConfirmationService {
  private readonly dialogService = inject(DialogService);

  confirm(data: ConfirmationDialogData): Observable<boolean> {
    return this.dialogService
      .open<ConfirmationDialogComponent, ConfirmationDialogData, boolean>(
        ConfirmationDialogComponent,
        data,
        { width: '420px' },
      )
      .pipe(map((result) => result === true));
  }
}
