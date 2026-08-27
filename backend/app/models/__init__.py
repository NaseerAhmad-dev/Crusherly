"""Import every model module so that:

1. `Base.metadata` is fully populated for Alembic autogenerate.
2. SQLAlchemy can resolve string-based `relationship()` references across modules.

Always add new models here.
"""

from app.core.database import Base  # noqa: F401
from app.models.attachment import Attachment  # noqa: F401
from app.models.audit import AuditEvent  # noqa: F401
from app.models.cost_centre import CostCentre, ProfitCentre  # noqa: F401
from app.models.fiscal_year import FiscalYear  # noqa: F401
from app.models.fleet import Driver, Vehicle  # noqa: F401
from app.models.location import Location  # noqa: F401
from app.models.master_data import MaterialCategory, PaymentTerm, ProductCategory, TaxCode  # noqa: F401
from app.models.material import Material, Product  # noqa: F401
from app.models.notification import Notification  # noqa: F401
from app.models.numbering import DocumentSequence  # noqa: F401
from app.models.organization import OrganizationUnit  # noqa: F401
from app.models.party import Customer, Supplier  # noqa: F401
from app.models.password_reset import PasswordResetToken  # noqa: F401
from app.models.production import ProductionEntry, ProductionOutput  # noqa: F401
from app.models.rbac import Permission, Role, RolePermission, UserRole  # noqa: F401
from app.models.refresh_session import RefreshSession  # noqa: F401
from app.models.scope import ScopeAssignment  # noqa: F401
from app.models.setting import Setting  # noqa: F401
from app.models.tenant import Tenant  # noqa: F401
from app.models.unit import Unit, UnitCategory, UnitConversion  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.weighbridge import WeighbridgeTicket  # noqa: F401
from app.models.workflow import (  # noqa: F401
    ApprovalAction,
    WorkflowDefinition,
    WorkflowInstance,
    WorkflowStepDefinition,
)

__all__ = [
    "Base",
    "Tenant",
    "OrganizationUnit",
    "User",
    "Permission",
    "Role",
    "RolePermission",
    "UserRole",
    "ScopeAssignment",
    "AuditEvent",
    "RefreshSession",
    "PasswordResetToken",
    "DocumentSequence",
    "FiscalYear",
    "WorkflowDefinition",
    "WorkflowStepDefinition",
    "WorkflowInstance",
    "ApprovalAction",
    "Attachment",
    "Notification",
    "Setting",
    "UnitCategory",
    "Unit",
    "UnitConversion",
    "Location",
    "CostCentre",
    "ProfitCentre",
    "WeighbridgeTicket",
    "ProductionEntry",
    "ProductionOutput",
    "MaterialCategory",
    "ProductCategory",
    "TaxCode",
    "PaymentTerm",
    "Material",
    "Product",
    "Customer",
    "Supplier",
    "Vehicle",
    "Driver",
]
