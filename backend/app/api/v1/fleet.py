"""Vehicles and Drivers."""

from app.api.v1.master_data_router import build_master_data_router
from app.schemas.fleet import (
    DriverCreateRequest,
    DriverResponse,
    DriverUpdateRequest,
    VehicleCreateRequest,
    VehicleResponse,
    VehicleUpdateRequest,
)
from app.services.fleet_service import driver_service, vehicle_service

vehicles_router = build_master_data_router(
    prefix="/vehicles",
    tags=["vehicles"],
    permission_prefix="vehicles",
    create_schema=VehicleCreateRequest,
    update_schema=VehicleUpdateRequest,
    response_schema=VehicleResponse,
    service=vehicle_service,
)

drivers_router = build_master_data_router(
    prefix="/drivers",
    tags=["drivers"],
    permission_prefix="drivers",
    create_schema=DriverCreateRequest,
    update_schema=DriverUpdateRequest,
    response_schema=DriverResponse,
    service=driver_service,
)
