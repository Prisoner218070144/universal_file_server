"""
File upload handler with validation and processing
"""

import os
import shutil
import time
from typing import Any, Dict, List, Tuple

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from config import Config
from utils.helpers import (
    generate_unique_filename,
    is_allowed_file,
    is_safe_path,
    sanitize_filename,
)


class UploadHandler:
    def __init__(self, root_drive: str = None):
        self.root_drive = root_drive or Config.ROOT_DRIVE
        self.max_file_size = Config.MAX_CONTENT_LENGTH

    def handle_upload(
        self, files: List[FileStorage], target_path: str = ""
    ) -> Dict[str, Any]:
        """
        Handle multiple file uploads

        Args:
            files: List of FileStorage objects
            target_path: Target directory path

        Returns:
            Dictionary with upload results
        """
        results = {
            "success": [],
            "errors": [],
            "total": len(files),
            "success_count": 0,
            "error_count": 0,
        }

        # Build full target path
        full_target_path = os.path.join(self.root_drive, target_path)

        # Ensure target directory exists
        os.makedirs(full_target_path, exist_ok=True)

        for file in files:
            if not file or file.filename == "":
                results["errors"].append({"filename": "unknown", "error": "Empty file"})
                results["error_count"] += 1
                continue

            try:
                # Get original filename
                original_filename = file.filename

                # Sanitize filename
                safe_filename = sanitize_filename(original_filename)

                # Check if file is allowed
                if not is_allowed_file(safe_filename):
                    results["errors"].append(
                        {
                            "filename": original_filename,
                            "error": f"File type not allowed: {safe_filename}",
                        }
                    )
                    results["error_count"] += 1
                    continue

                # Check file size
                file.seek(0, 2)  # Seek to end
                file_size = file.tell()
                file.seek(0)  # Reset to beginning

                if file_size > self.max_file_size:
                    results["errors"].append(
                        {
                            "filename": original_filename,
                            "error": f"File too large: {file_size} > {self.max_file_size}",
                        }
                    )
                    results["error_count"] += 1
                    continue

                # Generate unique filename if needed
                final_filename = generate_unique_filename(
                    full_target_path, safe_filename
                )

                # Save file
                save_path = os.path.join(full_target_path, final_filename)

                # Read all content and write to file (works for both FileStorage and mocks)
                file.seek(0)
                content = file.read()
                if content:
                    with open(save_path, "wb") as f:
                        if isinstance(content, bytes):
                            f.write(content)
                        else:
                            f.write(content.encode("utf-8"))

                # Verify file was saved
                if os.path.exists(save_path):
                    results["success"].append(
                        {
                            "original_name": original_filename,
                            "saved_name": final_filename,
                            "path": os.path.join(target_path, final_filename).replace(
                                "\\", "/"
                            ),
                            "size": file_size,
                            "timestamp": time.time(),
                        }
                    )
                    results["success_count"] += 1
                else:
                    results["errors"].append(
                        {"filename": original_filename, "error": "Failed to save file"}
                    )
                    results["error_count"] += 1

            except Exception as e:
                results["errors"].append(
                    {
                        "filename": (
                            file.filename if hasattr(file, "filename") else "unknown"
                        ),
                        "error": str(e),
                    }
                )
                results["error_count"] += 1

        return results

    def create_folder(self, folder_name: str, parent_path: str = "") -> Dict[str, Any]:
        try:
            # Sanitize folder name
            safe_folder_name = sanitize_filename(folder_name)

            if not safe_folder_name or safe_folder_name.strip() == "":
                return {"success": False, "error": "Invalid folder name"}

            # Build full path
            full_parent_path = os.path.join(self.root_drive, parent_path)
            folder_path = os.path.join(full_parent_path, safe_folder_name)

            # Check if folder already exists
            if os.path.exists(folder_path):
                return {
                    "success": False,
                    "error": f"Folder already exists: {safe_folder_name}",
                }

            # Create folder - use exist_ok=False to avoid race conditions
            try:
                os.makedirs(folder_path, exist_ok=False)
            except FileExistsError:
                # This handles the race condition where folder was created between check and creation
                return {
                    "success": False,
                    "error": f"Folder already exists: {safe_folder_name}",
                }

            # Verify creation
            if os.path.exists(folder_path) and os.path.isdir(folder_path):
                return {
                    "success": True,
                    "folder_name": safe_folder_name,
                    "folder_path": os.path.join(parent_path, safe_folder_name).replace(
                        "\\", "/"
                    ),
                    "message": f'Folder "{safe_folder_name}" created successfully',
                }
            else:
                return {"success": False, "error": "Failed to create folder"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def create_file(self, filename: str, parent_path: str = "") -> Dict[str, Any]:
        try:
            # Sanitize filename
            safe_filename = sanitize_filename(filename)

            if not safe_filename or safe_filename.strip() == "":
                return {"success": False, "error": "Invalid filename"}

            # Build full path
            full_parent_path = os.path.join(self.root_drive, parent_path)
            file_path = os.path.join(full_parent_path, safe_filename)

            # Check if file already exists
            if os.path.exists(file_path):
                return {
                    "success": False,
                    "error": f"File already exists: {safe_filename}",
                }

            # Create empty file using 'x' mode to prevent overwriting
            try:
                with open(file_path, "x") as f:
                    pass
            except FileExistsError:
                # This handles the race condition where file was created between check and creation
                return {
                    "success": False,
                    "error": f"File already exists: {safe_filename}",
                }

            # Verify creation
            if os.path.exists(file_path) and os.path.isfile(file_path):
                return {
                    "success": True,
                    "filename": safe_filename,
                    "file_path": os.path.join(parent_path, safe_filename).replace(
                        "\\", "/"
                    ),
                    "message": f'File "{safe_filename}" created successfully',
                }
            else:
                return {"success": False, "error": "Failed to create file"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def validate_upload_path(self, target_path: str) -> Tuple[bool, str]:
        """
        Validate upload target path

        Args:
            target_path: Path to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Build full path
            full_path = os.path.join(self.root_drive, target_path)

            # Check for path traversal
            if not is_safe_path(self.root_drive, full_path):
                return False, "Invalid path"

            # Check if path exists and is a directory
            if not os.path.exists(full_path):
                return False, "Target directory does not exist"

            if not os.path.isdir(full_path):
                return False, "Target path is not a directory"

            # Check write permissions
            if not os.access(full_path, os.W_OK):
                return False, "No write permission"

            return True, ""

        except Exception as e:
            return False, str(e)

    def cleanup_incomplete_uploads(self, timeout_seconds: int = 3600) -> int:
        """
        Cleanup incomplete upload files older than timeout

        Args:
            timeout_seconds: Timeout in seconds

        Returns:
            Number of files cleaned up
        """
        cleanup_count = 0
        current_time = time.time()

        # Look for .part files (incomplete uploads)
        for root, dirs, files in os.walk(self.root_drive):
            for file in files:
                if file.endswith(".part"):
                    file_path = os.path.join(root, file)
                    try:
                        file_mtime = os.path.getmtime(file_path)
                        if current_time - file_mtime > timeout_seconds:
                            os.remove(file_path)
                            cleanup_count += 1
                    except Exception:
                        continue

        return cleanup_count
