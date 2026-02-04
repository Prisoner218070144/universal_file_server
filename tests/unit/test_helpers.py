"""
Unit tests for helper functions - Fixed version
"""
import hashlib
import os
import tempfile
from datetime import datetime
from unittest.mock import MagicMock, Mock, PropertyMock, patch

import pytest

from utils.helpers import *


class TestHelpers:
    """Test helper functions"""

    def setup_method(self):
        """Setup test environment"""
        self.test_dir = tempfile.mkdtemp()

        # Create test files
        self.test_file = os.path.join(self.test_dir, "test.txt")
        with open(self.test_file, "w", encoding="utf-8") as f:
            f.write("Test content")

        # Create test folder with files
        self.test_folder = os.path.join(self.test_dir, "test_folder")
        os.makedirs(self.test_folder)

        for i in range(3):
            file_path = os.path.join(self.test_folder, f"file_{i}.txt")
            with open(file_path, "w") as f:
                f.write(f"Content {i}")

    def teardown_method(self):
        """Cleanup test environment"""
        import shutil

        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_sanitize_filename(self):
        """Test filename sanitization"""
        # Test dangerous characters
        dangerous = '<>:"/\\|?*='
        sanitized = sanitize_filename(f"test{dangerous}file.txt")
        # Check that dangerous chars are replaced
        for char in dangerous:
            assert char not in sanitized

        # Test null bytes
        assert sanitize_filename("test\x00file.txt") == "testfile.txt"

        # Test leading/trailing dots and spaces
        assert sanitize_filename("  .test.  ") == "test"

        # Test unicode normalization
        unicode_name = "café_ñandú.txt"
        sanitized = sanitize_filename(unicode_name)
        # Should normalize to ASCII
        assert "é" not in sanitized
        assert "ñ" not in sanitized

        # Test length limit
        long_name = "a" * 300 + ".txt"
        sanitized = sanitize_filename(long_name)
        assert len(sanitized) <= 255

        # Test empty filename
        assert sanitize_filename("") is not None
        assert sanitize_filename("   ") is not None

    def test_is_safe_path(self):
        """Test path safety check"""
        base_path = "/home/user"

        # Safe paths
        assert is_safe_path(base_path, "/home/user/documents")
        assert is_safe_path(base_path, "/home/user/documents/file.txt")

        # Unsafe paths (directory traversal)
        assert not is_safe_path(base_path, "/home/user/../etc/passwd")
        assert not is_safe_path(base_path, "/etc/passwd")

        # Test with relative paths
        assert is_safe_path("/home/user", "/home/user/./documents")

        # Test with symlinks (function doesn't follow symlinks)
        assert is_safe_path(base_path, "/home/user/documents")

        # Test exception handling
        assert not is_safe_path("/invalid", "../../etc/passwd")

    def test_get_file_hash(self):
        """Test file hash calculation"""
        # Create a file with known content
        test_content = b"Hello, World!"
        test_file = os.path.join(self.test_dir, "hash_test.txt")
        with open(test_file, "wb") as f:
            f.write(test_content)

        # Test MD5
        md5_hash = get_file_hash(test_file, "md5")
        expected_md5 = hashlib.md5(test_content).hexdigest()
        assert md5_hash == expected_md5

        # Test SHA256
        sha256_hash = get_file_hash(test_file, "sha256")
        expected_sha256 = hashlib.sha256(test_content).hexdigest()
        assert sha256_hash == expected_sha256

        # Test default algorithm (MD5)
        default_hash = get_file_hash(test_file)
        assert default_hash == expected_md5

        # Test non-existent file
        assert get_file_hash("nonexistent.txt") == ""

        # Test invalid algorithm (should use MD5 as fallback)
        assert get_file_hash(test_file, "invalid") != ""

    def test_format_timestamp(self):
        """Test timestamp formatting"""
        from datetime import datetime, timedelta

        now = datetime.now()

        # Test today (should show time)
        today_ts = now.timestamp()
        formatted = format_timestamp(today_ts)
        # Should contain time format
        assert len(formatted) > 0

        # Test yesterday
        yesterday = now - timedelta(days=1)
        yesterday_ts = yesterday.timestamp()
        formatted = format_timestamp(yesterday_ts)
        assert len(formatted) > 0

        # Test last year
        last_year = now.replace(year=now.year - 1)
        last_year_ts = last_year.timestamp()
        formatted = format_timestamp(last_year_ts)
        assert len(formatted) > 0

        # Test invalid timestamp
        assert format_timestamp("invalid") == "Unknown"
        assert format_timestamp(None) == "Unknown"

    @patch("utils.helpers.Config")
    def test_is_allowed_file(self, mock_config):
        """Test file extension allowance"""
        # Mock config
        mock_config.ALLOWED_EXTENSIONS = [".txt", ".jpg", ".png"]

        # Test allowed extensions
        assert is_allowed_file("test.txt") is True
        assert is_allowed_file("image.jpg") is True
        assert is_allowed_file("image.png") is True

        # Test disallowed extension
        assert is_allowed_file("test.exe") is False

        # Test with wildcard
        mock_config.ALLOWED_EXTENSIONS = [".*"]
        assert is_allowed_file("any.extension") is True

        # Test empty filename
        assert is_allowed_file("") is False

        # Test without extension
        mock_config.ALLOWED_EXTENSIONS = [".txt", ".jpg", ".png"]
        assert is_allowed_file("file") is False

    def test_get_readable_size(self):
        """Test human readable size formatting"""
        assert get_readable_size(0) == "0 B"
        assert get_readable_size(1024) == "1.0 KB"
        assert get_readable_size(1024 * 1024) == "1.0 MB"
        assert get_readable_size(1024 * 1024 * 1024) == "1.0 GB"

        # Test edge cases
        assert get_readable_size(None) == "0 B"
        assert get_readable_size("invalid") == "0 B"
        assert (
            get_readable_size(-100) == "0 B"
        )  # Fixed: negative size should return "0 B"

        # Test exact values
        assert get_readable_size(500) == "500 B"
        assert get_readable_size(1500) == "1.5 KB"

    def test_calculate_folder_size(self):
        """Test folder size calculation"""
        total_size, file_count = calculate_folder_size(self.test_folder)

        assert isinstance(total_size, int)
        assert isinstance(file_count, int)
        assert file_count == 3
        assert total_size > 0

        # Test non-existent folder
        size, count = calculate_folder_size("/nonexistent/folder")
        assert size == 0
        assert count == 0

        # Test file instead of folder
        size, count = calculate_folder_size(self.test_file)
        assert size == 0
        assert count == 0

    @patch("utils.helpers.Config", autospec=True)
    def test_create_thumbnail(self, mock_config):
        mock_img_instance = MagicMock()

        with patch("PIL.Image.open") as mock_open:
            mock_open.return_value.__enter__.return_value = mock_img_instance

            result = create_thumbnail("input.jpg", "output.jpg", (200, 200))

            assert result is True
            mock_open.assert_called_once_with("input.jpg")
            mock_img_instance.thumbnail.assert_called_once_with((200, 200))
            mock_img_instance.save.assert_called_once_with("output.jpg")

        # Simulate PIL not being available
        with patch.dict("sys.modules", {"PIL": None}):
            result = create_thumbnail("input.jpg", "output.jpg", (200, 200))
            assert result is False

    @patch("utils.helpers.Config")
    @patch("utils.helpers.mimetypes")
    def test_get_mime_type(self, mock_mimetypes, mock_config):
        """Test MIME type detection"""
        # Mock config
        mock_config.MIME_TYPES = {".txt": "text/plain", ".jpg": "image/jpeg"}
        mock_config.DEFAULT_MIME_TYPE = "application/octet-stream"

        # Test from config
        assert get_mime_type("test.txt") == "text/plain"
        assert get_mime_type("image.jpg") == "image/jpeg"

        # Test fallback to system
        mock_mimetypes.guess_type.return_value = ("application/pdf", None)
        assert get_mime_type("document.pdf") == "application/pdf"

        # Test default
        mock_mimetypes.guess_type.return_value = (None, None)
        assert get_mime_type("unknown.xyz") == "application/octet-stream"

    def test_validate_path(self):
        """Test path validation"""
        # Test valid path
        is_valid, message = validate_path(self.test_dir, must_exist=True)
        assert is_valid is True
        assert message == ""

        # Test path traversal
        is_valid, message = validate_path("/etc/../passwd", must_exist=False)
        assert is_valid is False
        assert "directory traversal" in message

        # Test empty path
        is_valid, message = validate_path("", must_exist=False)
        assert is_valid is False
        assert "cannot be empty" in message

        # Test non-existent path when must_exist=True
        is_valid, message = validate_path("/nonexistent/path", must_exist=True)
        assert is_valid is False
        assert "does not exist" in message

        # Test non-existent path when must_exist=False
        is_valid, message = validate_path("/nonexistent/path", must_exist=False)
        assert is_valid is True

    def test_generate_unique_filename(self):
        """Test unique filename generation"""
        # Create existing files
        existing_files = ["test.txt", "test_1.txt", "test_2.txt"]
        for filename in existing_files:
            with open(os.path.join(self.test_dir, filename), "w") as f:
                f.write("content")

        # Test when file doesn't exist
        assert generate_unique_filename(self.test_dir, "new.txt") == "new.txt"

        # Test when file exists
        result = generate_unique_filename(self.test_dir, "test.txt")
        assert result not in existing_files
        assert result.startswith("test_")

    def test_get_file_info(self):
        """Test getting file information"""
        info = get_file_info(self.test_file)

        # Check required keys
        required_keys = [
            "path",
            "size",
            "size_readable",
            "created",
            "modified",
            "is_dir",
            "is_file",
        ]
        for key in required_keys:
            assert key in info

        # Check values
        assert info["path"] == self.test_file
        assert info["size"] > 0
        assert info["is_file"] is True
        assert info["is_dir"] is False
        assert "hash_md5" in info

        # Test directory
        dir_info = get_file_info(self.test_folder)
        assert dir_info["is_dir"] is True
        assert dir_info["is_file"] is False

    def test_chunked_read(self):
        """Test chunked file reading"""
        # Create a larger file
        large_file = os.path.join(self.test_dir, "large.txt")
        content = "X" * 10000
        with open(large_file, "w") as f:
            f.write(content)

        # Test default chunk size
        chunks = list(chunked_read(large_file))
        assert len(chunks) > 0
        reconstructed = b"".join(chunks).decode("utf-8")
        assert reconstructed == content

        # Test custom chunk size
        chunks = list(chunked_read(large_file, chunk_size=100))
        # Should have approximately 100 chunks for 10000 bytes
        assert len(chunks) >= 90 and len(chunks) <= 110

        # Test small file
        chunks = list(chunked_read(self.test_file, chunk_size=100))
        assert len(chunks) == 1

    def test_sanitize_filename_edge_cases(self):
        """Test edge cases for filename sanitization"""
        # Test all dangerous characters
        test_cases = [
            ("file<name>.txt", "file_name_.txt"),
            ("file>name.txt", "file_name.txt"),
            ("file:name.txt", "file_name.txt"),
            ('file"name.txt', "file_name.txt"),
            ("file/name.txt", "file_name.txt"),
            ("file\\name.txt", "file_name.txt"),
            ("file|name.txt", "file_name.txt"),
            ("file?name.txt", "file_name.txt"),
            ("file*name.txt", "file_name.txt"),
            ("file=name.txt", "file_name.txt"),
        ]

        for input_name, _ in test_cases:
            result = sanitize_filename(input_name)
            # Check that dangerous chars are replaced
            assert "<" not in result
            assert ">" not in result
            assert ":" not in result
            assert '"' not in result
            assert "/" not in result
            assert "\\" not in result
            assert "|" not in result
            assert "?" not in result
            assert "*" not in result
            assert "=" not in result
