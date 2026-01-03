"""
Split View component for IDA Plugin Manager.

Provides a resizable split view with list and details panes.
"""

from typing import Optional, Callable
from src.models.plugin import Plugin
from src.ui.spacing import Spacing
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SplitView:
    """
    Resizable split view component.

    Features:
    - Left pane: Plugin list (60% default)
    - Right pane: Plugin details (40% default)
    - Resizable splitter
    - Collapsible details pane
    - Persistent split ratio
    """

    def __init__(self, dpg, settings_manager):
        """
        Initialize the split view.

        Args:
            dpg: Dear PyGui module reference
            settings_manager: SettingsManager instance for persistence
        """
        self.dpg = dpg
        self.settings = settings_manager

        # Split configuration
        self._split_ratio = self._load_split_ratio()  # Default 0.60 (60% list, 40% details)
        self._details_collapsed = self._load_details_collapsed()
        self._is_resizing = False

        # Tags
        self._container_tag: Optional[int] = None
        self._left_pane_tag = "split_left_pane"
        self._right_pane_tag = "split_right_pane"
        self._splitter_tag = "split_splitter"
        self._details_container_tag = "split_details_container"

        # Current plugin
        self._current_plugin: Optional[Plugin] = None

        # Callbacks
        self._on_install_callback: Optional[Callable] = None
        self._on_update_callback: Optional[Callable] = None
        self._on_uninstall_callback: Optional[Callable] = None

    def _load_split_ratio(self) -> float:
        """Load split ratio from settings."""
        try:
            config = self.settings.load()
            split_config = config.get("ui", {}).get("split_view", {})
            return split_config.get("ratio", 0.60)
        except Exception:
            return 0.60

    def _save_split_ratio(self, ratio: float) -> None:
        """Save split ratio to settings."""
        try:
            config = self.settings.load()
            if "ui" not in config:
                config["ui"] = {}
            if "split_view" not in config["ui"]:
                config["ui"]["split_view"] = {}
            config["ui"]["split_view"]["ratio"] = ratio
            self.settings.save(config)
        except Exception as e:
            logger.warning(f"Failed to save split ratio: {e}")

    def _load_details_collapsed(self) -> bool:
        """Load details collapsed state from settings."""
        try:
            config = self.settings.load()
            split_config = config.get("ui", {}).get("split_view", {})
            return split_config.get("collapsed", False)
        except Exception:
            return False

    def _save_details_collapsed(self, collapsed: bool) -> None:
        """Save details collapsed state to settings."""
        try:
            config = self.settings.load()
            if "ui" not in config:
                config["ui"] = {}
            if "split_view" not in config["ui"]:
                config["ui"]["split_view"] = {}
            config["ui"]["split_view"]["collapsed"] = collapsed
            self.settings.save(config)
        except Exception as e:
            logger.warning(f"Failed to save details collapsed state: {e}")

    def create(self, parent_tag: str, width: int, height: int) -> None:
        """
        Create the split view.

        Args:
            parent_tag: Parent widget tag
            width: Total width of split view
            height: Total height of split view
        """
        dpg = self.dpg

        # Calculate pane widths based on split ratio
        if self._details_collapsed:
            left_width = width - 20  # Reserve space for toggle button
            right_width = 0
        else:
            left_width = int(width * self._split_ratio)
            right_width = width - left_width - 20  # Reserve space for splitter

        # Main container
        with dpg.group(horizontal=True, tag="split_view_container", parent=parent_tag):
            # Left pane - Plugin list
            with dpg.child_window(label="Plugins", width=left_width, height=height,
                                  tag=self._left_pane_tag, border=True):
                pass  # Content will be added by main window

            # Splitter (resizable handle)
            if not self._details_collapsed:
                with dpg.group(width=20):
                    dpg.add_spacer(height=height // 2 - 10)
                    dpg.add_separator()
                    dpg.add_spacer(height=20)
                    # This could be made draggable in future
            else:
                # Toggle button to expand details
                dpg.add_spacer(width=10)
                dpg.add_button(label=">", width=10, callback=self._toggle_details, tag="split_expand_button")
                dpg.add_spacer(width=10)

            # Right pane - Plugin details
            if not self._details_collapsed:
                with dpg.child_window(label="Details", width=right_width, height=height,
                                      tag=self._right_pane_tag, border=True):
                    self._create_details_content()
            else:
                # Collapsed - no content
                pass

        # Toggle button in details header (for collapsing)
        if not self._details_collapsed and dpg.does_item_exist(self._right_pane_tag):
            # Add collapse button to details pane
            pass  # Will be added in toolbar or header

    def _create_details_content(self) -> None:
        """Create the details panel content."""
        dpg = self.dpg

        with dpg.group(tag=self._details_container_tag):
            dpg.add_spacer(height=Spacing.MD)

            if self._current_plugin:
                # Show plugin details
                self._show_plugin_details(self._current_plugin)
            else:
                # Empty state
                dpg.add_text("No plugin selected", color=(150, 150, 150, 255))
                dpg.add_spacer(height=Spacing.SM)
                dpg.add_text("Select a plugin from the list to view details",
                           color=(120, 120, 120, 255), wrap=300)

    def _show_plugin_details(self, plugin: Plugin) -> None:
        """Show details for selected plugin."""
        dpg = self.dpg

        # Clear previous content
        if dpg.does_item_exist(self._details_container_tag):
            dpg.delete_item(self._details_container_tag)

        with dpg.group(tag=self._details_container_tag):
            dpg.add_spacer(height=Spacing.MD)

            # Plugin name
            dpg.add_text(plugin.name, color=(100, 200, 255, 255))

            dpg.add_spacer(height=Spacing.SM)

            # Status badge
            status_text = self._get_status_text(plugin)
            status_color = self._get_status_color(plugin)
            dpg.add_text(f"Status: {status_text}", color=status_color)

            dpg.add_spacer(height=Spacing.SM)

            # Version and type
            if plugin.status.value == "installed":
                version_display = self._get_version_display(plugin)
                dpg.add_text(f"Version: {version_display}")
                dpg.add_spacer(height=Spacing.XS)

            dpg.add_text(f"Type: {plugin.plugin_type.value.capitalize()}")

            dpg.add_spacer(height=Spacing.MD)

            # Description
            if plugin.description:
                dpg.add_text("Description:")
                dpg.add_spacer(height=Spacing.XS)
                dpg.add_text(plugin.description, wrap=350, color=(180, 180, 180, 255))
                dpg.add_spacer(height=Spacing.MD)

            # Author
            if plugin.author:
                dpg.add_text(f"Author: {plugin.author}")
                dpg.add_spacer(height=Spacing.SM)

            # Repository
            if plugin.repository_url:
                dpg.add_text("Repository:", color=(150, 150, 150, 255))
                dpg.add_spacer(height=Spacing.XS)
                dpg.add_text(plugin.repository_url, wrap=350, color=(100, 160, 230, 255))
                dpg.add_spacer(height=Spacing.MD)

            # Tags
            if plugin.tags:
                tags_display = " ".join(f"[{tag}]" for tag in plugin.tags[:5])
                dpg.add_text(f"Tags: {tags_display}")
                dpg.add_spacer(height=Spacing.MD)

            # IDA Version compatibility
            if plugin.ida_version_min or plugin.ida_version_max:
                version_range = ""
                if plugin.ida_version_min:
                    version_range += f"{plugin.ida_version_min}+"
                if plugin.ida_version_max:
                    version_range += f" - {plugin.ida_version_max}"
                dpg.add_text(f"IDA: {version_range}")
                dpg.add_spacer(height=Spacing.MD)

            # Action buttons
            dpg.add_separator()
            dpg.add_spacer(height=Spacing.MD)

            with dpg.group(horizontal=True):
                if plugin.status.value == "not_installed":
                    dpg.add_button(label="Install", callback=self._on_install_clicked,
                                  width=100)
                elif plugin.status.value == "installed":
                    dpg.add_button(label="Update", callback=self._on_update_clicked,
                                  width=100)
                    dpg.add_spacer(width=Spacing.SM)
                    dpg.add_button(label="Uninstall", callback=self._on_uninstall_clicked,
                                  width=100)

            dpg.add_spacer(height=Spacing.LG)

            # Metadata info
            if plugin.added_at:
                from datetime import datetime
                added_str = plugin.added_at.strftime("%Y-%m-%d %H:%M")
                dpg.add_text(f"Added: {added_str}", color=(140, 140, 140, 255))

            if plugin.last_updated_at:
                updated_str = plugin.last_updated_at.strftime("%Y-%m-%d %H:%M")
                dpg.add_text(f"Updated: {updated_str}", color=(140, 140, 140, 255))

    def _get_status_text(self, plugin: Plugin) -> str:
        """Get status text for plugin."""
        status_map = {
            "installed": "Installed",
            "not_installed": "Not Installed",
            "failed": "Failed"
        }
        return status_map.get(plugin.status.value, "Unknown")

    def _get_status_color(self, plugin: Plugin) -> tuple:
        """Get status color for plugin."""
        from src.ui.themes import get_theme_color
        color_map = {
            "installed": "badge_installed",
            "not_installed": "badge_not_installed",
            "failed": "badge_failed"
        }
        color_name = color_map.get(plugin.status.value, "badge_unknown")
        return get_theme_color(color_name)

    def _get_version_display(self, plugin: Plugin) -> str:
        """Get version display string."""
        from src.models.plugin import InstallationMethod

        if plugin.installation_method == InstallationMethod.CLONE:
            return f"({plugin.installed_version[:8]})" if plugin.installed_version else "(dev)"
        else:
            return plugin.installed_version or "unknown"

    def set_plugin(self, plugin: Optional[Plugin]) -> None:
        """
        Set the current plugin and update details panel.

        Args:
            plugin: Plugin to show details for, or None to clear
        """
        self._current_plugin = plugin

        if self.dpg.does_item_exist(self._right_pane_tag):
            # Recreate details content
            if self.dpg.does_item_exist(self._details_container_tag):
                self.dpg.delete_item(self._details_container_tag)
            self._create_details_content()

    def _on_install_clicked(self) -> None:
        """Handle install button click."""
        if self._current_plugin and self._on_install_callback:
            self._on_install_callback(self._current_plugin)

    def _on_update_clicked(self) -> None:
        """Handle update button click."""
        if self._current_plugin and self._on_update_callback:
            self._on_update_callback(self._current_plugin)

    def _on_uninstall_clicked(self) -> None:
        """Handle uninstall button click."""
        if self._current_plugin and self._on_uninstall_callback:
            self._on_uninstall_callback(self._current_plugin)

    def _toggle_details(self) -> None:
        """Toggle details panel collapsed state."""
        self._details_collapsed = not self._details_collapsed
        self._save_details_collapsed(self._details_collapsed)

        # Recreate the split view
        # This would need to be called from main window
        # For now, just log the action
        logger.info(f"Details panel toggled: collapsed={self._details_collapsed}")

    def set_callbacks(self, on_install: Optional[Callable] = None,
                     on_update: Optional[Callable] = None,
                     on_uninstall: Optional[Callable] = None) -> None:
        """
        Set action callbacks.

        Args:
            on_install: Callback for install action
            on_update: Callback for update action
            on_uninstall: Callback for uninstall action
        """
        self._on_install_callback = on_install
        self._on_update_callback = on_update
        self._on_uninstall_callback = on_uninstall

    def get_left_pane_tag(self) -> str:
        """Get the left pane tag for adding content."""
        return self._left_pane_tag

    def get_right_pane_tag(self) -> str:
        """Get the right pane tag."""
        return self._right_pane_tag
