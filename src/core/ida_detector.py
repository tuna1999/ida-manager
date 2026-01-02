"""
IDA Pro installation detection and version detection.

Handles detection of IDA Pro installations on Windows, version extraction,
and plugin directory path resolution.
"""

import os
import re
from pathlib import Path
from typing import List, Optional, Tuple

import winreg

from src.config.constants import IDA_DEFAULT_PATHS, IDA_REGISTRY_KEYS
from src.utils.logger import get_logger

logger = get_logger(__name__)


class IDADetector:
    """
    IDA Pro installation detector.

    Detects IDA Pro installations using multiple methods:
    1. Windows Registry
    2. Common installation paths
    3. User configuration
    4. PATH environment variable
    """

    def __init__(self):
        """Initialize IDA detector."""
        self._cached_installations: Optional[List[Tuple[Path, str]]] = None

    def find_all_installations(self) -> List[Tuple[Path, str]]:
        """
        Find all IDA Pro installations on the system.

        Returns:
            List of tuples (installation_path, version)
        """
        if self._cached_installations is not None:
            return self._cached_installations

        installations = []

        # Method 1: Check Windows Registry
        installations.extend(self._find_from_registry())

        # Method 2: Check common paths
        installations.extend(self._find_from_common_paths())

        # Method 3: Check PATH environment variable
        installations.extend(self._find_from_path())

        # Remove duplicates and validate
        seen = set()
        unique_installations = []
        for path, version in installations:
            if str(path) not in seen:
                if self.validate_ida_installation(path):
                    seen.add(str(path))
                    # If version not found, try to detect it
                    if not version:
                        version = self.get_ida_version(path) or "unknown"
                    unique_installations.append((path, version))

        self._cached_installations = unique_installations
        return unique_installations

    def find_ida_installation(self, preferred_version: Optional[str] = None) -> Optional[Path]:
        """
        Find IDA Pro installation.

        Args:
            preferred_version: Preferred IDA version (e.g., "9.0", "8.4")

        Returns:
            Path to IDA Pro installation or None if not found.
        """
        installations = self.find_all_installations()

        if not installations:
            logger.warning("No IDA Pro installation found")
            return None

        # If preferred version specified, try to find matching installation
        if preferred_version:
            for path, version in installations:
                if version.startswith(preferred_version):
                    logger.info(f"Found IDA Pro {version} at {path}")
                    return path

        # Return first found installation
        path, version = installations[0]
        logger.info(f"Found IDA Pro {version} at {path}")
        return path

    def get_ida_version(self, ida_path: Path) -> Optional[str]:
        """
        Extract IDA Pro version from installation.

        Args:
            ida_path: Path to IDA Pro installation

        Returns:
            Version string or None if not found.
        """
        # Method 1: Check exe file properties
        version = self._get_exe_version(ida_path)
        if version:
            return version

        # Method 2: Parse idatag.cfg file
        version = self._parse_idatag_cfg(ida_path)
        if version:
            return version

        # Method 3: Extract from directory name
        version = self._extract_version_from_path(ida_path)
        if version:
            return version

        logger.warning(f"Could not determine IDA version for {ida_path}")
        return None

    def get_idausr_directories(self) -> List[Path]:
        """
        Get all IDAUSR directories from environment variable.

        IDAUSR can contain multiple paths separated by platform separator:
        - Windows: semicolon (;)
        - Linux/Mac: colon (:)

        Returns:
            List of IDAUSR directories. Returns default location if not set.
        """
        idausr_env = os.environ.get("IDAUSR", "")

        if not idausr_env:
            # Return default location based on platform
            if os.name == "nt":  # Windows
                return [Path(os.environ.get("APPDATA", "")) / "Hex-Rays" / "IDA Pro"]
            else:  # Linux/Mac
                return [Path(os.path.expanduser("~")) / ".idapro"]

        # Split by platform separator
        if os.name == "nt":  # Windows
            separator = ";"
        else:  # Linux/Mac
            separator = ":"

        # Parse and return paths
        paths = []
        for path_str in idausr_env.split(separator):
            path = Path(path_str.strip())
            if path.exists():
                paths.append(path)

        # If no existing paths found, return at least the first one
        return paths if paths else [Path(idausr_env.split(separator)[0])]

    def get_plugin_directory(self, ida_path: Path, prefer_user: bool = True) -> Path:
        """
        Get plugin directory for IDA installation.

        IDA loads plugins in this order:
        1. $IDAUSR/plugins (user plugins - priority)
        2. %IDADIR%/plugins (installation plugins)

        Args:
            ida_path: Path to IDA Pro installation
            prefer_user: If True, prefer IDAUSR/plugins (default: True)

        Returns:
            Path to plugins directory.
        """
        # 1. Check IDAUSR directories (user plugins)
        if prefer_user:
            idausr_dirs = self.get_idausr_directories()
            for idausr_dir in idausr_dirs:
                user_plugin_dir = idausr_dir / "plugins"
                if user_plugin_dir.exists():
                    logger.info(f"Using IDAUSR plugins directory: {user_plugin_dir}")
                    return user_plugin_dir

        # 2. Fallback to installation directory
        plugin_dir = ida_path / "plugins"
        if plugin_dir.exists():
            logger.info(f"Using IDADIR plugins directory: {plugin_dir}")
            return plugin_dir

        # 3. Create IDAUSR plugins dir as last resort
        if prefer_user:
            idausr_dirs = self.get_idausr_directories()
            if idausr_dirs:
                user_plugin_dir = idausr_dirs[0] / "plugins"
                user_plugin_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created IDAUSR plugins directory: {user_plugin_dir}")
                return user_plugin_dir

        # 4. Final fallback
        return plugin_dir

    def get_all_plugin_directories(self, ida_path: Path) -> List[Path]:
        """
        Get all plugin directories where IDA will look for plugins.

        Returns directories in IDA's loading order:
        1. All $IDAUSR/plugins directories (user plugins)
        2. %IDADIR%/plugins (installation plugins)

        Args:
            ida_path: Path to IDA Pro installation

        Returns:
            List of plugin directories in loading order.
        """
        plugin_dirs = []

        # 1. Add all IDAUSR/plugins directories
        idausr_dirs = self.get_idausr_directories()
        for idausr_dir in idausr_dirs:
            user_plugin_dir = idausr_dir / "plugins"
            if user_plugin_dir.exists():
                plugin_dirs.append(user_plugin_dir)

        # 2. Add installation directory
        plugin_dir = ida_path / "plugins"
        if plugin_dir.exists():
            plugin_dirs.append(plugin_dir)

        return plugin_dirs

    def validate_ida_installation(self, path: Path) -> bool:
        """
        Validate that path contains valid IDA Pro installation.

        Checks for:
        - ida.exe or idat.exe exists
        - plugins directory exists
        - cfg directory exists (optional but recommended)

        Args:
            path: Path to validate

        Returns:
            True if valid IDA installation, False otherwise.
        """
        # Check for main executables
        ida_exe = path / "ida.exe"
        idat_exe = path / "idat.exe"

        if not (ida_exe.exists() or idat_exe.exists()):
            return False

        # Check for plugins directory
        plugins_dir = path / "plugins"
        if not plugins_dir.exists():
            return False

        # cfg directory is optional but good indicator
        cfg_dir = path / "cfg"
        if not cfg_dir.exists():
            logger.warning(f"IDA installation at {path} missing cfg directory")

        return True

    # ============ Private Methods ============

    def _find_from_registry(self) -> List[Tuple[Path, str]]:
        """Find IDA installations from Windows registry."""
        installations = []

        try:
            for key_path, value_name in IDA_REGISTRY_KEYS:
                # Try both HKLM and HKCU
                for root_key in [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]:
                    try:
                        key = winreg.OpenKey(root_key, key_path)
                        install_dir, _ = winreg.QueryValueEx(key, value_name)
                        winreg.CloseKey(key)

                        if install_dir:
                            path = Path(install_dir)
                            version = self.get_ida_version(path)
                            installations.append((path, version))

                    except (WindowsError, FileNotFoundError):
                        continue

        except Exception as e:
            logger.debug(f"Error reading registry: {e}")

        return installations

    def _find_from_common_paths(self) -> List[Tuple[Path, str]]:
        """Find IDA installations from common paths."""
        installations = []

        for pattern_path in IDA_DEFAULT_PATHS:
            # Handle wildcard patterns
            if "*" in str(pattern_path):
                parent = pattern_path.parent
                pattern = pattern_path.name
                if parent.exists():
                    for path in parent.glob(pattern):
                        if path.is_dir():
                            version = self.get_ida_version(path)
                            installations.append((path, version))
            else:
                # Direct path
                if pattern_path.exists():
                    version = self.get_ida_version(pattern_path)
                    installations.append((pattern_path, version))

        return installations

    def _find_from_path(self) -> List[Tuple[Path, str]]:
        """Find IDA from PATH environment variable."""
        installations = []

        try:
            path_env = os.environ.get("PATH", "")
            for dir_path in path_env.split(os.pathsep):
                dir_path = Path(dir_path)
                ida_exe = dir_path / "ida.exe"
                idat_exe = dir_path / "idat.exe"

                if ida_exe.exists() or idat_exe.exists():
                    # Found IDA in PATH
                    version = self.get_ida_version(dir_path)
                    installations.append((dir_path, version))

        except Exception as e:
            logger.debug(f"Error searching PATH: {e}")

        return installations

    def _get_exe_version(self, ida_path: Path) -> Optional[str]:
        """Extract version from exe file properties."""
        try:
            ida_exe = ida_path / "ida.exe"
            if not ida_exe.exists():
                ida_exe = ida_path / "idat.exe"

            if ida_exe.exists():
                # Try to read version info using Windows API
                import win32api

                info = win32api.GetFileVersionInfo(str(ida_exe), "\\")
                ms = info["FileVersionMS"]
                ls = info["FileVersionLS"]
                version = f"{(ms >> 16) & 0xFFFF}.{(ms & 0xFFFF)}.{(ls >> 16) & 0xFFFF}.{(ls & 0xFFFF)}"
                # Return major.minor
                return ".".join(version.split(".")[:2])

        except ImportError:
            logger.debug("win32api not available for version extraction")
        except Exception as e:
            logger.debug(f"Failed to extract exe version: {e}")

        return None

    def _parse_idatag_cfg(self, ida_path: Path) -> Optional[str]:
        """Parse idatag.cfg for version information."""
        try:
            cfg_file = ida_path / "cfg" / "idatag.cfg"
            if not cfg_file.exists():
                return None

            with open(cfg_file, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            # Look for version pattern like: "Version 9.0" or similar
            patterns = [
                r"Version\s+(\d+\.\d+)",
                r"IDA\s+Version\s*[:=]\s*(\d+\.\d+)",
                r"HEXRAYS_IDA_VERSION\s*[:=]\s*[\"']?(\d+\.\d+)",
            ]

            for pattern in patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    return match.group(1)

        except Exception as e:
            logger.debug(f"Failed to parse idatag.cfg: {e}")

        return None

    def _extract_version_from_path(self, ida_path: Path) -> Optional[str]:
        """Extract version from directory name."""
        # Pattern: "IDA Pro X.Y" or "IDA Pro X.Y.ZZZ"
        match = re.search(r"IDA Pro\s+(\d+\.\d+)", str(ida_path), re.IGNORECASE)
        if match:
            return match.group(1)

        # Pattern: Just version number
        match = re.search(r"(\d+\.\d+)", str(ida_path))
        if match:
            return match.group(1)

        return None
