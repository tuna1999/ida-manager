"""
Release fetcher for GitHub plugin releases.

Handles fetching, parsing, and filtering GitHub releases for IDA plugins.
"""

from typing import List, Optional

from src.models.github_info import GitHubRelease, GitHubAsset
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ReleaseFetcher:
    """
    Fetch and manage GitHub releases for IDA plugins.

    Provides methods for:
    - Finding compatible releases
    - Filtering by version
    - Extracting download URLs
    - Parsing release metadata
    """

    def __init__(self):
        """Initialize release fetcher."""
        pass

    def get_latest_stable_release(self, releases: List[GitHubRelease]) -> Optional[GitHubRelease]:
        """
        Get the latest stable (non-prerelease) release.

        Args:
            releases: List of GitHubRelease objects

        Returns:
            Latest stable release or None
        """
        stable_releases = [r for r in releases if not r.prerelease]

        if not stable_releases:
            return None

        # Sort by publish date
        sorted_releases = sorted(
            stable_releases,
            key=lambda r: r.published_at or 0,
            reverse=True,
        )

        return sorted_releases[0]

    def get_latest_release(self, releases: List[GitHubRelease]) -> Optional[GitHubRelease]:
        """
        Get the latest release (including prereleases).

        Args:
            releases: List of GitHubRelease objects

        Returns:
            Latest release or None
        """
        if not releases:
            return None

        # Sort by publish date
        sorted_releases = sorted(
            releases,
            key=lambda r: r.published_at or 0,
            reverse=True,
        )

        return sorted_releases[0]

    def find_release_by_tag(self, releases: List[GitHubRelease], tag: str) -> Optional[GitHubRelease]:
        """
        Find a release by its tag name.

        Args:
            releases: List of GitHubRelease objects
            tag: Tag name to search for

        Returns:
            Matching release or None
        """
        for release in releases:
            if release.tag_name == tag:
                return release

        return None

    def find_release_by_version(
        self, releases: List[GitHubRelease], version: str
    ) -> Optional[GitHubRelease]:
        """
        Find a release by version number.

        Args:
            releases: List of GitHubRelease objects
            version: Version string (e.g., "1.0.0")

        Returns:
            Matching release or None
        """
        # Try exact match
        for release in releases:
            if version in release.tag_name:
                return release

        # Try with 'v' prefix
        version_with_v = f"v{version}"
        for release in releases:
            if release.tag_name == version_with_v:
                return release

        return None

    def get_compatible_asset(
        self,
        assets: List[GitHubAsset],
        preferred_patterns: Optional[List[str]] = None,
    ) -> Optional[GitHubAsset]:
        """
        Find the most appropriate asset to download.

        Args:
            assets: List of GitHubAsset objects
            preferred_patterns: List of preferred filename patterns (e.g., ["windows", "win64"])

        Returns:
            Best matching asset or None
        """
        if not assets:
            return None

        # If preferred patterns specified, try to find match
        if preferred_patterns:
            for pattern in preferred_patterns:
                for asset in assets:
                    if pattern.lower() in asset.name.lower():
                        logger.debug(f"Found asset matching pattern '{pattern}': {asset.name}")
                        return asset

        # Prefer .zip files (most common for plugins)
        for asset in assets:
            if asset.name.endswith(".zip"):
                return asset

        # Prefer .py files (for single-file plugins)
        for asset in assets:
            if asset.name.endswith(".py"):
                return asset

        # Fall back to .tar.gz files
        for asset in assets:
            if asset.name.endswith(".tar.gz") or asset.name.endswith(".tgz"):
                return asset

        # Return smallest asset as fallback
        return min(assets, key=lambda a: a.size)

    def get_download_url(
        self,
        release: GitHubRelease,
        preferred_patterns: Optional[List[str]] = None,
    ) -> Optional[str]:
        """
        Get the best download URL from a release.

        Args:
            release: GitHubRelease object
            preferred_patterns: Optional list of preferred filename patterns

        Returns:
            Download URL or None
        """
        if not release.assets:
            return None

        asset = self.get_compatible_asset(release.assets, preferred_patterns)

        return asset.download_url if asset else None

    def extract_version(self, tag_name: str) -> str:
        """
        Extract clean version number from tag name.

        Args:
            tag_name: Git tag name (e.g., "v1.0.0", "release-1.0.0")

        Returns:
            Clean version string
        """
        import re

        # Remove 'v' prefix
        version = tag_name.lstrip("vV")

        # Remove common prefixes
        for prefix in ["release-", "r", "ver-"]:
            if version.lower().startswith(prefix):
                version = version[len(prefix) :]
                break

        # Extract version numbers
        match = re.search(r"(\d+\.\d+[\d.]*)", version)
        if match:
            return match.group(1)

        return version

    def filter_by_compatibility(
        self,
        releases: List[GitHubRelease],
        ida_version: str,
        include_prerelease: bool = False,
    ) -> List[GitHubRelease]:
        """
        Filter releases by IDA version compatibility.

        This checks for version-specific tags like:
        - v1.0-ida90 (for IDA 9.0)
        - v1.0-ida84 (for IDA 8.4)

        Args:
            releases: List of GitHubRelease objects
            ida_version: Target IDA version (e.g., "9.0")
            include_prerelease: Whether to include prereleases

        Returns:
            Filtered list of releases
        """
        # Filter by prerelease
        if not include_prerelease:
            releases = [r for r in releases if not r.prerelease]

        # Normalize IDA version (e.g., "9.0" -> "90", "8.4" -> "84")
        ida_version_normalized = ida_version.replace(".", "")

        # Look for version-specific releases
        compatible = []
        for release in releases:
            tag_lower = release.tag_name.lower()
            # Check for IDA version tag
            if f"ida{ida_version_normalized}" in tag_lower:
                compatible.append(release)

        # If no version-specific releases found, return all (assuming compatible)
        if not compatible:
            return releases

        return compatible

    def get_changelog(self, release: GitHubRelease, max_length: int = 1000) -> str:
        """
        Get formatted changelog from release.

        Args:
            release: GitHubRelease object
            max_length: Maximum length of changelog

        Returns:
            Formatted changelog text
        """
        if not release.body:
            return "No release notes available."

        # Clean up the body
        changelog = release.body.strip()

        # Limit length
        if len(changelog) > max_length:
            changelog = changelog[:max_length] + "\n..."

        return changelog

    def get_all_releases_dict(self, releases: List[GitHubRelease]) -> List[dict]:
        """
        Convert releases to dictionary format for JSON serialization.

        Args:
            releases: List of GitHubRelease objects

        Returns:
            List of release dictionaries
        """
        return [
            {
                "id": r.id,
                "tag_name": r.tag_name,
                "name": r.name,
                "body": r.body,
                "published_at": r.published_at.isoformat() if r.published_at else None,
                "prerelease": r.prerelease,
                "html_url": r.html_url,
                "assets": [
                    {
                        "name": a.name,
                        "size": a.size,
                        "download_url": a.download_url,
                        "content_type": a.content_type,
                    }
                    for a in r.assets
                ],
            }
            for r in releases
        ]
