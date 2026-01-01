"""
Logging configuration for IDA Plugin Manager.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from src.config.constants import LOG_DIR, LOG_BACKUP_COUNT, LOG_FORMAT, LOG_MAX_BYTES


def setup_logging(
    log_dir: Path = LOG_DIR,
    log_level: str = "INFO",
    log_to_file: bool = True,
    log_to_console: bool = True,
) -> None:
    """
    Set up logging configuration.

    Args:
        log_dir: Directory to store log files
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Whether to log to file
        log_to_console: Whether to log to console
    """
    # Create log directory
    log_dir.mkdir(parents=True, exist_ok=True)

    # Convert log level string to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove existing handlers
    root_logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(LOG_FORMAT)

    # File handler
    if log_to_file:
        log_file = log_dir / "ida-plugin-manager.log"
        file_handler = RotatingFileHandler(
            log_file, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT, encoding="utf-8"
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Console handler
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance.

    Args:
        name: Logger name (typically __name__ of the module)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class PluginManagerFormatter(logging.Formatter):
    """
    Custom formatter for IDA Plugin Manager.
    Adds color coding for different log levels when outputting to console.
    """

    # ANSI color codes
    COLORS = {
        logging.DEBUG: "\033[36m",  # Cyan
        logging.INFO: "\033[32m",  # Green
        logging.WARNING: "\033[33m",  # Yellow
        logging.ERROR: "\033[31m",  # Red
        logging.CRITICAL: "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def __init__(self, fmt: str = None, use_colors: bool = True):
        """
        Initialize formatter.

        Args:
            fmt: Log format string
            use_colors: Whether to use colors in output
        """
        super().__init__(fmt)
        self.use_colors = use_colors

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with optional colors."""
        if self.use_colors and record.levelno in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelno]}{record.levelname}{self.RESET}"
        return super().format(record)
