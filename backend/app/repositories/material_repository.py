from app.models.material import Material, Product
from app.models.master_data import MaterialCategory, PaymentTerm, ProductCategory, TaxCode
from app.repositories.master_data_repository import MasterDataRepository

material_category_repository = MasterDataRepository(MaterialCategory)
product_category_repository = MasterDataRepository(ProductCategory)
tax_code_repository = MasterDataRepository(TaxCode)
payment_term_repository = MasterDataRepository(PaymentTerm)
material_repository = MasterDataRepository(Material)
product_repository = MasterDataRepository(Product)
