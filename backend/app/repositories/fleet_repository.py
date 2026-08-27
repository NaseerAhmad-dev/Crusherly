from app.models.fleet import Driver, Vehicle
from app.repositories.master_data_repository import MasterDataRepository

vehicle_repository = MasterDataRepository(Vehicle)
driver_repository = MasterDataRepository(Driver)
