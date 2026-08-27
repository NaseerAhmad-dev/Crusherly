"""Application configuration.

Loaded once from environment variables / `.env` via pydantic-settings. Local secrets live in
`.env` (never committed); production secrets are injected via Azure Key Vault into the same
environment variable names, so no code branches on where the secret physically lives.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Environment ---
    environment: Literal["development", "test", "staging", "production"] = "development"
    debug: bool = True

    # --- Database ---
    database_url: str = (
        "postgresql+asyncpg://crusher:crusher_dev_password@localhost:5432/stone_crusher"
    )
    db_pool_size: int = 10
    db_max_overflow: int = 10

    # --- Security ---
    jwt_secret_key: str = Field(default="dev-only-insecure-secret-change-me")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # --- CORS ---
    cors_allowed_origins: str = "http://localhost:4200"

    # --- Storage ---
    storage_provider: Literal["local", "azure"] = "local"
    local_storage_path: str = "./storage"
    azure_storage_connection_string: str = ""
    azure_storage_container: str = "attachments"

    # --- Azure Key Vault ---
    azure_key_vault_url: str = ""

    # --- Azure Application Insights ---
    applicationinsights_connection_string: str = ""

    # --- Rate limiting ---
    rate_limit_per_minute: int = 120

    # --- Uploads ---
    max_upload_size_mb: int = 25

    # --- API ---
    api_v1_prefix: str = "/api/v1"
    project_name: str = "Stone Crusher Management Platform"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
