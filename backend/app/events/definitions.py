"""Domain event payloads (Master Build Specification section 31).

Future business modules add their own events here (ProductionCompleted, StockReceived,
InvoiceCreated, PaymentReceived, MaintenanceCompleted, ...) following the same pattern.
"""

import uuid
from dataclasses import dataclass

from app.events.bus import DomainEvent


@dataclass(frozen=True)
class UserCreated(DomainEvent):
    user_id: uuid.UUID
    tenant_id: uuid.UUID | None
    email: str


@dataclass(frozen=True)
class TenantCreated(DomainEvent):
    tenant_id: uuid.UUID
    code: str


@dataclass(frozen=True)
class RoleChanged(DomainEvent):
    user_id: uuid.UUID
    tenant_id: uuid.UUID | None
    role_code: str


@dataclass(frozen=True)
class DocumentUploaded(DomainEvent):
    attachment_id: uuid.UUID
    tenant_id: uuid.UUID
    entity_type: str
    entity_id: str


@dataclass(frozen=True)
class ApprovalCompleted(DomainEvent):
    workflow_instance_id: uuid.UUID
    tenant_id: uuid.UUID
    final_state: str
