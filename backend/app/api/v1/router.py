from fastapi import APIRouter

from app.api.v1 import (
    attachments,
    audit,
    auth,
    dashboard,
    fleet,
    materials,
    notifications,
    organization_units,
    parties,
    permissions,
    production,
    roles,
    settings,
    tenants,
    units,
    users,
    weighbridge,
)

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(tenants.router)
api_router.include_router(roles.router)
api_router.include_router(permissions.router)
api_router.include_router(audit.router)
api_router.include_router(settings.router)
api_router.include_router(attachments.router)
api_router.include_router(notifications.router)
api_router.include_router(dashboard.router)
api_router.include_router(units.router)
api_router.include_router(organization_units.router)
api_router.include_router(weighbridge.router)
api_router.include_router(production.router)
api_router.include_router(materials.material_categories_router)
api_router.include_router(materials.materials_router)
api_router.include_router(materials.product_categories_router)
api_router.include_router(materials.products_router)
api_router.include_router(materials.tax_codes_router)
api_router.include_router(materials.payment_terms_router)
api_router.include_router(parties.customers_router)
api_router.include_router(parties.suppliers_router)
api_router.include_router(fleet.vehicles_router)
api_router.include_router(fleet.drivers_router)
