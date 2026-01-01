"""
Configuration management for IDA Plugin Manager.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.config.constants import (
    CONFIG_DIR,
    CONFIG_FILE,
    GITHUB_API_BASE,
    DEFAULT_AUTO_CHECK_UPDATES,
    DEFAULT_CHECK_INTERVAL_HOURS,
    DEFAULT_LOG_LEVEL,
    INSTALL_BACKUP_ENABLED,
    INSTALL_CONCURRENT_DOWNLOADS,
    UI_THEME_DARK,
    UI_WINDOW_HEIGHT,
    UI_WINDOW_WIDTH,
)


@dataclass
class IDAConfig:
    """IDA Pro configuration."""

    install_path: str = ""
    version: str = ""
    plugin_dir: str = ""
    auto_detect: bool = True


@dataclass
class GitHubConfig:
    """GitHub API configuration."""

    token: str = ""
    api_base: str = GITHUB_API_BASE
    rate_limit: Dict[str, int] = field(default_factory=lambda: {"remaining": 60, "reset": 0})


@dataclass
class UpdatesConfig:
    """Update settings configuration."""

    auto_check: bool = DEFAULT_AUTO_CHECK_UPDATES
    check_interval_hours: int = DEFAULT_CHECK_INTERVAL_HOURS
    include_pre_release: bool = False
    notify_only: bool = False


@dataclass
class UIConfig:
    """UI configuration."""

    theme: str = UI_THEME_DARK
    window_width: int = UI_WINDOW_WIDTH
    window_height: int = UI_WINDOW_HEIGHT
    column_widths: Dict[str, int] = field(
        default_factory=lambda: {"name": 200, "version": 80, "author": 120, "description": 300}
    )


@dataclass
class AdvancedConfig:
    """Advanced settings configuration."""

    log_level: str = DEFAULT_LOG_LEVEL
    backup_on_uninstall: bool = INSTALL_BACKUP_ENABLED
    keep_install_history: bool = True
    max_history_entries: int = 1000
    concurrent_downloads: int = INSTALL_CONCURRENT_DOWNLOADS


@dataclass
class AppConfig:
    """Main application configuration."""

    version: str = "0.1.0"
    ida: IDAConfig = field(default_factory=IDAConfig)
    github: GitHubConfig = field(default_factory=GitHubConfig)
    plugin_sources: List[str] = field(default_factory=list)
    updates: UpdatesConfig = field(default_factory=UpdatesConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    advanced: AdvancedConfig = field(default_factory=AdvancedConfig)


class SettingsManager:
    """
    Manage application configuration.

    Handles loading, saving, and accessing configuration settings.
    Configuration is stored in JSON format in the user's AppData directory.
    """

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize settings manager.

        Args:
            config_path: Path to configuration file. Defaults to CONFIG_FILE.
        """
        self.config_path = config_path or CONFIG_FILE
        self.config = AppConfig()
        self._ensure_config_dir()
        self.load()

    def _ensure_config_dir(self) -> None:
        """Ensure configuration directory exists."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> bool:
        """
        Load configuration from file.

        Returns:
            True if successful, False otherwise.
        """
        if not self.config_path.exists():
            self.save()  # Create default config
            return True

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Parse into config object
            self.config = AppConfig(
                version=data.get("version", "0.1.0"),
                ida=IDAConfig(**data.get("ida", {})),
                github=GitHubConfig(**data.get("github", {})),
                plugin_sources=data.get("plugin_sources", []),
                updates=UpdatesConfig(**data.get("updates", {})),
                ui=UIConfig(**data.get("ui", {})),
                advanced=AdvancedConfig(**data.get("advanced", {})),
            )
            return True

        except (json.JSONDecodeError, TypeError) as e:
            print(f"Failed to load config: {e}")
            return False

    def save(self) -> bool:
        """
        Save configuration to file.

        Returns:
            True if successful, False otherwise.
        """
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self._to_dict(), f, indent=2)
            return True
        except (IOError, TypeError) as e:
            print(f"Failed to save config: {e}")
            return False

    def _to_dict(self) -> Dict[str, Any]:
        """Convert config object to dictionary."""
        return {
            "version": self.config.version,
            "ida": {
                "install_path": self.config.ida.install_path,
                "version": self.config.ida.version,
                "plugin_dir": self.config.ida.plugin_dir,
                "auto_detect": self.config.ida.auto_detect,
            },
            "github": {
                "token": self.config.github.token,
                "api_base": self.config.github.api_base,
                "rate_limit": self.config.github.rate_limit,
            },
            "plugin_sources": self.config.plugin_sources,
            "updates": {
                "auto_check": self.config.updates.auto_check,
                "check_interval_hours": self.config.updates.check_interval_hours,
                "include_pre_release": self.config.updates.include_pre_release,
                "notify_only": self.config.updates.notify_only,
            },
            "ui": {
                "theme": self.config.ui.theme,
                "window_width": self.config.ui.window_width,
                "window_height": self.config.ui.window_height,
                "column_widths": self.config.ui.column_widths,
            },
            "advanced": {
                "log_level": self.config.advanced.log_level,
                "backup_on_uninstall": self.config.advanced.backup_on_uninstall,
                "keep_install_history": self.config.advanced.keep_install_history,
                "max_history_entries": self.config.advanced.max_history_entries,
                "concurrent_downloads": self.config.advanced.concurrent_downloads,
            },
        }

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by dot-notation key.

        Args:
            key: Configuration key in dot notation (e.g., "ida.install_path")
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        keys = key.split(".")
        value = self.config

        for k in keys:
            if hasattr(value, k):
                value = getattr(value, k)
            else:
                return default

        return value

    def set(self, key: str, value: Any) -> bool:
        """
        Set configuration value by dot-notation key.

        Args:
            key: Configuration key in dot notation
            value: Value to set

        Returns:
            True if successful, False otherwise
        """
        keys = key.split(".")
        obj = self.config

        for k in keys[:-1]:
            if hasattr(obj, k):
                obj = getattr(obj, k)
            else:
                return False

        setattr(obj, keys[-1], value)
        return self.save()

    def reset_to_defaults(self) -> None:
        """Reset configuration to defaults."""
        self.config = AppConfig()
        self.save()

    def export_config(self, destination: Path) -> bool:
        """
        Export configuration to file.

        Args:
            destination: Path to export configuration to

        Returns:
            True if successful, False otherwise
        """
        try:
            with open(destination, "w", encoding="utf-8") as f:
                json.dump(self._to_dict(), f, indent=2)
            return True
        except (IOError, TypeError) as e:
            print(f"Failed to export config: {e}")
            return False

    def import_config(self, source: Path) -> bool:
        """
        Import configuration from file.

        Args:
            source: Path to import configuration from

        Returns:
            True if successful, False otherwise
        """
        try:
            with open(source, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.config = AppConfig(
                version=data.get("version", "0.1.0"),
                ida=IDAConfig(**data.get("ida", {})),
                github=GitHubConfig(**data.get("github", {})),
                plugin_sources=data.get("plugin_sources", []),
                updates=UpdatesConfig(**data.get("updates", {})),
                ui=UIConfig(**data.get("ui", {})),
                advanced=AdvancedConfig(**data.get("advanced", {})),
            )
            return self.save()
        except (json.JSONDecodeError, TypeError, IOError) as e:
            print(f"Failed to import config: {e}")
            return False
