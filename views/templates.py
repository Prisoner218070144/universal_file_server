"""
Template rendering for Universal File Server
"""

from flask import render_template, url_for
from typing import List, Dict, Any, Optional
from datetime import datetime
import time

from models.file_system import FileSystemModel


class TemplateRenderer:
    def __init__(self):
        self.file_system = FileSystemModel()

    def render_browse_page(
        self,
        items: List[Dict[str, Any]],
        current_path: str,
        breadcrumbs: List[Dict[str, str]],
        parent_path: str,
        file_counts: Dict[str, int],
        files_by_type: Dict[str, List[Dict[str, Any]]],
        preview_nav_data: Dict[str, List[Dict[str, Any]]] = None,
    ) -> str:
        """
        Render browse page template

        Args:
            items: List of file/folder items
            current_path: Current directory path
            breadcrumbs: Breadcrumb navigation
            parent_path: Parent directory path
            file_counts: Counts of different file types
            files_by_type: Files grouped by type
            preview_nav_data: Navigation data for preview modal

        Returns:
            Rendered HTML
        """
        return render_template(
            "browse.html",
            items=items,
            current_path=current_path,
            breadcrumbs=breadcrumbs,
            parent_path=parent_path,
            file_counts=file_counts,
            files_by_type=files_by_type,
            preview_nav_data=preview_nav_data or {},
            title=f"File Server - {current_path or 'Root'}",
            year=datetime.now().year,
        )

    def render_search_page(
        self, results: List[Dict[str, Any]], query: str, search_stats: Dict[str, Any]
    ) -> str:
        """
        Render search results page

        Args:
            results: Search results
            query: Search query
            search_stats: Search statistics

        Returns:
            Rendered HTML
        """
        return render_template(
            "search.html",
            results=results,
            query=query,
            search_stats=search_stats,
            title=f"Search: {query}",
            year=datetime.now().year,
        )

    def render_error_page(
        self, error_message: str, error_code: int = 500, back_url: str = None
    ) -> str:
        """
        Render error page

        Args:
            error_message: Error message to display
            error_code: HTTP error code
            back_url: URL for back button

        Returns:
            Rendered HTML
        """
        error_titles = {
            400: "Bad Request",
            403: "Forbidden",
            404: "Not Found",
            500: "Internal Server Error",
            503: "Service Unavailable",
        }

        title = error_titles.get(error_code, "Error")

        return render_template(
            "error.html" if self._template_exists("error.html") else "base.html",
            error_message=error_message,
            error_code=error_code,
            error_title=title,
            back_url=back_url or url_for("routes.index"),
            title=f"Error {error_code} - {title}",
            year=datetime.now().year,
        )

    def _template_exists(self, template_name: str) -> bool:
        """
        Check if template exists

        Args:
            template_name: Name of template

        Returns:
            True if template exists
        """
        try:
            from flask import current_app

            template = current_app.jinja_env.get_template(template_name)
            return template is not None
        except Exception:
            return False
