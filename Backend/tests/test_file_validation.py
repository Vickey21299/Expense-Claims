"""
tests/test_file_validation.py
Unit tests for file validation in the storage service.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from app.services.storage import validate_file, FileValidationError, MAX_FILE_SIZE_BYTES


class TestFileValidation:
    """Tests for validate_file()."""

    def test_valid_pdf(self):
        mime = validate_file(b"%PDF-1.5 fake content", "receipt.pdf", "application/pdf")
        assert mime == "application/pdf"

    def test_valid_png(self):
        mime = validate_file(b"\x89PNG fake content", "screenshot.png", "image/png")
        assert mime == "image/png"

    def test_valid_jpg(self):
        mime = validate_file(b"\xff\xd8\xff fake jpeg", "photo.jpg", "image/jpeg")
        assert mime == "image/jpeg"

    def test_valid_jpeg(self):
        mime = validate_file(b"\xff\xd8\xff fake jpeg", "photo.jpeg", "image/jpeg")
        assert mime == "image/jpeg"

    def test_valid_webp(self):
        mime = validate_file(b"RIFF fake webp", "image.webp", "image/webp")
        assert mime == "image/webp"

    def test_empty_file_rejected(self):
        with pytest.raises(FileValidationError, match="empty"):
            validate_file(b"", "receipt.pdf", "application/pdf")

    def test_none_data_rejected(self):
        with pytest.raises(FileValidationError, match="empty"):
            validate_file(None, "receipt.pdf", "application/pdf")

    def test_oversized_file_rejected(self):
        huge_data = b"x" * (MAX_FILE_SIZE_BYTES + 1)
        with pytest.raises(FileValidationError, match="too large"):
            validate_file(huge_data, "big.pdf", "application/pdf")

    def test_no_extension_rejected(self):
        with pytest.raises(FileValidationError, match="no extension"):
            validate_file(b"some data", "receipt", "application/pdf")

    def test_unsupported_extension_rejected(self):
        with pytest.raises(FileValidationError, match="Unsupported file extension"):
            validate_file(b"some data", "document.docx", "application/vnd.openxmlformats")

    def test_unsupported_mime_with_valid_extension(self):
        # .pdf extension but wrong MIME → should infer from extension
        mime = validate_file(b"data", "receipt.pdf", "text/plain")
        assert mime == "application/pdf"

    def test_no_mime_inferred_from_extension(self):
        mime = validate_file(b"data", "receipt.png", None)
        assert mime == "image/png"

    def test_txt_extension_rejected(self):
        with pytest.raises(FileValidationError, match="Unsupported"):
            validate_file(b"text data", "notes.txt", "text/plain")

    def test_exe_extension_rejected(self):
        with pytest.raises(FileValidationError, match="Unsupported"):
            validate_file(b"binary", "virus.exe", "application/octet-stream")


class TestChecksum:
    def test_deterministic(self):
        from app.services.storage import compute_checksum

        data = b"Hello, World!"
        h1 = compute_checksum(data)
        h2 = compute_checksum(data)
        assert h1 == h2
        assert len(h1) == 64  # SHA-256 hex digest is 64 chars

    def test_different_data_different_checksum(self):
        from app.services.storage import compute_checksum

        h1 = compute_checksum(b"file1")
        h2 = compute_checksum(b"file2")
        assert h1 != h2


class TestStoragePath:
    def test_build_path(self):
        from app.services.storage import build_storage_path

        path = build_storage_path("claim-123", "doc-456", "receipt.pdf")
        assert path == "claims/claim-123/doc-456/receipt.pdf"

    def test_spaces_in_filename(self):
        from app.services.storage import build_storage_path

        path = build_storage_path("c1", "d1", "my receipt file.pdf")
        assert " " not in path
        assert "my_receipt_file.pdf" in path


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
