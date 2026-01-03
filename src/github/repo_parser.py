"""
GitHub repository parser for extracting plugin metadata.

Parses repository content to detect IDA plugins and extract metadata
from README, plugins.json, and other sources.
"""

import json
import re
from typing import Dict, List, Optional

from src.models.github_info import GitHubContentItem, GitHubPluginInfo
from src.models.plugin import PluginMetadata, PluginType, ValidationResult
from src.utils.logger import get_logger

logger = get_logger(__name__)


class RepoParser:
    """
    Parse GitHub repositories to extract IDA plugin metadata.

    Detects plugin type (legacy/modern) and extracts information from:
    - README files
    - plugins.json (modern plugins)
    - Repository structure
    - Setup files
    """

    def parse_repository(
        self,
        repo_name: str,
        contents: List[GitHubContentItem],
        readme: Optional[str] = None,
        plugins_json: Optional[dict] = None,
    ) -> ValidationResult:
        """
        Parse repository to validate as IDA plugin and extract metadata.

        Args:
            repo_name: Repository name
            contents: List of files/directories in repository
            readme: README content (optional)
            plugins_json: Parsed ida-plugin.json content (optional)

        Returns:
            ValidationResult with plugin type and metadata
        """
        # Check for ida-plugin.json (IDA Pro 9.0+ official format only)
        has_ida_plugin_json = any(
            item.name == "ida-plugin.json"
            for item in contents
            if item.type == "file"
        )

        if has_ida_plugin_json and plugins_json:
            return self._parse_modern_plugin(repo_name, contents, readme, plugins_json)

        # Check for legacy plugin patterns
        has_py_files = any(item.name.endswith(".py") for item in contents if item.type == "file")

        if has_py_files:
            return self._parse_legacy_plugin(repo_name, contents, readme)

        # Not a valid plugin
        return ValidationResult(
            valid=False,
            error="No IDA plugin structure detected (no ida-plugin.json or Python files with IDA entry points)"
        )

    def parse_readme(self, readme_content: str) -> PluginMetadata:
        """
        Parse README for plugin metadata.

        Args:
            readme_content: README content

        Returns:
            PluginMetadata object
        """
        metadata = PluginMetadata(name="", description="", readme_content=readme_content)

        # Extract name from first heading
        heading_match = re.search(r"^#\s+(.+)$", readme_content, re.MULTILINE)
        if heading_match:
            metadata.name = heading_match.group(1).strip()

        # Extract description from first paragraph
        desc_match = re.search(r"^#\s.+?\n+(.+?)\n\n", readme_content, re.DOTALL)
        if desc_match:
            metadata.description = desc_match.group(1).strip()

        # Extract author from common patterns
        author_patterns = [
            r"Author[:\s]+([^\n]+)",
            r"By[:\s]+([^\n]+)",
            r"@author\s+([^\n]+)",
        ]
        for pattern in author_patterns:
            match = re.search(pattern, readme_content, re.IGNORECASE)
            if match:
                metadata.author = match.group(1).strip()
                break

        # Extract IDA version compatibility
        version_patterns = [
            r"IDA\s+(\d+\.\d+)",
            r"IDA\s+Pro\s+(\d+\.\d+)",
            r"Requires\s+IDA\s+(\d+\.\d+)",
            r"Compatible\s+with\s+IDA\s+(\d+\.\d+)",
        ]
        for pattern in version_patterns:
            matches = re.findall(pattern, readme_content, re.IGNORECASE)
            if matches:
                versions = sorted(matches, key=lambda v: tuple(map(int, v.split("."))))
                metadata.ida_version_min = versions[0]
                metadata.ida_version_max = versions[-1]
                break

        # Extract version from patterns
        version_match = re.search(r"Version[:\s]+(\d+\.\d+[.\d]*)", readme_content, re.IGNORECASE)
        if version_match:
            metadata.version = version_match.group(1)

        return metadata

    def parse_plugins_json(self, json_content: dict) -> PluginMetadata:
        """
        Parse ida-plugin.json for IDA Pro 9.0+ plugin metadata.

        IDA Pro 9.0+ uses the following official format:
        {
          "IDAMetadataDescriptorVersion": 1,
          "plugin": {
            "name": "...",
            "entryPoint": "...",
            ...
          }
        }

        Args:
            json_content: Parsed ida-plugin.json content

        Returns:
            PluginMetadata object
        """
        # Check if IDA Pro 9.0+ format (has "plugin" wrapper)
        if "plugin" in json_content:
            plugin_data = json_content["plugin"]

            # Extract authors
            authors_list = plugin_data.get("authors", [])
            if authors_list and isinstance(authors_list, list):
                # Join multiple authors
                author = ", ".join(
                    a.get("name", "") if isinstance(a, dict) else str(a)
                    for a in authors_list
                )
            else:
                author = None

            # Extract IDA versions
            ida_versions = plugin_data.get("idaVersions", [])
            ida_version_min = ida_versions[0] if ida_versions else None
            ida_version_max = ida_versions[-1] if ida_versions else None

            return PluginMetadata(
                name=plugin_data.get("name", ""),
                version=plugin_data.get("version"),
                description=plugin_data.get("description"),
                author=author,
                ida_version_min=ida_version_min,
                ida_version_max=ida_version_max,
                dependencies=plugin_data.get("pythonDependencies", []),
                entry_point=plugin_data.get("entryPoint"),
            )
        else:
            # Legacy/custom format (direct fields)
            return PluginMetadata(
                name=json_content.get("name", ""),
                version=json_content.get("version"),
                description=json_content.get("description"),
                author=json_content.get("author"),
                ida_version_min=json_content.get("ida_version_min"),
                ida_version_max=json_content.get("ida_version_max"),
                dependencies=json_content.get("dependencies", []),
                entry_point=json_content.get("entry_point"),
            )

    def detect_plugin_type(self, contents: List[GitHubContentItem]) -> Optional[PluginType]:
        """
        Detect plugin type from repository contents.

        Args:
            contents: List of files/directories

        Returns:
            PluginType or None if not detectable
        """
        # Check for plugins.json
        for item in contents:
            if item.name == "plugins.json" and item.type == "file":
                return PluginType.MODERN

        # Check for typical IDA plugin patterns
        for item in contents:
            if item.type == "file" and item.name.endswith(".py"):
                # Could be legacy plugin
                return PluginType.LEGACY

        return None

    def extract_ida_version_compatibility(self, metadata: Dict) -> tuple[Optional[str], Optional[str]]:
        """
        Extract IDA version compatibility from metadata.

        Args:
            metadata: Metadata dictionary

        Returns:
            Tuple of (min_version, max_version)
        """
        min_version = metadata.get("ida_version_min") or metadata.get("min_ida_version")
        max_version = metadata.get("ida_version_max") or metadata.get("max_ida_version")

        return min_version, max_version

    def validate_ida_plugin(self, contents: List[GitHubContentItem]) -> ValidationResult:
        """
        Validate if repository contains IDA plugin.

        Args:
            contents: List of files/directories

        Returns:
            ValidationResult indicating if valid plugin
        """
        # Check for plugins.json (modern)
        if any(item.name == "plugins.json" and item.type == "file" for item in contents):
            return ValidationResult(
                valid=True,
                plugin_type=PluginType.MODERN,
                warnings=["Modern IDA plugin detected (plugins.json found)"]
            )

        # Check for Python files (legacy)
        py_files = [item for item in contents if item.type == "file" and item.name.endswith(".py")]

        if py_files:
            # Check for IDA entry points
            ida_patterns = ["PLUGIN_ENTRY", "IDAPEnter", "IDP_init"]
            for py_file in py_files:
                # Would need to fetch file content to check
                # For now, assume any Python file in repo could be IDA plugin
                pass

            return ValidationResult(
                valid=True,
                plugin_type=PluginType.LEGACY,
                warnings=["Legacy IDA plugin detected (Python files found)"]
            )

        return ValidationResult(
            valid=False,
            error="No IDA plugin structure found"
        )

    # ============ Private Methods ============

    def _parse_modern_plugin(
        self,
        repo_name: str,
        contents: List[GitHubContentItem],
        readme: Optional[str],
        plugins_json: dict,
    ) -> ValidationResult:
        """Parse modern plugin (with plugins.json)."""
        metadata = self.parse_plugins_json(plugins_json)

        warnings = []
        if not metadata.name:
            metadata.name = repo_name
            warnings.append("Plugin name not found in plugins.json, using repo name")

        if not metadata.entry_point:
            warnings.append("No entry_point specified in plugins.json")

        return ValidationResult(
            valid=True,
            plugin_type=PluginType.MODERN,
            metadata=metadata,
            warnings=warnings
        )

    def _parse_legacy_plugin(
        self,
        repo_name: str,
        contents: List[GitHubContentItem],
        readme: Optional[str],
    ) -> ValidationResult:
        """Parse legacy plugin (Python files)."""
        warnings = []

        if readme:
            metadata = self.parse_readme(readme)
        else:
            metadata = PluginMetadata(name=repo_name)

        if not metadata.name:
            metadata.name = repo_name
            warnings.append("Using repository name as plugin name")

        return ValidationResult(
            valid=True,
            plugin_type=PluginType.LEGACY,
            metadata=metadata,
            warnings=warnings
        )


