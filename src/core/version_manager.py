"""
Version management and compatibility checking.

Handles version parsing, comparison, and compatibility validation.
"""

from typing import Optional, Tuple

from packaging import version

from src.models.plugin import Plugin
from src.utils.logger import get_logger
from src.utils.validators import validate_ida_version, validate_version_string

logger = get_logger(__name__)


class VersionManager:
    """
    Manage plugin versions and compatibility.

    Provides:
    - Version parsing and comparison
    - Compatibility checking
    - Update detection
    """

    def __init__(self):
        """Initialize version manager."""
        pass

    def parse_version(self, version_str: str) -> Optional[version.Version]:
        """
        Parse version string into Version object.

        Args:
            version_str: Version string to parse

        Returns:
            Version object or None if invalid
        """
        try:
            # Clean version string
            cleaned = version_str.strip().lstrip("vV")
            return version.parse(cleaned)
        except version.InvalidVersion:
            logger.warning(f"Invalid version string: {version_str}")
            return None

    def compare_versions(self, v1: str, v2: str) -> int:
        """
        Compare two version strings.

        Args:
            v1: First version string
            v2: Second version string

        Returns:
            -1 if v1 < v2, 0 if v1 == v2, 1 if v1 > v2
        """
        parsed_v1 = self.parse_version(v1)
        parsed_v2 = self.parse_version(v2)

        if not parsed_v1 or not parsed_v2:
            return 0

        if parsed_v1 < parsed_v2:
            return -1
        elif parsed_v1 > parsed_v2:
            return 1
        else:
            return 0

    def check_compatibility(
        self,
        plugin: Plugin,
        ida_version: str,
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if plugin is compatible with IDA version.

        Args:
            plugin: Plugin object to check
            ida_version: IDA Pro version string

        Returns:
            Tuple of (is_compatible, error_message)
        """
        # Validate IDA version format
        if not validate_ida_version(ida_version):
            return False, f"Invalid IDA version format: {ida_version}"

        parsed_ida = self.parse_version(ida_version)

        # Check minimum version requirement
        if plugin.ida_version_min:
            if not validate_version_string(plugin.ida_version_min):
                return False, f"Invalid minimum version format: {plugin.ida_version_min}"

            min_ver = self.parse_version(plugin.ida_version_min)
            if min_ver and parsed_ida < min_ver:
                return False, f"Plugin requires IDA {plugin.ida_version_min} or newer (current: {ida_version})"

        # Check maximum version requirement
        if plugin.ida_version_max:
            if not validate_version_string(plugin.ida_version_max):
                return False, f"Invalid maximum version format: {plugin.ida_version_max}"

            max_ver = self.parse_version(plugin.ida_version_max)
            if max_ver and parsed_ida > max_ver:
                return False, f"Plugin requires IDA {plugin.ida_version_max} or older (current: {ida_version})"

        return True, None

    def get_latest_version(self, plugin: Plugin) -> Optional[str]:
        """
        Get the latest available version for a plugin.

        Args:
            plugin: Plugin object

        Returns:
            Latest version string or None
        """
        return plugin.latest_version

    def has_update(self, plugin: Plugin) -> bool:
        """
        Check if plugin has an available update.

        Args:
            plugin: Plugin object

        Returns:
            True if update available, False otherwise
        """
        if not plugin.installed_version or not plugin.latest_version:
            return False

        return self.compare_versions(plugin.latest_version, plugin.installed_version) > 0

    def get_compatible_ida_versions(self, plugin: Plugin) -> Tuple[Optional[str], Optional[str]]:
        """
        Get compatible IDA version range for plugin.

        Args:
            plugin: Plugin object

        Returns:
            Tuple of (min_version, max_version)
        """
        return plugin.ida_version_min, plugin.ida_version_max

    def is_version_newer(self, current: str, target: str) -> bool:
        """
        Check if target version is newer than current.

        Args:
            current: Current version string
            target: Target version string

        Returns:
            True if target is newer, False otherwise
        """
        return self.compare_versions(target, current) > 0

    def normalize_version(self, version_str: str) -> str:
        """
        Normalize version string to standard format.

        Args:
            version_str: Version string to normalize

        Returns:
            Normalized version string
        """
        parsed = self.parse_version(version_str)
        if parsed:
            return str(parsed)
        return version_str

    def get_version_delta(self, from_version: str, to_version: str) -> str:
        """
        Get version delta description.

        Args:
            from_version: Starting version
            to_version: Target version

        Returns:
            Description of version change
        """
        comparison = self.compare_versions(to_version, from_version)

        if comparison < 0:
            return f"downgrade to {to_version}"
        elif comparison == 0:
            return "same version"
        else:
            # Check if major version bump
            from_parsed = self.parse_version(from_version)
            to_parsed = self.parse_version(to_version)

            if from_parsed and to_parsed:
                if to_parsed.major > from_parsed.major:
                    return f"major update to {to_version}"
                elif to_parsed.minor > from_parsed.minor:
                    return f"minor update to {to_version}"
                else:
                    return f"patch update to {to_version}"

            return f"update to {to_version}"
