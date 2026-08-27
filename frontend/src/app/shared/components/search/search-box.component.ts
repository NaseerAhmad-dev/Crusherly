import { Component, DestroyRef, inject, input, output } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { debounceTime, distinctUntilChanged } from 'rxjs';

@Component({
  selector: 'app-search-box',
  standalone: true,
  imports: [ReactiveFormsModule, MatFormFieldModule, MatInputModule, MatIconModule],
  template: `
    <mat-form-field appearance="outline" class="search-box" subscriptSizing="dynamic">
      <mat-icon matPrefix aria-hidden="true">search</mat-icon>
      <input matInput [placeholder]="placeholder()" [formControl]="control" />
    </mat-form-field>
  `,
  styles: [
    `
      .search-box {
        width: 100%;
        max-width: 320px;
      }
    `,
  ],
})
export class SearchBoxComponent {
  readonly placeholder = input('Search…');
  readonly searchChange = output<string>();

  readonly control = new FormControl('', { nonNullable: true });

  constructor() {
    this.control.valueChanges
      .pipe(debounceTime(300), distinctUntilChanged(), takeUntilDestroyed(inject(DestroyRef)))
      .subscribe((value) => this.searchChange.emit(value.trim()));
  }
}
