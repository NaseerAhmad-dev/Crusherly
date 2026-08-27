from app.models.enums import AuditAction
from app.repositories.party_repository import customer_repository, supplier_repository
from app.services.master_data_service import MasterDataAuditActions, MasterDataService

_AUDIT_ACTIONS = MasterDataAuditActions(
    created=AuditAction.MASTER_DATA_CREATED.value,
    updated=AuditAction.MASTER_DATA_UPDATED.value,
    deactivated=AuditAction.MASTER_DATA_DEACTIVATED.value,
)

customer_service = MasterDataService(
    model=customer_repository.model,
    repository=customer_repository,
    resource_type="customer",
    audit_actions=_AUDIT_ACTIONS,
)

supplier_service = MasterDataService(
    model=supplier_repository.model,
    repository=supplier_repository,
    resource_type="supplier",
    audit_actions=_AUDIT_ACTIONS,
)
