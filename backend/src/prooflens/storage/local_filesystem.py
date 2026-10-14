"""Local filesystem implementation of StorageService."""

import re
from pathlib import Path

from prooflens.core.config import get_settings
from prooflens.core.exceptions import InvalidFileError
from prooflens.core.logging import get_logger
from prooflens.storage.base import StorageService

logger = get_logger("prooflens.storage.local")


def sanitize_filename(filename: str) -> str:
    """Removes path traversals and invalid characters from filename."""
    # Strip directory paths
    clean_name = Path(filename).name
    # Replace non-alphanumeric chars (excluding dot, hyphen, underscore)
    clean_name = re.sub(r"[^\w\.\-]", "_", clean_name)
    return clean_name or "document.pdf"


class LocalFilesystemStorage(StorageService):
    """Stores uploaded files in the local filesystem behind safe directory boundaries."""

    def __init__(self, base_dir: Path | None = None) -> None:
        settings = get_settings()
        self.base_dir = (base_dir or settings.get_storage_path()).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_path(self, storage_key: str) -> Path:
        """Resolves storage key to filesystem path and ensures no path traversal."""
        # Normalize relative path
        safe_rel = Path(storage_key).as_posix().lstrip("/\\")
        target_path = (self.base_dir / safe_rel).resolve()

        if not str(target_path).startswith(str(self.base_dir)):
            raise InvalidFileError(
                "Path traversal detected in storage key.",
                details={"storage_key": storage_key},
            )
        return target_path

    def save(self, data: bytes, document_id: str, filename: str) -> str:
        """Saves file bytes and returns storage key."""
        clean_name = sanitize_filename(filename)
        # Use document_id in filename to guarantee uniqueness
        file_name = f"{document_id}_{clean_name}"
        target_path = (self.base_dir / file_name).resolve()

        # Double check bounds
        if not str(target_path).startswith(str(self.base_dir)):
            raise InvalidFileError("Invalid destination storage key.")

        with open(target_path, "wb") as f:
            f.write(data)

        logger.info(f"Saved file {clean_name} ({len(data)} bytes) as {file_name}")
        return file_name

    def read(self, storage_key: str) -> bytes:
        """Reads file bytes from storage."""
        target_path = self._resolve_path(storage_key)
        if not target_path.exists():
            raise FileNotFoundError(f"File for key '{storage_key}' does not exist.")
        with open(target_path, "rb") as f:
            return f.read()

    def delete(self, storage_key: str) -> bool:
        """Deletes file from storage."""
        try:
            target_path = self._resolve_path(storage_key)
            if target_path.exists():
                target_path.unlink()
                logger.info(f"Deleted storage file for key: {storage_key}")
                return True
            return False
        except Exception as exc:
            logger.warning(f"Failed to delete storage file for key '{storage_key}': {exc}")
            return False

    def exists(self, storage_key: str) -> bool:
        """Checks if file exists."""
        try:
            target_path = self._resolve_path(storage_key)
            return target_path.exists() and target_path.is_file()
        except Exception:
            return False


_storage_instance = None


def get_storage_service() -> StorageService:
    """Returns singleton storage service."""
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = LocalFilesystemStorage()
    return _storage_instance
