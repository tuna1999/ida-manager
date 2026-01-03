"""
Core plugin management orchestration.

DEPRECATED: This class now delegates to PluginService.
Maintained for backwards compatibility.

New code should use PluginService directly.
"""

from pathlib import Path
from typing import List, Optional

from src.core.ida_detector import IDADetector
from src.core.installer import PluginInstaller
from src.core.version_manager import VersionManager
from src.database.db_manager import DatabaseManager
from src.database.models import Plugin as DBPlugin
from src.github.client import GitHubClient
from src.models.github_info import GitHubRepo, GitHubRelease
from src.models.plugin import (
    InstallationResult,
    Plugin,
    PluginMetadata,
    PluginType,
    UpdateInfo,
)
from src.services.plugin_service import PluginService
from src.utils.logger import get_logger

logger = get_logger(__name__)


class PluginManager:
    """
    Central plugin management orchestrator.

    DEPRECATED: This class now delegates to PluginService.
    All operations are forwarded to the service layer.

    For new code, use PluginService directly instead.
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        ida_detector: Optional[IDADetector] = None,
        installer: Optional[PluginInstaller] = None,
        github_client: Optional[GitHubClient] = None,
        version_manager: Optional[VersionManager] = None,
    ):
        """
        Initialize plugin manager.

        Args:
            db_manager: Database manager instance
            ida_detector: IDA detector instance (optional)
            installer: Plugin installer instance (optional)
            github_client: GitHub client instance (optional)
            version_manager: Version manager instance (optional)
        """
        self.db = db_manager
        self.ida_detector = ida_detector or IDADetector()
        self.github_client = github_client or GitHubClient()
        self.version_manager = version_manager or VersionManager()
        self.installer = installer or PluginInstaller(self.github_client, self.version_manager)

        # Create service layer for delegation
        self._service = PluginService(
            db_manager=db_manager,
            github_client=self.github_client,
            ida_detector=self.ida_detector,
            installer=self.installer,
            version_manager=self.version_manager,
        )

        logger.warning(
            "PluginManager is deprecated and now delegates to PluginService. "
            "Use PluginService directly in new code."
        )

    def scan_local_plugins(self) -> List[Plugin]:
        """
        Scan IDA Pro plugin directory for installed plugins.

        Returns:
            List of installed plugins
        """
        logger.info("Scanning for local plugins")

        # Find IDA installation
        ida_path = self.ida_detector.find_ida_installation()
        if not ida_path:
            logger.warning("No IDA installation found for plugin scan")
            return []

        # Get plugin directory
        plugin_dir = self.ida_detector.get_plugin_directory(ida_path)
        if not plugin_dir.exists():
            logger.info(f"Plugin directory does not exist: {plugin_dir}")
            return []

        plugins = []

        # Scan for plugins
        for item in plugin_dir.iterdir():
            if item.is_dir():
                # Modern plugin or directory-based legacy plugin
                validation = self.installer.validate_plugin_structure(item)
                if validation.valid:
                    plugin = self._create_plugin_from_path(item, validation.plugin_type)
                    if plugin:
                        plugins.append(plugin)

            elif item.is_file() and item.suffix == ".py":
                # Single-file legacy plugin
                plugin = self._create_legacy_plugin_from_file(item)
                if plugin:
                    plugins.append(plugin)

        logger.info(f"Found {len(plugins)} local plugins")
        return plugins

    def get_installed_plugins(self) -> List[Plugin]:
        """
        Get all plugins from database marked as installed.

        Returns:
            List of installed plugins
        """
        return self._service.get_installed_plugins()

    def get_all_plugins(self) -> List[Plugin]:
        """
        Get all plugins from database.

        Returns:
            List of all plugins
        """
        return self._service.get_all_plugins()

    def get_plugin(self, plugin_id: str) -> Optional[Plugin]:
        """
        Get a plugin by ID.

        Args:
            plugin_id: Plugin identifier

        Returns:
            Plugin or None
        """
        return self._service.get_plugin(plugin_id)

    def install_plugin(
        self,
        repo_url: str,
        method: str = "clone",
        branch: str = "main",
        version: Optional[str] = None,
        plugin_type: Optional[PluginType] = None,
        metadata: Optional[PluginMetadata] = None,
    ) -> InstallationResult:
        """
        Install a plugin from GitHub.

        Args:
            repo_url: GitHub repository URL
            method: Installation method ('clone' or 'release')
            branch: Branch to clone (for clone method)
            version: Version to install (for release method)
            plugin_type: Detected plugin type (optional)
            metadata: Parsed plugin metadata (optional)

        Returns:
            InstallationResult
        """
        return self._service.install_plugin(
            url=repo_url,
            method=method,
            branch=branch,
            plugin_type=plugin_type,
            metadata=metadata,
        )

    def uninstall_plugin(self, plugin_id: str, backup: bool = True) -> InstallationResult:
        """
        Uninstall a plugin.

        Args:
            plugin_id: Plugin identifier
            backup: Whether to create backup

        Returns:
            InstallationResult
        """
        return self._service.uninstall_plugin(plugin_id, backup)

    def update_plugin(self, plugin_id: str) -> InstallationResult:
        """
        Update a plugin to latest version.

        Args:
            plugin_id: Plugin identifier

        Returns:
            InstallationResult
        """
        return self._service.update_plugin(plugin_id)

    def check_updates(self, plugin_id: str) -> Optional[UpdateInfo]:
        """
        Check for plugin updates.

        Args:
            plugin_id: Plugin identifier

        Returns:
            UpdateInfo or None
        """
        return self._service.check_plugin_update(plugin_id)

    def check_all_updates(self) -> List[UpdateInfo]:
        """
        Check for updates for all installed plugins.

        Returns:
            List of UpdateInfo objects
        """
        return self._service.check_updates()

    # ============ Private Methods ============

    def _create_plugin_from_path(self, path: Path, plugin_type: PluginType) -> Optional[Plugin]:
        """Create Plugin object from directory path."""
        import json

        name = path.name
        version = None
        author = None
        description = None

        if plugin_type == PluginType.MODERN:
            plugins_json = path / "plugins.json"
            if plugins_json.exists():
                try:
                    data = json.loads(plugins_json.read_text())
                    name = data.get("name", name)
                    version = data.get("version")
                    author = data.get("author")
                    description = data.get("description")
                except (json.JSONDecodeError, IOError):
                    pass

        return Plugin(
            id=name,
            name=name,
            description=description,
            author=author,
            installed_version=version,
            plugin_type=plugin_type,
            install_path=str(path),
            is_active=True,
        )

    def _create_legacy_plugin_from_file(self, path: Path) -> Optional[Plugin]:
        """Create Plugin object from single .py file."""
        import re

        name = path.stem
        version = None
        author = None

        try:
            content = path.read_text(errors="ignore")

            # Extract version
            match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
            if match:
                version = match.group(1)

            # Extract author
            match = re.search(r'__author__\s*=\s*["\']([^"\']+)["\']', content)
            if match:
                author = match.group(1)

        except IOError:
            pass

        return Plugin(
            id=name,
            name=name,
            author=author,
            installed_version=version,
            plugin_type=PluginType.LEGACY,
            install_path=str(path),
            is_active=True,
        )
