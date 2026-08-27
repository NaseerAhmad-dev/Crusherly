"""The resolved security context for one authenticated request.

Built once per request (see app/services/security_context_service.py) from the database — never
from token claims beyond the user id — so a permission or role change takes effect on the very
next request. Every future business module authorizes through this object rather than
implementing its own tenant/permission logic (Master Build Specification section 11).
"""

import uuid
from dataclasses import dataclass, field

from app.models.enums import ScopeLevel
from app.models.user import User


@dataclass(frozen=True)
class PermissionGrant:
    permission_code: str
    scope_level: ScopeLevel
    organization_unit_id: uuid.UUID | None


@dataclass
class SecurityContext:
    user: User
    tenant_id: uuid.UUID | None
    is_platform_user: bool
    role_codes: set[str] = field(default_factory=set)
    grants: list[PermissionGrant] = field(default_factory=list)

    @property
    def permission_codes(self) -> set[str]:
        return {g.permission_code for g in self.grants}

    def has_permission(self, permission_code: str) -> bool:
        """RBAC-only check: does the user hold this permission at ANY scope?

        Use this for coarse checks (e.g. "can this user see the Users menu at all"). Use
        `AuthorizationService.authorize` for checks against a specific resource's scope.
        """
        return permission_code in self.permission_codes

    def grants_for(self, permission_code: str) -> list[PermissionGrant]:
        return [g for g in self.grants if g.permission_code == permission_code]
