"""
Application constants and default paths.
"""

import os
from pathlib import Path

# Application Info
APP_NAME = "IDA Plugin Manager"
APP_VERSION = "0.1.0"
APP_AUTHOR = "IDA Plugin Manager Team"

# Directory Paths
CONFIG_DIR = Path(os.environ.get("APPDATA", "")) / "IDA-Plugin-Manager"
CONFIG_FILE = CONFIG_DIR / "config.json"
LOG_DIR = CONFIG_DIR / "logs"
DATABASE_FILE = CONFIG_DIR / "plugins.db"

# IDA Pro Default Paths
IDA_DEFAULT_PATHS = [
    Path("C:/Program Files/IDA Pro 9.0"),
    Path("C:/Program Files/IDA Pro 8.4"),
    Path("C:/Program Files/IDA Pro 8.3"),
    Path("C:/Program Files (x86)/IDA Pro 9.0"),
    Path("C:/Program Files (x86)/IDA Pro 8.4"),
    Path(os.path.expandvars("%LOCALAPPDATA%/Programs/IDA Pro 9.0")),
    Path(os.path.expanduser("~/IDA Pro 9.0")),
]

# Windows Registry Keys for IDA Pro
IDA_REGISTRY_KEYS = [
    (r"SOFTWARE\Hex-Rays\IDA", "InstallDir"),
    (r"SOFTWARE\Wow6432Node\Hex-Rays\IDA", "InstallDir"),
]

# GitHub API
GITHUB_API_BASE = "https://api.github.com"
GITHUB_DEFAULT_TOPICS = ["ida-pro-plugin", "idapro", "ida-plugin"]
GITHUB_SEARCH_QUERY = "topic:ida-pro-plugin language:python"

# Plugin Types
PLUGIN_TYPE_LEGACY = "legacy"
PLUGIN_TYPE_MODERN = "modern"

# Compatibility
IDA_VERSION_MIN = "7.0"
IDA_VERSION_MAX = "9.9"

# UI Constants
UI_WINDOW_WIDTH = 1200
UI_WINDOW_HEIGHT = 800
UI_THEME_DARK = "Dark"
UI_THEME_LIGHT = "Light"

# Update Settings
DEFAULT_CHECK_INTERVAL_HOURS = 24
DEFAULT_AUTO_CHECK_UPDATES = True

# Installation
INSTALL_BACKUP_ENABLED = True
INSTALL_CONCURRENT_DOWNLOADS = 3

# Logging
DEFAULT_LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
LOG_BACKUP_COUNT = 5

# Cache
GITHUB_CACHE_TTL_SECONDS = 24 * 60 * 60  # 24 hours
