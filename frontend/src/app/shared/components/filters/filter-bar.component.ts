import { Component } from '@angular/core';

/** Generic slot for a row of filter controls above a DataTable — content-projected so each
 * feature area supplies its own filter controls (status dropdown, date range, ...). */
@Component({
  selector: 'app-filter-bar',
  standalone: true,
  template: `<div class="filter-bar"><ng-content></ng-content></div>`,
  styles: [
    `
      .filter-bar {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 12px;
        margin-bottom: 16px;
      }
    `,
  ],
})
export class FilterBarComponent {}
