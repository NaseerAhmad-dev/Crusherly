from app.models.enums import AuditAction
from app.repositories.material_repository import (
    material_category_repository,
    material_repository,
    payment_term_repository,
    product_category_repository,
    product_repository,
    tax_code_repository,
)
from app.services.master_data_service import MasterDataAuditActions, MasterDataService

_AUDIT_ACTIONS = MasterDataAuditActions(
    created=AuditAction.MASTER_DATA_CREATED.value,
    updated=AuditAction.MASTER_DATA_UPDATED.value,
    deactivated=AuditAction.MASTER_DATA_DEACTIVATED.value,
)

material_category_service = MasterDataService(
    model=material_category_repository.model,
    repository=material_category_repository,
    resource_type="material_category",
    audit_actions=_AUDIT_ACTIONS,
)

product_category_service = MasterDataService(
    model=product_category_repository.model,
    repository=product_category_repository,
    resource_type="product_category",
    audit_actions=_AUDIT_ACTIONS,
)

tax_code_service = MasterDataService(
    model=tax_code_repository.model,
    repository=tax_code_repository,
    resource_type="tax_code",
    audit_actions=_AUDIT_ACTIONS,
)

payment_term_service = MasterDataService(
    model=payment_term_repository.model,
    repository=payment_term_repository,
    resource_type="payment_term",
    audit_actions=_AUDIT_ACTIONS,
)

material_service = MasterDataService(
    model=material_repository.model,
    repository=material_repository,
    resource_type="material",
    audit_actions=_AUDIT_ACTIONS,
)

product_service = MasterDataService(
    model=product_repository.model,
    repository=product_repository,
    resource_type="product",
    audit_actions=_AUDIT_ACTIONS,
)
