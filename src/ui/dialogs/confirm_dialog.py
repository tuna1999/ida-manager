"""
Confirmation dialog for IDA Plugin Manager.

A generic modal dialog for confirming user actions.
"""

import uuid
from typing import Optional, Callable

from src.ui.spacing import Spacing
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ConfirmDialog:
    """
    Generic confirmation dialog.

    Features:
    - Customizable title and message
    - Optional detail text
    - Yes/No buttons
    - Callback-based result handling
    """

    def __init__(self, dpg):
        """
        Initialize the dialog.

        Args:
            dpg: Dear PyGui module reference
        """
        self.dpg = dpg
        # Generate unique instance ID for UUID-based tags
        self._instance_id = str(uuid.uuid4())[:8]
        self._dialog_id: Optional[int] = None
        self._result: Optional[bool] = None
        self._on_yes_callback: Optional[Callable] = None
        self._on_no_callback: Optional[Callable] = None

    def show(self, title: str, message: str, detail: str = "",
             on_yes: Optional[Callable] = None,
             on_no: Optional[Callable] = None) -> None:
        """
        Show a confirmation dialog.

        Args:
            title: Dialog title
            message: Main message/question
            detail: Optional detail text
            on_yes: Callback when Yes is clicked
            on_no: Callback when No is clicked
        """
        if self._dialog_id is not None and self.dpg.does_item_exist(self._dialog_id):
            # Dialog already open, close it first
            self._close()

        self._result = None
        self._on_yes_callback = on_yes
        self._on_no_callback = on_no

        # Use UUID-based tag for dialog window
        dialog_tag = f"confirm_dialog_{self._instance_id}"
        with self.dpg.window(label=title, modal=True,
                            tag=dialog_tag, width=400, height=200,
                            pos=(150, 150)):
            self._dialog_id = dialog_tag

            self.dpg.add_spacer(height=Spacing.MD)

            # Main message
            self.dpg.add_text(message, wrap=380)

            # Detail text (if provided)
            if detail:
                self.dpg.add_spacer(height=Spacing.SM)
                self.dpg.add_text(detail, color=(150, 150, 150, 255), wrap=380)

            self.dpg.add_spacer(height=Spacing.XL)

            # Yes/No buttons
            with self.dpg.group(horizontal=True):
                self.dpg.add_spacer(width=100)
                self.dpg.add_button(
                    label="Yes",
                    callback=self._on_yes,
                    width=80
                )
                self.dpg.add_spacer(width=20)
                self.dpg.add_button(
                    label="No",
                    callback=self._on_no,
                    width=80
                )

    def _on_yes(self) -> None:
        """Handle Yes button click."""
        self._result = True
        if self._on_yes_callback:
            self._on_yes_callback()
        self._close()

    def _on_no(self) -> None:
        """Handle No button click."""
        self._result = False
        if self._on_no_callback:
            self._on_no_callback()
        self._close()

    def _close(self) -> None:
        """Close the dialog."""
        if self._dialog_id and self.dpg.does_item_exist(self._dialog_id):
            self.dpg.delete_item(self._dialog_id)
            self._dialog_id = None

    @property
    def result(self) -> Optional[bool]:
        """Get the dialog result (True=Yes, False=No, None=Not answered)."""
        return self._result
