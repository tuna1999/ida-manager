"""
Font Manager for IDA Plugin Manager.

Provides DPI-aware font loading and management for Dear PyGui applications.
"""

import os
import platform
import ctypes
from typing import Optional, Dict, Tuple
from pathlib import Path

from src.config.settings import SettingsManager
from src.utils.logger import get_logger

logger = get_logger(__name__)


class FontManager:
    """
    Font manager with DPI awareness and system font loading.

    Features:
    - DPI detection (96 DPI = 1.0, 144 DPI = 1.5)
    - System font loading (Segoe UI, SF Pro Display, Ubuntu)
    - Font size presets (11, 13, 16, 20)
    - Monospace fonts for code/versions
    - Font customization via settings
    """

    # Font size presets
    SIZE_SMALL = 11
    SIZE_NORMAL = 13
    SIZE_LARGE = 16
    SIZE_HUGE = 20

    # System fonts by platform (name -> file path mappings)
    SYSTEM_FONTS = {
        "Windows": {
            "default": "Segoe UI",
            "default_path": "C:\\Windows\\Fonts\\segoeui.ttf",
            "monospace": "Consolas",
            "monospace_path": "C:\\Windows\\Fonts\\consola.ttf"
        },
        "Darwin": {  # macOS
            "default": "SF Pro Display",
            "default_path": "/System/Library/Fonts/SFNSDisplay.ttf",
            "monospace": "SF Mono",
            "monospace_path": "/System/Library/Fonts/SFMono-Regular.ttf"
        },
        "Linux": {
            "default": "Ubuntu",
            "default_path": "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
            "monospace": "Ubuntu Mono",
            "monospace_path": "/usr/share/fonts/truetype/ubuntu/UbuntuMono-R.ttf"
        }
    }

    def __init__(self, settings_manager: SettingsManager):
        """
        Initialize the font manager.

        Args:
            settings_manager: SettingsManager instance for persistence
        """
        self.settings = settings_manager
        self.dpg = None

        # Detect DPI scale
        self._dpi_scale = self._detect_dpi_scale()

        # Load font settings
        self._font_family = self._load_font_family()
        self._font_size = self._load_font_size()

        # Font registry
        self._fonts: Dict[str, int] = {}  # Font name -> font ID

        logger.info(f"FontManager initialized: DPI={self._dpi_scale:.2f}, font={self._font_family}, size={self._font_size}")

    def _detect_dpi_scale(self) -> float:
        """
        Detect DPI scaling factor.

        Returns:
            DPI scale (1.0 for 96 DPI, 1.5 for 144 DPI, etc.)
        """
        try:
            system = platform.system()

            if system == "Windows":
                # Windows DPI detection
                user32 = ctypes.windll.user32
                hdc = user32.GetDC(0)
                LOGPIXELSX = 88
                dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, LOGPIXELSX)
                user32.ReleaseDC(0, hdc)
                scale = dpi / 96.0
                logger.info(f"Windows DPI detected: {dpi} (scale={scale:.2f})")
                return scale

            elif system == "Darwin":  # macOS
                # macOS typically uses 72 DPI as base
                import subprocess
                result = subprocess.run(["defaults", "read", "-g", "AppleDisplayScaledFactors"],
                                      capture_output=True, text=True, timeout=2)
                if result.returncode == 0:
                    # Parse macOS display scale factor
                    try:
                        scale = float(result.stdout.strip())
                        logger.info(f"macOS scale detected: {scale:.2f}")
                        return scale
                    except ValueError:
                        pass
                return 1.0

            else:  # Linux and others
                # Try Xrandr for Linux
                import subprocess
                result = subprocess.run(["xrandr", "--query"],
                                      capture_output=True, text=True, timeout=2)
                if result.returncode == 0:
                    # Parse Xrandr output for DPI
                    for line in result.stdout.split('\n'):
                        if 'connected' in line and 'mm' in line:
                            parts = line.split()
                            for i, part in enumerate(parts):
                                if 'mm' in part and i > 0:
                                    try:
                                        mm = float(part.replace('mm', ''))
                                        px = float(parts[i-1].split('x')[0])
                                        dpi = (px * 25.4) / mm
                                        scale = dpi / 96.0
                                        logger.info(f"Linux DPI detected: {dpi:.0f} (scale={scale:.2f})")
                                        return scale
                                    except (ValueError, IndexError):
                                        continue

                # Fallback: try environment variables
                import os
                scale = float(os.environ.get("QT_SCALE_FACTOR", "1.0"))
                logger.info(f"Linux scale from env: {scale:.2f}")
                return scale

        except Exception as e:
            logger.warning(f"Failed to detect DPI scale: {e}. Using default 1.0")
            return 1.0

    def _load_font_family(self) -> str:
        """Load font family from settings."""
        try:
            config = self.settings.load()
            # Handle case where load() returns bool or dict
            if isinstance(config, bool):
                # Config might not exist yet or load failed, try config object
                config = {"ui": {}}
            elif not isinstance(config, dict):
                config = {"ui": {}}

            ui_config = config.get("ui", {}) if isinstance(config, dict) else {}
            font_family = ui_config.get("font_family") if isinstance(ui_config, dict) else None

            if font_family:
                return font_family

            # Auto-detect system font
            system = platform.system()
            if system == "Windows":
                return self.SYSTEM_FONTS["Windows"]["default"]
            elif system == "Darwin":
                return self.SYSTEM_FONTS["Darwin"]["default"]
            else:
                return self.SYSTEM_FONTS["Linux"]["default"]

        except Exception as e:
            logger.warning(f"Failed to load font family: {e}")
            return "Segoe UI"  # Fallback

    def _load_font_size(self) -> int:
        """Load font size from settings."""
        try:
            config = self.settings.load()
            # Handle case where load() returns bool or dict
            if isinstance(config, bool):
                config = {"ui": {}}
            elif not isinstance(config, dict):
                config = {"ui": {}}

            ui_config = config.get("ui", {}) if isinstance(config, dict) else {}
            font_size = ui_config.get("font_size") if isinstance(ui_config, dict) else None

            if font_size:
                return int(font_size)

            # Calculate based on DPI scale
            base_size = self.SIZE_NORMAL
            return int(base_size * self._dpi_scale)

        except Exception as e:
            logger.warning(f"Failed to load font size: {e}")
            return int(self.SIZE_NORMAL * self._dpi_scale)

    def _save_font_settings(self) -> None:
        """Save font settings to configuration."""
        try:
            config = self.settings.load()
            # Handle case where load() returns bool
            if isinstance(config, bool):
                config = {}
            elif not isinstance(config, dict):
                config = {}

            if "ui" not in config:
                config["ui"] = {}
            config["ui"]["font_family"] = self._font_family
            config["ui"]["font_size"] = self._font_size
            self.settings.save(config)
            logger.info(f"Font settings saved: {self._font_family} {self._font_size}px")
        except Exception as e:
            logger.warning(f"Failed to save font settings: {e}")

    def set_dpg(self, dpg) -> None:
        """
        Set Dear PyGui module reference.

        Args:
            dpg: Dear PyGui module
        """
        self.dpg = dpg
        # Don't load fonts yet - wait for load_fonts() to be called
        # Fonts must be loaded AFTER viewport is created

    def load_fonts(self) -> None:
        """
        Load fonts into Dear PyGui.

        Call this AFTER viewport is created but BEFORE setup_dearpygui().
        """
        if self.dpg and not self._fonts:
            self._load_fonts()

    def _get_font_file_path(self, font_key: str) -> Optional[str]:
        """
        Get the font file path for the current platform.

        Args:
            font_key: Either "default" or "monospace"

        Returns:
            Font file path or None if not found
        """
        system = platform.system()
        platform_key = "Windows" if system == "Windows" else "Darwin" if system == "Darwin" else "Linux"

        font_config = self.SYSTEM_FONTS.get(platform_key, {})
        font_path_key = f"{font_key}_path"
        font_path = font_config.get(font_path_key)

        # Check if font file exists
        if font_path and Path(font_path).exists():
            return font_path

        # Fallback: try common font locations on Windows
        if system == "Windows":
            fonts_dir = Path("C:\\Windows\\Fonts")
            if font_key == "default":
                # Try common fallback fonts
                for font_name in ["segoeui.ttf", "arial.ttf", "tahoma.ttf"]:
                    path = fonts_dir / font_name
                    if path.exists():
                        return str(path)
            elif font_key == "monospace":
                for font_name in ["consola.ttf", "cour.ttf"]:
                    path = fonts_dir / font_name
                    if path.exists():
                        return str(path)

        # No font found - return None to use Dear PyGui default
        logger.warning(f"Font file not found for {font_key} on {system}, using default")
        return None

    def _load_fonts(self) -> None:
        """Load all fonts into Dear PyGui."""
        if not self.dpg:
            logger.warning("Dear PyGui not set, cannot load fonts")
            return

        try:
            # Get font file path
            default_font_path = self._get_font_file_path("default")

            # Only try to load custom fonts if we found a valid font file
            # AND we can successfully load at least one font
            if default_font_path:
                # Try loading one font first to test if it works
                try:
                    # Dear PyGui 2.x: add_font returns font ID, use with_glyph_ranges for extended support
                    # Don't use tag parameter - it can cause issues in some DPG 2.x versions
                    test_font_id = self.dpg.add_font(
                        default_font_path,
                        self.SIZE_NORMAL,
                    )
                    # If successful, delete test font and proceed with full loading
                    self.dpg.delete_item(test_font_id)
                except Exception as test_error:
                    # Font loading failed - use default Dear PyGui font
                    logger.info(f"Custom font loading not supported, using Dear PyGui default: {test_error}")
                    logger.debug(f"Font path was: {default_font_path}")
                    logger.debug(f"Error type: {type(test_error).__name__}")
                    default_font_path = None

            # Load default font with different sizes
            sizes = [
                (self.SIZE_SMALL, "small"),
                (self.SIZE_NORMAL, "normal"),
                (self.SIZE_LARGE, "large"),
                (self.SIZE_HUGE, "huge")
            ]

            # Scale sizes by DPI
            for size, name in sizes:
                scaled_size = int(size * self._dpi_scale)

                # Load default font (use file path if available, otherwise skip)
                if default_font_path:
                    font_id = self.dpg.add_font(
                        default_font_path,
                        scaled_size,
                    )
                    self._fonts[name] = font_id
                    logger.info(f"Loaded font '{name}': {Path(default_font_path).name} {scaled_size}px")
                else:
                    # No font file available - use Dear PyGui default (register with None)
                    # Dear PyGui will use its built-in default font
                    logger.info(f"Using default Dear PyGui font for '{name}' at {scaled_size}px")
                    # Store dummy font ID - Dear PyGui will use default
                    self._fonts[name] = None

            # Load monospace font
            mono_font_path = self._get_font_file_path("monospace")

            if mono_font_path and default_font_path:
                mono_size = int(self.SIZE_SMALL * self._dpi_scale)
                mono_font_id = self.dpg.add_font(
                    mono_font_path,
                    mono_size,
                )
                self._fonts["mono"] = mono_font_id
                logger.info(f"Loaded font 'mono': {Path(mono_font_path).name} {mono_size}px")
            else:
                logger.info("Using default Dear PyGui font for 'mono'")
                self._fonts["mono"] = None

            # Apply default font (only if we have a custom font loaded)
            if self._fonts.get("normal") is not None:
                self.dpg.bind_font(self._fonts["normal"])
            else:
                logger.info("Using Dear PyGui default font")

        except Exception as e:
            logger.error(f"Failed to load fonts: {e}", exc_info=True)
            # Initialize with None so app can still run with default font
            if not self._fonts:
                self._fonts = {"small": None, "normal": None, "large": None, "huge": None, "mono": None}

    def get_font(self, font_name: str) -> Optional[int]:
        """
        Get font ID by name.

        Args:
            font_name: Font name (small, normal, large, huge, mono)

        Returns:
            Font ID or None
        """
        return self._fonts.get(font_name)

    def apply_font_to_item(self, item_tag: str, font_name: str) -> bool:
        """
        Apply font to a UI element.

        Args:
            item_tag: Tag of the UI element
            font_name: Font name (small, normal, large, huge, mono)

        Returns:
            True if successful or using default font
        """
        if not self.dpg:
            logger.warning("Dear PyGui not set")
            return False

        font_id = self._fonts.get(font_name)

        # If font_id is None, we're using Dear PyGui default - that's OK
        if font_id is None:
            logger.debug(f"Using default Dear PyGui font for {item_tag}")
            return True

        if not self.dpg.does_item_exist(item_tag):
            logger.warning(f"Item not found: {item_tag}")
            return False

        try:
            self.dpg.bind_font(item_tag, font_id)
            return True
        except Exception as e:
            logger.error(f"Failed to apply font: {e}")
            return False

    def set_font_family(self, font_family: str) -> None:
        """
        Set font family and reload fonts.

        Args:
            font_family: New font family name
        """
        self._font_family = font_family
        self._save_font_settings()

        if self.dpg:
            # Reload fonts
            self._load_fonts()
            logger.info(f"Font family changed to: {font_family}")

    def set_font_size(self, font_size: int) -> None:
        """
        Set font size and reload fonts.

        Args:
            font_size: New font size
        """
        self._font_size = font_size
        self._save_font_settings()

        if self.dpg:
            # Reload fonts
            self._load_fonts()
            logger.info(f"Font size changed to: {font_size}px")

    def get_dpi_scale(self) -> float:
        """Get DPI scale factor."""
        return self._dpi_scale

    def get_font_family(self) -> str:
        """Get current font family."""
        return self._font_family

    def get_font_size(self) -> int:
        """Get current font size."""
        return self._font_size

    def get_available_fonts(self) -> Dict[str, Dict[str, str]]:
        """
        Get available system fonts.

        Returns:
            Dict mapping platform names to font dicts
        """
        return self.SYSTEM_FONTS.copy()

    def get_font_size_presets(self) -> Dict[str, int]:
        """
        Get available font size presets.

        Returns:
            Dict mapping preset names to sizes
        """
        return {
            "Small": self.SIZE_SMALL,
            "Normal": self.SIZE_NORMAL,
            "Large": self.SIZE_LARGE,
            "Huge": self.SIZE_HUGE
        }
