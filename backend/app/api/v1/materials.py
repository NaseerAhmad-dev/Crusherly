"""Materials, Material Categories, Products, Product Categories, Tax Codes, and Payment Terms —
six master-data entities, each just an instantiation of `build_master_data_router()`."""

from app.api.v1.master_data_router import build_master_data_router
from app.schemas.master_data import MasterDataCreateRequest, MasterDataResponse, MasterDataUpdateRequest
from app.schemas.material import (
    MaterialCreateRequest,
    MaterialResponse,
    MaterialUpdateRequest,
    ProductCreateRequest,
    ProductResponse,
    ProductUpdateRequest,
)
from app.services.material_service import (
    material_category_service,
    material_service,
    payment_term_service,
    product_category_service,
    product_service,
    tax_code_service,
)

material_categories_router = build_master_data_router(
    prefix="/material-categories",
    tags=["material-categories"],
    permission_prefix="material_categories",
    create_schema=MasterDataCreateRequest,
    update_schema=MasterDataUpdateRequest,
    response_schema=MasterDataResponse,
    service=material_category_service,
)

materials_router = build_master_data_router(
    prefix="/materials",
    tags=["materials"],
    permission_prefix="materials",
    create_schema=MaterialCreateRequest,
    update_schema=MaterialUpdateRequest,
    response_schema=MaterialResponse,
    service=material_service,
)

product_categories_router = build_master_data_router(
    prefix="/product-categories",
    tags=["product-categories"],
    permission_prefix="product_categories",
    create_schema=MasterDataCreateRequest,
    update_schema=MasterDataUpdateRequest,
    response_schema=MasterDataResponse,
    service=product_category_service,
)

products_router = build_master_data_router(
    prefix="/products",
    tags=["products"],
    permission_prefix="products",
    create_schema=ProductCreateRequest,
    update_schema=ProductUpdateRequest,
    response_schema=ProductResponse,
    service=product_service,
)

tax_codes_router = build_master_data_router(
    prefix="/tax-codes",
    tags=["tax-codes"],
    permission_prefix="tax_codes",
    create_schema=MasterDataCreateRequest,
    update_schema=MasterDataUpdateRequest,
    response_schema=MasterDataResponse,
    service=tax_code_service,
)

payment_terms_router = build_master_data_router(
    prefix="/payment-terms",
    tags=["payment-terms"],
    permission_prefix="payment_terms",
    create_schema=MasterDataCreateRequest,
    update_schema=MasterDataUpdateRequest,
    response_schema=MasterDataResponse,
    service=payment_term_service,
)
