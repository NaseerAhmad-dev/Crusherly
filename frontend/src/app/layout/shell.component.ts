import { Component, computed, inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatListModule } from '@angular/material/list';
import { MatMenuModule } from '@angular/material/menu';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatToolbarModule } from '@angular/material/toolbar';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

import { AuthService } from '../core/auth/auth.service';

interface NavItem {
  label: string;
  icon: string;
  path: string;
  permissions: string[];
}

const NAV_ITEMS: NavItem[] = [
  { label: 'Dashboard', icon: 'dashboard', path: '/dashboard', permissions: ['dashboard.view'] },
  { label: 'Weighbridge', icon: 'scale', path: '/weighbridge', permissions: ['weighbridge.view'] },
  { label: 'Production', icon: 'factory', path: '/production', permissions: ['production.view'] },
  { label: 'Tenants', icon: 'apartment', path: '/tenants', permissions: ['tenants.view'] },
  { label: 'Users', icon: 'group', path: '/users', permissions: ['users.view'] },
  { label: 'Roles', icon: 'admin_panel_settings', path: '/roles', permissions: ['roles.view'] },
  { label: 'Audit Log', icon: 'history', path: '/audit', permissions: ['audit.view'] },
  { label: 'Settings', icon: 'settings', path: '/settings', permissions: ['settings.view'] },
];

/** The authenticated app shell: toolbar + side nav + routed content. Nav items are filtered by
 * the current user's permissions (Master Build Specification section 36) — the same list serves
 * both platform and tenant users since their permission grants naturally differ. */
@Component({
  selector: 'app-shell',
  standalone: true,
  imports: [
    RouterOutlet,
    RouterLink,
    RouterLinkActive,
    MatToolbarModule,
    MatSidenavModule,
    MatListModule,
    MatIconModule,
    MatButtonModule,
    MatMenuModule,
  ],
  templateUrl: './shell.component.html',
  styleUrl: './shell.component.scss',
})
export class ShellComponent {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  readonly currentUser = this.auth.currentUser;
  readonly visibleNavItems = computed(() =>
    NAV_ITEMS.filter((item) => this.auth.hasAnyPermission(item.permissions)),
  );

  logout(): void {
    this.auth.logout().subscribe(() => this.router.navigate(['/login']));
  }
}
