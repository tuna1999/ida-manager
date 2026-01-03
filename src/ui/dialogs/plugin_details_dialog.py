"""
Plugin Details dialog for IDA Plugin Manager.

Displays comprehensive information about a single plugin.
"""

import uuid
from datetime import datetime
from typing import Optional

from src.models.plugin import Plugin, PluginType
from src.ui.spacing import Spacing


class PluginDetailsDialog:
    """
    Dialog showing detailed plugin information.

    Displays:
    - Plugin name, version, author
    - Full description (scrollable)
    - Repository URL
    - Installation path
    - Plugin type
    - IDA version compatibility
    - Installation/update date
    - Dependencies (if available)
    """

    def __init__(self, dpg):
        """
        Initialize the Plugin Details dialog.

        Args:
            dpg: Dear PyGui module reference
        """
        self.dpg = dpg
        self._dialog_id: Optional[int] = None
        self._child_tag: Optional[int] = None
        # Generate unique instance ID for this dialog
        self._instance_id = str(uuid.uuid4())[:8]

    def show(self, plugin: Plugin) -> None:
        """
        Show the plugin details dialog.

        Args:
            plugin: Plugin object to display details for
        """
        if self._dialog_id is not None and self.dpg.does_item_exist(self._dialog_id):
            # Dialog already open, close and reopen with new data
            self._close()

        dialog_width = 600
        dialog_height = 500
        dialog_tag = f"plugin_details_dialog_{self._instance_id}"
        child_tag = f"details_content_{self._instance_id}"

        with self.dpg.window(
            label=f"Plugin Details - {plugin.name}",
            modal=True,
            tag=dialog_tag,
            width=dialog_width,
            height=dialog_height,
            pos=(150, 100)
        ):
            self._dialog_id = dialog_tag

            self.dpg.add_spacer(height=Spacing.SM)

            # Create child window for scrollable content
            with self.dpg.child_window(
                tag=child_tag,
                width=dialog_width - 20,
                height=dialog_height - 60,
                autosize_x=True,
                autosize_y=True,
                border=False
            ):
                self._child_tag = child_tag

                self.dpg.add_spacer(height=Spacing.XS)

                # Title and version
                title_text = f"{plugin.name} - {plugin.installed_version or plugin.latest_version or 'Unknown'}"
                self.dpg.add_text(title_text, color=(100, 200, 255, 255))
                self.dpg.add_spacer(height=Spacing.SM)

                # Author (if available)
                if plugin.author:
                    self.dpg.add_text(f"Author: {plugin.author}", color=(180, 180, 180, 255))
                    self.dpg.add_spacer(height=Spacing.XS)

                # Plugin type badge
                type_color = (150, 200, 150, 255) if plugin.plugin_type == PluginType.MODERN else (200, 180, 150, 255)
                type_text = f"Type: {plugin.plugin_type.value.upper()}"
                self.dpg.add_text(type_text, color=type_color)
                self.dpg.add_spacer(height=Spacing.SM)

                # Separator
                self.dpg.add_separator()
                self.dpg.add_spacer(height=Spacing.SM)

                # Description
                self.dpg.add_text("Description:", color=(200, 200, 200, 255))
                self.dpg.add_spacer(height=Spacing.XS)
                description = plugin.description or "No description available."
                self.dpg.add_text(description, wrap=dialog_width - 40)
                self.dpg.add_spacer(height=Spacing.MD)

                # Repository URL (if available)
                if plugin.repository_url:
                    self.dpg.add_text("Repository:", color=(200, 200, 200, 255))
                    self.dpg.add_spacer(height=Spacing.XS)
                    self.dpg.add_text(plugin.repository_url, wrap=dialog_width - 40, color=(100, 150, 255, 255))
                    self.dpg.add_spacer(height=Spacing.MD)

                # Installation path (if installed)
                if plugin.install_path:
                    self.dpg.add_text("Installation Path:", color=(200, 200, 200, 255))
                    self.dpg.add_spacer(height=Spacing.XS)
                    self.dpg.add_text(plugin.install_path, wrap=dialog_width - 40, color=(150, 150, 150, 255))
                    self.dpg.add_spacer(height=Spacing.MD)

                # IDA Version Compatibility
                if plugin.ida_version_min or plugin.ida_version_max:
                    self.dpg.add_text("IDA Compatibility:", color=(200, 200, 200, 255))
                    self.dpg.add_spacer(height=Spacing.XS)
                    if plugin.ida_version_min and plugin.ida_version_max:
                        compat_text = f"{plugin.ida_version_min} - {plugin.ida_version_max}"
                    elif plugin.ida_version_min:
                        compat_text = f"{plugin.ida_version_min} and later"
                    elif plugin.ida_version_max:
                        compat_text = f"Up to {plugin.ida_version_max}"
                    else:
                        compat_text = "Unknown"
                    self.dpg.add_text(compat_text, color=(150, 180, 200, 255))
                    self.dpg.add_spacer(height=Spacing.MD)

                # Version Information
                self.dpg.add_text("Version Information:", color=(200, 200, 200, 255))
                self.dpg.add_spacer(height=Spacing.XS)
                if plugin.installed_version:
                    version_text = f"Installed: {plugin.installed_version}"
                    self.dpg.add_text(version_text, color=(150, 200, 150, 255))
                if plugin.latest_version and plugin.latest_version != plugin.installed_version:
                    latest_text = f"Latest: {plugin.latest_version}"
                    self.dpg.add_text(latest_text, color=(150, 180, 255, 255))
                self.dpg.add_spacer(height=Spacing.MD)

                # Installation Date
                if plugin.install_date:
                    self.dpg.add_text("Installed:", color=(200, 200, 200, 255))
                    self.dpg.add_spacer(height=Spacing.XS)
                    date_str = plugin.install_date.strftime("%Y-%m-%d %H:%M:%S") if isinstance(plugin.install_date, datetime) else str(plugin.install_date)
                    self.dpg.add_text(date_str, color=(150, 150, 150, 255))
                    self.dpg.add_spacer(height=Spacing.MD)

                # Last Updated
                if plugin.last_updated:
                    self.dpg.add_text("Last Updated:", color=(200, 200, 200, 255))
                    self.dpg.add_spacer(height=Spacing.XS)
                    updated_str = plugin.last_updated.strftime("%Y-%m-%d %H:%M:%S") if isinstance(plugin.last_updated, datetime) else str(plugin.last_updated)
                    self.dpg.add_text(updated_str, color=(150, 150, 150, 255))
                    self.dpg.add_spacer(height=Spacing.MD)

                # Dependencies (if available in metadata)
                if plugin.metadata and "dependencies" in plugin.metadata:
                    deps = plugin.metadata["dependencies"]
                    if deps:
                        self.dpg.add_text("Dependencies:", color=(200, 200, 200, 255))
                        self.dpg.add_spacer(height=Spacing.XS)
                        deps_text = ", ".join(deps) if isinstance(deps, list) else str(deps)
                        self.dpg.add_text(deps_text, wrap=dialog_width - 40, color=(200, 180, 150, 255))
                        self.dpg.add_spacer(height=Spacing.MD)

                # Status
                self.dpg.add_text("Status:", color=(200, 200, 200, 255))
                self.dpg.add_spacer(height=Spacing.XS)
                status_text = "Active" if plugin.is_active else "Inactive"
                status_color = (150, 200, 150, 255) if plugin.is_active else (200, 150, 150, 255)
                self.dpg.add_text(status_text, color=status_color)

            self.dpg.add_spacer(height=Spacing.SM)

            # Close button
            with self.dpg.group(horizontal=True):
                self.dpg.add_spacer(width=(dialog_width // 2) - 50)
                self.dpg.add_button(label="Close", callback=self._close, width=100)

    def _close(self) -> None:
        """Close the dialog."""
        if self._dialog_id and self.dpg.does_item_exist(self._dialog_id):
            self.dpg.delete_item(self._dialog_id)
            self._dialog_id = None
            self._child_tag = None
