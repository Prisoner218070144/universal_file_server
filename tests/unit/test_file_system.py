"""
Unit tests for FileSystemModel - Fixed version
"""

import os
import tempfile
import time
from unittest.mock import MagicMock, Mock, patch

import pytest

from models.file_system import FileSystemModel


class TestFileSystemModel:
    """Test FileSystemModel class"""

    def setup_method(self):
        """Setup test environment"""
        self.test_dir = tempfile.mkdtemp()

        # Create a mock config for testing
        self.config_patcher = patch("models.file_system.Config")
        self.mock_config = self.config_patcher.start()

        # Set up mock config values
        self.mock_config.ROOT_DRIVE = self.test_dir
        self.mock_config.FILE_EXTENSIONS = {
            "video": [".mp4", ".mkv", ".avi", ".mov"],
            "audio": [".mp3", ".wav", ".flac"],
            "image": [".jpg", ".jpeg", ".png", ".gif", ".bmp"],
            "document": [".pdf", ".docx", ".doc"],
            "text": [
                ".txt",
                ".py",
                ".js",
                ".html",
                ".css",
                ".json",
                ".xml",
                ".csv",
                ".md",
                ".log",
                ".ini",
                ".cfg",
                ".conf",
            ],
            "other": [],
        }
        self.mock_config.FILE_ICONS = {
            "folder": "📁",
            "video": "🎬",
            "audio": "🎵",
            "image": "🖼️",
            "document": "📄",
            "text": "📝",
            "other": "📄",
        }
        self.mock_config.PERFORMANCE_CONFIG = {
            "DISABLE_FOLDER_SIZE": False,
            "CACHE_TIMEOUT": 10,
        }

        # Re-initialize model with mocked config
        self.model = FileSystemModel(self.test_dir)

        # Create test files and folders
        os.makedirs(os.path.join(self.test_dir, "test_folder"))
        os.makedirs(os.path.join(self.test_dir, "folder1", "subfolder"))

        with open(os.path.join(self.test_dir, "test.txt"), "w") as f:
            f.write("Test content")

        with open(os.path.join(self.test_dir, "image.jpg"), "wb") as f:
            f.write(b"fake image")

        with open(os.path.join(self.test_dir, "video.mp4"), "wb") as f:
            f.write(b"fake video")

        with open(os.path.join(self.test_dir, "document.pdf"), "wb") as f:
            f.write(b"fake pdf")

        with open(os.path.join(self.test_dir, "folder1", "file.txt"), "w") as f:
            f.write("Nested file")

    def teardown_method(self):
        """Cleanup test environment"""
        import shutil

        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        self.config_patcher.stop()

    def test_get_file_type(self):
        """Test file type detection"""
        assert self.model.get_file_type("test.txt") == "text"
        assert self.model.get_file_type("image.jpg") == "image"
        assert self.model.get_file_type("video.mp4") == "video"
        assert self.model.get_file_type("document.pdf") == "document"
        assert self.model.get_file_type("audio.mp3") == "audio"
        assert self.model.get_file_type("unknown.xyz") == "other"
        assert self.model.get_file_type("") == "other"

    def test_get_file_icon(self):
        """Test getting file icons"""
        assert self.model.get_file_icon("test.txt") == "📝"
        assert self.model.get_file_icon("folder") == "📄"
        assert self.model.get_file_icon("video.mp4") == "🎬"
        assert self.model.get_file_icon("unknown.xyz") == "📄"

    def test_format_file_size(self):
        """Test file size formatting"""
        assert self.model.format_file_size(0) == "0 B"
        assert self.model.format_file_size(1024) == "1.0 KB"
        assert self.model.format_file_size(1024 * 1024) == "1.0 MB"
        assert self.model.format_file_size(1024 * 1024 * 1024) == "1.0 GB"
        assert self.model.format_file_size(None) == "0 B"
        assert self.model.format_file_size("invalid") == "0 B"

    def test_get_folder_size(self):
        """Test folder size calculation"""
        # Test with file in folder
        folder_path = "folder1"
        size = self.model.get_folder_size(folder_path)
        assert isinstance(size, int)
        assert size > 0

        # Test empty folder
        empty_folder = "test_folder"
        assert self.model.get_folder_size(empty_folder) == 0

        # Test non-existent folder
        assert self.model.get_folder_size("nonexistent") == 0

    def test_get_folder_contents(self):
        """Test retrieving folder contents"""
        items, error = self.model.get_folder_contents("")
        assert error is None
        assert isinstance(items, list)

        # Verify folder structure
        folder_names = [item["name"] for item in items]
        assert "test_folder" in folder_names
        assert "test.txt" in folder_names

        # Test with path
        items, error = self.model.get_folder_contents("folder1")
        assert error is None
        assert any(item["name"] == "file.txt" for item in items)

        # Test non-existent path
        items, error = self.model.get_folder_contents("nonexistent")
        assert error is not None

        # Test file path instead of folder
        items, error = self.model.get_folder_contents("test.txt")
        assert error is not None

    def test_get_folder_contents_cache(self):
        """Test folder content caching"""
        # First call should populate cache
        items1, error1 = self.model.get_folder_contents("")
        assert error1 is None

        # Second call should use cache
        items2, error2 = self.model.get_folder_contents("")
        assert error2 is None

        # Verify same results
        assert len(items1) == len(items2)

    def test_search_files(self):
        """Test file search functionality"""
        # Debug: print what files exist
        print(f"Test directory: {self.test_dir}")
        for root, dirs, files in os.walk(self.test_dir):
            for file in files:
                print(f"  File: {os.path.join(root, file)}")

        # Search for existing file
        results = self.model.search_files("test.txt")
        print(f"Search for 'test.txt' found {len(results)} results")
        for r in results:
            print(f"  Result: {r['name']}")

        assert len(results) > 0
        assert any(r["name"] == "test.txt" for r in results)

        # Search with wildcard
        results = self.model.search_files("*.txt")
        print(f"Search for '*.txt' found {len(results)} results")
        assert any(r["name"] == "test.txt" for r in results)

        # Search with partial match
        results = self.model.search_files("test")
        print(f"Search for 'test' found {len(results)} results")
        assert any("test" in r["name"].lower() for r in results)

        # Search non-existent file
        results = self.model.search_files("nonexistent")
        assert len(results) == 0

        # Search with short query
        results = self.model.search_files("t")
        assert len(results) == 0

        # Search with empty query
        results = self.model.search_files("")
        assert len(results) == 0

        # Test search cache
        results1 = self.model.search_files("test")
        results2 = self.model.search_files("test")
        assert len(results1) == len(results2)

    def test_get_files_by_type(self):
        """Test grouping files by type"""
        items = [
            {"name": "test.txt", "type": "text"},
            {"name": "image.jpg", "type": "image"},
            {"name": "video.mp4", "type": "video"},
            {"name": "folder", "type": "folder"},
        ]

        grouped = self.model.get_files_by_type(items)

        assert "text" in grouped
        assert "image" in grouped
        assert "video" in grouped
        assert "folder" not in grouped  # Folders should be excluded

        # Test sorting
        items = [
            {"name": "z.txt", "type": "text"},
            {"name": "a.txt", "type": "text"},
            {"name": "m.txt", "type": "text"},
        ]

        grouped = self.model.get_files_by_type(items)
        assert grouped["text"][0]["name"] == "a.txt"
        assert grouped["text"][1]["name"] == "m.txt"
        assert grouped["text"][2]["name"] == "z.txt"

    def test_get_breadcrumbs(self):
        """Test breadcrumb generation"""
        # Test root path
        crumbs = self.model.get_breadcrumbs("")
        assert crumbs == []

        # Test single level
        crumbs = self.model.get_breadcrumbs("folder1")
        assert len(crumbs) == 1
        assert crumbs[0]["name"] == "folder1"
        assert crumbs[0]["path"] == "folder1"

        # Test nested path
        crumbs = self.model.get_breadcrumbs("folder1/subfolder")
        assert len(crumbs) == 2
        assert crumbs[0]["name"] == "folder1"
        assert crumbs[1]["name"] == "subfolder"

        # Test with backslashes
        crumbs = self.model.get_breadcrumbs("folder1\\subfolder")
        assert len(crumbs) == 2

    def test_get_parent_path(self):
        """Test getting parent path"""
        assert self.model.get_parent_path("") == ""
        assert self.model.get_parent_path("folder1") == ""
        assert self.model.get_parent_path("folder1/subfolder") == "folder1"
        assert self.model.get_parent_path("folder1\\subfolder") == "folder1"

    def test_count_file_types(self):
        """Test file type counting"""
        items = [
            {"type": "folder"},
            {"type": "folder"},
            {"type": "video"},
            {"type": "image"},
            {"type": "text"},
            {"type": "document"},
            {"type": "audio"},
            {"type": "other"},
        ]

        counts = self.model.count_file_types(items)

        assert counts["folders"] == 2
        assert counts["videos"] == 1
        assert counts["images"] == 1
        assert counts["text"] == 1
        assert counts["documents"] == 1
        assert counts["audios"] == 1
        assert counts["others"] == 1

    def test_clear_cache(self):
        """Test cache clearing"""
        # Populate cache
        self.model.get_folder_contents("")
        assert len(self.model._cache) > 0

        # Clear all cache
        self.model.clear_cache()
        assert len(self.model._cache) == 0

        # Test clearing specific path
        self.model.get_folder_contents("folder1")
        self.model.clear_cache("folder1")
        assert "contents_folder1" not in self.model._cache

    def test_quick_search(self):
        """Test quick search functionality"""
        # Search in root
        results = self.model.quick_search("test", "")
        assert len(results) > 0

        # Search with short query
        results = self.model.quick_search("t", "")
        assert len(results) == 0

        # Search empty query
        results = self.model.quick_search("", "")
        assert len(results) == 0

        # Search in non-existent directory
        results = self.model.quick_search("test", "nonexistent")
        assert len(results) == 0

    def test_get_modified_time(self):
        """Test getting modified time"""
        mtime = self.model._get_modified_time("test.txt")
        assert isinstance(mtime, float)
        assert mtime > 0

        # Test non-existent file
        mtime = self.model._get_modified_time("nonexistent.txt")
        assert mtime == 0

    def test_create_folder_item_fast(self):
        """Test fast folder item creation"""
        item = self.model._create_folder_item_fast("test_folder", "")
        assert item["name"] == "test_folder"
        assert item["type"] == "folder"
        assert item["icon"] == "📁"
        assert item["size"] == "..."
        assert item["loading_size"] is True
        assert item["file_count"] == 0

    def test_create_file_item_fast(self):
        """Test fast file item creation"""
        item = self.model._create_file_item_fast("test.txt", "", 1024)
        assert item["name"] == "test.txt"
        assert item["type"] == "text"
        assert item["raw_size"] == 1024
        assert "size" in item

    def test_create_folder_item(self):
        """Test complete folder item creation"""
        item = self.model._create_folder_item("test_folder", "", 1024)
        assert item["name"] == "test_folder"
        assert item["type"] == "folder"
        assert item["folder_size"] == 1024
        assert "file_count" in item

    def test_create_file_item(self):
        """Test complete file item creation"""
        full_path = os.path.join(self.test_dir, "test.txt")
        item = self.model._create_file_item("test.txt", full_path, "", 1024)
        assert item["name"] == "test.txt"
        assert item["type"] == "text"
        assert item["full_path"] == full_path
        assert "size" in item

    def test_count_files_in_folder(self):
        """Test counting files in folder"""
        count = self.model._count_files_in_folder("folder1")
        assert count > 0

        # Test non-existent folder
        count = self.model._count_files_in_folder("nonexistent")
        assert count == 0

    def test_search_cache_cleanup(self):
        """Test search cache cleanup"""
        # Add old cache entry
        old_time = time.time() - 1000
        self.model._search_cache["old_search"] = ([], old_time)

        # Add new cache entry
        new_time = time.time()
        self.model._search_cache["new_search"] = ([], new_time)

        # Trigger cleanup
        self.model._clean_search_cache()

        assert "old_search" not in self.model._search_cache
        assert "new_search" in self.model._search_cache

    @patch(
        "models.file_system.Config.PERFORMANCE_CONFIG", {"DISABLE_FOLDER_SIZE": True}
    )
    def test_folder_size_disabled(self):
        """Test when folder size calculation is disabled"""
        # Reinitialize model with patched config
        model = FileSystemModel(self.test_dir)
        size = model.get_folder_size("folder1")
        assert size == 0

    def test_get_folder_size_lazy(self):
        """Test lazy folder size loading"""
        result = self.model.get_folder_size_lazy("folder1")
        assert "size" in result
        assert "file_count" in result

    def test_sorting_items(self):
        """Test sorting of items"""
        items = [
            {"name": "z_folder", "type": "folder"},
            {"name": "a_folder", "type": "folder"},
            {"name": "z_file.txt", "type": "text"},
            {"name": "a_file.txt", "type": "text"},
        ]

        # Sort items (folders first, then files, alphabetically)
        items.sort(
            key=lambda x: (x.get("type", "") != "folder", x.get("name", "").lower())
        )

        assert items[0]["name"] == "a_folder"
        assert items[1]["name"] == "z_folder"
        assert items[2]["name"] == "a_file.txt"
        assert items[3]["name"] == "z_file.txt"
