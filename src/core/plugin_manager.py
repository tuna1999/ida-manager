"""
Core plugin management orchestration.

Coordinates plugin scanning, installation, updates, and database operations.
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
from src.models.plugin import InstallationResult, Plugin, PluginType, UpdateInfo
from src.utils.logger import get_logger

logger = get_logger(__name__)


class PluginManager:
    """
    Central plugin management orchestrator.

    Coordinates all plugin operations:
    - Scanning local plugins
    - Managing installation/uninstallation
    - Checking for updates
    - Database synchronization
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
        db_plugins = self.db.get_installed_plugins()
        return [self._db_to_model(p) for p in db_plugins]

    def get_all_plugins(self) -> List[Plugin]:
        """
        Get all plugins from database.

        Returns:
            List of all plugins
        """
        db_plugins = self.db.get_all_plugins()
        return [self._db_to_model(p) for p in db_plugins]

    def install_plugin(
        self,
        repo_url: str,
        method: str = "clone",
        branch: str = "main",
        version: Optional[str] = None,
    ) -> InstallationResult:
        """
        Install a plugin from GitHub.

        Args:
            repo_url: GitHub repository URL
            method: Installation method ('clone' or 'release')
            branch: Branch to clone (for clone method)
            version: Version to install (for release method)

        Returns:
            InstallationResult
        """
        from src.utils.validators import parse_github_url

        parsed = parse_github_url(repo_url)
        if not parsed:
            return InstallationResult(
                success=False,
                plugin_id="",
                message="Invalid GitHub URL",
                error="Could not parse repository URL",
            )

        owner, repo_name = parsed
        plugin_id = f"{owner}/{repo_name}"

        logger.info(f"Installing plugin: {plugin_id} (method: {method})")

        # Find IDA installation
        ida_path = self.ida_detector.find_ida_installation()
        if not ida_path:
            return InstallationResult(
                success=False,
                plugin_id=plugin_id,
                message="IDA Pro installation not found",
                error="Could not detect IDA Pro installation",
            )

        # Get plugin directory
        plugin_dir = self.ida_detector.get_plugin_directory(ida_path)
        install_path = plugin_dir / repo_name

        # Check if already installed
        existing = self.db.get_plugin(plugin_id)
        if existing:
            return InstallationResult(
                success=False,
                plugin_id=plugin_id,
                message="Plugin already installed",
                error=f"Plugin {plugin_id} is already installed",
                previous_version=existing.installed_version,
            )

        # Install using specified method
        result: InstallationResult

        if method == "clone":
            result = self.installer.install_from_github_clone(repo_url, install_path, branch)

        elif method == "release":
            # Fetch releases
            releases = self.github_client.get_releases(owner, repo_name)

            if not releases:
                return InstallationResult(
                    success=False,
                    plugin_id=plugin_id,
                    message="No releases found",
                    error="Repository has no releases",
                )

            # Find target release
            target_release = None
            if version:
                for r in releases:
                    if version in r.tag_name:
                        target_release = r
                        break
            else:
                # Get latest stable
                target_release = next(
                    (r for r in releases if not r.prerelease),
                    releases[0]
                )

            if not target_release:
                return InstallationResult(
                    success=False,
                    plugin_id=plugin_id,
                    message="Release not found",
                    error=f"Version {version} not found",
                )

            result = self.installer.install_from_github_release(repo_url, target_release, install_path)

        else:
            return InstallationResult(
                success=False,
                plugin_id=plugin_id,
                message="Invalid installation method",
                error=f"Unknown method: {method}",
            )

        # Update database if successful
        if result.success:
            self._add_plugin_to_database(
                plugin_id=plugin_id,
                name=repo_name,
                repository_url=repo_url,
                install_path=str(install_path),
                version=result.new_version,
                plugin_type=result.data.get("plugin_type") if isinstance(result.data, dict) else None,
            )

        return result

    def uninstall_plugin(self, plugin_id: str, backup: bool = True) -> InstallationResult:
        """
        Uninstall a plugin.

        Args:
            plugin_id: Plugin identifier
            backup: Whether to create backup

        Returns:
            InstallationResult
        """
        logger.info(f"Uninstalling plugin: {plugin_id}")

        db_plugin = self.db.get_plugin(plugin_id)
        if not db_plugin:
            return InstallationResult(
                success=False,
                plugin_id=plugin_id,
                message="Plugin not found",
                error="Plugin is not installed",
            )

        plugin = self._db_to_model(db_plugin)
        result = self.installer.uninstall_plugin(plugin, backup)

        if result.success:
            # Update database
            self.db.log_installation(
                plugin_id=plugin_id,
                action="uninstall",
                version=plugin.installed_version,
                success=True,
            )

            # Remove from database or mark as uninstalled
            self.db.delete_plugin(plugin_id)

        return result

    def update_plugin(self, plugin_id: str) -> InstallationResult:
        """
        Update a plugin to latest version.

        Args:
            plugin_id: Plugin identifier

        Returns:
            InstallationResult
        """
        logger.info(f"Updating plugin: {plugin_id}")

        db_plugin = self.db.get_plugin(plugin_id)
        if not db_plugin:
            return InstallationResult(
                success=False,
                plugin_id=plugin_id,
                message="Plugin not installed",
            )

        plugin = self._db_to_model(db_plugin)

        # Check for updates
        update_info = self.check_updates(plugin_id)
        if not update_info or not update_info.has_update:
            return InstallationResult(
                success=True,
                plugin_id=plugin_id,
                message="Plugin is already up to date",
            )

        # Uninstall current version
        self.uninstall_plugin(plugin_id, backup=True)

        # Install new version
        from src.utils.validators import parse_github_url

        repo_url = plugin.repository_url
        parsed = parse_github_url(repo_url) if repo_url else None

        if not parsed:
            return InstallationResult(
                success=False,
                plugin_id=plugin_id,
                message="Invalid repository URL",
            )

        owner, repo_name = parsed

        # Get target release
        releases = self.github_client.get_releases(owner, repo_name)
        target_release = None

        for r in releases:
            if update_info.latest_version in r.tag_name:
                target_release = r
                break

        if not target_release:
            return InstallationResult(
                success=False,
                plugin_id=plugin_id,
                message="Update version not found",
            )

        # Install new version
        ida_path = self.ida_detector.find_ida_installation()
        if not ida_path:
            return InstallationResult(
                success=False,
                plugin_id=plugin_id,
                message="IDA Pro not found",
            )

        plugin_dir = self.ida_detector.get_plugin_directory(ida_path)
        install_path = plugin_dir / repo_name

        result = self.installer.install_from_github_release(repo_url, target_release, install_path)

        if result.success:
            # Log update
            self.db.log_installation(
                plugin_id=plugin_id,
                action="update",
                version=result.new_version,
                success=True,
            )

        return result

    def check_updates(self, plugin_id: str) -> Optional[UpdateInfo]:
        """
        Check for plugin updates.

        Args:
            plugin_id: Plugin identifier

        Returns:
            UpdateInfo or None
        """
        db_plugin = self.db.get_plugin(plugin_id)
        if not db_plugin or not db_plugin.repository_url:
            return None

        from src.utils.validators import parse_github_url

        parsed = parse_github_url(db_plugin.repository_url)
        if not parsed:
            return None

        owner, repo_name = parsed

        # Fetch latest release
        latest_release = self.github_client.get_latest_release(owner, repo_name)

        if not latest_release:
            return None

        # Extract version
        from src.github.release_fetcher import ReleaseFetcher

        fetcher = ReleaseFetcher()
        latest_version = fetcher.extract_version(latest_release.tag_name)

        # Compare versions
        has_update = False
        if db_plugin.installed_version:
            has_update = self.version_manager.is_version_newer(db_plugin.installed_version, latest_version)

        return UpdateInfo(
            has_update=has_update,
            current_version=db_plugin.installed_version,
            latest_version=latest_version,
            changelog=fetcher.get_changelog(latest_release),
            release_url=latest_release.html_url,
        )

    def check_all_updates(self) -> List[UpdateInfo]:
        """
        Check for updates for all installed plugins.

        Returns:
            List of UpdateInfo objects
        """
        updates = []

        for plugin in self.get_installed_plugins():
            if plugin.repository_url:
                info = self.check_updates(plugin.id)
                if info and info.has_update:
                    updates.append(info)

        return updates

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

    def _add_plugin_to_database(
        self,
        plugin_id: str,
        name: str,
        repository_url: str,
        install_path: str,
        version: Optional[str],
        plugin_type: Optional[PluginType] = None,
    ) -> None:
        """Add plugin to database."""
        from datetime import datetime

        db_plugin = DBPlugin(
            id=plugin_id,
            name=name,
            repository_url=repository_url,
            install_path=install_path,
            installed_version=version,
            plugin_type=plugin_type or PluginType.LEGACY,
            install_date=datetime.utcnow(),
            is_active=True,
        )

        self.db.add_plugin(db_plugin)
        self.db.log_installation(
            plugin_id=plugin_id,
            action="install",
            version=version,
            success=True,
        )

    def _db_to_model(self, db_plugin: DBPlugin) -> Plugin:
        """Convert database model to Pydantic model."""
        return Plugin(
            id=db_plugin.id,
            name=db_plugin.name,
            description=db_plugin.description,
            author=db_plugin.author,
            repository_url=db_plugin.repository_url,
            installed_version=db_plugin.installed_version,
            latest_version=db_plugin.latest_version,
            install_date=db_plugin.install_date,
            last_updated=db_plugin.last_updated,
            plugin_type=db_plugin.plugin_type,
            ida_version_min=db_plugin.ida_version_min,
            ida_version_max=db_plugin.ida_version_max,
            is_active=db_plugin.is_active,
            install_path=db_plugin.install_path,
            metadata={},
        )
