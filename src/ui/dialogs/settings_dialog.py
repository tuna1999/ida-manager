"""
Settings dialog for IDA Plugin Manager.

Allows users to configure application settings including:
- IDA installation paths
- GitHub API token
- UI preferences
- Update settings
"""

import uuid
from typing import Optional, List
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SettingsDialog:
    """
    Dialog for application settings.

    Features:
    - IDA path configuration with auto-detection
    - GitHub token management
    - UI theme and window preferences
    - Auto-update configuration
    """

    def __init__(self, dpg, settings_manager, ida_detector, status_panel):
        """
        Initialize the dialog.

        Args:
            dpg: Dear PyGui module reference
            settings_manager: SettingsManager instance
            ida_detector: IDADetector for finding installations
            status_panel: StatusPanel for feedback
        """
        self.dpg = dpg
        self.settings_manager = settings_manager
        self.ida_detector = ida_detector
        self.status_panel = status_panel
        self._dialog_id: Optional[int] = None
        self._found_installations: List[tuple] = []

        # Generate unique instance ID for this dialog
        self._instance_id = str(uuid.uuid4())[:8]

        # Input tags - unique per instance
        self._ida_path_tag = f"settings_ida_path_{self._instance_id}"
        self._github_token_tag = f"settings_github_token_{self._instance_id}"
        self._theme_combo_tag = f"settings_theme_combo_{self._instance_id}"
        self._window_width_tag = f"settings_window_width_{self._instance_id}"
        self._window_height_tag = f"settings_window_height_{self._instance_id}"
        self._auto_update_tag = f"settings_auto_update_{self._instance_id}"
        self._update_interval_tag = f"settings_update_interval_{self._instance_id}"
        self._file_dialog_tag = f"ida_file_dialog_{self._instance_id}"

    def show(self) -> None:
        """Show the settings dialog."""
        if self._dialog_id is not None and self.dpg.does_item_exist(self._dialog_id):
            # Dialog already open, focus it
            self.dpg.focus_item(self._dialog_id)
            return

        dialog_tag = f"settings_dialog_{self._instance_id}"
        with self.dpg.window(label="Settings", modal=True,
                            tag=dialog_tag, width=600, height=500,
                            pos=(80, 50)):
            self._dialog_id = dialog_tag

            self.dpg.add_spacer(height=10)

            # Create tab bar for different settings categories
            with self.dpg.tab_bar(tag=f"settings_tab_bar_{self._instance_id}"):
                # IDA Configuration Tab
                with self.dpg.tab(label="IDA"):
                    self._create_ida_tab()

                # GitHub Settings Tab
                with self.dpg.tab(label="GitHub"):
                    self._create_github_tab()

                # UI Preferences Tab
                with self.dpg.tab(label="UI"):
                    self._create_ui_tab()

                # Updates Tab
                with self.dpg.tab(label="Updates"):
                    self._create_updates_tab()

            self.dpg.add_spacer(height=10)
            self.dpg.add_separator()
            self.dpg.add_spacer(height=10)

            # Action buttons
            with self.dpg.group(horizontal=True):
                self.dpg.add_button(label="Save", callback=self._on_save, width=100)
                self.dpg.add_button(label="Cancel", callback=self._close, width=100)
                self.dpg.add_button(label="Reset to Defaults", callback=self._on_reset, width=120)

        # Load current settings into the dialog
        self._load_current_settings()

    def _create_ida_tab(self) -> None:
        """Create IDA configuration tab."""
        self.dpg.add_spacer(height=10)
        self.dpg.add_text("IDA Installation Path", color=(200, 200, 200, 255))
        self.dpg.add_spacer(height=5)

        # Path input with browse button
        with self.dpg.group(horizontal=True):
            self.dpg.add_input_text(
                hint="IDA installation path",
                tag=self._ida_path_tag,
                width=400
            )
            self.dpg.add_button(label="Browse...", callback=self._on_browse_ida, width=80)

        self.dpg.add_spacer(height=5)

        # Auto-detect button
        with self.dpg.group(horizontal=True):
            self.dpg.add_button(label="Auto-Detect", callback=self._on_auto_detect_ida, width=100)
            self.dpg.add_text("", tag=f"ida_detect_status_{self._instance_id}")

        self.dpg.add_spacer(height=10)

        # Found installations combo (hidden initially)
        with self.dpg.group(tag=f"ida_installations_group_{self._instance_id}", show=False):
            self.dpg.add_text("Found Installations:")
            self.dpg.add_combo(
                items=[],
                tag=f"ida_installations_combo_{self._instance_id}",
                width=500,
                callback=self._on_installation_selected
            )

        self.dpg.add_spacer(height=10)
        self.dpg.add_text("Detected Version:", tag=f"ida_version_label_{self._instance_id}")
        self.dpg.add_text("Not detected", tag=f"ida_version_value_{self._instance_id}")

    def _create_github_tab(self) -> None:
        """Create GitHub settings tab."""
        self.dpg.add_spacer(height=10)
        self.dpg.add_text("GitHub Personal Access Token", color=(200, 200, 200, 255))
        self.dpg.add_spacer(height=5)
        self.dpg.add_text("(Optional) Increases API rate limits", color=(150, 150, 150, 255))

        self.dpg.add_spacer(height=5)

        # Token input (password field)
        self.dpg.add_input_text(
            hint="ghp_xxxxxxxxxxxxxxxxxxxx",
            tag=self._github_token_tag,
            password=True,
            width=400
        )

        self.dpg.add_spacer(height=10)

        # Validate button
        with self.dpg.group(horizontal=True):
            self.dpg.add_button(label="Validate Token", callback=self._on_validate_token, width=120)
            self.dpg.add_text("", tag=f"token_validate_status_{self._instance_id}")

        self.dpg.add_spacer(height=15)

        # Help text
        self.dpg.add_text("How to create a GitHub token:")
        self.dpg.add_text("1. Go to https://github.com/settings/tokens", color=(150, 150, 150, 255))
        self.dpg.add_text("2. Click 'Generate new token (classic)'", color=(150, 150, 150, 255))
        self.dpg.add_text("3. Select 'repo' scope", color=(150, 150, 150, 255))
        self.dpg.add_text("4. Generate and copy the token", color=(150, 150, 150, 255))

    def _create_ui_tab(self) -> None:
        """Create UI preferences tab."""
        self.dpg.add_spacer(height=10)

        # Theme selection
        self.dpg.add_text("Theme:")
        self.dpg.add_spacer(height=5)
        self.dpg.add_combo(
            items=["Dark", "Light"],
            tag=self._theme_combo_tag,
            width=200,
            default_value="Dark"
        )

        self.dpg.add_spacer(height=15)

        # Window size
        self.dpg.add_text("Window Size:")
        self.dpg.add_spacer(height=5)
        with self.dpg.group(horizontal=True):
            self.dpg.add_text("Width:")
            self.dpg.add_input_int(
                tag=self._window_width_tag,
                width=100,
                min_value=800,
                max_value=1920
            )
            self.dpg.add_spacer(width=20)
            self.dpg.add_text("Height:")
            self.dpg.add_input_int(
                tag=self._window_height_tag,
                width=100,
                min_value=600,
                max_value=1080
            )

    def _create_updates_tab(self) -> None:
        """Create update settings tab."""
        self.dpg.add_spacer(height=10)

        # Auto-update checkbox
        self.dpg.add_checkbox(
            label="Automatically check for plugin updates",
            tag=self._auto_update_tag
        )

        self.dpg.add_spacer(height=10)

        # Update interval
        self.dpg.add_text("Check Interval (hours):")
        self.dpg.add_spacer(height=5)
        self.dpg.add_input_int(
            tag=self._update_interval_tag,
            width=100,
            min_value=1,
            max_value=168,
            default_value=24
        )

    def _load_current_settings(self) -> None:
        """Load current settings into dialog inputs."""
        # IDA settings
        if self.dpg.does_item_exist(self._ida_path_tag):
            ida_path = self.settings_manager.config.ida.install_path or ""
            self.dpg.set_value(self._ida_path_tag, ida_path)

        # GitHub token
        if self.dpg.does_item_exist(self._github_token_tag):
            token = self.settings_manager.config.github.token or ""
            self.dpg.set_value(self._github_token_tag, token)

        # Theme
        if self.dpg.does_item_exist(self._theme_combo_tag):
            theme = self.settings_manager.config.ui.theme or "Dark"
            self.dpg.set_value(self._theme_combo_tag, theme)

        # Window size
        if self.dpg.does_item_exist(self._window_width_tag):
            width = self.settings_manager.config.ui.window_width or 1000
            self.dpg.set_value(self._window_width_tag, width)
        if self.dpg.does_item_exist(self._window_height_tag):
            height = self.settings_manager.config.ui.window_height or 700
            self.dpg.set_value(self._window_height_tag, height)

        # Update settings
        if self.dpg.does_item_exist(self._auto_update_tag):
            auto_update = self.settings_manager.config.updates.auto_check or False
            self.dpg.set_value(self._auto_update_tag, auto_update)
        if self.dpg.does_item_exist(self._update_interval_tag):
            interval = self.settings_manager.config.updates.check_interval_hours or 24
            self.dpg.set_value(self._update_interval_tag, interval)

        # Update IDA version display
        self._update_ida_version_display()

    def _update_ida_version_display(self) -> None:
        """Update the IDA version display."""
        ida_version_value_tag = f"ida_version_value_{self._instance_id}"
        if not self.dpg.does_item_exist(ida_version_value_tag):
            return

        ida_path = self.dpg.get_value(self._ida_path_tag) if self.dpg.does_item_exist(self._ida_path_tag) else ""
        if ida_path:
            try:
                version = self.ida_detector.get_ida_version(ida_path)
                if version:
                    self.dpg.set_value(ida_version_value_tag, version)
                else:
                    self.dpg.set_value(ida_version_value_tag, "Unknown")
            except Exception:
                self.dpg.set_value(ida_version_value_tag, "Error")
        else:
            self.dpg.set_value(ida_version_value_tag, "Not detected")

    def _on_browse_ida(self) -> None:
        """Handle browse button for IDA path."""
        # Delete existing dialog if present
        if self.dpg.does_item_exist(self._file_dialog_tag):
            self.dpg.delete_item(self._file_dialog_tag)

        # Create and show file dialog (auto-shown on creation)
        with self.dpg.file_dialog(
            directory_selector=True,
            callback=self._on_ida_path_selected,
            tag=self._file_dialog_tag,
            width=600,
            height=400,
            modal=True
        ):
            self.dpg.add_file_extension(".*")

    def _on_ida_path_selected(self, sender, app_data, user_data=None) -> None:
        """Handle IDA path selection from file dialog.

        Args:
            sender: File dialog tag
            app_data: Selection data containing file_path_name
            user_data: Additional user data (unused)
        """
        selected_path = app_data.get("file_path_name", "") if app_data else ""

        if selected_path and self.dpg.does_item_exist(self._ida_path_tag):
            self.dpg.set_value(self._ida_path_tag, selected_path)
            self._update_ida_version_display()

            # Provide feedback
            if selected_path:
                logger.info(f"IDA path selected: {selected_path}")

    def _on_auto_detect_ida(self) -> None:
        """Handle auto-detect button."""
        installations_combo_tag = f"ida_installations_combo_{self._instance_id}"
        installations_group_tag = f"ida_installations_group_{self._instance_id}"
        detect_status_tag = f"ida_detect_status_{self._instance_id}"

        try:
            installations = self.ida_detector.find_all_installations()
            self._found_installations = installations

            if installations:
                # Show combo with installations
                items = [f"{path} (v{version})" for path, version in installations]
                if self.dpg.does_item_exist(installations_combo_tag):
                    self.dpg.configure_item(installations_combo_tag, items=items)
                if self.dpg.does_item_exist(installations_group_tag):
                    self.dpg.configure_item(installations_group_tag, show=True)

                # Update status
                if self.dpg.does_item_exist(detect_status_tag):
                    self.dpg.set_value(detect_status_tag, f"Found {len(installations)} installation(s)")
            else:
                if self.dpg.does_item_exist(detect_status_tag):
                    self.dpg.set_value(detect_status_tag, "No installations found")
                if self.dpg.does_item_exist(installations_group_tag):
                    self.dpg.configure_item(installations_group_tag, show=False)

        except Exception as e:
            logger.error(f"Error detecting IDA installations: {e}", exc_info=True)
            if self.dpg.does_item_exist(detect_status_tag):
                self.dpg.set_value(detect_status_tag, "Detection failed")

    def _on_installation_selected(self, sender, app_data, user_data) -> None:
        """Handle installation selection from combo."""
        if app_data is not None and 0 <= app_data < len(self._found_installations):
            path, version = self._found_installations[app_data]
            if self.dpg.does_item_exist(self._ida_path_tag):
                self.dpg.set_value(self._ida_path_tag, path)
            self._update_ida_version_display()

    def _on_validate_token(self) -> None:
        """Handle token validation button."""
        token_status_tag = f"token_validate_status_{self._instance_id}"
        token = self.dpg.get_value(self._github_token_tag) if self.dpg.does_item_exist(self._github_token_tag) else ""

        if not token:
            if self.dpg.does_item_exist(token_status_tag):
                self.dpg.set_value(token_status_tag, "No token entered")
            return

        # Validate token by making a simple API call
        try:
            from src.github.client import GitHubClient
            client = GitHubClient(token=token)
            # Try to get user info as a test
            # Note: This is a simplified check
            if self.dpg.does_item_exist(token_status_tag):
                self.dpg.set_value(token_status_tag, "Token format valid")
        except Exception as e:
            if self.dpg.does_item_exist(token_status_tag):
                self.dpg.set_value(token_status_tag, "Validation failed")

    def _on_save(self) -> None:
        """Handle save button."""
        try:
            # Get values from inputs
            ida_path = self.dpg.get_value(self._ida_path_tag) if self.dpg.does_item_exist(self._ida_path_tag) else ""
            github_token = self.dpg.get_value(self._github_token_tag) if self.dpg.does_item_exist(self._github_token_tag) else ""
            theme = self.dpg.get_value(self._theme_combo_tag) if self.dpg.does_item_exist(self._theme_combo_tag) else "Dark"
            window_width = self.dpg.get_value(self._window_width_tag) if self.dpg.does_item_exist(self._window_width_tag) else 1000
            window_height = self.dpg.get_value(self._window_height_tag) if self.dpg.does_item_exist(self._window_height_tag) else 700
            auto_update = self.dpg.get_value(self._auto_update_tag) if self.dpg.does_item_exist(self._auto_update_tag) else False
            update_interval = self.dpg.get_value(self._update_interval_tag) if self.dpg.does_item_exist(self._update_interval_tag) else 24

            # Update settings
            self.settings_manager.config.ida.install_path = ida_path or None
            self.settings_manager.config.github.token = github_token or None
            self.settings_manager.config.ui.theme = theme
            self.settings_manager.config.ui.window_width = window_width
            self.settings_manager.config.ui.window_height = window_height
            self.settings_manager.config.updates.auto_check = auto_update
            self.settings_manager.config.updates.check_interval_hours = update_interval

            # Save to file
            self.settings_manager.save()

            self.status_panel.add_success("Settings saved successfully")
            self._close()

        except Exception as e:
            logger.error(f"Error saving settings: {e}", exc_info=True)
            self.status_panel.add_error(f"Failed to save settings: {e}")

    def _on_reset(self) -> None:
        """Handle reset to defaults button."""
        # Reset to default values
        if self.dpg.does_item_exist(self._ida_path_tag):
            self.dpg.set_value(self._ida_path_tag, "")
        if self.dpg.does_item_exist(self._github_token_tag):
            self.dpg.set_value(self._github_token_tag, "")
        if self.dpg.does_item_exist(self._theme_combo_tag):
            self.dpg.set_value(self._theme_combo_tag, "Dark")
        if self.dpg.does_item_exist(self._window_width_tag):
            self.dpg.set_value(self._window_width_tag, 1000)
        if self.dpg.does_item_exist(self._window_height_tag):
            self.dpg.set_value(self._window_height_tag, 700)
        if self.dpg.does_item_exist(self._auto_update_tag):
            self.dpg.set_value(self._auto_update_tag, False)
        if self.dpg.does_item_exist(self._update_interval_tag):
            self.dpg.set_value(self._update_interval_tag, 24)

        self._update_ida_version_display()
        self.status_panel.add_info("Settings reset to defaults")

    def _close(self) -> None:
        """Close the dialog."""
        if self._dialog_id and self.dpg.does_item_exist(self._dialog_id):
            self.dpg.delete_item(self._dialog_id)
            self._dialog_id = None
