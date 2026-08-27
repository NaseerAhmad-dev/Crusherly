"""Blob storage abstraction (Master Build Specification section 21).

    StorageService
     ├── LocalStorageProvider   (default outside production; writes under LOCAL_STORAGE_PATH)
     └── AzureBlobStorageProvider (used when STORAGE_PROVIDER=azure)

Callers (see app/services/attachment_service.py) depend only on the `StorageProvider` protocol,
never on a concrete provider, so switching providers is a configuration change, not a code change.
"""

import os
import uuid
from abc import ABC, abstractmethod
from datetime import UTC
from pathlib import Path

from app.core.config import get_settings

settings = get_settings()


class StorageProvider(ABC):
    @abstractmethod
    async def upload(self, key: str, content: bytes, content_type: str) -> None: ...

    @abstractmethod
    async def download(self, key: str) -> bytes: ...

    @abstractmethod
    async def delete(self, key: str) -> None: ...

    @abstractmethod
    async def generate_access_url(self, key: str, expires_in_seconds: int = 3600) -> str: ...


class LocalStorageProvider(StorageProvider):
    """Writes to the local filesystem. Suitable for local development only."""

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _resolve(self, key: str) -> Path:
        # Defend against path traversal via a malicious storage_key.
        safe_key = key.replace("..", "").lstrip("/\\")
        path = (self.base_path / safe_key).resolve()
        if self.base_path.resolve() not in path.parents and path != self.base_path.resolve():
            raise ValueError("Invalid storage key.")
        return path

    async def upload(self, key: str, content: bytes, content_type: str) -> None:
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    async def download(self, key: str) -> bytes:
        return self._resolve(key).read_bytes()

    async def delete(self, key: str) -> None:
        path = self._resolve(key)
        if path.exists():
            os.remove(path)

    async def generate_access_url(self, key: str, expires_in_seconds: int = 3600) -> str:
        # Local development has no public URL; the API's download endpoint is used instead.
        return f"/api/v1/attachments/local/{key}"


class AzureBlobStorageProvider(StorageProvider):
    """Wraps azure-storage-blob. Used when STORAGE_PROVIDER=azure."""

    def __init__(self, connection_string: str, container: str):
        from azure.storage.blob.aio import BlobServiceClient

        self._client = BlobServiceClient.from_connection_string(connection_string)
        self._container = container

    async def upload(self, key: str, content: bytes, content_type: str) -> None:
        from azure.storage.blob import ContentSettings

        container_client = self._client.get_container_client(self._container)
        await container_client.upload_blob(
            key,
            content,
            overwrite=True,
            content_settings=ContentSettings(content_type=content_type),
        )

    async def download(self, key: str) -> bytes:
        container_client = self._client.get_container_client(self._container)
        stream = await container_client.download_blob(key)
        return await stream.readall()

    async def delete(self, key: str) -> None:
        container_client = self._client.get_container_client(self._container)
        await container_client.delete_blob(key)

    async def generate_access_url(self, key: str, expires_in_seconds: int = 3600) -> str:
        from datetime import datetime, timedelta

        from azure.storage.blob import BlobSasPermissions, generate_blob_sas

        account_key = self._client.credential.account_key
        sas_token = generate_blob_sas(
            account_name=self._client.account_name,
            container_name=self._container,
            blob_name=key,
            account_key=account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.now(UTC) + timedelta(seconds=expires_in_seconds),
        )
        return f"{self._client.url}/{self._container}/{key}?{sas_token}"


_provider: StorageProvider | None = None


def get_storage_provider() -> StorageProvider:
    global _provider
    if _provider is not None:
        return _provider

    if settings.storage_provider == "azure":
        _provider = AzureBlobStorageProvider(
            settings.azure_storage_connection_string, settings.azure_storage_container
        )
    else:
        _provider = LocalStorageProvider(settings.local_storage_path)
    return _provider


def build_storage_key(
    tenant_id: uuid.UUID, entity_type: str, entity_id: str, file_name: str
) -> str:
    unique_suffix = uuid.uuid4().hex[:12]
    safe_name = file_name.replace("/", "_").replace("\\", "_")
    return f"{tenant_id}/{entity_type}/{entity_id}/{unique_suffix}_{safe_name}"
