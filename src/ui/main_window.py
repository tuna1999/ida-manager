"""
Main application window for IDA Plugin Manager.

Built with Dear PyGui 2.x for a native Windows feel.
"""

import sys
from typing import Optional

from src.config.settings import SettingsManager
from src.core.ida_detector import IDADetector
from src.core.plugin_manager import PluginManager
from src.database.db_manager import DatabaseManager
from src.models.plugin import Plugin
from src.ui.plugin_browser import PluginBrowser
from src.ui.status_panel import StatusPanel
from src.ui.themes import apply_theme
from src.ui.dialogs.settings_dialog import SettingsDialog
from src.ui.dialogs.install_url_dialog import InstallURLDialog
from src.ui.dialogs.about_dialog import AboutDialog
from src.ui.dialogs.plugin_details_dialog import PluginDetailsDialog
from src.ui.dialogs.progress_dialog import ProgressDialog
from src.ui.dialogs.confirm_dialog import ConfirmDialog
from src.utils.logger import setup_logging, get_logger

logger = get_logger(__name__)


class MainWindow:
    """
    Main application window.

    Coordinates all UI components and handles user interactions.
    """

    def __init__(self):
        """Initialize main window."""
        # Initialize settings
        self.settings = SettingsManager()
        setup_logging(log_level=self.settings.config.advanced.log_level)

        # Initialize core components
        self.db_manager = DatabaseManager()
        self.db_manager.init_database()

        self.ida_detector = IDADetector()
        self.plugin_manager = PluginManager(
            db_manager=self.db_manager,
            ida_detector=self.ida_detector,
        )

        # UI components
        self.status_panel = StatusPanel()
        self.plugin_browser = PluginBrowser()

        # Set up callbacks
        self._setup_browser_callbacks()

        # Load plugins
        self._load_plugins()

        # Dear PyGui context
        self._dpg = None
        self._window_id = None

        self.status_panel.add_info("Application initialized")

    def _setup_browser_callbacks(self) -> None:
        """Set up plugin browser callbacks."""
        self.plugin_browser.on_install_callback = self._on_install_plugin
        self.plugin_browser.on_update_callback = self._on_update_plugin
        self.plugin_browser.on_uninstall_callback = self._on_uninstall_plugin

    def _load_plugins(self) -> None:
        """Load plugins from database."""
        try:
            plugins = self.plugin_manager.get_all_plugins()
            self.plugin_browser.set_plugins(plugins)
            self.status_panel.add_success(f"Loaded {len(plugins)} plugins")
        except Exception as e:
            self.status_panel.add_error(f"Failed to load plugins: {e}")

    def run(self) -> int:
        """
        Run the application.

        Returns:
            Exit code
        """
        try:
            import dearpygui.dearpygui as dpg

            self._dpg = dpg

            # Create context
            dpg.create_context()

            # Create viewport
            dpg.create_viewport(
                title=f"IDA Plugin Manager v{self.settings.config.version}",
                width=self.settings.config.ui.window_width,
                height=self.settings.config.ui.window_height,
            )

            # Apply theme
            apply_theme(self.settings.config.ui.theme)

            # Create main window
            self._create_main_window()

            # Set up as primary window
            dpg.set_primary_window("main_window", True)

            # Start
            dpg.setup_dearpygui()
            dpg.show_viewport()
            dpg.start_dearpygui()

            # Cleanup
            dpg.destroy_context()

            return 0

        except ImportError:
            logger.error("Dear PyGui not installed. Install with: pip install dearpygui")
            return 1
        except Exception as e:
            logger.error(f"Application error: {e}", exc_info=True)
            return 1

    def _create_main_window(self) -> None:
        """Create main window UI."""
        dpg = self._dpg

        with dpg.window(label="IDA Plugin Manager", tag="main_window", width=800, height=600):
            # Menu bar
            self._create_menu_bar()

            # Toolbar
            self._create_toolbar()

            # Main content - use group instead of splitter for simplicity
            dpg.add_spacer(height=10)
            with dpg.group(horizontal=True):
                # Left panel - Filters
                self._create_filter_panel()

                # Right panel - Plugin list
                self._create_plugin_list_panel()

            # Status bar
            dpg.add_spacer(height=10)
            self._create_status_bar()

    def _create_menu_bar(self) -> None:
        """Create menu bar."""
        dpg = self._dpg

        with dpg.menu_bar():
            with dpg.menu(label="File"):
                dpg.add_menu_item(label="Refresh Plugins", callback=self._on_refresh)
                dpg.add_menu_item(label="Install from URL...", callback=self._on_install_from_url)
                dpg.add_separator()
                dpg.add_menu_item(label="Settings", callback=self._on_settings)
                dpg.add_separator()
                dpg.add_menu_item(label="Exit", callback=self._on_exit)

            with dpg.menu(label="View"):
                dpg.add_menu_item(label="Installed Only", callback=self._on_toggle_installed)
                dpg.add_menu_item(label="Available Only", callback=self._on_toggle_available)
                dpg.add_separator()
                dpg.add_menu_item(label="Sort by Name", callback=lambda: self._on_sort("name"))
                dpg.add_menu_item(label="Sort by Version", callback=lambda: self._on_sort("version"))

            with dpg.menu(label="Tools"):
                dpg.add_menu_item(label="Check for Updates", callback=self._on_check_updates)
                dpg.add_menu_item(label="Scan Local Plugins", callback=self._on_scan_local)

            with dpg.menu(label="Help"):
                dpg.add_menu_item(label="About", callback=self._on_about)

    def _create_toolbar(self) -> None:
        """Create toolbar."""
        dpg = self._dpg

        with dpg.group(horizontal=True):
            dpg.add_button(label="Refresh", callback=self._on_refresh, width=80)
            dpg.add_button(label="Install", callback=self._on_install_from_url, width=80)
            dpg.add_button(label="Settings", callback=self._on_settings, width=80)
            dpg.add_spacer(width=20)

            # IDA status
            ida_version = self.settings.config.ida.version or "Not detected"
            dpg.add_text(f"IDA: {ida_version}")

    def _create_filter_panel(self) -> None:
        """Create filter panel."""
        dpg = self._dpg

        with dpg.child_window(label="Filters", width=250, height=400):
            dpg.add_spacer(height=10)

            # Search
            dpg.add_text("Search:")
            dpg.add_input_text(
                tag="search_input",
                hint="Search plugins...",
                width=200,
                callback=self._on_search_changed,
            )

            dpg.add_spacer(height=10)
            dpg.add_separator()

            # Filters
            dpg.add_text("Show:")
            dpg.add_checkbox(
                label="Installed Only",
                tag="filter_installed",
                callback=self._on_filter_changed,
            )
            dpg.add_checkbox(
                label="Available Only",
                tag="filter_available",
                callback=self._on_filter_changed,
            )

            dpg.add_spacer(height=10)
            dpg.add_separator()

            # Type filter
            dpg.add_text("Type:")
            dpg.add_combo(
                items=["All", "Legacy", "Modern"],
                tag="filter_type_combo",
                default_value="All",
                width=200,
                callback=self._on_type_filter_changed,
            )

            dpg.add_spacer(height=10)
            dpg.add_separator()

            # Statistics
            dpg.add_text("Statistics:")
            dpg.add_text(f"Total: {self.plugin_browser.get_plugin_count()}", tag="stat_total")
            dpg.add_text(
                f"Installed: {self.plugin_browser.get_installed_count()}",
                tag="stat_installed",
            )
            dpg.add_text(
                f"Available: {self.plugin_browser.get_available_count()}",
                tag="stat_available",
            )

    def _create_plugin_list_panel(self) -> None:
        """Create plugin list panel with interactive table."""
        dpg = self._dpg

        # Specify parent explicitly to avoid context issues when refreshing
        with dpg.child_window(label="Plugins", width=500, height=400, autosize_x=True, autosize_y=True, tag="plugins_child_window", parent="main_window"):
            plugins = self.plugin_browser.filtered_plugins

            if not plugins:
                dpg.add_text("No plugins found. Use 'Scan Local Plugins' to discover plugins.")
                return

            # Create table with header row
            with dpg.table(header_row=True, row_background=True, borders_innerH=True,
                          borders_outerV=True, scrollY=True, height=350,
                          tag="plugin_table", callback=self._on_table_selection):
                # Header columns
                with dpg.table_row():
                    dpg.add_table_column(label="Name", init_width_or_weight=150)
                    dpg.add_table_column(label="Version", init_width_or_weight=80)
                    dpg.add_table_column(label="Type", init_width_or_weight=80)
                    dpg.add_table_column(label="Status", init_width_or_weight=100)
                    dpg.add_table_column(label="Author", init_width_or_weight=120)

                # Data rows
                for plugin in plugins:
                    with dpg.table_row(tag=f"row_{plugin.id}"):
                        dpg.add_text(plugin.name)
                        dpg.add_text(plugin.installed_version or "-")
                        dpg.add_text(plugin.plugin_type.capitalize())
                        status = "Installed" if plugin.installed_version else "Available"
                        dpg.add_text(status)
                        dpg.add_text(plugin.author or "Unknown")

            # Action buttons below table
            dpg.add_spacer(height=5)
            with dpg.group(horizontal=True, tag="plugin_buttons_group"):
                dpg.add_button(label="Install", callback=self._on_install_selected, width=80)
                dpg.add_button(label="Update", callback=self._on_update_selected, width=80)
                dpg.add_button(label="Uninstall", callback=self._on_uninstall_selected, width=80)
                dpg.add_button(label="Details", callback=self._on_show_details, width=80)

    def _create_status_bar(self) -> None:
        """Create status bar."""
        dpg = self._dpg

        with dpg.child_window(label="Status", height=60, autosize_x=True):
            msg, msg_type = self.status_panel.get_latest_message()
            if msg:
                dpg.add_text(f"[{msg_type.upper()}] {msg}")
            else:
                dpg.add_text("Ready")

    # ============ Event Handlers ============

    def _on_refresh(self) -> None:
        """Handle refresh action."""
        self._load_plugins()
        self.status_panel.add_info("Plugins refreshed")
        self._refresh_ui()

    def _on_install_from_url(self) -> None:
        """Handle install from URL."""
        from src.ui.dialogs.install_url_dialog import InstallURLDialog

        dialog = InstallURLDialog(self._dpg, self.plugin_manager, self.status_panel)
        dialog.show()

    def _on_settings(self) -> None:
        """Handle settings."""
        from src.ui.dialogs.settings_dialog import SettingsDialog

        dialog = SettingsDialog(self._dpg, self.settings, self.ida_detector, self.status_panel)
        dialog.show()

    def _on_exit(self) -> None:
        """Handle exit."""
        if self._dpg:
            self._dpg.stop_dearpygui()

    def _on_toggle_installed(self) -> None:
        """Toggle installed filter."""
        self.plugin_browser.set_show_installed_only(True)
        self._refresh_ui()

    def _on_toggle_available(self) -> None:
        """Toggle available filter."""
        self.plugin_browser.set_show_available_only(True)
        self._refresh_ui()

    def _on_sort(self, sort_by: str) -> None:
        """Handle sort action."""
        self.plugin_browser.set_sort_by(sort_by)
        self._refresh_ui()

    def _on_check_updates(self) -> None:
        """Handle check for updates."""
        if self._dpg is None:
            return

        # Show progress dialog
        progress = ProgressDialog(self._dpg)
        progress.show(title="Checking for Updates", status="Checking for plugin updates...", show_cancel=False)

        try:
            # Check for updates
            updates = self.plugin_manager.check_all_updates()

            # Close progress dialog
            progress.close()

            # Display results
            if updates:
                count = len(updates)
                self.status_panel.add_success(f"Found {count} plugin(s) with updates")

                # Show details of plugins with updates
                for plugin, update_info in updates[:5]:  # Show first 5
                    self.status_panel.add_info(f"{plugin.name}: {plugin.installed_version} → {update_info.latest_version}")
                if len(updates) > 5:
                    self.status_panel.add_info(f"...and {len(updates) - 5} more")
            else:
                self.status_panel.add_info("No updates available for installed plugins")

        except Exception as e:
            progress.close()
            logger.error(f"Error checking for updates: {e}", exc_info=True)
            self.status_panel.add_error(f"Failed to check for updates: {e}")

    def _on_scan_local(self) -> None:
        """Handle scan local plugins."""
        if self._dpg is None:
            return

        # Show progress dialog
        progress = ProgressDialog(self._dpg)
        progress.show(title="Scanning Local Plugins", status="Scanning for IDA plugins...", show_cancel=False)

        try:
            # Scan for local plugins
            plugins = self.plugin_manager.scan_local_plugins()

            # Close progress dialog
            progress.close()

            # Show result
            self.status_panel.add_success(f"Found {len(plugins)} local plugins")

            # Add discovered plugins to database
            added_count = 0
            for plugin in plugins:
                from src.database.models import Plugin as DBPlugin
                from datetime import datetime

                existing = self.db_manager.get_plugin(plugin.id)
                if not existing:
                    db_plugin = DBPlugin(
                        id=plugin.id,
                        name=plugin.name,
                        description=plugin.description,
                        author=plugin.author,
                        installed_version=plugin.installed_version,
                        plugin_type=plugin.plugin_type,
                        install_path=plugin.install_path,
                        is_active=True,
                        install_date=datetime.utcnow() if plugin.installed_version else None,
                    )
                    self.db_manager.add_plugin(db_plugin)
                    added_count += 1

            if added_count > 0:
                self.status_panel.add_info(f"Added {added_count} new plugin(s) to database")

            self._load_plugins()
            self._refresh_ui()
        except Exception as e:
            progress.close()
            logger.error(f"Error scanning local plugins: {e}", exc_info=True)
            self.status_panel.add_error(f"Scan failed: {e}")

    def _on_about(self) -> None:
        """Handle about dialog."""
        if self._dpg is None:
            return

        dialog = AboutDialog(self._dpg, version=self.settings.config.version)
        dialog.show()

    def _on_search_changed(self) -> None:
        """Handle search text change."""
        dpg = self._dpg
        text = dpg.get_value("search_input")
        self.plugin_browser.set_filter_text(text)
        self._refresh_ui()

    def _on_filter_changed(self) -> None:
        """Handle filter change."""
        dpg = self._dpg
        installed = dpg.get_value("filter_installed")
        available = dpg.get_value("filter_available")

        if installed:
            self.plugin_browser.set_show_installed_only(True)
        elif available:
            self.plugin_browser.set_show_available_only(True)
        else:
            self.plugin_browser.set_show_installed_only(False)
            self.plugin_browser.set_show_available_only(False)

        self._refresh_ui()

    def _on_type_filter_changed(self) -> None:
        """Handle type filter change."""
        dpg = self._dpg
        type_value = dpg.get_value("filter_type_combo").lower()

        if type_value == "all":
            self.plugin_browser.set_filter_type("all")
        else:
            self.plugin_browser.set_filter_type(type_value)

        self._refresh_ui()

    def _on_install_plugin(self, plugin) -> None:
        """Handle plugin install."""
        self.status_panel.add_info(f"Installing {plugin.name}...")

    def _on_update_plugin(self, plugin) -> None:
        """Handle plugin update."""
        self.status_panel.add_info(f"Updating {plugin.name}...")

    def _on_uninstall_plugin(self, plugin) -> None:
        """Handle plugin uninstall."""
        self.status_panel.add_info(f"Uninstalling {plugin.name}...")

    def _on_table_selection(self, sender, app_data, user_data) -> None:
        """Handle table row selection."""
        # app_data contains selected row index in Dear PyGui table
        if app_data is not None:
            row = int(app_data) if isinstance(app_data, (int, str)) else app_data[0]
            # Get the plugin at the selected row
            plugin = self.plugin_browser.get_plugin_at_index(row)
            if plugin:
                self.plugin_browser.selected_plugin = plugin
                self.status_panel.add_info(f"Selected: {plugin.name}")

    def _on_install_selected(self) -> None:
        """Handle install button click."""
        plugin = self.plugin_browser.selected_plugin
        if plugin:
            self._on_install_plugin(plugin)
        else:
            self.status_panel.add_warning("Please select a plugin to install")

    def _on_update_selected(self) -> None:
        """Handle update button click."""
        plugin = self.plugin_browser.selected_plugin
        if not plugin:
            self.status_panel.add_warning("Please select a plugin to update")
            return

        from src.ui.dialogs.confirm_dialog import ConfirmDialog

        def do_update():
            self._on_update_plugin(plugin)

        dialog = ConfirmDialog(self._dpg)
        dialog.show(
            title="Confirm Update",
            message=f"Update '{plugin.name}' to the latest version?",
            detail=f"Current version: {plugin.installed_version or 'Unknown'}",
            on_yes=do_update
        )

    def _on_uninstall_selected(self) -> None:
        """Handle uninstall button click."""
        plugin = self.plugin_browser.selected_plugin
        if not plugin:
            self.status_panel.add_warning("Please select a plugin to uninstall")
            return

        from src.ui.dialogs.confirm_dialog import ConfirmDialog

        def do_uninstall():
            self._on_uninstall_plugin(plugin)

        dialog = ConfirmDialog(self._dpg)
        dialog.show(
            title="Confirm Uninstall",
            message=f"Are you sure you want to uninstall '{plugin.name}'?",
            detail=f"Version: {plugin.installed_version or 'Unknown'}\nThis action cannot be undone.",
            on_yes=do_uninstall
        )

    def _on_show_details(self) -> None:
        """Handle details button click."""
        plugin = self.plugin_browser.selected_plugin
        if plugin and self._dpg:
            dialog = PluginDetailsDialog(self._dpg)
            dialog.show(plugin)
        else:
            self.status_panel.add_warning("Please select a plugin to view details")

    def _refresh_ui(self) -> None:
        """Refresh UI elements."""
        # Update statistics
        if self._dpg:
            self._dpg.set_value("stat_total", f"Total: {self.plugin_browser.get_plugin_count()}")
            self._dpg.set_value("stat_installed", f"Installed: {self.plugin_browser.get_installed_count()}")
            self._dpg.set_value("stat_available", f"Available: {self.plugin_browser.get_available_count()}")

            # Delete and recreate plugin child window for proper refresh
            if self._dpg.does_item_exist("plugins_child_window"):
                self._dpg.delete_item("plugins_child_window")

            # Recreate the plugin list panel
            self._create_plugin_list_panel()


def main() -> int:
    """
    Main entry point for GUI application.

    Returns:
        Exit code
    """
    app = MainWindow()
    return app.run()
