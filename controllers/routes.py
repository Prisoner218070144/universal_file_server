"""
Route handlers with simplified MKV support
"""

import io
import os
import re
import shutil
import time
import urllib.parse
import zipfile

import mammoth
from flask import Blueprint, Response, jsonify, redirect, request, send_file
from werkzeug.utils import secure_filename

from config import Config
from models.file_system import FileSystemModel
from utils.upload_handler import UploadHandler
from views.templates import TemplateRenderer

# Create blueprint
routes = Blueprint("routes", __name__)

# Initialize model, view, and upload handler
file_system = FileSystemModel()
template_renderer = TemplateRenderer()
upload_handler = UploadHandler()


@routes.route("/")
@routes.route("/browse/")
@routes.route("/browse//")  # Handle double slash case
def index():
    """Home page - shows root of F drive"""
    return browse_folder("")


@routes.route("/browse/<path:folder_path>")
def browse_folder(folder_path):
    """Display contents of a folder"""
    try:
        # Decode the URL-encoded path
        decoded_path = urllib.parse.unquote(folder_path)
    except:
        decoded_path = folder_path

    # Security: prevent path traversal
    safe_path = decoded_path.replace("..", "").replace("//", "/")

    # Remove any trailing slash
    safe_path = safe_path.rstrip("/")

    # Get folder contents from model
    items, error = file_system.get_folder_contents(safe_path)

    if error:
        # Try to see if it's a file instead of a folder
        full_path = os.path.join(file_system.root_drive, safe_path)
        if os.path.exists(full_path) and os.path.isfile(full_path):
            return serve_file(safe_path)
        return f"Error: {error}", 404

    # Get navigation data from model
    breadcrumbs = file_system.get_breadcrumbs(safe_path)
    parent_path = file_system.get_parent_path(safe_path)
    file_counts = file_system.count_file_types(items)

    # Get files by type for preview navigation
    files_by_type = file_system.get_files_by_type(items)

    # Get all files in current directory for preview modal
    preview_nav_data = {}
    for file_type, type_items in files_by_type.items():
        preview_nav_data[file_type] = [
            {"name": item["name"], "path": item["path"], "type": item["type"]}
            for item in type_items
        ]

    # Render view
    return template_renderer.render_browse_page(
        items,
        safe_path,
        breadcrumbs,
        parent_path,
        file_counts,
        files_by_type,
        preview_nav_data,
    )


@routes.route("/api/folder_size/<path:folder_path>")
def get_folder_size_api(folder_path):
    """API endpoint for lazy loading folder sizes"""
    decoded_path = urllib.parse.unquote(folder_path)
    safe_path = decoded_path.replace("..", "").replace("//", "/")

    result = file_system.get_folder_size_lazy(safe_path)
    return jsonify(result)


@routes.route("/file/<path:file_path>")
def serve_file(file_path):
    """Serve file directly for viewing in browser"""
    decoded_path = urllib.parse.unquote(file_path)
    full_path = os.path.join(file_system.root_drive, decoded_path)

    if not os.path.exists(full_path) or os.path.isdir(full_path):
        return "File not found", 404

    # Check file extension
    file_ext = os.path.splitext(decoded_path)[1].lower()

    # For media files, redirect to stream
    if file_ext in Config.MEDIA_EXTENSIONS:
        return redirect(f"/stream/{file_path}")

    # For PDF files, serve inline
    if file_ext == ".pdf":
        return send_file(full_path, mimetype="application/pdf")

    # For text files, serve with proper encoding
    if file_ext in [
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
    ]:
        return send_file(full_path, mimetype="text/plain; charset=utf-8")

    # For other files, serve normally
    mime_type = _get_mime_type(full_path)
    if not mime_type:
        mime_type = "application/octet-stream"

    return send_file(full_path, mimetype=mime_type)


