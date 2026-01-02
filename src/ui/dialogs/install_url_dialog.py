"""
Install from URL dialog for IDA Plugin Manager.

Allows users to install plugins directly from GitHub URLs.
"""

from typing import Optional, Callable
from src.models.plugin import PluginMetadata
from src.utils.logger import get_logger

logger = get_logger(__name__)


class InstallURLDialog:
    """
    Dialog for installing plugins from GitHub URLs.

    Features:
    - URL input with validation
    - Plugin preview before installation
    - Integration with GitHubClient and RepoParser
    """

    def __init__(self, dpg, plugin_manager, status_panel):
        """
        Initialize the dialog.

        Args:
            dpg: Dear PyGui module reference
            plugin_manager: PluginManager instance for operations
            status_panel: StatusPanel for user feedback
        """
        self.dpg = dpg
        self.plugin_manager = plugin_manager
        self.status_panel = status_panel
        self.plugin_info: Optional[PluginMetadata] = None
        self._dialog_id: Optional[int] = None
        self._url_input_tag = "install_url_input"
        self._preview_group_tag = "install_preview_group"
        self._install_button_tag = "install_confirm_button"

    def show(self, on_install_callback: Optional[Callable] = None) -> None:
        """
        Show the install URL dialog.

        Args:
            on_install_callback: Optional callback for install action
        """
        if self._dialog_id is not None and self.dpg.does_item_exist(self._dialog_id):
            # Dialog already open, focus it
            self.dpg.focus_item(self._dialog_id)
            return

        with self.dpg.window(label="Install from URL", modal=True,
                            tag="install_url_dialog", width=500, height=400,
                            pos=(100, 100)):
            self._dialog_id = "install_url_dialog"

            self.dpg.add_spacer(height=10)
            self.dpg.add_text("Enter GitHub Repository URL:")
            self.dpg.add_spacer(height=5)

            # URL input field
            self.dpg.add_input_text(
                hint="https://github.com/owner/repo",
                tag=self._url_input_tag,
                width=450,
                callback=self._on_url_changed
            )

            self.dpg.add_spacer(height=10)

            # Validate button
            self.dpg.add_button(
                label="Validate & Preview",
                callback=self._on_validate,
                width=150
            )

            self.dpg.add_spacer(height=15)
            self.dpg.add_separator()
            self.dpg.add_spacer(height=10)

            # Preview section (hidden initially)
            with self.dpg.group(tag=self._preview_group_tag, show=False):
                self.dpg.add_text("[Preview]", color=(150, 150, 150, 255))
                self.dpg.add_spacer(height=5)

                self.dpg.add_text("Name:", tag="preview_name_label")
                self.dpg.add_text("Not loaded", tag="preview_name_value")
                self.dpg.add_spacer(height=5)

                self.dpg.add_text("Description:", tag="preview_desc_label")
                self.dpg.add_text("Not loaded", tag="preview_desc_value", wrap=450)
                self.dpg.add_spacer(height=5)

                self.dpg.add_text("Version:", tag="preview_version_label")
                self.dpg.add_text("Not loaded", tag="preview_version_value")
                self.dpg.add_spacer(height=5)

                self.dpg.add_text("Author:", tag="preview_author_label")
                self.dpg.add_text("Not loaded", tag="preview_author_value")

            self.dpg.add_spacer(height=15)

            # Action buttons
            with self.dpg.group(horizontal=True):
                self.dpg.add_button(
                    label="Install",
                    tag=self._install_button_tag,
                    callback=lambda: self._on_install(on_install_callback),
                    width=100,
                    enabled=False
                )
                self.dpg.add_button(
                    label="Cancel",
                    callback=self._close,
                    width=100
                )

    def _on_url_changed(self, sender, app_data, user_data) -> None:
        """Handle URL input change."""
        # Reset preview when URL changes
        self.plugin_info = None
        if self.dpg.does_item_exist(self._preview_group_tag):
            self.dpg.configure_item(self._preview_group_tag, show=False)
        if self.dpg.does_item_exist(self._install_button_tag):
            self.dpg.configure_item(self._install_button_tag, enabled=False)

    def _on_validate(self) -> None:
        """Handle validate button click."""
        url = self.dpg.get_value(self._url_input_tag)

        if not url:
            self.status_panel.add_warning("Please enter a GitHub URL")
            return

        # Validate URL format
        from src.utils.validators import validate_github_url, parse_github_url

        if not validate_github_url(url):
            self.status_panel.add_error("Invalid GitHub URL format")
            return

        # Parse URL to get owner/repo
        try:
            owner, repo = parse_github_url(url)
        except Exception as e:
            self.status_panel.add_error(f"Failed to parse URL: {e}")
            return

        # Fetch repository info
        try:
            from src.github.client import GitHubClient
            from src.github.repo_parser import RepoParser

            client = GitHubClient()
            repo_info = client.get_repository_info(owner, repo)

            if not repo_info:
                self.status_panel.add_error("Repository not found or API error")
                return

            # Parse plugin metadata
            parser = RepoParser()
            self.plugin_info = parser.parse_repository(
                owner, repo, repo_info, None, client
            )

            if not self.plugin_info or not self.plugin_info.is_valid:
                self.status_panel.add_error("This repository does not contain a valid IDA plugin")
                self.plugin_info = None
                return

            # Update preview
            self._update_preview()

            # Enable install button
            if self.dpg.does_item_exist(self._install_button_tag):
                self.dpg.configure_item(self._install_button_tag, enabled=True)

            self.status_panel.add_success("Plugin validated successfully")

        except Exception as e:
            logger.error(f"Error validating plugin: {e}", exc_info=True)
            self.status_panel.add_error(f"Validation failed: {e}")
            self.plugin_info = None

    def _update_preview(self) -> None:
        """Update the preview section with plugin info."""
        if not self.plugin_info:
            return

        # Show preview group
        if self.dpg.does_item_exist(self._preview_group_tag):
            self.dpg.configure_item(self._preview_group_tag, show=True)

        # Update preview values
        if self.dpg.does_item_exist("preview_name_value"):
            self.dpg.set_value("preview_name_value", self.plugin_info.name or "Unknown")

        if self.dpg.does_item_exist("preview_desc_value"):
            desc = self.plugin_info.description or "No description available"
            self.dpg.set_value("preview_desc_value", desc)

        if self.dpg.does_item_exist("preview_version_value"):
            version = self.plugin_info.latest_version or "Unknown"
            self.dpg.set_value("preview_version_value", version)

        if self.dpg.does_item_exist("preview_author_value"):
            author = self.plugin_info.author or "Unknown"
            self.dpg.set_value("preview_author_value", author)

    def _on_install(self, callback: Optional[Callable] = None) -> None:
        """Handle install button click."""
        if not self.plugin_info:
            self.status_panel.add_error("No plugin to install")
            return

        # Close dialog
        self._close()

        # Execute install via callback or directly
        if callback:
            callback(self.plugin_info)
        else:
            # Direct install
            try:
                url = self.dpg.get_value(self._url_input_tag)
                from src.utils.validators import parse_github_url
                owner, repo = parse_github_url(url)

                # Use full URL with install_plugin method
                # use_development=True maps to method="clone" (git clone)
                result = self.plugin_manager.install_plugin(
                    repo_url=url,
                    method="clone",   # Clone = git clone (development version)
                    branch="main"
                )

                if result.success:
                    self.status_panel.add_success(f"Installed {self.plugin_info.name} successfully")
                else:
                    self.status_panel.add_error(f"Installation failed: {result.message}")

            except Exception as e:
                logger.error(f"Error installing plugin: {e}", exc_info=True)
                self.status_panel.add_error(f"Installation error: {e}")

    def _close(self) -> None:
        """Close the dialog."""
        if self._dialog_id and self.dpg.does_item_exist(self._dialog_id):
            self.dpg.delete_item(self._dialog_id)
            self._dialog_id = None

        # Reset state
        self.plugin_info = None
