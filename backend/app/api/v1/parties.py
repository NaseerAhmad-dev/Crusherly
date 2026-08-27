"""Customers and Suppliers — identical schema shape (see app/schemas/party.py), separate tables
and permissions."""

from app.api.v1.master_data_router import build_master_data_router
from app.schemas.party import PartyCreateRequest, PartyResponse, PartyUpdateRequest
from app.services.party_service import customer_service, supplier_service

customers_router = build_master_data_router(
    prefix="/customers",
    tags=["customers"],
    permission_prefix="customers",
    create_schema=PartyCreateRequest,
    update_schema=PartyUpdateRequest,
    response_schema=PartyResponse,
    service=customer_service,
)

suppliers_router = build_master_data_router(
    prefix="/suppliers",
    tags=["suppliers"],
    permission_prefix="suppliers",
    create_schema=PartyCreateRequest,
    update_schema=PartyUpdateRequest,
    response_schema=PartyResponse,
    service=supplier_service,
)