@routes.route("/stream/<path:file_path>")
def stream_file(file_path):
    """Stream media files with proper headers"""
    decoded_path = urllib.parse.unquote(file_path)
    full_path = os.path.join(file_system.root_drive, decoded_path)

    if not os.path.exists(full_path):
        return "File not found", 404

    # Get file size
    try:
        file_size = os.path.getsize(full_path)
    except:
        file_size = 0

    # Get MIME type
    mime_type = _get_mime_type(full_path)

    # Handle range requests for seeking
    range_header = request.headers.get("Range", None)
    if range_header:
        return _handle_range_request(full_path, file_size, range_header, mime_type)
    else:
        # Serve entire file with streaming headers
        return _serve_full_file(full_path, file_size, mime_type)


@routes.route("/download/<path:file_path>")
def download_file(file_path):
    """Force download of a file"""
    decoded_path = urllib.parse.unquote(file_path)
    full_path = os.path.join(file_system.root_drive, decoded_path)

    if not os.path.exists(full_path):
        return "File not found", 404

    # For MKV files, ensure proper MIME type
    file_ext = os.path.splitext(decoded_path)[1].lower()
    if file_ext == ".mkv":
        return send_file(
            full_path,
            as_attachment=True,
            mimetype="video/x-matroska",
            download_name=os.path.basename(decoded_path),
        )

    return send_file(full_path, as_attachment=True)


@routes.route("/download_folder/<path:folder_path>")
def download_folder(folder_path):
    """Download entire folder as ZIP file"""
    decoded_path = urllib.parse.unquote(folder_path)
    full_path = os.path.join(file_system.root_drive, decoded_path)

    if not os.path.exists(full_path) or not os.path.isdir(full_path):
        return "Folder not found", 404

    # Generate ZIP file in memory
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, "w", zipfile.ZIP_DEFLATED) as zf:
        _add_folder_to_zip(full_path, decoded_path, zf)

    memory_file.seek(0)

    # Get folder name for the ZIP file
    if decoded_path:
        folder_name = os.path.basename(decoded_path)
    else:
        folder_name = "F_Drive"

    zip_filename = f"{folder_name}.zip"

    return send_file(
        memory_file,
        mimetype="application/zip",
        as_attachment=True,
        download_name=zip_filename,
    )


@routes.route("/search")
def search_files():
    """Search for files by name"""
    query = request.args.get("q", "").lower()
    if not query:
        return redirect("/")

    # Search files using model
    results = file_system.search_files(query)

    # Get search stats
    search_stats = {
        "query": query,
        "count": len(results),
        "folders": sum(1 for r in results if r.get("type") == "folder"),
        "files": sum(1 for r in results if r.get("type") != "folder"),
    }

    # Render search results view
    return template_renderer.render_search_page(results, query, search_stats)


@routes.route("/upload/", methods=["POST"])
@routes.route("/upload/<path:folder_path>", methods=["POST"])
def upload_files(folder_path=""):
    """Handle file uploads"""
    decoded_path = urllib.parse.unquote(folder_path) if folder_path else ""
    safe_path = decoded_path.replace("..", "").replace("//", "/")

    try:
        # Check if files are in the request
        if "files[]" not in request.files:
            return (
                jsonify({"error": "No files selected", "success": [], "errors": []}),
                400,
            )

        files = request.files.getlist("files[]")
        if not files or (len(files) == 1 and files[0].filename == ""):
            return (
                jsonify({"error": "No files selected", "success": [], "errors": []}),
                400,
            )

        results = upload_handler.handle_upload(files, safe_path)
        return jsonify(results)

    except Exception as e:
        return jsonify({"error": str(e), "success": [], "errors": []}), 500


