"""
Add Plugin dialog for IDA Plugin Manager.

Allows users to add plugins to catalog without installing.
"""

import uuid
from typing import Optional, Callable

from src.models.plugin import ValidationResult
from src.ui.spacing import Spacing
from src.utils.logger import get_logger

logger = get_logger(__name__)


class InstallURLDialog:
    """
    Dialog for adding plugins to catalog.

    Features:
    - URL input with validation
    - Plugin preview before adding
    - Integration with GitHubClient and RepoParser
    """

    def __init__(self, dpg, plugin_service, status_panel):
        """
        Initialize the dialog.

        Args:
            dpg: Dear PyGui module reference
            plugin_service: PluginService instance for operations
            status_panel: StatusPanel for user feedback
        """
        self.dpg = dpg
        self.plugin_service = plugin_service
        self.status_panel = status_panel
        self.plugin_info: Optional[ValidationResult] = None
        self._validated_url: Optional[str] = None  # Store validated URL
        # Generate unique instance ID for UUID-based tags
        self._instance_id = str(uuid.uuid4())[:8]
        self._dialog_id: Optional[int] = None
        self._url_input_tag = f"install_url_input_{self._instance_id}"
        self._preview_group_tag = f"install_preview_group_{self._instance_id}"
        self._install_button_tag = f"install_confirm_button_{self._instance_id}"

    def show(self, on_add_callback: Optional[Callable] = None) -> None:
        """
        Show the add plugin dialog.

        Args:
            on_add_callback: Optional callback for add action
        """
        if self._dialog_id is not None and self.dpg.does_item_exist(self._dialog_id):
            # Dialog already open, focus it
            self.dpg.focus_item(self._dialog_id)
            return

        # Use UUID-based tag for dialog window
        dialog_tag = f"install_url_dialog_{self._instance_id}"
        with self.dpg.window(label="Add Plugin from URL", modal=True,
                            tag=dialog_tag, width=500, height=400,
                            pos=(100, 100)):
            self._dialog_id = dialog_tag

            self.dpg.add_spacer(height=Spacing.SM)
            self.dpg.add_text("Enter GitHub Repository URL:")
            self.dpg.add_spacer(height=Spacing.XS)

            # URL input field
            self.dpg.add_input_text(
                hint="https://github.com/owner/repo",
                tag=self._url_input_tag,
                width=450,
                callback=self._on_url_changed
            )

            self.dpg.add_spacer(height=Spacing.SM)

            # Validate button
            self.dpg.add_button(
                label="Validate & Preview",
                callback=self._on_validate,
                width=150
            )

            self.dpg.add_spacer(height=Spacing.MD)
            self.dpg.add_separator()
            self.dpg.add_spacer(height=Spacing.SM)

            # Preview section (hidden initially)
            with self.dpg.group(tag=self._preview_group_tag, show=False):
                self.dpg.add_text("[Preview]", color=(150, 150, 150, 255))
                self.dpg.add_spacer(height=Spacing.XS)

                self.dpg.add_text("Name:", tag=f"preview_name_label_{self._instance_id}")
                self.dpg.add_text("Not loaded", tag=f"preview_name_value_{self._instance_id}")
                self.dpg.add_spacer(height=Spacing.XS)

                self.dpg.add_text("Description:", tag=f"preview_desc_label_{self._instance_id}")
                self.dpg.add_text("Not loaded", tag=f"preview_desc_value_{self._instance_id}", wrap=450)
                self.dpg.add_spacer(height=Spacing.XS)

                self.dpg.add_text("Version:", tag=f"preview_version_label_{self._instance_id}")
                self.dpg.add_text("Not loaded", tag=f"preview_version_value_{self._instance_id}")
                self.dpg.add_spacer(height=Spacing.XS)

                self.dpg.add_text("Author:", tag=f"preview_author_label_{self._instance_id}")
                self.dpg.add_text("Not loaded", tag=f"preview_author_value_{self._instance_id}")

            self.dpg.add_spacer(height=Spacing.MD)

            # Action buttons
            with self.dpg.group(horizontal=True):
                self.dpg.add_button(
                    label="Add",
                    tag=self._install_button_tag,
                    callback=lambda: self._on_add_to_catalog(on_add_callback),
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
        # Get current URL value
        current_url = self.dpg.get_value(self._url_input_tag)

        # Only reset if URL actually changed from the validated URL
        # This prevents Dear PyGui from firing this callback at unexpected times
        if self._validated_url and current_url == self._validated_url:
            logger.debug(f"URL unchanged ({current_url}), not resetting plugin_info")
            return

        # Reset preview when URL changes
        logger.info(f"URL changed from '{self._validated_url}' to '{current_url}', resetting plugin_info")
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

        logger.info(f"=== VALIDATE START === URL: {url}")

        if not validate_github_url(url):
            logger.error(f"URL validation failed: {url}")
            self.status_panel.add_error("Invalid GitHub URL format")
            return

        # Parse URL to get owner/repo
        parsed = parse_github_url(url)
        if not parsed:
            logger.error(f"Failed to parse URL (returned None): {url}")
            self.status_panel.add_error("Failed to parse GitHub URL")
            return

        owner, repo = parsed
        logger.info(f"Parsed URL: owner={owner}, repo={repo}")

        # Fetch repository info
        try:
            from src.github.client import GitHubClient
            from src.github.repo_parser import RepoParser

            client = GitHubClient()

            # Fetch repository contents
            logger.info(f"Fetching repository contents for {owner}/{repo}...")
            contents = client.get_repository_contents(owner, repo)
            logger.info(f"Got {len(contents) if contents else 0} items in repository")

            if not contents:
                logger.error("No contents returned from repository")

                # Provide more specific error message
                error_msg = (
                    "Could not access repository. Possible reasons:\n"
                    "• Repository does not exist or URL is incorrect\n"
                    "• Repository is private (add GitHub token in settings)\n"
                    "• Network or API error"
                )
                self.status_panel.add_error(error_msg)
                return

            # Fetch README for metadata
            logger.info("Fetching README...")
            readme = client.get_readme(owner, repo)
            if readme:
                logger.info(f"README fetched: {len(readme)} characters")
            else:
                logger.warning("No README found")

            # Check for ida-plugin.json (IDA Pro 9.0+ official format only)
            plugins_json = None
            plugins_json_item = next((item for item in contents if item.name == "ida-plugin.json"), None)
            if plugins_json_item and plugins_json_item.download_url:
                logger.info(f"Found {plugins_json_item.name}, fetching...")
                import requests
                try:
                    response = requests.get(plugins_json_item.download_url, timeout=10)
                    if response.status_code == 200:
                        import json
                        plugins_json = json.loads(response.text)
                        logger.info(f"{plugins_json_item.name} parsed successfully")
                except Exception as e:
                    logger.warning(f"Failed to fetch {plugins_json_item.name}: {e}")

            # Parse plugin metadata
            logger.info("Parsing plugin metadata...")
            parser = RepoParser()
            self.plugin_info = parser.parse_repository(
                repo, contents, readme, plugins_json
            )

            logger.info(f"Parse result: valid={self.plugin_info.valid if self.plugin_info else None}, "
                       f"plugin_type={self.plugin_info.plugin_type if self.plugin_info else None}, "
                       f"has_metadata={self.plugin_info.metadata is not None if self.plugin_info else False}")

            if self.plugin_info and self.plugin_info.metadata:
                logger.info(f"Metadata: name={self.plugin_info.metadata.name}, "
                           f"version={self.plugin_info.metadata.version}, "
                           f"description={self.plugin_info.metadata.description[:50] if self.plugin_info.metadata.description else None}...")

            if not self.plugin_info or not self.plugin_info.valid:
                logger.error(f"Plugin validation failed: {self.plugin_info.error if self.plugin_info else 'No result'}")
                self.status_panel.add_error("This repository does not contain a valid IDA plugin")
                self.plugin_info = None
                self._validated_url = None
                return

            # Store validated URL for install
            self._validated_url = url

            # Update preview
            logger.info("Updating preview...")
            self._update_preview()

            # Enable install button
            if self.dpg.does_item_exist(self._install_button_tag):
                self.dpg.configure_item(self._install_button_tag, enabled=True)

            logger.info("=== VALIDATE SUCCESS ===")
            self.status_panel.add_success("Plugin validated successfully")

        except Exception as e:
            logger.error(f"Error validating plugin: {e}", exc_info=True)
            self.status_panel.add_error(f"Validation failed: {e}")
            self.plugin_info = None

    def _update_preview(self) -> None:
        """Update the preview section with plugin info."""
        if not self.plugin_info or not self.plugin_info.metadata:
            return

        metadata = self.plugin_info.metadata

        # Show preview group
        if self.dpg.does_item_exist(self._preview_group_tag):
            self.dpg.configure_item(self._preview_group_tag, show=True)

        # Update preview values (using UUID-based tags)
        name_value_tag = f"preview_name_value_{self._instance_id}"
        desc_value_tag = f"preview_desc_value_{self._instance_id}"
        version_value_tag = f"preview_version_value_{self._instance_id}"
        author_value_tag = f"preview_author_value_{self._instance_id}"

        if self.dpg.does_item_exist(name_value_tag):
            self.dpg.set_value(name_value_tag, metadata.name or "Unknown")

        if self.dpg.does_item_exist(desc_value_tag):
            desc = metadata.description or "No description available"
            self.dpg.set_value(desc_value_tag, desc)

        if self.dpg.does_item_exist(version_value_tag):
            version = metadata.version or "Unknown"
            self.dpg.set_value(version_value_tag, version)

        if self.dpg.does_item_exist(author_value_tag):
            author = metadata.author or "Unknown"
            self.dpg.set_value(author_value_tag, author)

    def _on_add_to_catalog(self, callback: Optional[Callable] = None) -> None:
        """Handle add to catalog button click."""
        logger.info("=== ADD TO CATALOG START ===")

        if not self.plugin_info:
            logger.error("No plugin_info available")
            self.status_panel.add_error("No plugin to add")
            return

        logger.info(f"plugin_info: valid={self.plugin_info.valid}, "
                   f"has_metadata={self.plugin_info.metadata is not None}")

        # Use stored validated URL instead of reading from input field
        url = self._validated_url
        logger.info(f"Using validated URL: '{url}'")

        if not url:
            logger.error("No validated URL available")
            self.status_panel.add_error("No URL to add")
            return

        # CRITICAL: Save plugin_info to local variables BEFORE closing dialog
        # Closing the dialog may trigger callbacks that reset self.plugin_info
        plugin_info_copy = self.plugin_info
        metadata = plugin_info_copy.metadata if plugin_info_copy else None

        logger.info(f"Saved metadata={metadata} before closing dialog")

        # Close dialog
        self._close()

        # Execute add via callback or directly
        if callback:
            logger.info("Using callback for add")
            callback(plugin_info_copy)
        else:
            # Direct add
            try:
                # Use add_plugin_to_catalog method
                logger.info("Calling plugin_service.add_plugin_to_catalog...")
                logger.info(f"Adding with metadata={metadata}")

                result = self.plugin_service.add_plugin_to_catalog(
                    url=url,
                    metadata=metadata,
                )

                logger.info(f"Add result: {result}")

                if result:
                    # Use local metadata variable (saved before closing dialog)
                    plugin_name = metadata.name if metadata else "plugin"
                    logger.info(f"=== ADD SUCCESS === {plugin_name}")
                    self.status_panel.add_success(f"Added {plugin_name} to catalog")
                else:
                    logger.error(f"=== ADD FAILED ===")
                    self.status_panel.add_error("Failed to add plugin to catalog")

            except Exception as e:
                logger.error(f"Error adding plugin to catalog: {e}", exc_info=True)
                self.status_panel.add_error(f"Add error: {e}")

    def _close(self) -> None:
        """Close the dialog."""
        if self._dialog_id and self.dpg.does_item_exist(self._dialog_id):
            self.dpg.delete_item(self._dialog_id)
            self._dialog_id = None

        # Reset state
        self.plugin_info = None
