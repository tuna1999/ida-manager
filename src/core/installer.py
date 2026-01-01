"""
Plugin installation and uninstallation logic.

Handles installing, updating, and uninstalling IDA Pro plugins
from various sources (GitHub clone, release download, local files).
"""

import json
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Optional

from src.core.version_manager import VersionManager
from src.github.client import GitHubClient
from src.github.repo_parser import RepoParser
from src.models.github_info import GitHubRepo, GitHubRelease
from src.models.plugin import InstallationResult, Plugin, PluginType, ValidationResult
from src.utils.file_ops import (
    backup_directory,
    cleanup_temp_directory,
    extract_archive,
    Result as FileResult,
    safe_copy_directory,
    safe_delete_directory,
)
from src.utils.logger import get_logger
from src.utils.validators import parse_github_url, validate_github_url

logger = get_logger(__name__)


class PluginInstaller:
    """
    Handle plugin installation and uninstallation.

    Supports:
    - Installation from GitHub clone
    - Installation from GitHub release download
    - Legacy plugin installation
    - Modern plugin installation (with plugins.json)
    - Plugin uninstallation with backup
    - Plugin updates
    """

    def __init__(
        self,
        github_client: Optional[GitHubClient] = None,
        version_manager: Optional[VersionManager] = None,
    ):
        """
        Initialize plugin installer.

        Args:
            github_client: GitHub API client (optional)
            version_manager: Version manager (optional)
        """
        self.github_client = github_client or GitHubClient()
        self.version_manager = version_manager or VersionManager()
        self.repo_parser = RepoParser()

    def install_from_github_clone(
        self,
        repo_url: str,
        destination: Path,
        branch: str = "main",
    ) -> InstallationResult:
        """
        Install plugin by cloning GitHub repository.

        Args:
            repo_url: GitHub repository URL
            destination: Installation destination path
            branch: Branch to clone (default: "main")

        Returns:
            InstallationResult with operation status
        """
        # Validate URL
        if not validate_github_url(repo_url):
            return InstallationResult(
                success=False,
                plugin_id="",
                message="Invalid GitHub URL",
                error="Invalid GitHub repository URL format",
            )

        # Parse URL
        parsed = parse_github_url(repo_url)
        if not parsed:
            return InstallationResult(
                success=False,
                plugin_id="",
                message="Failed to parse GitHub URL",
                error="Could not extract owner/repo from URL",
            )

        owner, repo_name = parsed
        plugin_id = f"{owner}/{repo_name}"

        logger.info(f"Installing plugin from GitHub clone: {plugin_id}")

        try:
            # Clone repository
            success = self.github_client.clone_repository(repo_url, destination, branch)

            if not success:
                return InstallationResult(
                    success=False,
                    plugin_id=plugin_id,
                    message="Failed to clone repository",
                    error="Git clone operation failed",
                )

            # Validate plugin structure
            validation = self._validate_plugin_structure(destination)

            if not validation.valid:
                # Cleanup on failure
                safe_delete_directory(destination)
                return InstallationResult(
                    success=False,
                    plugin_id=plugin_id,
                    message="Invalid plugin structure",
                    error=validation.error,
                )

            # Success
            logger.info(f"Successfully installed {plugin_id} from clone")
            return InstallationResult(
                success=True,
                plugin_id=plugin_id,
                message=f"Successfully installed {repo_name}",
                new_version=self._extract_version_from_clone(destination),
            )

        except Exception as e:
            logger.error(f"Installation failed: {e}")
            safe_delete_directory(destination)
            return InstallationResult(
                success=False,
                plugin_id=plugin_id,
                message="Installation failed",
                error=str(e),
            )

    def install_from_github_release(
        self,
        repo_url: str,
        release: GitHubRelease,
        destination: Path,
    ) -> InstallationResult:
        """
        Install plugin from GitHub release.

        Args:
            repo_url: GitHub repository URL
            release: Release to install
            destination: Installation destination path

        Returns:
            InstallationResult with operation status
        """
        parsed = parse_github_url(repo_url)
        if not parsed:
            return InstallationResult(
                success=False,
                plugin_id="",
                message="Failed to parse GitHub URL",
            )

        owner, repo_name = parsed
        plugin_id = f"{owner}/{repo_name}"

        logger.info(f"Installing plugin from GitHub release: {plugin_id} {release.tag_name}")

        try:
            # Find appropriate asset
            download_url = None
            for asset in release.assets:
                if asset.name.endswith(".zip"):
                    download_url = asset.download_url
                    break
                elif asset.name.endswith(".py") and not download_url:
                    download_url = asset.download_url

            if not download_url:
                return InstallationResult(
                    success=False,
                    plugin_id=plugin_id,
                    message="No downloadable asset found in release",
                    error="Release contains no .zip or .py files",
                )

            # Download to temp file
            temp_dir = Path(tempfile.mkdtemp(prefix="ida_plugin_release_"))

            try:
                # Download
                temp_file = temp_dir / "release.zip"
                downloaded = self.github_client.download_release_asset(download_url, temp_file)

                if not downloaded:
                    return InstallationResult(
                        success=False,
                        plugin_id=plugin_id,
                        message="Failed to download release asset",
                        error="Download operation failed",
                    )

                # Extract archive
                extract_result = extract_archive(temp_file, temp_dir / "extracted")

                if not extract_result.success:
                    return InstallationResult(
                        success=False,
                        plugin_id=plugin_id,
                        message="Failed to extract release archive",
                        error=extract_result.error,
                    )

                # Copy to destination
                extracted_path = temp_dir / "extracted"
                contents = list(extracted_path.iterdir())

                # If archive contains single directory, use its contents
                if len(contents) == 1 and contents[0].is_dir():
                    source = contents[0]
                else:
                    source = extracted_path

                safe_copy_directory(source, destination)

                # Validate
                validation = self._validate_plugin_structure(destination)
                if not validation.valid:
                    safe_delete_directory(destination)
                    return InstallationResult(
                        success=False,
                        plugin_id=plugin_id,
                        message="Invalid plugin structure",
                        error=validation.error,
                    )

                # Success
                version = self.github_client.__class__.__dict__.get("ReleaseFetcher", type(
                    "ReleaseFetcher", (), {}
                )()).extract_version(release.tag_name) if hasattr(release, "tag_name") else release.tag_name

                logger.info(f"Successfully installed {plugin_id} from release")
                return InstallationResult(
                    success=True,
                    plugin_id=plugin_id,
                    message=f"Successfully installed {repo_name} {version}",
                    new_version=version,
                )

            finally:
                # Cleanup temp directory
                shutil.rmtree(temp_dir, ignore_errors=True)

        except Exception as e:
            logger.error(f"Release installation failed: {e}")
            return InstallationResult(
                success=False,
                plugin_id=plugin_id,
                message="Installation failed",
                error=str(e),
            )

    def uninstall_plugin(self, plugin: Plugin, backup: bool = True) -> InstallationResult:
        """
        Uninstall a plugin.

        Args:
            plugin: Plugin to uninstall
            backup: Whether to create backup before uninstall

        Returns:
            InstallationResult with operation status
        """
        logger.info(f"Uninstalling plugin: {plugin.name}")

        try:
            install_path = Path(plugin.install_path) if plugin.install_path else None

            if not install_path or not install_path.exists():
                return InstallationResult(
                    success=False,
                    plugin_id=plugin.id,
                    message="Plugin installation not found",
                    error="Plugin files do not exist at expected location",
                )

            # Create backup if requested
            backup_path = None
            if backup:
                backup_path = backup_directory(install_path)

            # Delete plugin files
            result = safe_delete_directory(install_path)

            if not result.success:
                # Restore backup if deletion failed
                if backup_path and backup_path.exists():
                    safe_copy_directory(backup_path, install_path)
                return InstallationResult(
                    success=False,
                    plugin_id=plugin.id,
                    message="Failed to delete plugin files",
                    error=result.error,
                )

            logger.info(f"Successfully uninstalled {plugin.name}")
            return InstallationResult(
                success=True,
                plugin_id=plugin.id,
                message=f"Successfully uninstalled {plugin.name}",
                previous_version=plugin.installed_version,
            )

        except Exception as e:
            logger.error(f"Uninstallation failed: {e}")
            return InstallationResult(
                success=False,
                plugin_id=plugin.id,
                message="Uninstallation failed",
                error=str(e),
            )

    def validate_plugin_structure(self, plugin_path: Path) -> ValidationResult:
        """
        Validate plugin directory structure.

        Args:
            plugin_path: Path to plugin directory

        Returns:
            ValidationResult
        """
        return self._validate_plugin_structure(plugin_path)

    # ============ Private Methods ============

    def _validate_plugin_structure(self, plugin_path: Path) -> ValidationResult:
        """Validate plugin structure and detect type."""
        if not plugin_path.exists():
            return ValidationResult(valid=False, error="Plugin path does not exist")

        # Check for plugins.json (modern plugin)
        plugins_json = plugin_path / "plugins.json"
        if plugins_json.exists():
            try:
                with open(plugins_json, "r") as f:
                    data = json.load(f)

                # Validate required fields
                if "name" not in data or "version" not in data:
                    return ValidationResult(
                        valid=False,
                        error="Invalid plugins.json: missing required fields",
                    )

                # Check entry point exists
                entry_point = data.get("entry_point", "plugin.py")
                entry_path = plugin_path / entry_point
                if not entry_path.exists():
                    return ValidationResult(
                        valid=False,
                        error=f"Entry point {entry_point} not found",
                    )

                return ValidationResult(
                    valid=True,
                    plugin_type=PluginType.MODERN,
                )

            except json.JSONDecodeError as e:
                return ValidationResult(
                    valid=False,
                    error=f"Invalid plugins.json: {e}",
                )

        # Check for legacy plugin patterns
        py_files = list(plugin_path.glob("*.py"))

        if py_files:
            # Look for IDA plugin entry points
            for py_file in py_files:
                content = py_file.read_text(errors="ignore")
                if "PLUGIN_ENTRY" in content or "IDAPEnter" in content or "IDP_init" in content:
                    return ValidationResult(
                        valid=True,
                        plugin_type=PluginType.LEGACY,
                    )

            # Any Python file could be a plugin
            if len(py_files) == 1:
                return ValidationResult(
                    valid=True,
                    plugin_type=PluginType.LEGACY,
                )

        return ValidationResult(
            valid=False,
            error="No valid plugin structure found",
        )

    def _extract_version_from_clone(self, plugin_path: Path) -> Optional[str]:
        """Extract version from cloned plugin."""
        # Check plugins.json
        plugins_json = plugin_path / "plugins.json"
        if plugins_json.exists():
            try:
                data = json.loads(plugins_json.read_text())
                return data.get("version")
            except (json.JSONDecodeError, IOError):
                pass

        # Check for version in Python files
        for py_file in plugin_path.glob("*.py"):
            content = py_file.read_text(errors="ignore")
            import re

            match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
            if match:
                return match.group(1)

        return None