@routes.route("/create_folder/", methods=["POST"])
@routes.route("/create_folder/<path:folder_path>", methods=["POST"])
def create_folder(folder_path=""):
    """Create a new folder"""
    decoded_path = urllib.parse.unquote(folder_path) if folder_path else ""
    safe_path = decoded_path.replace("..", "").replace("//", "/")

    data = request.get_json()
    if not data or "folder_name" not in data:
        return jsonify({"error": "Folder name is required"}), 400

    folder_name = data["folder_name"].strip()
    if not folder_name:
        return jsonify({"error": "Invalid folder name"}), 400

    # Use secure_filename
    folder_name = secure_filename(folder_name)
    if not folder_name:
        folder_name = f"folder_{int(time.time())}"

    try:
        result = upload_handler.create_folder(folder_name, safe_path)
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@routes.route("/create_file/", methods=["POST"])
@routes.route("/create_file/<path:folder_path>", methods=["POST"])
def create_file(folder_path=""):
    """Create a new empty file"""
    decoded_path = urllib.parse.unquote(folder_path) if folder_path else ""
    safe_path = decoded_path.replace("..", "").replace("//", "/")

    data = request.get_json()
    if not data or "filename" not in data:
        return jsonify({"error": "Filename is required"}), 400

    filename = data["filename"].strip()
    if not filename:
        return jsonify({"error": "Invalid filename"}), 400

    # Use secure_filename
    filename = secure_filename(filename)
    if not filename:
        filename = f"file_{int(time.time())}.txt"

    try:
        result = upload_handler.create_file(filename, safe_path)
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@routes.route("/api/preview/<path:file_path>")
def get_preview_data(file_path):
    """Get file preview data for modal"""
    decoded_path = urllib.parse.unquote(file_path)
    safe_path = decoded_path.replace("..", "").replace("//", "/")
    full_path = os.path.join(file_system.root_drive, safe_path)

    if not os.path.exists(full_path):
        return jsonify({"error": "File not found"}), 404

    # Get file info
    filename = os.path.basename(full_path)
    file_type = file_system.get_file_type(filename)

    # Get file size
    try:
        file_size = os.path.getsize(full_path)
        readable_size = file_system.format_file_size(file_size)
    except:
        readable_size = "Unknown"

    # Get MIME type
    mime_type = _get_mime_type(full_path)

    # Get navigation data
    dir_path = os.path.dirname(safe_path) if safe_path else ""
    items, _ = file_system.get_folder_contents(dir_path)

    same_type_files = []
    prev_file = next_file = None

    if items:
        # Get files of same type
        for item in items:
            if item.get("type") != "folder" and item.get("type") == file_type:
                same_type_files.append(item)

        # Sort files
        same_type_files.sort(key=lambda x: (x.get("name", "").lower()))

        # Find current file index
        current_index = -1
        for i, item in enumerate(same_type_files):
            if item.get("path") == safe_path:
                current_index = i
                break

        if current_index >= 0:
            prev_file = (
                same_type_files[current_index - 1] if current_index > 0 else None
            )
            next_file = (
                same_type_files[current_index + 1]
                if current_index < len(same_type_files) - 1
                else None
            )

    return jsonify(
        {
            "success": True,
            "filename": filename,
            "file_path": safe_path,
            "file_type": file_type,
            "file_size": readable_size,
            "mime_type": mime_type,
            "prev_file": prev_file,
            "next_file": next_file,
            "total_files": len(same_type_files),
            "current_index": current_index + 1 if current_index >= 0 else 0,
        }
    )


@routes.route("/api/file_content/<path:file_path>")
def get_file_content(file_path):
    """Get file content for text preview"""
    decoded_path = urllib.parse.unquote(file_path)
    safe_path = decoded_path.replace("..", "").replace("//", "/")
    full_path = os.path.join(file_system.root_drive, safe_path)

    if not os.path.exists(full_path):
        return jsonify({"error": "File not found"}), 404

    # Check file size (limit text preview to 5MB)
    try:
        file_size = os.path.getsize(full_path)
        if file_size > 5 * 1024 * 1024:  # 5MB limit
            return jsonify({"error": "File too large for preview", "size": file_size})
    except:
        pass

    # Check if it's a text file
    file_ext = os.path.splitext(full_path)[1].lower()
    text_extensions = [
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
    ]

    if file_ext not in text_extensions:
        return jsonify({"error": "File is not a text file"}), 400

    try:
        # Try different encodings
        encodings = ["utf-8", "latin-1", "cp1252", "iso-8859-1"]
        content = None

        for encoding in encodings:
            try:
                with open(full_path, "r", encoding=encoding) as f:
                    content = f.read()
                break
            except UnicodeDecodeError:
                continue

        if content is None:
            return jsonify({"error": "Cannot decode file content"}), 400

        return jsonify({"success": True, "content": content})

    except Exception as e:
        return jsonify({"error": str(e)}), 400


