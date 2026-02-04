"""
File system models with enhanced features and optimized performance
"""

import fnmatch
import mimetypes
import os
import time
from concurrent.futures import ThreadPoolExecutor

from config import Config


class FileSystemModel:
    def __init__(self, root_drive=Config.ROOT_DRIVE):
        self.root_drive = os.path.abspath(root_drive)
        self._cache = {}
        # Use PERFORMANCE_CONFIG from Config with fallback defaults
        self._cache_timeout = getattr(Config, "PERFORMANCE_CONFIG", {}).get(
            "CACHE_TIMEOUT", 10
        )
        self._search_cache = {}
        self._folder_size_cache = {}
        self._executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="FileSystemModel"
        )
        mimetypes.init()

    def get_file_type(self, filename):
        """Determine file type based on extension using centralized config"""
        if not filename:
            return "other"

        file_ext = os.path.splitext(filename)[1].lower()

        # Quick checks for common types
        if not file_ext:
            return "other"

        # Check each file type category from config
        for file_type, extensions in Config.FILE_EXTENSIONS.items():
            if file_ext in extensions:
                return file_type

        return "other"

    def get_file_icon(self, filename):
        """Get appropriate icon for file type"""
        file_type = self.get_file_type(filename)
        return Config.FILE_ICONS.get(file_type, "📄")

    def format_file_size(self, size_bytes):
        """Convert bytes to human readable format"""
        if size_bytes is None or size_bytes == 0:
            return "0 B"

        try:
            size_bytes = float(size_bytes)
        except:
            return "0 B"

        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1

        return f"{size_bytes:.1f} {size_names[i]}"

    def get_folder_size(self, folder_path):
        """Optimized folder size calculation"""
        # Check if folder size calculation is disabled
        perf_config = getattr(Config, "PERFORMANCE_CONFIG", {})
        if perf_config.get("DISABLE_FOLDER_SIZE", False):
            return 0

        cache_key = f"size_{folder_path}"
        current_time = time.time()

        # Check cache
        if cache_key in self._folder_size_cache:
            size, timestamp = self._folder_size_cache[cache_key]
            if current_time - timestamp < self._cache_timeout * 5:
                return size

        full_path = os.path.join(self.root_drive, folder_path)

        if not os.path.exists(full_path) or not os.path.isdir(full_path):
            self._folder_size_cache[cache_key] = (0, current_time)
            return 0

        total_size = 0

        try:
            # Use os.scandir for better performance
            with os.scandir(full_path) as entries:
                for entry in entries:
                    try:
                        if entry.is_file(follow_symlinks=False):
                            total_size += entry.stat(follow_symlinks=False).st_size
                    except (OSError, PermissionError):
                        continue
        except (OSError, PermissionError):
            pass

        self._folder_size_cache[cache_key] = (total_size, current_time)
        return total_size

    def get_folder_contents(self, folder_path):
        """Optimized folder content retrieval"""
        cache_key = f"contents_{folder_path}"
        current_time = time.time()

        if cache_key in self._cache:
            cached_data, timestamp = self._cache[cache_key]
            if current_time - timestamp < self._cache_timeout:
                return cached_data, None

        try:
            if "%" in folder_path:
                import urllib.parse

                folder_path = urllib.parse.unquote(folder_path)

            full_path = os.path.join(self.root_drive, folder_path)

            if not folder_path:
                full_path = self.root_drive

            if not os.path.exists(full_path):
                return None, "Path not found"

            if not os.path.isdir(full_path):
                return None, "Path is not a directory"

            items = []

            try:
                # Use os.scandir (much faster than os.listdir)
                with os.scandir(full_path) as entries:
                    for entry in entries:
                        item_name = entry.name

                        # Skip hidden files
                        if item_name.startswith("."):
                            continue

                        try:
                            if entry.is_dir():
                                # Create folder item without calculating size initially
                                items.append(
                                    self._create_folder_item_fast(
                                        item_name, folder_path
                                    )
                                )
                            else:
                                # File - get size without additional stats if possible
                                try:
                                    file_size = entry.stat(
                                        follow_symlinks=False
                                    ).st_size
                                    items.append(
                                        self._create_file_item_fast(
                                            item_name, folder_path, file_size
                                        )
                                    )
                                except:
                                    continue
                        except (OSError, PermissionError):
                            continue
            except (OSError, PermissionError):
                return None, "Permission denied"

            # Sort items
            items.sort(
                key=lambda x: (
                    x.get("type", "") != "folder",  # Folders first (False < True)
                    x.get("name", "").lower()
                    if x.get("name")
                    else "",  # Safe string comparison
                )
            )

            self._cache[cache_key] = (items, current_time)
            return items, None

        except Exception as e:
            print(f"Error in get_folder_contents: {e}")
            return None, str(e)

    def _create_folder_item_fast(self, name, parent_path):
        """Fast folder item creation without size calculation"""
        if parent_path:
            item_path = os.path.join(parent_path, name).replace("\\", "/")
        else:
            item_path = name

        return {
            "name": name,
            "type": "folder",
            "icon": "📁",
            "size": "...",  # Placeholder, not empty string
            "path": item_path,
            "file_count": 0,  # Use integer 0 instead of empty string
            "folder_size": 0,
            "modified": self._get_modified_time(item_path),
            "loading_size": True,
        }

    def _create_file_item_fast(self, name, parent_path, file_size):
        """Fast file item creation"""
        file_type = self.get_file_type(name)

        if parent_path:
            item_path = os.path.join(parent_path, name).replace("\\", "/")
        else:
            item_path = name

        return {
            "name": name,
            "type": file_type,
            "icon": self.get_file_icon(name),
            "size": self.format_file_size(file_size) if file_size else "0 B",
            "path": item_path,
            "full_path": os.path.join(self.root_drive, item_path),
            "modified": self._get_modified_time(item_path),
            "raw_size": file_size,  # Keep numeric size for sorting if needed
        }

    def get_folder_size_lazy(self, folder_path):
        """Get folder size with lazy loading (for AJAX requests)"""
        perf_config = getattr(Config, "PERFORMANCE_CONFIG", {})
        if perf_config.get("DISABLE_FOLDER_SIZE"):
            return {"size": "0 B", "file_count": 0}

        # Start async calculation if not cached
        cache_key = f"size_{folder_path}"
        if cache_key not in self._folder_size_cache:
            # Schedule async calculation
            self._executor.submit(self._calculate_folder_size_async, folder_path)
            return {"size": "Calculating...", "file_count": "..."}

        size, _ = self._folder_size_cache[cache_key]

        # Count files (simplified - just immediate files)
        full_path = os.path.join(self.root_drive, folder_path)
        file_count = 0
        try:
            with os.scandir(full_path) as entries:
                for entry in entries:
                    if entry.is_file():
                        file_count += 1
        except:
            file_count = 0

        return {"size": self.format_file_size(size), "file_count": file_count}

    def _calculate_folder_size_async(self, folder_path):
        """Calculate folder size in background thread"""
        full_path = os.path.join(self.root_drive, folder_path)
        total_size = 0

        try:
            # Fast calculation - limited recursion
            for dirpath, dirnames, filenames in os.walk(full_path, followlinks=False):
                for filename in filenames:
                    try:
                        filepath = os.path.join(dirpath, filename)
                        if os.path.isfile(filepath):
                            total_size += os.path.getsize(filepath)
                    except:
                        continue
                # Limit recursion depth for performance
                if dirpath.count(os.sep) - full_path.count(os.sep) > 3:
                    dirnames[:] = []  # Don't recurse deeper
        except:
            total_size = 0

        cache_key = f"size_{folder_path}"
        self._folder_size_cache[cache_key] = (total_size, time.time())

    def search_files(self, query, max_results=1000):
        """Enhanced search for files across the entire drive (like OS search)"""
        if not query or len(query.strip()) < 1:
            return []

        query = query.strip().lower()

        # Add minimum length requirement for non-wildcard searches
        # The test expects at least 2 characters for normal searches
        # Allow wildcard searches to be shorter (like "*" or "*.txt")
        has_wildcard = "*" in query or "?" in query
        if not has_wildcard and len(query) < 2:
            return []

        cache_key = f"search_{query}"

        # Check cache first
        if cache_key in self._search_cache:
            cached_data, timestamp = self._search_cache[cache_key]
            if time.time() - timestamp < self._cache_timeout:
                return cached_data

        results = []
        search_count = 0

        # Determine search type
        has_wildcard = "*" in query or "?" in query

        if has_wildcard:
            # Use fnmatch for wildcard search
            pattern = query
        else:
            # Simple substring search - make pattern for fnmatch
            pattern = f"*{query}*"

        # Define recursive search function
        def search_in_directory(current_path):
            nonlocal search_count
            if search_count >= max_results:
                return

            try:
                with os.scandir(current_path) as entries:
                    for entry in entries:
                        if search_count >= max_results:
                            break

                        try:
                            entry_name = entry.name

                            # Skip hidden files and system directories
                            if entry_name.startswith(".") or entry_name in [
                                "$RECYCLE.BIN",
                                "System Volume Information",
                                "Thumbs.db",
                            ]:
                                continue

                            # Check if name matches query
                            matches = False
                            if has_wildcard:
                                matches = fnmatch.fnmatch(entry_name.lower(), pattern)
                            else:
                                matches = query in entry_name.lower()

                            if matches:
                                # Get relative path from root drive
                                try:
                                    rel_path = os.path.relpath(
                                        entry.path, self.root_drive
                                    )
                                except ValueError:
                                    # If path is not relative (different drive), skip
                                    continue

                                if entry.is_dir():
                                    folder_size = self.get_folder_size(rel_path)
                                    results.append(
                                        self._create_folder_item(
                                            entry_name,
                                            os.path.dirname(rel_path),
                                            folder_size,
                                        )
                                    )
                                else:
                                    try:
                                        file_size = entry.stat().st_size
                                        results.append(
                                            self._create_file_item(
                                                entry_name,
                                                entry.path,
                                                os.path.dirname(rel_path),
                                                file_size,
                                            )
                                        )
                                    except:
                                        continue

                                search_count += 1

                            # Recursively search subdirectories
                            if entry.is_dir():
                                # Skip certain system directories
                                if entry_name.lower() not in [
                                    "windows",
                                    "program files",
                                    "program files (x86)",
                                    "system32",
                                ]:
                                    search_in_directory(entry.path)

                        except (PermissionError, OSError):
                            continue  # Skip inaccessible files/folders

            except (PermissionError, OSError):
                pass  # Skip inaccessible directories
            except Exception as e:
                print(f"Error scanning directory {current_path}: {e}")

        try:
            # Start search from root drive
            search_in_directory(self.root_drive)
        except Exception as e:
            print(f"Search error: {e}")

        # Sort results: folders first, then files, then alphabetically
        results.sort(
            key=lambda x: (
                x.get("type", "") != "folder",  # Safe comparison
                x.get("name", "").lower() if x.get("name") else "",  # Safe string
            )
        )

        # Cache results
        self._search_cache[cache_key] = (results, time.time())

        # Clean old cache entries
        self._clean_search_cache()

        return results

    def _clean_search_cache(self):
        """Remove old search cache entries"""
        current_time = time.time()
        keys_to_remove = []

        for key, (_, timestamp) in self._search_cache.items():
            if (
                current_time - timestamp > self._cache_timeout * 5
            ):  # 5x longer cache for searches
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del self._search_cache[key]

    def get_files_by_type(self, items):
        """Group files by type for preview navigation"""
        files_by_type = {}
        for item in items:
            if item.get("type") != "folder":
                file_type = item.get("type", "other")
                if file_type not in files_by_type:
                    files_by_type[file_type] = []
                files_by_type[file_type].append(item)

        # Sort each type's files by name
        for file_type in files_by_type:
            files_by_type[file_type].sort(key=lambda x: x["name"].lower())

        return files_by_type

    def _create_folder_item(self, name, parent_path, folder_size=0):
        """Create folder item dictionary"""
        # Ensure proper path joining
        if parent_path:
            item_path = os.path.join(parent_path, name).replace("\\", "/")
        else:
            item_path = name

        return {
            "name": name,
            "type": "folder",
            "icon": "📁",
            "size": self.format_file_size(folder_size),
            "path": item_path,
            "file_count": self._count_files_in_folder(item_path),
            "folder_size": folder_size,
            "modified": self._get_modified_time(item_path),
        }

    def _create_file_item(self, name, full_path, parent_path, file_size=None):
        """Create file item dictionary"""
        file_type = self.get_file_type(name)

        if file_size is None:
            try:
                file_size = os.path.getsize(full_path)
            except:
                file_size = 0

        # Ensure proper path joining
        if parent_path:
            item_path = os.path.join(parent_path, name).replace("\\", "/")
        else:
            item_path = name

        return {
            "name": name,
            "type": file_type,
            "icon": self.get_file_icon(name),
            "size": self.format_file_size(file_size),
            "path": item_path,
            "full_path": full_path,
            "modified": self._get_modified_time(full_path),
        }

    def _count_files_in_folder(self, folder_path):
        """Count number of files in a folder (recursive for accuracy)"""
        full_path = os.path.join(self.root_drive, folder_path)
        file_count = 0

        if os.path.exists(full_path) and os.path.isdir(full_path):
            try:
                for dirpath, dirnames, filenames in os.walk(full_path):
                    file_count += len(filenames)
            except (OSError, PermissionError):
                pass

        return file_count

    def _get_modified_time(self, path):
        """Get modified time for a file/folder"""
        full_path = os.path.join(self.root_drive, path)
        try:
            return os.path.getmtime(full_path)
        except:
            return 0

    def get_breadcrumbs(self, current_path):
        """Generate breadcrumb navigation"""
        breadcrumbs = []
        path_parts = []

        if current_path:
            # Split path properly, handling both forward and backslashes
            normalized_path = current_path.replace("\\", "/")
            for part in normalized_path.split("/"):
                if part:
                    path_parts.append(part)
                    breadcrumbs.append({"name": part, "path": "/".join(path_parts)})

        return breadcrumbs

    def get_parent_path(self, current_path):
        """Get parent directory path"""
        if not current_path:
            return ""

        # Handle both forward and backslashes
        normalized_path = current_path.replace("\\", "/")
        path_parts = normalized_path.split("/")

        if len(path_parts) > 1:
            return "/".join(path_parts[:-1])
        else:
            return ""

    def count_file_types(self, items):
        """Count files by type for statistics"""
        counts = {
            "folders": 0,
            "videos": 0,
            "audios": 0,
            "images": 0,
            "documents": 0,
            "text": 0,
            "others": 0,
        }

        for item in items:
            if item["type"] == "folder":
                counts["folders"] += 1
            elif item["type"] == "video":
                counts["videos"] += 1
            elif item["type"] == "audio":
                counts["audios"] += 1
            elif item["type"] == "image":
                counts["images"] += 1
            elif item["type"] == "document":
                counts["documents"] += 1
            elif item["type"] == "text":
                counts["text"] += 1
            else:
                counts["others"] += 1

        return counts

    def clear_cache(self, path=None):
        """Clear cache for a specific path or all cache"""
        if path:
            cache_key = f"contents_{path}"
            if cache_key in self._cache:
                del self._cache[cache_key]
        else:
            self._cache.clear()

    def quick_search(self, query, current_path=""):
        """Quick search within current directory (for instant search suggestions)"""
        if not query or len(query) < 2:
            return []

        query = query.lower()
        results = []

        try:
            # Build full path
            if current_path:
                full_path = os.path.join(self.root_drive, current_path)
            else:
                full_path = self.root_drive

            if not os.path.exists(full_path) or not os.path.isdir(full_path):
                return []

            # Quick scan of current directory only
            with os.scandir(full_path) as entries:
                for entry in entries:
                    try:
                        if query in entry.name.lower():
                            if entry.is_dir():
                                results.append(
                                    {
                                        "name": entry.name,
                                        "type": "folder",
                                        "icon": "📁",
                                        "path": os.path.join(
                                            current_path, entry.name
                                        ).replace("\\", "/"),
                                    }
                                )
                            else:
                                results.append(
                                    {
                                        "name": entry.name,
                                        "type": self.get_file_type(entry.name),
                                        "icon": self.get_file_icon(entry.name),
                                        "path": os.path.join(
                                            current_path, entry.name
                                        ).replace("\\", "/"),
                                    }
                                )
                    except:
                        continue

            # Limit results for quick search
            return results[:50]

        except Exception as e:
            print(f"Quick search error: {e}")
            return []
