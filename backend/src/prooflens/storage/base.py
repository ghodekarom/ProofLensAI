"""Abstract base storage service."""

from abc import ABC, abstractmethod


class StorageService(ABC):
    """Abstract interface for storing and retrieving uploaded document files."""

    @abstractmethod
    def save(self, data: bytes, document_id: str, filename: str) -> str:
        """Saves file bytes and returns a persistent storage key."""
        pass

    @abstractmethod
    def read(self, storage_key: str) -> bytes:
        """Reads and returns file bytes for a given storage key."""
        pass

    @abstractmethod
    def delete(self, storage_key: str) -> bool:
        """Deletes file identified by storage key."""
        pass

    @abstractmethod
    def exists(self, storage_key: str) -> bool:
        """Checks if a file exists for the given storage key."""
        pass
