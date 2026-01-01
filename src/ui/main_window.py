"""
Main application window for IDA Plugin Manager.

Built with Dear PyGui 2.x for a native Windows feel.
"""

import sys

from src.config.settings import SettingsManager
from src.core.ida_detector import IDADetector
from src.core.plugin_manager import PluginManager
from src.database.db_manager import DatabaseManager
from src.ui.plugin_browser import PluginBrowser
from src.ui.status_panel import StatusPanel
from src.ui.themes import apply_theme
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
        """Create plugin list panel."""
        dpg = self._dpg

        with dpg.child_window(label="Plugins", width=500, height=400, autosize_x=True, autosize_y=True):
            dpg.add_text("Plugin list will appear here")

            # For now, show a simple list of plugin names
            plugins = self.plugin_browser.filtered_plugins
            if plugins:
                for i, plugin in enumerate(plugins[:10]):  # Show first 10
                    status = "Installed" if plugin.installed_version else "Available"
                    dpg.add_text(f"{plugin.name} ({status})")

                if len(plugins) > 10:
                    dpg.add_text(f"... and {len(plugins) - 10} more")
            else:
                dpg.add_text("No plugins found. Use 'Scan Local Plugins' to discover plugins.")

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
        self.status_panel.add_info("Install from URL feature coming soon")

    def _on_settings(self) -> None:
        """Handle settings."""
        self.status_panel.add_info("Settings dialog coming soon")

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
        self.status_panel.add_info("Checking for updates...")

    def _on_scan_local(self) -> None:
        """Handle scan local plugins."""
        try:
            plugins = self.plugin_manager.scan_local_plugins()
            self.status_panel.add_success(f"Found {len(plugins)} local plugins")

            # Add discovered plugins to database
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

            self._load_plugins()
            self._refresh_ui()
        except Exception as e:
            self.status_panel.add_error(f"Scan failed: {e}")

    def _on_about(self) -> None:
        """Handle about dialog."""
        self.status_panel.add_info("IDA Plugin Manager v0.1.0")

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

    def _refresh_ui(self) -> None:
        """Refresh UI elements."""
        # Update statistics
        if self._dpg:
            self._dpg.set_value("stat_total", f"Total: {self.plugin_browser.get_plugin_count()}")
            self._dpg.set_value("stat_installed", f"Installed: {self.plugin_browser.get_installed_count()}")
            self._dpg.set_value("stat_available", f"Available: {self.plugin_browser.get_available_count()}")

            # Refresh plugin list (would need full redraw in production)
            # For now, this is a simplified version


def main() -> int:
    """
    Main entry point for GUI application.

    Returns:
        Exit code
    """
    app = MainWindow()
    return app.run()
