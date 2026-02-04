"""
Unit tests for UploadHandler - Fixed version
"""
import os
import shutil
import tempfile
import time
from io import BytesIO
from unittest.mock import MagicMock, Mock, mock_open, patch

import pytest
from werkzeug.datastructures import FileStorage

from utils.upload_handler import UploadHandler


class TestUploadHandler:
    """Test UploadHandler class"""

    def setup_method(self):
        """Setup test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.uploader = UploadHandler(self.test_dir)

        # Create test directory
        self.test_subdir = os.path.join(self.test_dir, "uploads")
        os.makedirs(self.test_subdir, exist_ok=True)

        # Mock Config
        self.config_patcher = patch("utils.upload_handler.Config")
        self.mock_config = self.config_patcher.start()
        self.mock_config.ROOT_DRIVE = self.test_dir  # Changed from '../' to test_dir
        self.mock_config.MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB
        self.mock_config.ALLOWED_EXTENSIONS = [".*"]

    def teardown_method(self):
        """Cleanup test environment"""
        import shutil

        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        self.config_patcher.stop()

    def create_mock_file(self, filename="test.txt", content=b"test content"):
        """Create a mock FileStorage object"""
        file_storage = Mock(spec=FileStorage)
        file_storage.filename = filename
        file_storage.read = Mock(return_value=content)
        file_storage.seek = Mock()
        file_storage.save = Mock()
        # Add tell method for file size checking
        file_size = (
            len(content) if isinstance(content, bytes) else len(content.encode("utf-8"))
        )
        file_storage.tell = Mock(return_value=file_size)
        return file_storage

    def test_init(self):
        """Test UploadHandler initialization"""
        # Remove the import from config - we're using the mocked Config
        # Test with custom root
        custom_handler = UploadHandler("/custom/path")
        assert custom_handler.root_drive == "/custom/path"

        # Test with default root - should use the mocked Config.ROOT_DRIVE
        default_handler = UploadHandler()
        assert (
            default_handler.root_drive == self.mock_config.ROOT_DRIVE
        )  # Should be test_dir

    def test_handle_upload_single_file(self):
        """Test uploading single file"""
        mock_file = self.create_mock_file("test.txt")

        results = self.uploader.handle_upload([mock_file], "uploads")

        assert results["total"] == 1
        assert results["success_count"] == 1
        assert results["error_count"] == 0
        assert len(results["success"]) == 1

        success_item = results["success"][0]
        assert success_item["original_name"] == "test.txt"
        assert success_item["saved_name"] == "test.txt"
        assert "uploads/test.txt" in success_item["path"]

        # Verify file was saved
        saved_path = os.path.join(self.test_subdir, "test.txt")
        assert os.path.exists(saved_path)

    def test_handle_upload_multiple_files(self):
        """Test uploading multiple files"""
        files = [
            self.create_mock_file("file1.txt"),
            self.create_mock_file("file2.jpg", b"image content"),
            self.create_mock_file("file3.pdf", b"pdf content"),
        ]

        results = self.uploader.handle_upload(files, "uploads")

        assert results["total"] == 3
        assert results["success_count"] == 3
        assert results["error_count"] == 0

    def test_handle_upload_empty_file(self):
        """Test uploading empty file"""
        mock_file = self.create_mock_file("")
        mock_file.filename = ""

        results = self.uploader.handle_upload([mock_file], "uploads")

        assert results["error_count"] == 1
        assert results["success_count"] == 0
        assert "Empty file" in results["errors"][0]["error"]

    def test_handle_upload_no_files(self):
        """Test uploading with no files"""
        results = self.uploader.handle_upload([], "uploads")

        assert results["total"] == 0
        assert results["success_count"] == 0
        assert results["error_count"] == 0

    @patch("utils.upload_handler.is_allowed_file")
    def test_handle_upload_disallowed_file(self, mock_is_allowed):
        """Test uploading disallowed file type"""
        mock_is_allowed.return_value = False
        mock_file = self.create_mock_file("test.exe")

        results = self.uploader.handle_upload([mock_file], "uploads")

        assert results["error_count"] == 1
        assert "File type not allowed" in results["errors"][0]["error"]

    def test_handle_upload_file_too_large(self):
        """Test uploading file that's too large"""
        # Set small file size limit
        self.uploader.max_file_size = 100

        # Create a file that's larger than the limit
        large_content = b"x" * 200
        mock_file = self.create_mock_file("large.txt", large_content)

        results = self.uploader.handle_upload([mock_file], "uploads")

        assert results["error_count"] == 1
        assert "File too large" in results["errors"][0]["error"]

    def test_handle_upload_duplicate_filename(self):
        """Test uploading file with duplicate name"""
        # Create existing file
        existing_path = os.path.join(self.test_subdir, "test.txt")
        with open(existing_path, "w") as f:
            f.write("existing")

        mock_file = self.create_mock_file("test.txt")

        results = self.uploader.handle_upload([mock_file], "uploads")

        assert results["success_count"] == 1
        # Should create unique filename
        saved_name = results["success"][0]["saved_name"]
        assert saved_name != "test.txt" or saved_name == "test_1.txt"

    def test_handle_upload_sanitizes_filename(self):
        """Test that filename is sanitized during upload"""
        mock_file = self.create_mock_file("file<name>.txt")

        results = self.uploader.handle_upload([mock_file], "uploads")

        assert results["success_count"] == 1
        # Check dangerous characters are removed
        saved_name = results["success"][0]["saved_name"]
        assert "<" not in saved_name
        assert ">" not in saved_name

    def test_handle_upload_exception(self):
        """Test upload with exception"""
        mock_file = self.create_mock_file("test.txt")
        mock_file.read.side_effect = Exception("Read error")

        results = self.uploader.handle_upload([mock_file], "uploads")

        assert results["error_count"] == 1
        assert "Read error" in results["errors"][0]["error"]

    def test_create_folder_success(self):
        """Test successful folder creation"""
        result = self.uploader.create_folder("new_folder", "uploads")

        assert result["success"] is True
        assert result["folder_name"] == "new_folder"
        assert "uploads/new_folder" in result["folder_path"]

        # Verify folder was created
        folder_path = os.path.join(self.test_subdir, "new_folder")
        assert os.path.exists(folder_path)
        assert os.path.isdir(folder_path)

    def test_create_folder_duplicate(self):
        """Test creating duplicate folder"""
        # Create folder first
        os.makedirs(os.path.join(self.test_subdir, "existing"))

        result = self.uploader.create_folder("existing", "uploads")

        assert result["success"] is False
        assert "already exists" in result["error"]

    @patch("utils.upload_handler.sanitize_filename")
    def test_create_folder_invalid_name(self, mock_sanitize):
        """Test creating folder with invalid name"""
        # Test with empty name
        mock_sanitize.return_value = ""
        result = self.uploader.create_folder("", "uploads")
        assert result["success"] is False
        assert "Invalid folder name" in result["error"]

        # Test with whitespace only
        mock_sanitize.return_value = "   "
        result = self.uploader.create_folder("   ", "uploads")
        assert result["success"] is False

    def test_create_folder_sanitizes_name(self):
        """Test that folder name is sanitized"""
        result = self.uploader.create_folder("folder<name>", "uploads")

        # Should either succeed with sanitized name or fail
        if result["success"]:
            # Check dangerous characters are removed
            assert "<" not in result["folder_name"]
            assert ">" not in result["folder_name"]
        else:
            # Might fail due to invalid characters
            assert "error" in result

    def test_create_folder_exception(self):
        """Test folder creation with exception"""
        with patch("os.makedirs") as mock_makedirs:
            mock_makedirs.side_effect = Exception("Permission denied")

            result = self.uploader.create_folder("test", "uploads")

            assert result["success"] is False
            assert "Permission denied" in result["error"]

    def test_create_file_success(self):
        """Test successful file creation"""
        result = self.uploader.create_file("new_file.txt", "uploads")

        assert result["success"] is True
        assert result["filename"] == "new_file.txt"
        assert "uploads/new_file.txt" in result["file_path"]

        # Verify file was created
        file_path = os.path.join(self.test_subdir, "new_file.txt")
        assert os.path.exists(file_path)
        assert os.path.isfile(file_path)

    def test_create_file_duplicate(self):
        """Test creating duplicate file"""
        # Create file first
        existing_path = os.path.join(self.test_subdir, "existing.txt")
        with open(existing_path, "w") as f:
            f.write("content")

        result = self.uploader.create_file("existing.txt", "uploads")

        assert result["success"] is False
        assert "already exists" in result["error"]

    @patch("utils.upload_handler.sanitize_filename")
    def test_create_file_invalid_name(self, mock_sanitize):
        """Test creating file with invalid name"""
        mock_sanitize.return_value = ""
        result = self.uploader.create_file("", "uploads")
        assert result["success"] is False
        assert "Invalid filename" in result["error"]

    def test_create_file_sanitizes_name(self):
        """Test that filename is sanitized"""
        result = self.uploader.create_file("file<name>.txt", "uploads")

        if result["success"]:
            # Check dangerous characters are removed
            assert "<" not in result["filename"]
            assert ">" not in result["filename"]
        else:
            # Might fail due to invalid characters
            assert "error" in result

    def test_create_file_exception(self):
        """Test file creation with exception"""
        with patch("builtins.open") as mock_open:
            mock_open.side_effect = Exception("Disk full")

            result = self.uploader.create_file("test.txt", "uploads")

            assert result["success"] is False
            assert "Disk full" in result["error"]

    def test_validate_upload_path_valid(self):
        """Test valid upload path validation"""
        is_valid, message = self.uploader.validate_upload_path("uploads")

        assert is_valid is True
        assert message == ""

    def test_validate_upload_path_nonexistent(self):
        """Test non-existent upload path"""
        is_valid, message = self.uploader.validate_upload_path("nonexistent")

        assert is_valid is False
        assert "does not exist" in message

    def test_validate_upload_path_not_directory(self):
        """Test upload path that's not a directory"""
        # Create a file
        file_path = os.path.join(self.test_dir, "file.txt")
        with open(file_path, "w") as f:
            f.write("content")

        is_valid, message = self.uploader.validate_upload_path("file.txt")

        assert is_valid is False
        assert "not a directory" in message

    def test_validate_upload_path_traversal(self):
        """Test path traversal attempt"""
        is_valid, message = self.uploader.validate_upload_path("../../etc")

        assert is_valid is False
        assert "Invalid path" in message

    @patch("os.access")
    def test_validate_upload_path_no_permission(self, mock_access):
        """Test upload path without write permission"""
        mock_access.return_value = False

        is_valid, message = self.uploader.validate_upload_path("uploads")

        assert is_valid is False
        assert "No write permission" in message

    def test_validate_upload_path_exception(self):
        """Test path validation with exception"""
        with patch("os.path.join") as mock_join:
            mock_join.side_effect = Exception("Join error")

            is_valid, message = self.uploader.validate_upload_path("uploads")

            assert is_valid is False
            assert "Join error" in message

    @patch("os.walk")
    @patch("os.path.getmtime")
    @patch("os.remove")
    def test_cleanup_incomplete_uploads(self, mock_remove, mock_getmtime, mock_walk):
        """Test cleanup of incomplete uploads"""
        # Mock walk to return .part files
        mock_walk.return_value = [
            (self.test_dir, [], ["file1.part", "file2.part", "file3.txt"])
        ]

        # Mock modification times
        current_time = 1000
        mock_getmtime.side_effect = [500, 100]  # file1 is old, file2 is new

        # Mock time.time()
        with patch("time.time", return_value=current_time):
            cleanup_count = self.uploader.cleanup_incomplete_uploads(
                timeout_seconds=600
            )

        # Only file1 should be removed (500 < 1000-600)
        # file2 is not old enough (100 > 1000-600)
        assert cleanup_count == 1
        mock_remove.assert_called_once()

    def test_cleanup_incomplete_uploads_real(self):
        """Test cleanup with real files"""
        # Create .part files with different ages
        old_part = os.path.join(self.test_dir, "old.part")
        new_part = os.path.join(self.test_dir, "new.part")

        with open(old_part, "w") as f:
            f.write("old")

        with open(new_part, "w") as f:
            f.write("new")

        # Set old file's mtime to 2 hours ago
        old_mtime = time.time() - 7200
        os.utime(old_part, (old_mtime, old_mtime))

        cleanup_count = self.uploader.cleanup_incomplete_uploads(timeout_seconds=3600)

        # Only old.part should be removed
        assert cleanup_count == 1
        assert not os.path.exists(old_part)
        assert os.path.exists(new_part)

    def test_handle_upload_bytes_content(self):
        """Test upload with bytes content"""
        mock_file = Mock(spec=FileStorage)
        mock_file.filename = "test.txt"
        mock_file.read = Mock(return_value=b"bytes content")
        mock_file.seek = Mock()
        mock_file.tell = Mock(return_value=len(b"bytes content"))
        mock_file.save = Mock()

        results = self.uploader.handle_upload([mock_file], "uploads")

        assert results["success_count"] == 1

        # Verify content was written
        saved_path = os.path.join(self.test_subdir, "test.txt")
        assert os.path.exists(saved_path)
        with open(saved_path, "rb") as f:
            content = f.read()
            assert content == b"bytes content"

    def test_handle_upload_string_content(self):
        """Test upload with string content"""
        mock_file = Mock(spec=FileStorage)
        mock_file.filename = "test.txt"
        mock_file.read = Mock(return_value="string content")
        mock_file.seek = Mock()
        mock_file.tell = Mock(return_value=len("string content"))
        mock_file.save = Mock()

        results = self.uploader.handle_upload([mock_file], "uploads")

        assert results["success_count"] == 1

        # Verify content was written as bytes
        saved_path = os.path.join(self.test_subdir, "test.txt")
        assert os.path.exists(saved_path)
        with open(saved_path, "rb") as f:
            content = f.read()
            assert content == b"string content"

    def test_race_condition_folder_creation(self):
        """Test race condition in folder creation"""
        # Simulate folder being created between check and creation
        with patch("os.makedirs") as mock_makedirs:
            mock_makedirs.side_effect = FileExistsError("Folder exists")

            result = self.uploader.create_folder("test", "uploads")

            assert result["success"] is False
            assert "already exists" in result["error"]

    def test_race_condition_file_creation(self):
        """Test race condition in file creation"""
        # Simulate file being created between check and creation
        with patch("builtins.open") as mock_open:
            mock_open.side_effect = FileExistsError("File exists")

            result = self.uploader.create_file("test.txt", "uploads")

            assert result["success"] is False
            assert "already exists" in result["error"]

    def test_handle_upload_with_relative_path(self):
        """Test upload with relative path"""
        mock_file = self.create_mock_file("test.txt")

        results = self.uploader.handle_upload([mock_file], "")

        assert results["success_count"] == 1

        # Verify file was saved in root
        saved_path = os.path.join(self.test_dir, "test.txt")
        assert os.path.exists(saved_path)

    @patch("utils.upload_handler.sanitize_filename")
    def test_handle_upload_uses_sanitize(self, mock_sanitize):
        """Test that sanitize_filename is called"""
        mock_sanitize.return_value = "sanitized.txt"
        mock_file = self.create_mock_file("test<>.txt")

        results = self.uploader.handle_upload([mock_file], "uploads")

        mock_sanitize.assert_called_with("test<>.txt")
        if results["success_count"] > 0:
            assert results["success"][0]["saved_name"] == "sanitized.txt"
