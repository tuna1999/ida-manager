"""
Version comparison utilities for IDA Pro version strings.

Provides proper semantic version comparison to avoid string comparison bugs.
"""

from functools import total_ordering
from logging import getLogger
from typing import Optional, Tuple

from packaging.version import InvalidVersion, Version

logger = getLogger(__name__)


@total_ordering
class IDAVersion:
    """
    IDA Pro version wrapper for proper comparison.

    Handles version strings like:
    - "9.0" → Version(9, 0, 0)
    - "9.0.1" → Version(9, 0, 1)
    - "8.4" → Version(8, 4, 0)
    """

    def __init__(self, version_string: Optional[str]):
        """
        Initialize IDAVersion from string.

        Args:
            version_string: Version string (e.g., "9.0", "8.4.1")
        """
        self.raw = version_string
        self._version: Optional[Version] = None

        if version_string:
            try:
                # Normalize version string
                # Handle formats like "9.0", "8.4", "7.5 SP1"
                normalized = version_string.strip()

                # Remove common suffixes
                for suffix in [" SP", " SP1", " SP2", " SP3", "-sp1", "-sp2", "-sp3"]:
                    normalized = normalized.replace(suffix, ".0")

                self._version = Version(normalized)
            except (InvalidVersion, ValueError) as e:
                logger.warning(f"Invalid version string '{version_string}': {e}")
                self._version = None

    @property
    def is_valid(self) -> bool:
        """Check if version is valid."""
        return self._version is not None

    def __eq__(self, other) -> bool:
        """Compare versions for equality."""
        if not isinstance(other, IDAVersion):
            return NotImplemented
        if not self.is_valid or not other.is_valid:
            return False
        return self._version == other._version

    def __lt__(self, other) -> bool:
        """
        Compare versions for less-than.

        This fixes the string comparison bug where "8.10" < "8.9" would be True.
        """
        if not isinstance(other, IDAVersion):
            return NotImplemented
        if not self.is_valid or not other.is_valid:
            return False
        return self._version < other._version

    def __le__(self, other) -> bool:
        """Compare versions for less-than-or-equal."""
        if not isinstance(other, IDAVersion):
            return NotImplemented
        if not self.is_valid or not other.is_valid:
            return False
        return self._version <= other._version

    def __gt__(self, other) -> bool:
        """Compare versions for greater-than."""
        if not isinstance(other, IDAVersion):
            return NotImplemented
        if not self.is_valid or not other.is_valid:
            return False
        return self._version > other._version

    def __ge__(self, other) -> bool:
        """Compare versions for greater-than-or-equal."""
        if not isinstance(other, IDAVersion):
            return NotImplemented
        if not self.is_valid or not other.is_valid:
            return False
        return self._version >= other._version

    def __str__(self) -> str:
        """String representation."""
        return self.raw or "Unknown"

    def __repr__(self) -> str:
        """Developer representation."""
        return f"IDAVersion('{self.raw}')"


def compare_versions(v1: Optional[str], v2: Optional[str]) -> int:
    """
    Compare two version strings.

    Args:
        v1: First version string
        v2: Second version string

    Returns:
        -1 if v1 < v2
         0 if v1 == v2
         1 if v1 > v2

    Examples:
        >>> compare_versions("8.10", "8.9")
        1  # 8.10 > 8.9 (correct!)

        >>> compare_versions("9.0", "8.9")
        1  # 9.0 > 8.9

        >>> compare_versions("7.5", "7.5.1")
        -1  # 7.5 < 7.5.1
    """
    version1 = IDAVersion(v1)
    version2 = IDAVersion(v2)

    if version1 < version2:
        return -1
    elif version1 > version2:
        return 1
    else:
        return 0


def is_version_compatible(
    plugin_version_min: Optional[str],
    plugin_version_max: Optional[str],
    ida_version: str,
) -> bool:
    """
    Check if a plugin is compatible with the given IDA version.

    Uses proper version comparison instead of string comparison.

    Args:
        plugin_version_min: Minimum IDA version required (inclusive)
        plugin_version_max: Maximum IDA version supported (inclusive)
        ida_version: Current IDA version

    Returns:
        True if compatible, False otherwise

    Examples:
        >>> is_version_compatible("8.0", "9.0", "8.5")
        True

        >>> is_version_compatible("9.0", "9.2", "8.9")
        False  # 8.9 < 9.0

        >>> is_version_compatible(None, "9.0", "8.5")
        True  # No minimum requirement
    """
    ida_ver = IDAVersion(ida_version)

    if not ida_ver.is_valid:
        logger.warning(f"Invalid IDA version: {ida_version}")
        return False

    # Check minimum version
    if plugin_version_min:
        min_ver = IDAVersion(plugin_version_min)
        if min_ver.is_valid and ida_ver < min_ver:
            return False

    # Check maximum version
    if plugin_version_max:
        max_ver = IDAVersion(plugin_version_max)
        if max_ver.is_valid and ida_ver > max_ver:
            return False

    return True
