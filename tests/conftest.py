"""
Pytest configuration and fixtures
"""
import os
import sys
import tempfile
import pytest
from unittest.mock import Mock, patch, MagicMock
from flask import Flask


# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


@pytest.fixture
def temp_directory():
    """Create a temporary directory for testing"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir

    # Cleanup
    import shutil

    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


@pytest.fixture
def mock_config():
    """Mock configuration"""
    with patch("controllers.routes.Config") as mock_config:
        # Set default values
        mock_config.ROOT_DRIVE = "/test/drive"
        mock_config.MEDIA_EXTENSIONS = {".mp4", ".mkv", ".mp3"}
        mock_config.MIME_TYPES = {
            ".txt": "text/plain",
            ".jpg": "image/jpeg",
            ".mp4": "video/mp4",
            ".mkv": "video/x-matroska",
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
            ".mp3": "audio/mpeg",
        }
        mock_config.FILE_EXTENSIONS = {
            "video": [".mp4", ".mkv"],
            "audio": [".mp3"],
            "image": [".jpg", ".jpeg"],
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
        mock_config.FILE_ICONS = {
            "folder": "📁",
            "video": "🎬",
            "audio": "🎵",
            "image": "🖼️",
            "document": "📄",
            "text": "📝",
            "other": "📄",
        }
        mock_config.ALLOWED_EXTENSIONS = [".*"]
        mock_config.MAX_CONTENT_LENGTH = 100 * 1024 * 1024
        mock_config.PERFORMANCE_CONFIG = {
            "DISABLE_FOLDER_SIZE": False,
            "CACHE_TIMEOUT": 10,
            "MAX_WORD_PREVIEW_SIZE": 10 * 1024 * 1024,
        }
        mock_config.DEFAULT_MIME_TYPE = "application/octet-stream"
        yield mock_config


@pytest.fixture
def flask_app():
    """Create a Flask app for testing"""
    app = Flask(__name__, template_folder=os.path.join(project_root, "templates"))
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret-key"
    app.config["SERVER_NAME"] = "localhost"  # Required for URL building
    return app


@pytest.fixture
def test_client(flask_app):
    """Create a test client"""
    return flask_app.test_client()


@pytest.fixture
def mock_file_storage():
    """Create a mock FileStorage object"""

    def _create_mock_file(filename="test.txt", content=b"test content"):
        mock_file = Mock()
        mock_file.filename = filename
        mock_file.read = Mock(return_value=content)
        mock_file.seek = Mock()
        mock_file.save = Mock()
        mock_file.tell = Mock(
            return_value=len(content)
            if isinstance(content, bytes)
            else len(content.encode("utf-8"))
        )
        return mock_file

    return _create_mock_file


@pytest.fixture
def sample_file_structure(temp_directory):
    """Create a sample file structure for testing"""
    # Create directories
    os.makedirs(os.path.join(temp_directory, "folder1", "subfolder"))
    os.makedirs(os.path.join(temp_directory, "folder2"))

    # Create files
    files = [
        ("file1.txt", "Content 1"),
        ("file2.jpg", b"fake image"),
        ("file3.mp4", b"fake video"),
        ("file4.pdf", b"fake pdf"),
        ("file5.mp3", b"fake audio"),
        ("file6.json", '{"key": "value"}'),
        ("file7.py", "print('Hello')"),
        ("folder1/file8.txt", "Nested content"),
        ("folder1/subfolder/file9.txt", "Deep nested"),
        ("document.docx", b"fake docx"),
        ("document.doc", b"fake doc"),
        ("video.mkv", b"fake mkv"),
    ]

    for path, content in files:
        full_path = os.path.join(temp_directory, path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        mode = "wb" if isinstance(content, bytes) else "w"
        with open(full_path, mode) as f:
            f.write(content)

    return temp_directory


@pytest.fixture
def mock_os_walk():
    """Mock os.walk for testing"""
    with patch("os.walk") as mock_walk:
        yield mock_walk


@pytest.fixture
def mock_os_scandir():
    """Mock os.scandir for testing"""
    with patch("os.scandir") as mock_scandir:
        yield mock_scandir


@pytest.fixture
def mock_os_path():
    """Mock os.path functions for testing"""
    with patch("os.path") as mock_path:
        yield mock_path


@pytest.fixture
def mock_shutil():
    """Mock shutil functions for testing"""
    with patch("shutil") as mock_shutil:
        yield mock_shutil


@pytest.fixture
def mock_time():
    """Mock time functions for testing"""
    with patch("time.time") as mock_time:
        mock_time.return_value = 1000.0
        yield mock_time


@pytest.fixture
def patch_all_dependencies():
    """Patch all external dependencies for isolated testing"""
    patches = [
        patch("os.path.exists"),
        patch("os.path.isdir"),
        patch("os.path.isfile"),
        patch("os.path.getsize"),
        patch("os.path.getmtime"),
        patch("os.listdir"),
        patch("os.scandir"),
        patch("os.walk"),
        patch("os.makedirs"),
        patch("os.remove"),
        patch("shutil.rmtree"),
        patch("shutil.copy2"),
        patch("shutil.copytree"),
        patch("shutil.move"),
        patch("time.time"),
    ]

    mocks = []
    for p in patches:
        mocks.append(p.start())

    yield mocks

    for p in patches:
        p.stop()


@pytest.fixture
def mock_mammoth():
    """Mock mammoth for Word document testing"""
    with patch("controllers.routes.mammoth") as mock_mammoth:
        mock_result = Mock()
        mock_result.value = "<p>Converted content</p>"
        mock_result.messages = []
        mock_mammoth.convert_to_html.return_value = mock_result
        yield mock_mammoth


def pytest_configure(config):
    """Pytest configuration hook"""
    # Add custom markers
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "functional: mark test as functional test")
    config.addinivalue_line("markers", "slow: mark test as slow running")


def pytest_collection_modifyitems(config, items):
    """Modify test collection"""
    # Skip slow tests by default unless --run-slow is specified
    if not config.getoption("--run-slow"):
        skip_slow = pytest.mark.skip(reason="need --run-slow option to run")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)


def pytest_addoption(parser):
    """Add custom command line options"""
    parser.addoption(
        "--run-slow", action="store_true", default=False, help="run slow tests"
    )
    parser.addoption(
        "--coverage",
        action="store_true",
        default=False,
        help="generate coverage report",
    )
