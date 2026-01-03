"""
Plugin Service Layer.

Business logic layer between UI and Core components.
Separates business operations from data access and presentation.

Responsibilities:
- Plugin installation orchestration
- Update checking
- Compatibility validation
- Plugin discovery and search
"""

from logging import getLogger
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timezone

from src.core.ida_detector import IDADetector
from src.core.installer import PluginInstaller
from src.core.version_manager import VersionManager
from src.database.db_manager import DatabaseManager
from src.database.models import Plugin as DBPlugin
from src.github.client import GitHubClient
from src.github.repo_parser import RepoParser
from src.github.release_fetcher import ReleaseFetcher
from src.models.plugin import (
    InstallationMethod,
    InstallationResult,
    Plugin,
    PluginMetadata,
    PluginStatus,
    PluginType,
    ValidationResult,
    UpdateInfo,
)
from src.models.github_info import GitHubRepo, GitHubRelease
from src.repositories.plugin_repository import PluginRepository
from src.services.plugin_tagger import PluginTagger
from src.utils.version_utils import IDAVersion, is_version_compatible
from src.utils.validators import parse_github_url

logger = getLogger(__name__)


class PluginService:
    """
    Service layer for plugin operations.

    Provides high-level business logic for plugin management,
    abstracting away the complexity of core components.
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        github_client: Optional[GitHubClient] = None,
        ida_detector: Optional[IDADetector] = None,
        installer: Optional[PluginInstaller] = None,
        version_manager: Optional[VersionManager] = None,
        repository: Optional[PluginRepository] = None,
    ):
        """
        Initialize plugin service.

        Args:
            db_manager: Database manager for data persistence
            github_client: GitHub API client (optional, will create if None)
            ida_detector: IDA installation detector (optional, will create if None)
            installer: Plugin installer (optional, will create if None)
            version_manager: Version manager (optional, will create if None)
            repository: Plugin repository (optional, will create if None)
        """
        self.db = db_manager
        self.repository = repository or PluginRepository(db_manager)

        # Create or inject dependencies
        self.github_client = github_client or GitHubClient()
        self.ida_detector = ida_detector or IDADetector()
        self.version_manager = version_manager or VersionManager()

        # Installer depends on github_client and version_manager
        self.installer = installer or PluginInstaller(
            self.github_client,
            self.version_manager,
        )

        # Tagger for automatic tag extraction
        self.tagger = PluginTagger(self.github_client)

    # ============ Plugin Discovery ============

    def validate_plugin_from_url(self, url: str) -> ValidationResult:
        """
        Validate a plugin from GitHub URL.

        Args:
            url: GitHub repository URL

        Returns:
            ValidationResult with plugin metadata
        """
        from src.utils.validators import parse_github_url

        logger.info(f"Validating plugin from URL: {url}")

        # Parse URL
        parsed = parse_github_url(url)
        if not parsed:
            return ValidationResult(
                valid=False,
                error="Invalid GitHub URL format",
            )

        owner, repo = parsed

        # Fetch repository contents
        contents = self.github_client.get_repository_contents(owner, repo)
        if not contents:
            return ValidationResult(
                valid=False,
                error="Could not access repository. It may not exist or is private.",
            )

        # Fetch README
        readme = self.github_client.get_readme(owner, repo)

        # Check for ida-plugin.json
        plugins_json = None
        plugins_json_item = next(
            (item for item in contents if item.name == "ida-plugin.json"),
            None
        )
        if plugins_json_item and plugins_json_item.download_url:
            import requests
            try:
                response = requests.get(plugins_json_item.download_url, timeout=10)
                if response.status_code == 200:
                    import json
                    plugins_json = json.loads(response.text)
                    logger.info("ida-plugin.json parsed successfully")
            except Exception as e:
                logger.warning(f"Failed to fetch ida-plugin.json: {e}")

        # Parse plugin metadata
        parser = RepoParser()
        result = parser.parse_repository(repo, contents, readme, plugins_json)

        logger.info(f"Validation result: valid={result.valid}, type={result.plugin_type}")
        return result

    # ============ Plugin Installation ============

    def install_plugin(
        self,
        url: str,
        method: str = "clone",
        branch: str = "main",
        plugin_type: Optional[PluginType] = None,
        metadata: Optional[PluginMetadata] = None,
    ) -> InstallationResult:
        """
        Install a plugin from GitHub.

        Args:
            url: GitHub repository URL
            method: Installation method ('clone' or 'release')
            branch: Branch to clone (for clone method)
            plugin_type: Detected plugin type (optional)
            metadata: Parsed plugin metadata (optional)

        Returns:
            InstallationResult
        """
        logger.info(f"Installing plugin: {url} (method: {method})")

        # Parse URL
        parsed = parse_github_url(url)
        if not parsed:
            return InstallationResult(
                success=False,
                plugin_id="",
                message="Invalid GitHub URL",
                error="Could not parse repository URL",
            )

        owner, repo_name = parsed
        plugin_id = f"{owner}/{repo_name}"

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
        existing = self.repository.find_by_id(plugin_id)
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
            result = self.installer.install_from_github_clone(
                url, install_path, branch, plugin_type, metadata
            )

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

            # Get latest stable
            target_release = next(
                (r for r in releases if not r.prerelease),
                releases[0]
            )

            result = self.installer.install_from_github_release(
                url, target_release, install_path, plugin_type, metadata
            )

        else:
            return InstallationResult(
                success=False,
                plugin_id=plugin_id,
                message="Invalid installation method",
                error=f"Unknown method: {method}",
            )

        # Update database if successful
        if result.success:
            # Determine installation method
            install_method = InstallationMethod.CLONE if method == "clone" else InstallationMethod.RELEASE

            self._add_plugin_to_database(
                plugin_id=plugin_id,
                name=repo_name,
                repository_url=url,
                install_path=str(install_path),
                version=result.new_version,
                plugin_type=result.plugin_type,
                installation_method=install_method.value,
                status=PluginStatus.INSTALLED.value,
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

        plugin = self.repository.find_by_id(plugin_id)
        if not plugin:
            return InstallationResult(
                success=False,
                plugin_id=plugin_id,
                message="Plugin not found",
                error="Plugin is not installed",
            )

        result = self.installer.uninstall_plugin(plugin, backup)

        if result.success:
            # Update database - set status back to not_installed
            self.db.log_installation(
                plugin_id=plugin_id,
                action="uninstall",
                version=plugin.installed_version,
                success=True,
            )

            # Update plugin status to not_installed
            self.repository.update_status(plugin_id, PluginStatus.NOT_INSTALLED)

        return result

    def add_plugin_to_catalog(
        self,
        url: str,
        metadata: Optional[PluginMetadata] = None,
    ) -> bool:
        """
        Add plugin to catalog without installing.

        This saves the plugin information to the database with
        status='not_installed' so it can be installed later.

        Args:
            url: GitHub repository URL
            metadata: Parsed plugin metadata (optional)

        Returns:
            True if added successfully
        """
        logger.info(f"Adding plugin to catalog: {url}")

        # Parse URL
        parsed = parse_github_url(url)
        if not parsed:
            logger.error(f"Failed to parse GitHub URL: {url}")
            return False

        owner, repo_name = parsed
        plugin_id = f"{owner}/{repo_name}"

        # Check if already exists
        existing = self.repository.find_by_id(plugin_id)
        if existing:
            logger.warning(f"Plugin already exists in catalog: {plugin_id}")
            return False

        # Fetch repository info
        repo_info = self.github_client.get_repository_info(owner, repo_name)

        # Get description from metadata or repo info
        description = None
        if metadata:
            description = metadata.description
        if not description and repo_info:
            description = ", ".join(repo_info.topics) if repo_info.topics else None

        # Extract tags using PluginTagger
        tags = self.tagger.update_plugin_tags(
            owner=owner,
            repo=repo_name,
            description=description,
        )

        # Get last update time from GitHub
        last_updated = None
        if repo_info:
            last_updated = repo_info.last_fetched

        # Add to database with status = not_installed
        db_plugin = DBPlugin(
            id=plugin_id,
            name=repo_name,
            repository_url=url,
            install_path=None,  # No install path yet
            installed_version=None,
            plugin_type=metadata.plugin_type if metadata else PluginType.LEGACY,
            status=PluginStatus.NOT_INSTALLED.value,
            installation_method=None,  # Not installed yet
            added_at=datetime.now(timezone.utc),
            last_updated_at=last_updated,
            tags=tags if tags else None,
            is_active=True,
        )

        self.db.add_plugin(db_plugin)
        logger.info(f"Successfully added {plugin_id} to catalog")
        return True

    def update_plugin(self, plugin_id: str) -> InstallationResult:
        """
        Update a plugin to latest version.

        Args:
            plugin_id: Plugin identifier

        Returns:
            InstallationResult
        """
        logger.info(f"Updating plugin: {plugin_id}")

        plugin = self.repository.find_by_id(plugin_id)
        if not plugin:
            return InstallationResult(
                success=False,
                plugin_id=plugin_id,
                message="Plugin not installed",
            )

        # Check for updates
        update_info = self.check_plugin_update(plugin_id)
        if not update_info or not update_info.has_update:
            return InstallationResult(
                success=True,
                plugin_id=plugin_id,
                message="Plugin is already up to date",
            )

        # Uninstall current version
        self.uninstall_plugin(plugin_id, backup=True)

        # Install new version
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

    # ============ Plugin Queries ============

    def get_all_plugins(self) -> List[Plugin]:
        """Get all plugins from database."""
        return self.repository.find_all()

    def get_installed_plugins(self) -> List[Plugin]:
        """Get all installed plugins."""
        return self.repository.find_installed()

    def get_plugin(self, plugin_id: str) -> Optional[Plugin]:
        """Get a plugin by ID."""
        return self.repository.find_by_id(plugin_id)

    # ============ Update Checking ============

    def check_updates(self) -> List[UpdateInfo]:
        """
        Check for updates to all installed plugins.

        Returns:
            List of UpdateInfo objects for plugins with updates available
        """
        logger.info("Checking for plugin updates")
        updates = []

        for plugin in self.get_installed_plugins():
            if plugin.repository_url:
                info = self.check_plugin_update(plugin.id)
                if info and info.has_update:
                    updates.append(info)

        return updates

    def check_plugin_update(self, plugin_id: str) -> Optional[UpdateInfo]:
        """
        Check if a specific plugin has an update available.

        Args:
            plugin_id: Plugin identifier

        Returns:
            UpdateInfo if update available, None otherwise
        """
        logger.info(f"Checking update for plugin: {plugin_id}")

        plugin = self.repository.find_by_id(plugin_id)
        if not plugin or not plugin.repository_url:
            return None

        parsed = parse_github_url(plugin.repository_url)
        if not parsed:
            return None

        owner, repo_name = parsed

        # Fetch latest release
        latest_release = self.github_client.get_latest_release(owner, repo_name)

        if not latest_release:
            return None

        # Extract version
        fetcher = ReleaseFetcher()
        latest_version = fetcher.extract_version(latest_release.tag_name)

        # Compare versions
        has_update = False
        if plugin.installed_version:
            has_update = self.version_manager.is_version_newer(
                plugin.installed_version,
                latest_version
            )

        return UpdateInfo(
            has_update=has_update,
            current_version=plugin.installed_version,
            latest_version=latest_version,
            changelog=fetcher.get_changelog(latest_release),
            release_url=latest_release.html_url,
        )

    # ============ Compatibility ============

    def get_compatible_plugins(self, ida_version: str) -> List[Plugin]:
        """
        Get plugins compatible with given IDA version.

        Uses proper version comparison (IDAVersion utility).

        Args:
            ida_version: IDA Pro version string

        Returns:
            List of compatible plugins
        """
        logger.info(f"Fetching plugins compatible with IDA {ida_version}")

        return self.repository.find_compatible(ida_version)

    def is_plugin_compatible(
        self,
        plugin_id: str,
        ida_version: str,
    ) -> bool:
        """
        Check if a plugin is compatible with IDA version.

        Args:
            plugin_id: Plugin identifier
            ida_version: IDA Pro version string

        Returns:
            True if compatible, False otherwise
        """
        return self.repository.is_compatible(plugin_id, ida_version)

    # ============ Plugin Discovery ============

    def search_plugins(self, query: str) -> List[Plugin]:
        """
        Search plugins by name or description.

        Args:
            query: Search query

        Returns:
            List of matching plugins
        """
        return self.repository.search(query)

    def discover_github_plugins(self, search_query: str = "ida pro") -> List[GitHubRepo]:
        """
        Discover IDA plugins on GitHub.

        Args:
            search_query: Search query for GitHub

        Returns:
            List of GitHub repositories
        """
        logger.info(f"Discovering plugins on GitHub: {search_query}")

        repos = self.github_client.search_repositories(
            query=search_query,
            sort="stars",
            order="desc",
            per_page=100,
        )

        logger.info(f"Found {len(repos)} repositories")
        return repos

    # ============ Private Methods ============

    def _add_plugin_to_database(
        self,
        plugin_id: str,
        name: str,
        repository_url: str,
        install_path: str,
        version: Optional[str],
        plugin_type: Optional[PluginType] = None,
        installation_method: Optional[str] = None,
        status: Optional[str] = None,
        tags: Optional[List[str]] = None,
        last_updated_at: Optional[datetime] = None,
    ) -> None:
        """Add plugin to database."""
        db_plugin = DBPlugin(
            id=plugin_id,
            name=name,
            repository_url=repository_url,
            install_path=install_path,
            installed_version=version,
            plugin_type=plugin_type or PluginType.LEGACY,
            install_date=datetime.now(timezone.utc),
            installation_method=installation_method,
            status=status or PluginStatus.INSTALLED.value,
            tags=tags,
            last_updated_at=last_updated_at,
            is_active=True,
        )

        self.db.add_plugin(db_plugin)
        self.db.log_installation(
            plugin_id=plugin_id,
            action="install",
            version=version,
            success=True,
        )

    # ============ Lifecycle Management ============

    def close(self):
        """Close the service and cleanup resources."""
        logger.info("Closing PluginService")

        try:
            self.github_client.close()
        except Exception as e:
            logger.error(f"Failed to close GitHub client: {e}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
