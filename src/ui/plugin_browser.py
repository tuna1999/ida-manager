"""
Plugin browser component for displaying plugin list.
"""

from typing import List, Optional, Callable

from src.models.plugin import Plugin
from src.utils.logger import get_logger

logger = get_logger(__name__)


class PluginBrowser:
    """
    Plugin browser view component.

    Displays list of plugins with filtering, sorting, and actions.
    """

    def __init__(self):
        """Initialize plugin browser."""
        self.plugins: List[Plugin] = []
        self.filtered_plugins: List[Plugin] = []

        # Filter state
        self.filter_text = ""
        self.show_installed_only = False
        self.show_available_only = False
        self.filter_type = "all"  # all, legacy, modern

        # Sort state
        self.sort_by = "name"  # name, version, author, type
        self.sort_ascending = True

        # Selection
        self.selected_plugin: Optional[Plugin] = None

        # Callbacks
        self.on_install_callback: Optional[Callable] = None
        self.on_update_callback: Optional[Callable] = None
        self.on_uninstall_callback: Optional[Callable] = None

    def set_plugins(self, plugins: List[Plugin]) -> None:
        """
        Set plugins to display.

        Args:
            plugins: List of plugins
        """
        self.plugins = plugins
        self.apply_filters()

    def apply_filters(self) -> None:
        """Apply current filters to plugin list."""
        filtered = self.plugins

        # Text filter
        if self.filter_text:
            filter_lower = self.filter_text.lower()
            filtered = [p for p in filtered if filter_lower in p.name.lower()]

        # Installed/Available filter
        if self.show_installed_only:
            filtered = [p for p in filtered if p.installed_version is not None]
        elif self.show_available_only:
            filtered = [p for p in filtered if p.installed_version is None]

        # Type filter
        if self.filter_type == "legacy":
            filtered = [p for p in filtered if p.plugin_type == "legacy"]
        elif self.filter_type == "modern":
            filtered = [p for p in filtered if p.plugin_type == "modern"]

        self.filtered_plugins = filtered
        self.apply_sort()

    def apply_sort(self) -> None:
        """Apply current sorting to plugin list."""
        reverse = not self.sort_ascending

        if self.sort_by == "name":
            self.filtered_plugins.sort(key=lambda p: p.name.lower(), reverse=reverse)
        elif self.sort_by == "version":
            self.filtered_plugins.sort(
                key=lambda p: p.installed_version or "",
                reverse=reverse,
            )
        elif self.sort_by == "author":
            self.filtered_plugins.sort(
                key=lambda p: p.author or "",
                reverse=reverse,
            )
        elif self.sort_by == "type":
            self.filtered_plugins.sort(
                key=lambda p: p.plugin_type,
                reverse=reverse,
            )

    def set_filter_text(self, text: str) -> None:
        """Set text filter."""
        self.filter_text = text
        self.apply_filters()

    def set_show_installed_only(self, value: bool) -> None:
        """Set installed only filter."""
        self.show_installed_only = value
        self.show_available_only = False
        self.apply_filters()

    def set_show_available_only(self, value: bool) -> None:
        """Set available only filter."""
        self.show_available_only = value
        self.show_installed_only = False
        self.apply_filters()

    def set_filter_type(self, filter_type: str) -> None:
        """Set type filter."""
        self.filter_type = filter_type
        self.apply_filters()

    def set_sort_by(self, sort_by: str) -> None:
        """Set sort field."""
        self.sort_by = sort_by
        self.apply_sort()

    def toggle_sort_direction(self) -> None:
        """Toggle sort direction."""
        self.sort_ascending = not self.sort_ascending
        self.apply_sort()

    def get_plugin_at_index(self, index: int) -> Optional[Plugin]:
        """
        Get plugin at index.

        Args:
            index: Index in filtered list

        Returns:
            Plugin or None
        """
        if 0 <= index < len(self.filtered_plugins):
            return self.filtered_plugins[index]
        return None

    def get_plugin_count(self) -> int:
        """Get number of filtered plugins."""
        return len(self.filtered_plugins)

    def get_installed_count(self) -> int:
        """Get number of installed plugins."""
        return sum(1 for p in self.plugins if p.installed_version is not None)

    def get_available_count(self) -> int:
        """Get number of available plugins."""
        return sum(1 for p in self.plugins if p.installed_version is None)

    def install_selected(self) -> bool:
        """
        Install selected plugin.

        Returns:
            True if callback executed
        """
        if self.selected_plugin and self.on_install_callback:
            self.on_install_callback(self.selected_plugin)
            return True
        return False

    def update_selected(self) -> bool:
        """
        Update selected plugin.

        Returns:
            True if callback executed
        """
        if self.selected_plugin and self.on_update_callback:
            self.on_update_callback(self.selected_plugin)
            return True
        return False

    def uninstall_selected(self) -> bool:
        """
        Uninstall selected plugin.

        Returns:
            True if callback executed
        """
        if self.selected_plugin and self.on_uninstall_callback:
            self.on_uninstall_callback(self.selected_plugin)
            return True
        return False

    def can_install(self, plugin: Plugin) -> bool:
        """Check if plugin can be installed."""
        return plugin.installed_version is None

    def can_update(self, plugin: Plugin) -> bool:
        """Check if plugin can be updated."""
        return plugin.installed_version is not None

    def can_uninstall(self, plugin: Plugin) -> bool:
        """Check if plugin can be uninstalled."""
        return plugin.installed_version is not None

    def get_status_text(self, plugin: Plugin) -> str:
        """Get status text for plugin."""
        if plugin.installed_version:
            return f"Installed ({plugin.installed_version})"
        return "Available"