@routes.route("/api/word_document_content/<path:file_path>")
def get_word_document_content(file_path):
    """Get Word document content converted to HTML for preview"""
    decoded_path = urllib.parse.unquote(file_path)
    safe_path = decoded_path.replace("..", "").replace("//", "/")
    full_path = os.path.join(file_system.root_drive, safe_path)

    if not os.path.exists(full_path):
        return jsonify({"error": "File not found"}), 404

    # Check file size (limit Word doc preview to 10MB)
    try:
        file_size = os.path.getsize(full_path)
        if file_size > Config.PERFORMANCE_CONFIG.get(
            "MAX_WORD_PREVIEW_SIZE", 10 * 1024 * 1024
        ):
            return jsonify(
                {
                    "error": "File too large for preview",
                    "size": file_size,
                    "max_size": Config.PERFORMANCE_CONFIG.get(
                        "MAX_WORD_PREVIEW_SIZE", 10 * 1024 * 1024
                    ),
                }
            )
    except:
        pass

    # Check if it's a Word document
    file_ext = os.path.splitext(full_path)[1].lower()
    if file_ext not in [".docx", ".doc"]:
        return jsonify({"error": "File is not a Word document"}), 400

    try:
        if file_ext == ".docx":
            # Use mammoth to convert DOCX to HTML
            with open(full_path, "rb") as docx_file:
                result = mammoth.convert_to_html(docx_file)
                html = result.value
                messages = result.messages

            # Clean and sanitize the HTML
            html = _clean_word_html(html)

            return jsonify(
                {
                    "success": True,
                    "content": html,
                    "messages": [str(msg) for msg in messages],
                    "file_type": "docx",
                }
            )
        else:
            # For .doc files, we can't convert them easily
            # Provide a message and option to download
            return jsonify(
                {
                    "success": True,
                    "content": '<div class="doc-preview-notice"><p>⚠️ <strong>Note:</strong> .doc files cannot be previewed directly.</p><p>Please download the file and open it with Microsoft Word or convert it to .docx format for preview.</p></div>',
                    "file_type": "doc",
                    "needs_conversion": True,
                }
            )

    except Exception as e:
        return (
            jsonify(
                {
                    "error": f"Error processing Word document: {str(e)}",
                    "file_type": file_ext,
                }
            ),
            400,
        )


def _clean_word_html(html):
    """Clean and sanitize HTML generated from Word documents"""
    if not html:
        return html

    # Add basic styling for Word document preview
    html = f"""
    <div class="word-document-preview">
        <style>
            .word-document-preview {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 100%;
                overflow-x: auto;
            }}
            .word-document-preview h1, 
            .word-document-preview h2, 
            .word-document-preview h3, 
            .word-document-preview h4 {{
                margin-top: 1.5em;
                margin-bottom: 0.5em;
                color: #2c3e50;
            }}
            .word-document-preview p {{
                margin-bottom: 1em;
            }}
            .word-document-preview ul, 
            .word-document-preview ol {{
                margin-left: 2em;
                margin-bottom: 1em;
            }}
            .word-document-preview table {{
                border-collapse: collapse;
                margin-bottom: 1em;
                width: 100%;
            }}
            .word-document-preview table, 
            .word-document-preview th, 
            .word-document-preview td {{
                border: 1px solid #ddd;
            }}
            .word-document-preview th, 
            .word-document-preview td {{
                padding: 8px;
                text-align: left;
            }}
            .word-document-preview th {{
                background-color: #f2f2f2;
                font-weight: bold;
            }}
            .word-document-preview img {{
                max-width: 100%;
                height: auto;
                margin: 1em 0;
            }}
            .word-document-preview blockquote {{
                border-left: 4px solid #3498db;
                margin: 1em 0;
                padding-left: 1em;
                color: #555;
            }}
            .doc-preview-notice {{
                background-color: #fff3cd;
                border: 1px solid #ffeaa7;
                border-radius: 5px;
                padding: 15px;
                margin: 20px 0;
            }}
        </style>
        {html}
    </div>
    """

    return html


