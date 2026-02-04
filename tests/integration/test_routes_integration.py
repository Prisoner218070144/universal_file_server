"""
Integration tests for routes
"""
import os
import tempfile
import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from werkzeug.datastructures import FileStorage
from io import BytesIO


class TestRoutesIntegration:
    """Integration tests for routes"""

    def setup_method(self):
        """Setup test environment"""
        self.test_dir = tempfile.mkdtemp()

        # Create test directory structure
        os.makedirs(os.path.join(self.test_dir, "test_folder"))
        os.makedirs(os.path.join(self.test_dir, "folder1", "subfolder"))
        os.makedirs(os.path.join(self.test_dir, "folder 1"))  # Folder with space

        # Create test files
        test_files = [
            ("test.txt", "Text content"),
            ("image.jpg", b"fake image"),
            ("video.mp4", b"fake video"),
            ("document.pdf", b"fake pdf"),
            ("audio.mp3", b"fake audio"),
            ("data.json", '{"key": "value"}'),
            ("script.py", "print('Hello')"),
            ("styles.css", "body { color: red; }"),
            ("index.html", "<html><body>Hello</body></html>"),
            ("readme.md", "# Readme"),
            ("data.csv", "name,age\nJohn,30"),
            ("config.ini", "[section]\nkey=value"),
        ]

        for filename, content in test_files:
            path = os.path.join(self.test_dir, filename)
            mode = "wb" if isinstance(content, bytes) else "w"
            with open(path, mode) as f:
                f.write(content)

        # Create Word document for testing
        docx_path = os.path.join(self.test_dir, "document.docx")
        with open(docx_path, "wb") as f:
            # Write minimal DOCX structure
            f.write(b"PK\x03\x04")  # ZIP header

        # Create MKV file
        mkv_path = os.path.join(self.test_dir, "video.mkv")
        with open(mkv_path, "wb") as f:
            f.write(b"fake mkv")

        # Create .doc file
        doc_path = os.path.join(self.test_dir, "document.doc")
        with open(doc_path, "wb") as f:
            f.write(b"fake doc")

        # Create large file
        large_path = os.path.join(self.test_dir, "large.txt")
        with open(large_path, "w") as f:
            f.write("X" * (6 * 1024 * 1024))  # 6MB

        # Patch config
        self.config_patcher = patch("controllers.routes.Config")
        self.mock_config = self.config_patcher.start()

        # Configure mock config
        self.mock_config.ROOT_DRIVE = self.test_dir
        self.mock_config.MEDIA_EXTENSIONS = {".mp4", ".mkv", ".mp3", ".avi", ".mov"}
        self.mock_config.MIME_TYPES = {
            ".txt": "text/plain",
            ".jpg": "image/jpeg",
            ".mp4": "video/mp4",
            ".mkv": "video/x-matroska",
            ".mp3": "audio/mpeg",
            ".pdf": "application/pdf",
            ".json": "application/json",
            ".py": "text/x-python",
            ".css": "text/css",
            ".html": "text/html",
            ".md": "text/markdown",
            ".csv": "text/csv",
            ".ini": "text/plain",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".doc": "application/msword",
        }
        self.mock_config.FILE_EXTENSIONS = {
            "video": [".mp4", ".mkv", ".avi", ".mov"],
            "audio": [".mp3", ".wav", ".flac"],
            "image": [".jpg", ".jpeg", ".png", ".gif"],
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
        self.mock_config.ALLOWED_EXTENSIONS = [".*"]
        self.mock_config.MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB
        self.mock_config.PERFORMANCE_CONFIG = {
            "DISABLE_FOLDER_SIZE": False,
            "CACHE_TIMEOUT": 10,
            "MAX_WORD_PREVIEW_SIZE": 10 * 1024 * 1024,
        }

        # Import routes after patching config
        from controllers.routes import routes

        # Create test app
        from flask import Flask

        self.app = Flask(__name__)
        self.app.register_blueprint(routes)
        self.app.config["TESTING"] = True
        self.app.config["SECRET_KEY"] = "test-key"

        self.client = self.app.test_client()

        # Mock template renderer
        self.template_patcher = patch("controllers.routes.template_renderer")
        self.mock_template = self.template_patcher.start()
        self.mock_template.render_browse_page.return_value = "Browse page"
        self.mock_template.render_search_page.return_value = "Search page"

        # Mock file system model
        self.model_patcher = patch("controllers.routes.file_system")
        self.mock_model = self.model_patcher.start()

        # Set the root_drive attribute to use the test directory
        self.mock_model.root_drive = self.test_dir

        # Set up mock methods
        self.mock_model.get_folder_contents.return_value = ([], None)
        self.mock_model.get_breadcrumbs.return_value = []
        self.mock_model.get_parent_path.return_value = ""
        self.mock_model.count_file_types.return_value = {
            "folders": 0,
            "videos": 0,
            "audios": 0,
            "images": 0,
            "documents": 0,
            "text": 0,
            "others": 0,
        }
        self.mock_model.get_files_by_type.return_value = {}
        self.mock_model.get_file_type.return_value = "text"
        self.mock_model.format_file_size.return_value = "1 KB"
        self.mock_model.get_folder_size_lazy.return_value = {
            "size": "1.0 KB",
            "file_count": 5,
        }
        self.mock_model.search_files.return_value = []

        # Mock upload handler
        self.upload_patcher = patch("controllers.routes.upload_handler")
        self.mock_upload = self.upload_patcher.start()

    def teardown_method(self):
        """Cleanup test environment"""
        import shutil

        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

        self.config_patcher.stop()
        self.template_patcher.stop()
        self.model_patcher.stop()
        self.upload_patcher.stop()

    def test_index_route(self):
        """Test index route"""
        # Mock folder contents
        mock_items = [
            {"name": "test.txt", "type": "text", "path": "test.txt"},
            {"name": "folder1", "type": "folder", "path": "folder1"},
        ]
        self.mock_model.get_folder_contents.return_value = (mock_items, None)
        self.mock_model.get_breadcrumbs.return_value = []
        self.mock_model.get_parent_path.return_value = ""
        self.mock_model.count_file_types.return_value = {
            "folders": 1,
            "videos": 0,
            "audios": 0,
            "images": 0,
            "documents": 0,
            "text": 1,
            "others": 0,
        }
        self.mock_model.get_files_by_type.return_value = {}

        response = self.client.get("/")

        assert response.status_code == 200
        self.mock_template.render_browse_page.assert_called_once()

    def test_browse_folder_success(self):
        """Test browsing existing folder"""
        mock_items = [
            {"name": "file.txt", "type": "text", "path": "folder1/file.txt"},
        ]
        self.mock_model.get_folder_contents.return_value = (mock_items, None)
        self.mock_model.get_breadcrumbs.return_value = [
            {"name": "folder1", "path": "folder1"}
        ]
        self.mock_model.get_parent_path.return_value = ""
        self.mock_model.count_file_types.return_value = {
            "folders": 0,
            "videos": 0,
            "audios": 0,
            "images": 0,
            "documents": 0,
            "text": 1,
            "others": 0,
        }
        self.mock_model.get_files_by_type.return_value = {}

        response = self.client.get("/browse/folder1")

        assert response.status_code == 200
        self.mock_template.render_browse_page.assert_called_once()

    def test_browse_folder_not_found(self):
        """Test browsing non-existent folder"""
        self.mock_model.get_folder_contents.return_value = (None, "Path not found")

        response = self.client.get("/browse/nonexistent")

        assert response.status_code == 404
        assert "Error:" in response.get_data(as_text=True)

    def test_browse_with_double_slash(self):
        """Test browsing with double slash in URL"""
        response = self.client.get("/browse//")
        assert response.status_code == 308

    def test_browse_url_encoded_path(self):
        """Test browsing with URL encoded path"""
        # Create a file in the folder with space
        test_file = os.path.join(self.test_dir, "folder 1", "test.txt")
        with open(test_file, "w") as f:
            f.write("Test content")

        # Mock the folder contents
        mock_items = [
            {"name": "test.txt", "type": "text", "path": "folder 1/test.txt"},
        ]

        # Create a side effect to handle different paths
        def get_folder_contents_side_effect(path):
            if path == "folder 1":
                return (mock_items, None)
            return ([], None)

        self.mock_model.get_folder_contents.side_effect = (
            get_folder_contents_side_effect
        )
        self.mock_model.get_breadcrumbs.return_value = [
            {"name": "folder 1", "path": "folder 1"}
        ]
        self.mock_model.get_parent_path.return_value = ""
        self.mock_model.count_file_types.return_value = {
            "folders": 0,
            "videos": 0,
            "audios": 0,
            "images": 0,
            "documents": 0,
            "text": 1,
            "others": 0,
        }
        self.mock_model.get_files_by_type.return_value = {}

        response = self.client.get("/browse/folder%201")

        assert response.status_code == 200
        # Verify path was decoded
        call_args = self.mock_model.get_folder_contents.call_args[0][0]
        assert ".." not in call_args  # Path traversal removed

    def test_serve_text_file(self):
        """Test serving text file"""
        response = self.client.get("/file/test.txt")
        assert response.status_code == 200
        # Check Content-Type more flexibly (headers might have extra spaces)
        content_type = response.headers.get("Content-Type", "")
        assert "text/plain" in content_type
        assert "charset=utf-8" in content_type.lower()
        assert b"Text content" in response.data

    def test_serve_pdf_file(self):
        """Test serving PDF file"""
        response = self.client.get("/file/document.pdf")

        assert response.status_code == 200
        assert response.mimetype == "application/pdf"

    def test_serve_media_file_redirect(self):
        """Test serving media file (should redirect to stream)"""
        response = self.client.get("/file/video.mp4", follow_redirects=False)

        assert response.status_code == 302
        assert "/stream/video.mp4" in response.location

    def test_serve_mkv_file_download(self):
        """Test serving MKV file for download"""
        response = self.client.get("/download/video.mkv")

        assert response.status_code == 200
        assert response.mimetype == "video/x-matroska"
        assert "attachment" in response.headers.get("Content-Disposition", "")

    def test_serve_file_not_found(self):
        """Test serving non-existent file"""
        response = self.client.get("/file/nonexistent.txt")

        assert response.status_code == 404

    def test_stream_file_full(self):
        """Test streaming file without range header"""
        response = self.client.get("/stream/test.txt")

        assert response.status_code == 200
        assert "Accept-Ranges" in response.headers
        assert response.headers["Accept-Ranges"] == "bytes"

    def test_stream_file_with_range(self):
        """Test streaming file with range header"""
        headers = {"Range": "bytes=0-4"}
        response = self.client.get("/stream/test.txt", headers=headers)

        assert response.status_code == 206  # Partial Content
        assert "Content-Range" in response.headers

    def test_stream_file_not_found(self):
        """Test streaming non-existent file"""
        response = self.client.get("/stream/nonexistent.txt")

        assert response.status_code == 404

    def test_download_folder_zip(self):
        """Test downloading folder as ZIP"""
        response = self.client.get("/download_folder/folder1")

        assert response.status_code == 200
        assert response.mimetype == "application/zip"
        assert "attachment" in response.headers.get("Content-Disposition", "")

    def test_download_folder_not_found(self):
        """Test downloading non-existent folder"""
        response = self.client.get("/download_folder/nonexistent")

        assert response.status_code == 404

    def test_search_files(self):
        """Test file search"""
        mock_results = [
            {"name": "test.txt", "type": "text", "path": "test.txt"},
        ]
        self.mock_model.search_files.return_value = mock_results

        response = self.client.get("/search?q=test")

        assert response.status_code == 200
        self.mock_template.render_search_page.assert_called_once()

    def test_search_empty_query(self):
        """Test search with empty query (should redirect to home)"""
        response = self.client.get("/search?q=", follow_redirects=False)

        assert response.status_code == 302
        assert response.location == "/"

    def test_upload_files_success(self):
        """Test successful file upload"""
        self.mock_upload.handle_upload.return_value = {
            "success": [{"original_name": "test.txt", "saved_name": "test.txt"}],
            "errors": [],
            "success_count": 1,
            "error_count": 0,
        }

        data = {"files[]": (BytesIO(b"test content"), "test.txt")}

        response = self.client.post(
            "/upload/folder1", data=data, content_type="multipart/form-data"
        )

        assert response.status_code == 200
        json_response = json.loads(response.data)
        assert json_response["success_count"] == 1

    def test_upload_no_files(self):
        """Test upload with no files selected"""
        response = self.client.post("/upload/folder1")

        assert response.status_code == 400
        json_response = json.loads(response.data)
        assert "No files selected" in json_response["error"]

    def test_upload_empty_file_list(self):
        """Test upload with empty file list"""
        data = {"files[]": (BytesIO(b""), "")}

        response = self.client.post(
            "/upload/folder1", data=data, content_type="multipart/form-data"
        )

        assert response.status_code == 400
        json_response = json.loads(response.data)
        assert "No files selected" in json_response["error"]

    def test_create_folder_success(self):
        """Test creating folder"""
        self.mock_upload.create_folder.return_value = {
            "success": True,
            "folder_name": "new_folder",
            "folder_path": "folder1/new_folder",
        }

        data = {"folder_name": "new_folder"}

        response = self.client.post(
            "/create_folder/folder1",
            data=json.dumps(data),
            content_type="application/json",
        )

        assert response.status_code == 200
        json_response = json.loads(response.data)
        assert json_response["success"] is True

    def test_create_folder_missing_name(self):
        """Test creating folder without name"""
        response = self.client.post(
            "/create_folder/folder1",
            data=json.dumps({}),
            content_type="application/json",
        )

        assert response.status_code == 400
        json_response = json.loads(response.data)
        assert "Folder name is required" in json_response["error"]

    def test_create_file_success(self):
        """Test creating file"""
        self.mock_upload.create_file.return_value = {
            "success": True,
            "filename": "new_file.txt",
            "file_path": "folder1/new_file.txt",
        }

        data = {"filename": "new_file.txt"}

        response = self.client.post(
            "/create_file/folder1",
            data=json.dumps(data),
            content_type="application/json",
        )

        assert response.status_code == 200
        json_response = json.loads(response.data)
        assert json_response["success"] is True

    def test_get_preview_data(self):
        """Test getting file preview data"""
        # Mock the folder contents for this test
        mock_items = [
            {"name": "test.txt", "type": "text", "path": "test.txt"},
            {"name": "test2.txt", "type": "text", "path": "test2.txt"},
        ]

        self.mock_model.get_folder_contents.return_value = (mock_items, None)
        self.mock_model.get_file_type.return_value = "text"
        self.mock_model.format_file_size.return_value = "12 B"

        response = self.client.get("/api/preview/test.txt")

        assert response.status_code == 200
        json_response = json.loads(response.data)
        assert json_response["success"] is True
        assert json_response["filename"] == "test.txt"

    def test_get_preview_data_not_found(self):
        """Test getting preview for non-existent file"""
        with patch("os.path.exists", return_value=False):
            response = self.client.get("/api/preview/nonexistent.txt")

            assert response.status_code == 404
            json_response = json.loads(response.data)
            assert "File not found" in json_response["error"]

    def test_get_file_content_success(self):
        """Test getting file content for text preview"""
        # Mock the file reading for this test
        with patch("builtins.open", create=True) as mock_open:
            mock_file = MagicMock()
            mock_file.read.return_value = "Text content"
            mock_open.return_value.__enter__.return_value = mock_file

            # Mock file size
            with patch("os.path.getsize", return_value=12):
                response = self.client.get("/api/file_content/test.txt")

                assert response.status_code == 200
                json_response = json.loads(response.data)
                assert json_response["success"] is True
                assert json_response["content"] == "Text content"

    def test_get_file_content_too_large(self):
        """Test getting file content for large file"""
        # Mock file size to be > 5MB
        with patch("os.path.getsize", return_value=6 * 1024 * 1024):
            response = self.client.get("/api/file_content/large.txt")

            assert response.status_code == 200
            json_response = json.loads(response.data)
            assert "File too large" in json_response["error"]

    def test_get_file_content_not_text(self):
        """Test getting content for non-text file"""
        response = self.client.get("/api/file_content/image.jpg")

        assert response.status_code == 400
        json_response = json.loads(response.data)
        assert "File is not a text file" in json_response["error"]

    @patch("controllers.routes.mammoth")
    def test_get_word_document_content_docx(self, mock_mammoth):
        """Test getting Word document content (DOCX)"""
        # Setup mock mammoth
        mock_result = Mock()
        mock_result.value = "<p>Converted content</p>"
        mock_result.messages = []
        mock_mammoth.convert_to_html.return_value = mock_result

        # Mock file size
        with patch("os.path.getsize", return_value=1024):
            # Mock file opening
            with patch("builtins.open", create=True) as mock_open:
                mock_file = MagicMock()
                mock_file.__enter__.return_value = mock_file
                mock_open.return_value = mock_file

                response = self.client.get("/api/word_document_content/document.docx")

                assert response.status_code == 200
                json_response = json.loads(response.data)
                assert json_response["success"] is True
                assert "content" in json_response

    def test_get_word_document_content_doc(self):
        """Test getting Word document content (DOC)"""
        # Mock file size
        with patch("os.path.getsize", return_value=1024):
            response = self.client.get("/api/word_document_content/document.doc")

            assert response.status_code == 200
            json_response = json.loads(response.data)
            assert json_response["file_type"] == "doc"
            assert json_response["needs_conversion"] is True

    def test_get_word_document_content_not_word(self):
        """Test getting non-Word document content"""
        response = self.client.get("/api/word_document_content/test.txt")

        assert response.status_code == 400
        json_response = json.loads(response.data)
        assert "File is not a Word document" in json_response["error"]

    def test_get_directory_files(self):
        """Test getting directory files for playlist"""
        mock_items = [
            {"name": "test.txt", "type": "text", "path": "test.txt"},
            {"name": "video.mp4", "type": "video", "path": "video.mp4"},
        ]
        self.mock_model.get_folder_contents.return_value = (mock_items, None)

        response = self.client.get("/get_directory_files/")

        assert response.status_code == 200
        json_response = json.loads(response.data)
        assert "files" in json_response
        assert len(json_response["files"]) == 2

    def test_delete_file_success(self):
        """Test deleting file"""
        # Mock file existence
        with patch("os.path.exists", return_value=True):
            with patch("os.path.isdir", return_value=False):
                with patch("os.remove") as mock_remove:
                    response = self.client.delete("/delete/test.txt")

                    assert response.status_code == 200
                    json_response = json.loads(response.data)
                    assert json_response["success"] is True
                    mock_remove.assert_called_once()

    def test_delete_folder_success(self):
        """Test deleting folder"""
        # Mock folder existence
        with patch("os.path.exists", return_value=True):
            with patch("os.path.isdir", return_value=True):
                with patch("shutil.rmtree") as mock_rmtree:
                    response = self.client.delete("/delete/folder1")

                    assert response.status_code == 200
                    json_response = json.loads(response.data)
                    assert json_response["success"] is True
                    mock_rmtree.assert_called_once()

    def test_delete_not_found(self):
        """Test deleting non-existent file"""
        with patch("os.path.exists", return_value=False):
            response = self.client.delete("/delete/nonexistent.txt")

            assert response.status_code == 404
            json_response = json.loads(response.data)
            assert "File not found" in json_response["error"]

    def test_copy_item_success(self):
        """Test copying item"""
        with patch("os.path.exists", side_effect=[True, False]):
            with patch("os.path.isdir", return_value=False):
                with patch("shutil.copy2") as mock_copy:
                    data = {
                        "source": "test.txt",
                        "destination": "folder1",
                        "overwrite": False,
                    }

                    response = self.client.post(
                        "/copy", data=json.dumps(data), content_type="application/json"
                    )

                    assert response.status_code == 200
                    json_response = json.loads(response.data)
                    assert json_response["success"] is True
                    mock_copy.assert_called_once()

    def test_copy_item_missing_params(self):
        """Test copying without required parameters"""
        data = {"source": "test.txt"}  # Missing destination

        response = self.client.post(
            "/copy", data=json.dumps(data), content_type="application/json"
        )

        assert response.status_code == 400
        json_response = json.loads(response.data)
        assert "Source and destination are required" in json_response["error"]

    def test_move_item_success(self):
        """Test moving item"""
        # Create the actual file structure
        source_file = os.path.join(self.test_dir, "to_move.txt")
        with open(source_file, "w") as f:
            f.write("Move me")

        # Create destination folder
        dest_folder = os.path.join(self.test_dir, "folder1")
        os.makedirs(dest_folder, exist_ok=True)

        # Mock the necessary functions
        with patch("os.path.exists") as mock_exists:
            # Make exists return True for source, False for destination file
            def exists_side_effect(path):
                if path == source_file:
                    return True
                if path == os.path.join(dest_folder, "to_move.txt"):
                    return False
                # For any other path, use the real os.path.exists
                return os.path.exists(path)

            mock_exists.side_effect = exists_side_effect

            with patch("os.path.isdir") as mock_isdir:
                mock_isdir.return_value = False  # Source is a file

                with patch("shutil.move") as mock_move:
                    data = {
                        "source": "to_move.txt",
                        "destination": "folder1",
                        "overwrite": False,
                    }

                    response = self.client.post(
                        "/move", data=json.dumps(data), content_type="application/json"
                    )

                    assert response.status_code == 200
                    json_response = json.loads(response.data)
                    assert json_response["success"] is True

                    # Verify move was called
                    assert mock_move.called

    def test_folder_size_api(self):
        """Test folder size API endpoint"""
        response = self.client.get("/api/folder_size/folder1")

        assert response.status_code == 200
        json_response = json.loads(response.data)
        assert "size" in json_response
        assert "file_count" in json_response

    def test_path_traversal_protection(self):
        """Test path traversal protection"""
        # Test with path traversal attempts
        test_paths = [
            "../etc/passwd",
            "..\\Windows\\System32",
            "folder/../../root",
            "folder/../..",
        ]

        for path in test_paths:
            encoded_path = path.replace(" ", "%20")
            response = self.client.get(f"/browse/{encoded_path}")

            # Should either 404 or have sanitized path
            if response.status_code == 200:
                # Check that path traversal was removed
                call_args = self.mock_model.get_folder_contents.call_args[0][0]
                assert ".." not in call_args

    def test_upload_exception_handling(self):
        """Test upload exception handling"""
        self.mock_upload.handle_upload.side_effect = Exception("Upload failed")

        data = {"files[]": (BytesIO(b"test content"), "test.txt")}

        response = self.client.post(
            "/upload/folder1", data=data, content_type="multipart/form-data"
        )

        assert response.status_code == 500
        json_response = json.loads(response.data)
        assert "Upload failed" in json_response["error"]

    def test_create_folder_exception_handling(self):
        """Test create folder exception handling"""
        self.mock_upload.create_folder.side_effect = Exception("Permission denied")

        data = {"folder_name": "new_folder"}

        response = self.client.post(
            "/create_folder/folder1",
            data=json.dumps(data),
            content_type="application/json",
        )

        assert response.status_code == 500
        json_response = json.loads(response.data)
        assert "Permission denied" in json_response["error"]

    def test_handle_range_request(self):
        """Test range request handling"""
        from controllers.routes import _handle_range_request

        # Create a test file
        test_file = os.path.join(self.test_dir, "range_test.txt")
        with open(test_file, "w") as f:
            f.write("0123456789")

        file_size = os.path.getsize(test_file)

        # Mock request
        mock_request = Mock(headers={"Range": "bytes=2-5"})

        with patch("controllers.routes.request", mock_request):
            response = _handle_range_request(
                test_file, file_size, "bytes=2-5", "text/plain"
            )

            assert response.status_code == 206
            assert "Content-Range" in response.headers

    def test_serve_full_file(self):
        """Test serving full file"""
        from controllers.routes import _serve_full_file

        test_file = os.path.join(self.test_dir, "test.txt")
        file_size = os.path.getsize(test_file)

        response = _serve_full_file(test_file, file_size, "text/plain")

        assert response.status_code == 200
        assert "Accept-Ranges" in response.headers

    def test_get_mime_type(self):
        """Test MIME type detection"""
        from controllers.routes import _get_mime_type

        # Test MKV special handling
        assert _get_mime_type("video.mkv") == "video/x-matroska"

        # Test from config
        assert _get_mime_type("test.txt") == "text/plain"

        # Test unknown extension
        assert _get_mime_type("unknown.xyz") == "application/octet-stream"

    def test_clean_word_html(self):
        """Test Word HTML cleaning"""
        from controllers.routes import _clean_word_html

        html = "<p>Test content</p>"
        cleaned = _clean_word_html(html)

        assert "word-document-preview" in cleaned
        assert "Test content" in cleaned

        # Test empty HTML
        assert _clean_word_html("") == ""
        assert _clean_word_html(None) is None
