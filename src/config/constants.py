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
# Uses glob patterns to match any version - future-proof for IDA 9.x, 10.x, etc.
IDA_DEFAULT_PATHS = [
    # Glob patterns for "IDA Pro" - matches: IDA Pro 9.0, IDA Pro 9.1, IDA Pro 10.0, etc.
    Path("C:/Program Files/IDA Pro*"),
    Path("C:/Program Files (x86)/IDA Pro*"),
    # Glob patterns for "IDA Professional" - matches: IDA Professional 9.0, 9.1, 9.3, 9.4, etc.
    Path("C:/Program Files/IDA Professional*"),
    Path("C:/Program Files (x86)/IDA Professional*"),
    # User/local installations (any version)
    Path(os.path.expanduser("~/IDA*")),
    Path(os.path.expandvars("%LOCALAPPDATA%/Programs/IDA*")),
    # Fallback: any directory starting with IDA in Program Files
    Path("C:/Program Files/IDA*"),
    Path("C:/Program Files (x86)/IDA*"),
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
# Support IDA Pro 7.x through future versions (10.x, 11.x, etc.)
IDA_VERSION_MIN = "7.0"
IDA_VERSION_MAX = "99.0"  # No upper limit to support all future versions

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
