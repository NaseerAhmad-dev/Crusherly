from app.models.enums import AuditAction
from app.repositories.fleet_repository import driver_repository, vehicle_repository
from app.services.master_data_service import MasterDataAuditActions, MasterDataService

_AUDIT_ACTIONS = MasterDataAuditActions(
    created=AuditAction.MASTER_DATA_CREATED.value,
    updated=AuditAction.MASTER_DATA_UPDATED.value,
    deactivated=AuditAction.MASTER_DATA_DEACTIVATED.value,
)

vehicle_service = MasterDataService(
    model=vehicle_repository.model,
    repository=vehicle_repository,
    resource_type="vehicle",
    audit_actions=_AUDIT_ACTIONS,
)

driver_service = MasterDataService(
    model=driver_repository.model,
    repository=driver_repository,
    resource_type="driver",
    audit_actions=_AUDIT_ACTIONS,
)
