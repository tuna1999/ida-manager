"""
Progress dialog for IDA Plugin Manager.

Modal dialog showing progress for long-running operations.
"""

from typing import Optional, Callable
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ProgressDialog:
    """
    Progress dialog for long-running operations.

    Features:
    - Progress bar with percentage
    - Status text message
    - Optional cancel button
    - Callback-based updates
    """

    def __init__(self, dpg):
        """
        Initialize the dialog.

        Args:
            dpg: Dear PyGui module reference
        """
        self.dpg = dpg
        self._dialog_id: Optional[int] = None
        self._progress_bar_tag = "progress_bar"
        self._status_text_tag = "progress_status"
        self._percentage_tag = "progress_percentage"
        self._cancel_callback: Optional[Callable] = None
        self._is_closed = False

    def show(self, title: str = "Processing",
             status: str = "Please wait...",
             show_cancel: bool = False,
             on_cancel: Optional[Callable] = None) -> None:
        """
        Show the progress dialog.

        Args:
            title: Dialog window title
            status: Initial status message
            show_cancel: Whether to show cancel button
            on_cancel: Callback when cancel is clicked
        """
        if self._dialog_id is not None and self.dpg.does_item_exist(self._dialog_id):
            # Dialog already open
            return

        self._cancel_callback = on_cancel
        self._is_closed = False

        with self.dpg.window(label=title, modal=True,
                            tag="progress_dialog", width=400, height=150,
                            pos=(150, 200)):
            self._dialog_id = "progress_dialog"

            self.dpg.add_spacer(height=20)

            # Status text
            self.dpg.add_text(status, tag=self._status_text_tag, wrap=380)

            self.dpg.add_spacer(height=20)

            # Progress bar
            self.dpg.add_progress_bar(
                tag=self._progress_bar_tag,
                width=380,
                default_value=0.0,
                overlay="0%"
            )

            self.dpg.add_spacer(height=10)

            # Percentage text
            self.dpg.add_text("0%", tag=self._percentage_tag)

            self.dpg.add_spacer(height=15)

            # Cancel button (optional)
            if show_cancel:
                with self.dpg.group(horizontal=True):
                    self.dpg.add_spacer(width=150)
                    self.dpg.add_button(
                        label="Cancel",
                        callback=self._on_cancel,
                        width=80
                    )

    def update_progress(self, value: float, status: Optional[str] = None) -> None:
        """
        Update the progress bar.

        Args:
            value: Progress value (0.0 to 1.0)
            status: Optional new status message
        """
        if self._is_closed:
            return

        # Clamp value between 0 and 1
        value = max(0.0, min(1.0, value))

        # Update progress bar
        if self.dpg.does_item_exist(self._progress_bar_tag):
            self.dpg.set_value(self._progress_bar_tag, value)
            percentage = int(value * 100)
            self.dpg.configure_item(self._progress_bar_tag, overlay=f"{percentage}%")

        # Update percentage text
        if self.dpg.does_item_exist(self._percentage_tag):
            percentage = int(value * 100)
            self.dpg.set_value(self._percentage_tag, f"{percentage}%")

        # Update status if provided
        if status and self.dpg.does_item_exist(self._status_text_tag):
            self.dpg.set_value(self._status_text_tag, status)

    def set_indeterminate(self, status: Optional[str] = None) -> None:
        """
        Show indeterminate progress (for operations without known duration).

        Args:
            status: Optional new status message
        """
        if self._is_closed:
            return

        # Set progress to 0 but show it as active
        if self.dpg.does_item_exist(self._progress_bar_tag):
            self.dpg.set_value(self._progress_bar_tag, 0.0)
            self.dpg.configure_item(self._progress_bar_tag, overlay="Working...")

        # Update status if provided
        if status and self.dpg.does_item_exist(self._status_text_tag):
            self.dpg.set_value(self._status_text_tag, status)

    def close(self) -> None:
        """Close the dialog."""
        if self._dialog_id and self.dpg.does_item_exist(self._dialog_id):
            self.dpg.delete_item(self._dialog_id)
            self._dialog_id = None
        self._is_closed = True

    def _on_cancel(self) -> None:
        """Handle cancel button click."""
        if self._cancel_callback:
            self._cancel_callback()
        self.close()

    @property
    def is_closed(self) -> bool:
        """Check if the dialog is closed."""
        return self._is_closed
