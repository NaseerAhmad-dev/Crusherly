"""Shared enums used across Phase 0 models."""

import enum


class TenantStatus(enum.StrEnum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    INACTIVE = "INACTIVE"


class UserStatus(enum.StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    LOCKED = "LOCKED"


class ScopeLevel(enum.StrEnum):
    """Answers 'where' a permission applies. Ordered broadest to narrowest."""

    PLATFORM = "PLATFORM"
    TENANT = "TENANT"
    BUSINESS_UNIT = "BUSINESS_UNIT"
    PLANT = "PLANT"
    SITE = "SITE"
    DEPARTMENT = "DEPARTMENT"


class OrganizationUnitType(enum.StrEnum):
    BUSINESS_UNIT = "BUSINESS_UNIT"
    PLANT = "PLANT"
    SITE = "SITE"
    DEPARTMENT = "DEPARTMENT"


class RecordStatus(enum.StrEnum):
    """Generic controlled-state lifecycle for master data / documents.

    Individual modules may define their own transition rules on top of this shared vocabulary
    (see docs/workflows.md); this enum only fixes the shared set of names so status values are
    consistent platform-wide.
    """

    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"
    CLOSED = "CLOSED"


class MasterDataStatus(enum.StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class AuditAction(enum.StrEnum):
    LOGIN = "LOGIN"
    LOGIN_FAILED = "LOGIN_FAILED"
    LOGOUT = "LOGOUT"
    USER_CREATED = "USER_CREATED"
    USER_UPDATED = "USER_UPDATED"
    USER_DISABLED = "USER_DISABLED"
    ROLE_CREATED = "ROLE_CREATED"
    ROLE_UPDATED = "ROLE_UPDATED"
    ROLE_DELETED = "ROLE_DELETED"
    PERMISSION_CHANGED = "PERMISSION_CHANGED"
    TENANT_CREATED = "TENANT_CREATED"
    TENANT_UPDATED = "TENANT_UPDATED"
    TENANT_SUSPENDED = "TENANT_SUSPENDED"
    SETTINGS_CHANGED = "SETTINGS_CHANGED"
    WEIGHBRIDGE_TICKET_CREATED = "WEIGHBRIDGE_TICKET_CREATED"
    WEIGHBRIDGE_TICKET_COMPLETED = "WEIGHBRIDGE_TICKET_COMPLETED"
    WEIGHBRIDGE_TICKET_CANCELLED = "WEIGHBRIDGE_TICKET_CANCELLED"
    PRODUCTION_ENTRY_CREATED = "PRODUCTION_ENTRY_CREATED"
    PRODUCTION_ENTRY_SUBMITTED = "PRODUCTION_ENTRY_SUBMITTED"
    MASTER_DATA_CREATED = "MASTER_DATA_CREATED"
    MASTER_DATA_UPDATED = "MASTER_DATA_UPDATED"
    MASTER_DATA_DEACTIVATED = "MASTER_DATA_DEACTIVATED"
    PRODUCTION_ENTRY_CANCELLED = "PRODUCTION_ENTRY_CANCELLED"


class WorkflowAction(enum.StrEnum):
    SUBMIT = "SUBMIT"
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    RETURN = "RETURN"
    CANCEL = "CANCEL"


class NotificationChannel(enum.StrEnum):
    IN_APP = "IN_APP"
    EMAIL = "EMAIL"
    SMS = "SMS"
    PUSH = "PUSH"
    WHATSAPP = "WHATSAPP"


class WeighbridgeTicketType(enum.StrEnum):
    """Whether material is coming into the plant (e.g. a raw-material purchase) or leaving it
    (e.g. a finished-aggregate sale)."""

    INBOUND = "INBOUND"
    OUTBOUND = "OUTBOUND"


class WeighbridgeTicketStatus(enum.StrEnum):
    """A ticket is OPEN after the first weighment, COMPLETED once the second weighment closes it
    out, or CANCELLED (e.g. the vehicle left without loading)."""

    OPEN = "OPEN"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class ProductionShift(enum.StrEnum):
    DAY = "DAY"
    NIGHT = "NIGHT"


class ProductionEntryStatus(enum.StrEnum):
    """DRAFT while a shift's outputs are still being entered, SUBMITTED once the shift's
    production is finalized (still cancellable by an admin — e.g. a mis-entered shift — but no
    longer editable), or CANCELLED."""

    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    CANCELLED = "CANCELLED"
