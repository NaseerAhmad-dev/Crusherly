from app.models.party import Customer, Supplier
from app.repositories.master_data_repository import MasterDataRepository

customer_repository = MasterDataRepository(Customer)
supplier_repository = MasterDataRepository(Supplier)
