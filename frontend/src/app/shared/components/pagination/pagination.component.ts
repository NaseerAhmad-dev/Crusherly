import { Component, input, output } from '@angular/core';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';

export interface PageChangeEvent {
  page: number;
  pageSize: number;
}

/** Wraps MatPaginator to speak the backend's 1-based `page` (MatPaginator's pageIndex is 0-based). */
@Component({
  selector: 'app-pagination',
  standalone: true,
  imports: [MatPaginatorModule],
  template: `
    <mat-paginator
      [length]="totalItems()"
      [pageSize]="pageSize()"
      [pageIndex]="page() - 1"
      [pageSizeOptions]="[10, 20, 50, 100]"
      (page)="onPage($event)"
    />
  `,
})
export class PaginationComponent {
  readonly page = input(1);
  readonly pageSize = input(20);
  readonly totalItems = input(0);
  readonly pageChange = output<PageChangeEvent>();

  onPage(event: PageEvent): void {
    this.pageChange.emit({ page: event.pageIndex + 1, pageSize: event.pageSize });
  }
}
