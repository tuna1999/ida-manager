"""
Status panel component for displaying messages and feedback.
"""

from typing import List, Tuple
from datetime import datetime

from src.ui.themes import get_status_color
from src.utils.logger import get_logger

logger = get_logger(__name__)


class StatusMessage:
    """Single status message."""

    def __init__(self, message: str, status_type: str = "info", timestamp: datetime = None):
        """
        Initialize status message.

        Args:
            message: Message text
            status_type: Type ("success", "warning", "error", "info")
            timestamp: Message timestamp (default: now)
        """
        self.message = message
        self.status_type = status_type
        self.timestamp = timestamp or datetime.now()


class StatusPanel:
    """
    Status panel for displaying operation feedback.

    Shows messages with color coding and timestamps.
    """

    def __init__(self, max_messages: int = 100):
        """
        Initialize status panel.

        Args:
            max_messages: Maximum number of messages to keep
        """
        self.max_messages = max_messages
        self.messages: List[StatusMessage] = []

    def add_info(self, message: str) -> None:
        """Add info message."""
        self._add_message(message, "info")
        logger.info(message)

    def add_success(self, message: str) -> None:
        """Add success message."""
        self._add_message(message, "success")
        logger.info(f"SUCCESS: {message}")

    def add_warning(self, message: str) -> None:
        """Add warning message."""
        self._add_message(message, "warning")
        logger.warning(message)

    def add_error(self, message: str, exception: Exception = None) -> None:
        """Add error message."""
        self._add_message(message, "error")
        if exception:
            logger.error(f"{message}: {exception}", exc_info=exception)
        else:
            logger.error(message)

    def _add_message(self, message: str, status_type: str) -> None:
        """Add message to list."""
        msg = StatusMessage(message, status_type)
        self.messages.append(msg)

        # Trim to max
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]

    def get_latest_message(self) -> Tuple[str, str]:
        """
        Get latest message text and type.

        Returns:
            Tuple of (message, status_type)
        """
        if self.messages:
            msg = self.messages[-1]
            return msg.message, msg.status_type
        return "", "info"

    def get_recent_messages(self, count: int = 10) -> List[StatusMessage]:
        """
        Get recent messages.

        Args:
            count: Number of recent messages

        Returns:
            List of recent messages
        """
        return self.messages[-count:]

    def clear(self) -> None:
        """Clear all messages."""
        self.messages.clear()

    def get_message_color(self, status_type: str, theme: str = "Dark") -> Tuple[int, int, int, int]:
        """Get color for message type."""
        return get_status_color(status_type, theme)