class ReleaseFetcher:
    """
    Fetch and parse GitHub release information.

    Handles finding compatible releases and extracting download URLs.
    """

    def get_download_url(self, assets: List, asset_pattern: Optional[str] = None) -> Optional[str]:
        """
        Find appropriate download URL from release assets.

        Args:
            assets: List of GitHubAsset objects
            asset_pattern: Optional pattern to match asset names

        Returns:
            Download URL or None
        """
        if not assets:
            return None

        # If pattern specified, find matching asset
        if asset_pattern:
            for asset in assets:
                if asset_pattern.lower() in asset.name.lower():
                    return asset.download_url

        # Prefer .zip files
        for asset in assets:
            if asset.name.endswith(".zip"):
                return asset.download_url

        # Prefer .py files for plugins
        for asset in assets:
            if asset.name.endswith(".py"):
                return asset.download_url

        # Fall back to first asset
        return assets[0].download_url if assets else None

    def parse_version_from_tag(self, tag: str) -> str:
        """
        Extract version number from git tag.

        Args:
            tag: Git tag string (e.g., "v1.0.0", "release-1.0")

        Returns:
            Version string
        """
        # Remove 'v' prefix if present
        version = tag.lstrip("v")

        # Extract just version numbers
        match = re.search(r"(\d+\.\d+[\d.]*)", version)
        if match:
            return match.group(1)

        return version

    def get_compatible_release(
        self,
        releases: List,
        ida_version: str,
        allow_prerelease: bool = False,
    ) -> Optional:
        """
        Find release compatible with IDA version.

        Args:
            releases: List of GitHubRelease objects
            ida_version: Target IDA version
            allow_prerelease: Whether to include pre-releases

        Returns:
            GitHubRelease object or None
        """
        # Filter out prereleases if not allowed
        if not allow_prerelease:
            releases = [r for r in releases if not r.prerelease]

        if not releases:
            return None

        # Look for version-specific tags (e.g., v1.0-ida84)
        version_tag = f"-ida{ida_version.replace('.', '')}"
        for release in releases:
            if version_tag in release.tag_name:
                return release

        # Return latest release
        return releases[0]

    def extract_release_notes(self, release_body: Optional[str]) -> str:
        """
        Extract release notes from release body.

        Args:
            release_body: Release body text

        Returns:
            Cleaned release notes
        """
        if not release_body:
            return ""

        # Remove common noise patterns
        lines = []
        for line in release_body.split("\n"):
            line = line.strip()
            # Skip empty lines and common markdown patterns
            if line and not line.startswith("#"):
                lines.append(line)

        return "\n".join(lines[:20])  # Limit to first 20 lines
