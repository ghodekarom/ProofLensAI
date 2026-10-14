"""Storage package for ProofLens AI."""

from prooflens.storage.base import StorageService
from prooflens.storage.local_filesystem import LocalFilesystemStorage, get_storage_service

__all__ = ["StorageService", "LocalFilesystemStorage", "get_storage_service"]
