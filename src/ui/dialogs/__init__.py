"""
Dialog components for IDA Plugin Manager UI.

This package contains modal dialogs for various user interactions:
- InstallURLDialog: Install plugin from GitHub URL
- SettingsDialog: Application settings
- ConfirmDialog: Confirmation dialogs
- ProgressDialog: Progress indication for long operations
"""

from src.ui.dialogs.install_url_dialog import InstallURLDialog
from src.ui.dialogs.settings_dialog import SettingsDialog
from src.ui.dialogs.confirm_dialog import ConfirmDialog
from src.ui.dialogs.progress_dialog import ProgressDialog

__all__ = ["InstallURLDialog", "SettingsDialog", "ConfirmDialog", "ProgressDialog"]
