"""
Configuration settings for Universal File Server
"""

import os
import secrets
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).resolve().parent

class Config:
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY', secrets.token_hex(32))
    DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB
    HOST = os.environ.get('HOST', '0.0.0.0')
    PORT = int(os.environ.get('PORT', 8000))

    # File system settings
    ROOT_DRIVE = os.environ.get('ROOT_DRIVE', '../')
    if not os.path.exists(ROOT_DRIVE):
        ROOT_DRIVE = BASE_DIR / 'data'

    # Create data directory if it doesn't exist
    if ROOT_DRIVE == BASE_DIR / 'data':
        (BASE_DIR / 'data').mkdir(exist_ok=True)

    # Temporary directory for conversions
    TEMP_DIR = BASE_DIR / 'temp'
    TEMP_DIR.mkdir(exist_ok=True)

    # File extension categories
    FILE_EXTENSIONS = {
        'video': ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.mpg', '.mpeg'],
        'audio': ['.mp3', '.wav', '.ogg', '.flac', '.aac', '.wma', '.m4a'],
        'image': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg', '.tiff', '.ico'],
        'document': [
            # Microsoft Office
            '.pdf', '.doc', '.docx', '.dot', '.dotx', '.docm', '.dotm',
            '.xls', '.xlsx', '.xlsm', '.xlt', '.xltx', '.xltm', '.xlsb', '.xlam',
            '.ppt', '.pptx', '.pptm', '.pot', '.potx', '.potm', '.pps', '.ppsx', '.ppsm',
            # OpenDocument
            '.odt', '.ods', '.odp', '.odg', '.odf',
            # Other
            '.rtf', '.txt', '.csv', '.tsv', '.xml', '.json', '.yaml', '.yml'
        ],
        'text': ['.txt', '.py', '.js', '.html', '.css', '.json', '.xml', '.csv', '.md', '.log', '.ini', '.cfg', '.conf', '.yaml', '.yml'],
        'archive': ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2'],
        'code': ['.py', '.js', '.java', '.cpp', '.c', '.h', '.cs', '.php', '.rb', '.go', '.rs', '.ts', '.swift', '.kt', '.scala'],
        'executable': ['.exe', '.msi', '.bat', '.sh', '.bin', '.app']
    }

    # MIME types for file serving
    MIME_TYPES = {
        # Video
        '.mp4': 'video/mp4',
        '.avi': 'video/x-msvideo',
        '.mkv': 'video/x-matroska',
        '.mov': 'video/quicktime',
        '.wmv': 'video/x-ms-wmv',
        '.flv': 'video/x-flv',
        '.webm': 'video/webm',
        '.m4v': 'video/x-m4v',
        '.mpg': 'video/mpeg',
        '.mpeg': 'video/mpeg',
        
        # Audio
        '.mp3': 'audio/mpeg',
        '.wav': 'audio/wav',
        '.ogg': 'audio/ogg',
        '.flac': 'audio/flac',
        '.aac': 'audio/aac',
        '.wma': 'audio/x-ms-wma',
        '.m4a': 'audio/mp4',
        
        # Images
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.bmp': 'image/bmp',
        '.webp': 'image/webp',
        '.svg': 'image/svg+xml',
        '.tiff': 'image/tiff',
        '.ico': 'image/x-icon',
        
        # Documents
        '.pdf': 'application/pdf',
        
        # Microsoft Office
        '.doc': 'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.dot': 'application/msword-template',
        '.dotx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.template',
        '.docm': 'application/vnd.ms-word.document.macroEnabled.12',
        '.dotm': 'application/vnd.ms-word.template.macroEnabled.12',
        
        '.xls': 'application/vnd.ms-excel',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.xlsm': 'application/vnd.ms-excel.sheet.macroEnabled.12',
        '.xlt': 'application/vnd.ms-excel-template',
        '.xltx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.template',
        '.xltm': 'application/vnd.ms-excel.template.macroEnabled.12',
        '.xlsb': 'application/vnd.ms-excel.sheet.binary.macroEnabled.12',
        '.xlam': 'application/vnd.ms-excel.addin.macroEnabled.12',
        
        '.ppt': 'application/vnd.ms-powerpoint',
        '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        '.pptm': 'application/vnd.ms-powerpoint.presentation.macroEnabled.12',
        '.pot': 'application/vnd.ms-powerpoint-template',
        '.potx': 'application/vnd.openxmlformats-officedocument.presentationml.template',
        '.potm': 'application/vnd.ms-powerpoint.template.macroEnabled.12',
        '.pps': 'application/vnd.ms-powerpoint',
        '.ppsx': 'application/vnd.openxmlformats-officedocument.presentationml.slideshow',
        '.ppsm': 'application/vnd.ms-powerpoint.slideshow.macroEnabled.12',
        
        # OpenDocument
        '.odt': 'application/vnd.oasis.opendocument.text',
        '.ods': 'application/vnd.oasis.opendocument.spreadsheet',
        '.odp': 'application/vnd.oasis.opendocument.presentation',
        '.odg': 'application/vnd.oasis.opendocument.graphics',
        '.odf': 'application/vnd.oasis.opendocument.formula',
        
        # Other
        '.rtf': 'application/rtf',
        '.txt': 'text/plain',
        '.html': 'text/html',
        '.css': 'text/css',
        '.js': 'application/javascript',
        '.json': 'application/json',
        '.xml': 'application/xml',
        '.csv': 'text/csv',
        '.md': 'text/markdown',
        '.yaml': 'application/x-yaml',
        '.yml': 'application/x-yaml',
        
        # Archives
        '.zip': 'application/zip',
        '.rar': 'application/x-rar-compressed',
        '.7z': 'application/x-7z-compressed',
        '.tar': 'application/x-tar',
        '.gz': 'application/gzip',
        
        # Code
        '.py': 'text/x-python',
        '.java': 'text/x-java-source',
        '.cpp': 'text/x-c++src',
        '.c': 'text/x-csrc',
        '.h': 'text/x-chdr',
        '.cs': 'text/x-csharp',
        '.php': 'application/x-httpd-php',
        '.rb': 'text/x-ruby',
        '.go': 'text/x-go',
        '.rs': 'text/rust',
        '.ts': 'application/typescript',
        '.swift': 'text/x-swift',
        '.kt': 'text/x-kotlin',
        '.scala': 'text/x-scala',
        
        # Executables
        '.exe': 'application/x-msdownload',
        '.msi': 'application/x-msi',
        '.bat': 'application/x-msdos-program',
        '.sh': 'application/x-shellscript',
        '.bin': 'application/octet-stream',
        '.app': 'application/x-executable'
    }

    # Default MIME type
    DEFAULT_MIME_TYPE = 'application/octet-stream'

    # Media extensions for streaming
    MEDIA_EXTENSIONS = FILE_EXTENSIONS['video'] + FILE_EXTENSIONS['audio']
    
    # Office document extensions
    OFFICE_EXTENSIONS = {
        'word': ['.doc', '.docx', '.dot', '.dotx', '.docm', '.dotm', '.rtf', '.odt'],
        'excel': ['.xls', '.xlsx', '.xlsm', '.xlt', '.xltx', '.xltm', '.xlsb', '.xlam', '.ods', '.csv'],
        'powerpoint': ['.ppt', '.pptx', '.pptm', '.pot', '.potx', '.potm', '.pps', '.ppsx', '.ppsm', '.odp'],
        'pdf': ['.pdf']
    }
    
    # Performance settings
    PERFORMANCE_CONFIG = {
        'ENABLE_CACHE': True,
        'CACHE_TIMEOUT': 60,
        'MAX_PREVIEW_FILES': 100,
        'DISABLE_FOLDER_SIZE': False,
        'LAZY_LOAD_FOLDER_SIZE': True,
        'PRELOAD_LEVELS': 1,
        'MAX_OFFICE_PREVIEW_SIZE': 50 * 1024 * 1024,  # 50MB limit for Office doc preview
        'PDF_CONVERSION_TIMEOUT': 30,  # seconds
        'PDF_CACHE_DIR': TEMP_DIR / 'pdf_cache',
        'IMAGE_CACHE_DIR': TEMP_DIR / 'image_cache',
        'ENABLE_UNOCONV': False,  # Set to True if unoconv is installed
        'UNOCONV_PATH': '/usr/bin/unoconv',  # Path to unoconv
    }

    # File icons
    FILE_ICONS = {
        'folder': '📁',
        'video': '🎬',
        'audio': '🎵',
        'image': '🖼️',
        'document': '📄',
        'word': '📝',
        'excel': '📊',
        'powerpoint': '📽️',
        'pdf': '📕',
        'text': '📝',
        'archive': '📦',
        'code': '💻',
        'executable': '⚙️',
        'other': '📄'
    }

    # Upload settings
    ALLOWED_EXTENSIONS = set(
        FILE_EXTENSIONS['video'] +
        FILE_EXTENSIONS['audio'] +
        FILE_EXTENSIONS['image'] +
        FILE_EXTENSIONS['document'] +
        FILE_EXTENSIONS['text'] +
        FILE_EXTENSIONS['archive'] +
        FILE_EXTENSIONS['code'] +
        ['.*']  # Allow all files
    )

    # Security settings
    ALLOWED_HOSTS = ['*']  # Configure for production
    SESSION_COOKIE_SECURE = not DEBUG
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # Cache settings
    CACHE_TYPE = 'flask_caching.backends.SimpleCache'  # Use 'redis' or 'memcached' in production
    CACHE_DEFAULT_TIMEOUT = 300

    # Logging configuration
    LOGGING_CONFIG = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
            },
        },
        'handlers': {
            'default': {
                'level': 'INFO',
                'formatter': 'standard',
                'class': 'logging.StreamHandler',
            },
            'file': {
                'level': 'DEBUG',
                'formatter': 'standard',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': BASE_DIR / 'logs' / 'app.log',
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5,
            },
        },
        'loggers': {
            '': {
                'handlers': ['default', 'file'],
                'level': 'INFO',
                'propagate': True
            },
        }
    }