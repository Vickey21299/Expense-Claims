"""
app/services/storage.py
Supabase Storage integration for receipt uploads.

Files are stored at:  expense-receipts/claims/{claim_id}/{document_id}/{filename}
"""
import hashlib
from pathlib import PurePosixPath

from app.core.config import settings
from app.core.database import supabase
from app.core.logging import get_logger

logger = get_logger(__name__)

# Allowed MIME types and corresponding extensions
ALLOWED_MIME_TYPES: dict[str, list[str]] = {
    "application/pdf": [".pdf"],
    "image/png": [".png"],
    "image/jpeg": [".jpg", ".jpeg"],
    "image/webp": [".webp"],
}

MAX_FILE_SIZE_BYTES = settings.OCR_MAX_FILE_SIZE_MB * 1024 * 1024
BUCKET = settings.STORAGE_BUCKET


class StorageError(Exception):
    """Raised when a storage operation fails."""
    pass


class FileValidationError(ValueError):
    """Raised when uploaded file fails validation."""
    pass


def validate_file(
    file_data: bytes,
    filename: str,
    content_type: str | None,
) -> str:
    """
    Validate uploaded file.
    Returns the normalised MIME type.
    Raises FileValidationError on any issue.
    """
    # Empty file
    if not file_data or len(file_data) == 0:
        raise FileValidationError("File is empty.")

    # Size check
    if len(file_data) > MAX_FILE_SIZE_BYTES:
        raise FileValidationError(
            f"File too large ({len(file_data) / 1024 / 1024:.1f} MB). "
            f"Maximum allowed: {settings.OCR_MAX_FILE_SIZE_MB} MB."
        )

    # Extension check
    ext = PurePosixPath(filename).suffix.lower()
    if not ext:
        raise FileValidationError(f"File has no extension: {filename}")

    valid_extensions = {e for exts in ALLOWED_MIME_TYPES.values() for e in exts}
    if ext not in valid_extensions:
        raise FileValidationError(
            f"Unsupported file extension '{ext}'. "
            f"Allowed: {', '.join(sorted(valid_extensions))}"
        )

    # MIME type check
    mime = (content_type or "").lower().strip()
    if mime and mime not in ALLOWED_MIME_TYPES:
        # Try to infer from extension
        for m, exts in ALLOWED_MIME_TYPES.items():
            if ext in exts:
                mime = m
                break
        else:
            raise FileValidationError(
                f"Unsupported MIME type '{content_type}'. "
                f"Allowed: {', '.join(ALLOWED_MIME_TYPES.keys())}"
            )
    elif not mime:
        # Infer from extension
        for m, exts in ALLOWED_MIME_TYPES.items():
            if ext in exts:
                mime = m
                break
        else:
            raise FileValidationError(f"Cannot determine MIME type for '{filename}'.")

    return mime


def compute_checksum(file_data: bytes) -> str:
    """Return SHA-256 hex digest of file data."""
    return hashlib.sha256(file_data).hexdigest()


def build_storage_path(claim_id: str, document_id: str, filename: str) -> str:
    """Build a predictable storage path."""
    # Sanitise filename (keep only safe chars)
    safe_name = PurePosixPath(filename).name.replace(" ", "_")
    return f"claims/{claim_id}/{document_id}/{safe_name}"


def upload_receipt(
    claim_id: str,
    document_id: str,
    file_data: bytes,
    filename: str,
    mime_type: str,
) -> str:
    """
    Upload a receipt to Supabase Storage.
    Returns the storage path.
    """
    storage_path = build_storage_path(claim_id, document_id, filename)

    try:
        result = supabase.storage.from_(BUCKET).upload(
            path=storage_path,
            file=file_data,
            file_options={"content-type": mime_type},
        )
        logger.info(
            "Receipt uploaded to storage",
            extra={"storage_path": storage_path, "size_bytes": len(file_data)},
        )
        return storage_path
    except Exception as exc:
        error_msg = str(exc)
        # If file already exists (duplicate upload), treat as success
        if "Duplicate" in error_msg or "already exists" in error_msg:
            logger.warning(
                "File already exists in storage, treating as success",
                extra={"storage_path": storage_path},
            )
            return storage_path
        logger.error("Storage upload failed", extra={"error": error_msg})
        raise StorageError(f"Failed to upload to storage: {error_msg}") from exc


def download_receipt(storage_path: str) -> bytes:
    """Download a receipt from Supabase Storage."""
    try:
        data = supabase.storage.from_(BUCKET).download(storage_path)
        logger.info("Receipt downloaded from storage", extra={"path": storage_path})
        return data
    except Exception as exc:
        logger.error("Storage download failed", extra={"path": storage_path, "error": str(exc)})
        raise StorageError(f"Failed to download from storage: {exc}") from exc


def delete_receipt(storage_path: str) -> None:
    """Delete a receipt from Supabase Storage."""
    try:
        supabase.storage.from_(BUCKET).remove([storage_path])
        logger.info("Receipt deleted from storage", extra={"path": storage_path})
    except Exception as exc:
        logger.warning("Storage delete failed (non-fatal)", extra={"path": storage_path, "error": str(exc)})


def get_public_url(storage_path: str) -> str:
    """Get a public URL for a stored receipt."""
    try:
        result = supabase.storage.from_(BUCKET).get_public_url(storage_path)
        return result
    except Exception:
        return ""