@routes.route("/get_directory_files/")
@routes.route("/get_directory_files/<path:folder_path>")
def get_directory_files(folder_path=""):
    """Get all files in directory for playlist navigation"""
    decoded_path = urllib.parse.unquote(folder_path) if folder_path else ""
    safe_path = decoded_path.replace("..", "").replace("//", "/")

    items, error = file_system.get_folder_contents(safe_path)
    if error:
        return jsonify({"error": error}), 404

    # Filter only files (not folders) and add full URLs
    files = []
    for item in items:
        if item.get("type") != "folder":
            item["url"] = f"/file/{urllib.parse.quote(item['path'])}"
            # Only add stream_url for media files
            if item["type"] in ["video", "audio"]:
                item["stream_url"] = f"/stream/{urllib.parse.quote(item['path'])}"
            else:
                item["stream_url"] = None
            files.append(item)

    return jsonify({"files": files})


@routes.route("/delete/<path:file_path>", methods=["DELETE"])
def delete_file(file_path):
    """Delete a file or folder"""
    decoded_path = urllib.parse.unquote(file_path)
    safe_path = decoded_path.replace("..", "").replace("//", "/")
    full_path = os.path.join(file_system.root_drive, safe_path)

    if not os.path.exists(full_path):
        return jsonify({"error": "File not found"}), 404

    try:
        if os.path.isdir(full_path):
            shutil.rmtree(full_path)
        else:
            os.remove(full_path)

        return jsonify({"success": True, "message": "Deleted successfully"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Clipboard operations
@routes.route("/copy", methods=["POST"])
def copy_item():
    """Copy a file or folder"""
    data = request.get_json()
    if not data or "source" not in data or "destination" not in data:
        return jsonify({"error": "Source and destination are required"}), 400

    source = data["source"]
    destination = data["destination"]
    overwrite = data.get("overwrite", False)

    # Build full paths
    source_full = os.path.join(file_system.root_drive, source)
    dest_full = os.path.join(file_system.root_drive, destination)

    # Get the base name of source
    source_name = os.path.basename(source)

    # Check if source exists
    if not os.path.exists(source_full):
        return jsonify({"error": "Source does not exist"}), 404

    # Build destination path with same name
    dest_path = os.path.join(dest_full, source_name)

    # Check if destination already exists
    if os.path.exists(dest_path) and not overwrite:
        return jsonify({"error": "Destination already exists"}), 409

    try:
        # Copy file or folder
        if os.path.isdir(source_full):
            if os.path.exists(dest_path):
                shutil.rmtree(dest_path)
            shutil.copytree(source_full, dest_path)
        else:
            shutil.copy2(source_full, dest_path)

        # Build relative path for response
        rel_dest = os.path.join(destination, source_name).replace("\\", "/")

        return jsonify(
            {
                "success": True,
                "message": f"Copied {source_name} successfully",
                "new_path": rel_dest,
            }
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@routes.route("/move", methods=["POST"])
def move_item():
    """Move a file or folder"""
    data = request.get_json()
    if not data or "source" not in data or "destination" not in data:
        return jsonify({"error": "Source and destination are required"}), 400

    source = data["source"]
    destination = data["destination"]
    overwrite = data.get("overwrite", False)

    # Build full paths
    source_full = os.path.join(file_system.root_drive, source)
    dest_full = os.path.join(file_system.root_drive, destination)

    # Get the base name of source
    source_name = os.path.basename(source)

    # Check if source exists
    if not os.path.exists(source_full):
        return jsonify({"error": "Source does not exist"}), 404

    # Build destination path with same name
    dest_path = os.path.join(dest_full, source_name)

    # Check if destination already exists
    if os.path.exists(dest_path) and not overwrite:
        return jsonify({"error": "Destination already exists"}), 409

    try:
        # Move file or folder
        if os.path.exists(dest_path):
            if os.path.isdir(dest_path):
                shutil.rmtree(dest_path)
            else:
                os.remove(dest_path)

        shutil.move(source_full, dest_path)

        # Build relative path for response
        rel_dest = os.path.join(destination, source_name).replace("\\", "/")

        return jsonify(
            {
                "success": True,
                "message": f"Moved {source_name} successfully",
                "new_path": rel_dest,
            }
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


def _handle_range_request(file_path, file_size, range_header, mime_type):
    """Handle HTTP range requests for media streaming"""
    byte1, byte2 = 0, None
    match = re.search(r"(\d+)-(\d*)", range_header)

    if match:
        groups = match.groups()
        if groups[0]:
            byte1 = int(groups[0])
        if groups[1]:
            byte2 = int(groups[1])

    if byte2 is None:
        byte2 = file_size - 1

    length = byte2 - byte1 + 1

    def generate():
        with open(file_path, "rb") as f:
            f.seek(byte1)
            remaining = length
            while remaining > 0:
                chunk_size = min(8192, remaining)
                data = f.read(chunk_size)
                if not data:
                    break
                remaining -= len(data)
                yield data

    resp = Response(
        generate(),
        status=206,
        mimetype=mime_type,
        direct_passthrough=True,
        headers={
            "Content-Range": f"bytes {byte1}-{byte2}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(length),
            "Content-Disposition": "inline",
            "X-Content-Type-Options": "nosniff",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Range",
            "Cache-Control": "no-cache",
        },
    )

    return resp


def _serve_full_file(file_path, file_size, mime_type):
    """Serve entire file with streaming headers"""

    def generate():
        with open(file_path, "rb") as f:
            while True:
                data = f.read(8192)
                if not data:
                    break
                yield data

    resp = Response(
        generate(),
        mimetype=mime_type,
        headers={
            "Content-Length": str(file_size),
            "Accept-Ranges": "bytes",
            "Content-Disposition": "inline",
            "X-Content-Type-Options": "nosniff",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Range",
            "Cache-Control": "no-cache",
        },
    )

    return resp


def _get_mime_type(file_path):
    """Get correct MIME type for file using centralized config"""
    file_ext = os.path.splitext(file_path)[1].lower()

    # Special handling for MKV files
    if file_ext == ".mkv":
        return "video/x-matroska"

    return Config.MIME_TYPES.get(file_ext, "application/octet-stream")


def _add_folder_to_zip(folder_path, base_path, zip_file):
    """Recursively add folder contents to ZIP file"""
    for root, dirs, files in os.walk(folder_path):
        # Calculate relative path for ZIP structure
        relative_root = os.path.relpath(root, os.path.dirname(folder_path))
        if relative_root == ".":
            zip_root = base_path
        else:
            zip_root = os.path.join(base_path, relative_root)

        # Add directories
        for dir_name in dirs:
            dir_path = os.path.join(root, dir_name)
            zip_dir_path = os.path.join(zip_root, dir_name)
            zip_file.write(dir_path, zip_dir_path)

        # Add files
        for file_name in files:
            file_path = os.path.join(root, file_name)
            zip_file_path = os.path.join(zip_root, file_name)

            # Skip if it's a symlink or we can't read it
            if not os.path.islink(file_path) and os.access(file_path, os.R_OK):
                try:
                    zip_file.write(file_path, zip_file_path)
                except (OSError, PermissionError):
                    # Skip files we can't read
                    continue
