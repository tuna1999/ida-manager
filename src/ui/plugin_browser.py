"""
Plugin browser component for displaying plugin list.
"""

from datetime import datetime, timezone
from typing import List, Optional, Callable

from src.models.plugin import InstallationMethod, Plugin, PluginStatus, PluginType
from src.ui.themes import get_theme_color
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
        self.filter_status = "all"  # all, installed, not_installed, failed
        self.filter_type = "all"  # all, legacy, modern

        # Sort state
        self.sort_by = "name"  # name, status, version, method, last_updated
        self.sort_ascending = True

        # Selection
        self.selected_plugin: Optional[Plugin] = None

        # Callbacks
        self.on_install_callback: Optional[Callable] = None
        self.on_update_callback: Optional[Callable] = None
        self.on_uninstall_callback: Optional[Callable] = None
        self.on_remove_callback: Optional[Callable] = None

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

        # Status filter
        if self.filter_status == "installed":
            filtered = [p for p in filtered if p.status == PluginStatus.INSTALLED]
        elif self.filter_status == "not_installed":
            filtered = [p for p in filtered if p.status == PluginStatus.NOT_INSTALLED]
        elif self.filter_status == "failed":
            filtered = [p for p in filtered if p.status == PluginStatus.FAILED]

        # Type filter
        if self.filter_type == "legacy":
            filtered = [p for p in filtered if p.plugin_type == PluginType.LEGACY]
        elif self.filter_type == "modern":
            filtered = [p for p in filtered if p.plugin_type == PluginType.MODERN]

        self.filtered_plugins = filtered
        self.apply_sort()

    def apply_advanced_filters(self, filters: dict) -> None:
        """
        Apply advanced filters from AdvancedSearch component.

        Args:
            filters: Dict with keys: text, statuses (list), types (list),
                     tags (list), date_range (str: "7d", "30d", "90d", "all")
        """
        filtered = self.plugins

        # Text filter
        text = filters.get("text", "")
        if text:
            text_lower = text.lower()
            filtered = [p for p in filtered if text_lower in p.name.lower()]

        # Status filters (multi-select)
        statuses = filters.get("statuses", [])
        if statuses:
            status_map = {
                "installed": PluginStatus.INSTALLED,
                "not_installed": PluginStatus.NOT_INSTALLED,
                "failed": PluginStatus.FAILED
            }
            filtered = [p for p in filtered if p.status in [status_map.get(s) for s in statuses if s in status_map]]

        # Type filters (multi-select)
        types = filters.get("types", [])
        if types:
            type_map = {
                "legacy": PluginType.LEGACY,
                "modern": PluginType.MODERN
            }
            filtered = [p for p in filtered if p.plugin_type in [type_map.get(t) for t in types if t in type_map]]

        # Tag filters (multi-select)
        tags = filters.get("tags", [])
        if tags:
            filtered = [p for p in filtered if any(tag in (p.tags or []) for tag in tags)]

        # Date range filter
        date_range = filters.get("date_range", "all")
        if date_range != "all":
            from datetime import timedelta, datetime, timezone

            days_map = {"7d": 7, "30d": 30, "90d": 90}
            days = days_map.get(date_range)
            if days:
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
                filtered = [p for p in filtered if p.last_updated_at and p.last_updated_at >= cutoff_date]

        self.filtered_plugins = filtered
        self.apply_sort()
        logger.info(f"Applied advanced filters: {len(self.filtered_plugins)} results")

    def apply_sort(self) -> None:
        """Apply current sorting to plugin list."""
        reverse = not self.sort_ascending

        if self.sort_by == "name":
            self.filtered_plugins.sort(key=lambda p: p.name.lower(), reverse=reverse)
        elif self.sort_by == "status":
            # Sort by status (not_installed first, then installed, then failed)
            status_order = {
                PluginStatus.NOT_INSTALLED: 0,
                PluginStatus.INSTALLED: 1,
                PluginStatus.FAILED: 2,
            }
            self.filtered_plugins.sort(
                key=lambda p: status_order.get(p.status, 99),
                reverse=reverse,
            )
        elif self.sort_by == "version":
            self.filtered_plugins.sort(
                key=lambda p: p.installed_version or "",
                reverse=reverse,
            )
        elif self.sort_by == "method":
            self.filtered_plugins.sort(
                key=lambda p: p.installation_method.value if p.installation_method else "",
                reverse=reverse,
            )
        elif self.sort_by == "last_updated":
            self.filtered_plugins.sort(
                key=lambda p: p.last_updated_at or datetime.min,
                reverse=not reverse,  # Most recent first
            )

    def set_filter_text(self, text: str) -> None:
        """Set text filter."""
        self.filter_text = text
        self.apply_filters()

    def set_filter_status(self, status: str) -> None:
        """Set status filter."""
        self.filter_status = status
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
        return sum(1 for p in self.plugins if p.status == PluginStatus.INSTALLED)

    def get_not_installed_count(self) -> int:
        """Get number of not installed plugins."""
        return sum(1 for p in self.plugins if p.status == PluginStatus.NOT_INSTALLED)

    def get_failed_count(self) -> int:
        """Get number of failed plugins."""
        return sum(1 for p in self.plugins if p.status == PluginStatus.FAILED)

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

    def remove_selected(self) -> bool:
        """
        Remove selected plugin from catalog.

        Returns:
            True if callback executed
        """
        if self.selected_plugin and self.on_remove_callback:
            self.on_remove_callback(self.selected_plugin)
            return True
        return False

    def can_install(self, plugin: Plugin) -> bool:
        """Check if plugin can be installed."""
        return plugin.status == PluginStatus.NOT_INSTALLED

    def can_update(self, plugin: Plugin) -> bool:
        """Check if plugin can be updated."""
        return plugin.status == PluginStatus.INSTALLED

    def can_uninstall(self, plugin: Plugin) -> bool:
        """Check if plugin can be uninstalled."""
        return plugin.status == PluginStatus.INSTALLED

    def can_remove(self, plugin: Plugin) -> bool:
        """Check if plugin can be removed from catalog."""
        return True  # All plugins can be removed

    def get_status_text(self, plugin: Plugin) -> str:
        """Get status text for plugin."""
        if plugin.status == PluginStatus.INSTALLED:
            return "Installed"
        elif plugin.status == PluginStatus.NOT_INSTALLED:
            return "Not Installed"
        elif plugin.status == PluginStatus.FAILED:
            return "Failed"
        return "Unknown"

    def get_status_color(self, plugin: Plugin) -> tuple:
        """Get status color for UI display (RGB) from theme."""
        if plugin.status == PluginStatus.INSTALLED:
            return get_theme_color("badge_installed")
        elif plugin.status == PluginStatus.NOT_INSTALLED:
            return get_theme_color("badge_not_installed")
        elif plugin.status == PluginStatus.FAILED:
            return get_theme_color("badge_failed")
        return get_theme_color("badge_unknown")

    def get_version_display(self, plugin: Plugin) -> str:
        """Get version string for display."""
        if plugin.status != PluginStatus.INSTALLED:
            return "-"

        if plugin.installation_method == InstallationMethod.CLONE:
            # Show commit hash for clone
            return f"({plugin.installed_version[:8]})" if plugin.installed_version else "(dev)"
        else:
            # Show version tag for release
            return plugin.installed_version or "unknown"

    def get_method_badge(self, plugin: Plugin) -> str:
        """Get installation method badge."""
        if plugin.status != PluginStatus.INSTALLED:
            return "-"

        if plugin.installation_method == InstallationMethod.CLONE:
            return "[Clone]"
        elif plugin.installation_method == InstallationMethod.RELEASE:
            return "[Release]"
        else:
            return "[Unknown]"

    def get_method_color(self, plugin: Plugin) -> tuple:
        """Get installation method color for UI display (RGB) from theme."""
        if plugin.status != PluginStatus.INSTALLED:
            return get_theme_color("badge_unknown")

        if plugin.installation_method == InstallationMethod.CLONE:
            return get_theme_color("badge_clone")
        elif plugin.installation_method == InstallationMethod.RELEASE:
            return get_theme_color("badge_release")
        else:
            return get_theme_color("badge_unknown")

    def get_tags_display(self, plugin: Plugin) -> str:
        """Get tags as display string with badges."""
        if not plugin.tags:
            return "-"

        # Show max 3 tags
        display_tags = plugin.tags[:3]

        # Format as badges: [tag1][tag2][tag3]
        return "".join(f"[{tag}]" for tag in display_tags)

    def format_last_update(self, plugin: Plugin) -> str:
        """Format last update time for display."""
        if not plugin.last_updated_at:
            return "Never"

        now = datetime.now(timezone.utc)
        delta = now - plugin.last_updated_at

        if delta.days > 365:
            years = delta.days // 365
            return f"{years}y ago"
        elif delta.days > 30:
            months = delta.days // 30
            return f"{months}mo ago"
        elif delta.days > 0:
            return f"{delta.days}d ago"
        elif delta.seconds > 3600:
            hours = delta.seconds // 3600
            return f"{hours}h ago"
        elif delta.seconds > 60:
            minutes = delta.seconds // 60
            return f"{minutes}m ago"
        else:
            return "Just now"
