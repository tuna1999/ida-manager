"""
Validation utilities for IDA Plugin Manager.

Provides input validation for URLs, versions, filenames, etc.
"""

import re
from typing import Optional


def validate_github_url(url: str) -> bool:
    """
    Validate GitHub repository URL.

    Args:
        url: URL to validate

    Returns:
        True if valid GitHub URL, False otherwise
    """
    if not url:
        return False

    # Match github.com URLs
    patterns = [
        r"^https?://github\.com/[^/]+/[^/]+/?$",
        r"^git@github\.com:([^/]+)/([^/]+)\.git$",
    ]

    for pattern in patterns:
        if re.match(pattern, url):
            return True

    return False


def parse_github_url(url: str) -> Optional[tuple[str, str]]:
    """
    Parse owner and repo from GitHub URL.

    Args:
        url: GitHub repository URL

    Returns:
        Tuple of (owner, repo) or None if invalid
    """
    if not url:
        return None

    # Parse https://github.com/owner/repo
    match = re.match(r"^https?://github\.com/([^/]+)/([^/]+)/?$", url)
    if match:
        return match.group(1), match.group(2)

    # Parse git@github.com:owner/repo.git
    match = re.match(r"^git@github\.com:([^/]+)/([^/]+)\.git$", url)
    if match:
        return match.group(1), match.group(2)

    return None


def validate_plugin_name(name: str) -> bool:
    """
    Validate plugin name.

    Args:
        name: Plugin name to validate

    Returns:
        True if valid, False otherwise
    """
    if not name or len(name) < 2 or len(name) > 100:
        return False

    # Allow alphanumeric, spaces, hyphens, underscores
    pattern = r"^[\w\s\-\.]+$"
    return bool(re.match(pattern, name))


def validate_version_string(version: str) -> bool:
    """
    Validate version string format.

    Accepts formats like:
    - 1.0.0
    - 1.0
    - v1.0.0

    Args:
        version: Version string to validate

    Returns:
        True if valid format, False otherwise
    """
    if not version:
        return False

    # Remove 'v' prefix
    version = version.lstrip("vV")

    # Match semantic version pattern
    pattern = r"^\d+(\.\d+){0,2}([a-zA-Z0-9\-]+)?$"
    return bool(re.match(pattern, version))


def validate_ida_version(version: str) -> bool:
    """
    Validate IDA Pro version string.

    IDA versions are typically X.Y format (e.g., 9.0, 8.4)

    Args:
        version: IDA version string

    Returns:
        True if valid IDA version format, False otherwise
    """
    if not version:
        return False

    # Match X.Y format
    match = re.match(r"^(\d+\.\d+)(\.\d+)?$", version)
    if not match:
        return False

    # Check reasonable version range
    major, minor = map(int, version.split(".")[:2])

    # IDA Pro versions roughly between 5.0 and 10.0
    if not (5 <= major <= 10):
        return False

    if not (0 <= minor <= 99):
        return False

    return True


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing invalid characters.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    # Remove invalid characters for Windows
    invalid_chars = r'[<>:"/\\|?*]'
    sanitized = re.sub(invalid_chars, "_", filename)

    # Remove leading/trailing spaces and dots
    sanitized = sanitized.strip(". ")

    # Limit length
    if len(sanitized) > 255:
        sanitized = sanitized[:255]

    return sanitized or "unnamed"


def validate_path(path: str) -> bool:
    """
    Validate file system path.

    Args:
        path: Path string to validate

    Returns:
        True if path appears valid, False otherwise
    """
    if not path:
        return False

    # Check for invalid characters
    invalid_chars = r'<>:"|?*'
    if any(char in path for char in invalid_chars):
        return False

    return True


def is_safe_url(url: str) -> bool:
    """
    Check if URL is safe (HTTPS or localhost).

    Args:
        url: URL to check

    Returns:
        True if URL appears safe, False otherwise
    """
    if not url:
        return False

    return url.startswith(("https://", "http://localhost", "http://127.0.0.1"))


def validate_token(token: str) -> bool:
    """
    Validate GitHub personal access token format.

    GitHub tokens typically start with 'ghp_', 'github_pat_', etc.

    Args:
        token: Token string to validate

    Returns:
        True if token format appears valid, False otherwise
    """
    if not token:
        return True  # Empty token is valid (no authentication)

    # GitHub token patterns
    patterns = [
        r"^ghp_[A-Za-z0-9]{36}$",  # GitHub Personal Access Token
        r"^github_pat_[A-Za-z0-9_]{82}$",  # GitHub Fine-grained token
        r"^gho_[A-Za-z0-9]{36}$",  # GitHub OAuth token
        r"^ghu_[A-Za-z0-9]{36}$",  # GitHub user token
    ]

    for pattern in patterns:
        if re.match(pattern, token):
            return True

    return False
