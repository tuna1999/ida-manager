"""
About dialog for IDA Plugin Manager.

Displays application information, version, license, and links.
"""

import uuid
from typing import Optional


class AboutDialog:
    """
    About dialog for the application.

    Shows:
    - Application name and version
    - Description
    - License information
    - Links to repository
    """

    def __init__(self, dpg, version: str = "0.1.0"):
        """
        Initialize the About dialog.

        Args:
            dpg: Dear PyGui module reference
            version: Application version string
        """
        self.dpg = dpg
        self.version = version
        self._dialog_id: Optional[int] = None
        # Generate unique instance ID for this dialog
        self._instance_id = str(uuid.uuid4())[:8]

    def show(self) -> None:
        """Show the about dialog."""
        if self._dialog_id is not None and self.dpg.does_item_exist(self._dialog_id):
            # Dialog already open, focus it
            self.dpg.focus_item(self._dialog_id)
            return

        dialog_width = 500
        dialog_height = 350
        dialog_tag = f"about_dialog_{self._instance_id}"

        with self.dpg.window(
            label="About IDA Plugin Manager",
            modal=True,
            tag=dialog_tag,
            width=dialog_width,
            height=dialog_height,
            pos=(200, 200)
        ):
            self._dialog_id = dialog_tag

            self.dpg.add_spacer(height=15)

            # Title
            self.dpg.add_text("IDA Plugin Manager", color=(100, 200, 255, 255))
            self.dpg.add_spacer(height=5)

            # Version
            version_text = f"Version {self.version}"
            self.dpg.add_text(version_text, color=(180, 180, 180, 255))
            self.dpg.add_spacer(height=15)

            # Description
            description = (
                "A standalone Windows application for managing IDA Pro plugins.\n"
                "Discover, install, update, and manage plugins from GitHub."
            )
            self.dpg.add_text(description, wrap=dialog_width - 40)
            self.dpg.add_spacer(height=15)

            # Features
            features_text = (
                "Features:\n"
                "• Plugin discovery from GitHub\n"
                "• Installation via git clone or release downloads\n"
                "• Version tracking and update checking\n"
                "• Support for both legacy and modern plugin formats"
            )
            self.dpg.add_text(features_text, wrap=dialog_width - 40, color=(150, 180, 150, 255))
            self.dpg.add_spacer(height=15)

            # License
            self.dpg.add_text("License: MIT", color=(150, 150, 150, 255))
            self.dpg.add_spacer(height=5)

            # Links
            self.dpg.add_text("GitHub Repository:", color=(150, 150, 150, 255))
            repo_url = "https://github.com/yourusername/IDA-plugins-manager"
            self.dpg.add_text(repo_url, wrap=dialog_width - 40, color=(100, 150, 255, 255))

            self.dpg.add_spacer(height=15)

            # Close button
            with self.dpg.group(horizontal=True):
                # Center the button
                self.dpg.add_spacer(width=(dialog_width // 2) - 50)
                self.dpg.add_button(label="Close", callback=self._close, width=100)

    def _close(self) -> None:
        """Close the dialog."""
        if self._dialog_id and self.dpg.does_item_exist(self._dialog_id):
            self.dpg.delete_item(self._dialog_id)
            self._dialog_id = None
