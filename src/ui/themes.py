"""
UI themes for IDA Plugin Manager.

Defines color schemes and styling for Dear PyGui interface.
"""

from typing import Dict, Tuple


class Theme:
    """Base theme class."""

    @staticmethod
    def get_colors() -> Dict[str, Tuple[int, int, int, int]]:
        """Return theme color dictionary."""
        raise NotImplementedError


class DarkTheme(Theme):
    """Dark theme for the application."""

    @staticmethod
    def get_colors() -> Dict[str, Tuple[int, int, int, int]]:
        """Return dark theme colors."""
        return {
            # Window backgrounds
            "window_bg": (23, 23, 23, 255),
            "child_bg": (30, 30, 30, 255),
            "popup_bg": (30, 30, 30, 255),

            # Text
            "text": (220, 220, 220, 255),
            "text_disabled": (120, 120, 120, 255),

            # Buttons
            "button": (60, 60, 60, 255),
            "button_hovered": (80, 80, 80, 255),
            "button_active": (50, 50, 50, 255),

            # Frames
            "frame_bg": (40, 40, 40, 255),

            # Headers
            "header": (50, 50, 50, 255),
            "header_hovered": (60, 60, 60, 255),
            "header_active": (45, 45, 45, 255),

            # Selection
            "selection": (70, 70, 180, 255),
            "selection_hovered": (80, 80, 190, 255),

            # Title bar
            "title_bg": (20, 20, 20, 255),
            "title_bg_active": (25, 25, 25, 255),

            # Scrollbar
            "scrollbar_bg": (30, 30, 30, 255),
            "scrollbar_grab": (60, 60, 60, 255),
            "scrollbar_grab_hovered": (80, 80, 80, 255),
            "scrollbar_grab_active": (50, 50, 50, 255),

            # Status colors
            "success": (100, 200, 100, 255),
            "warning": (200, 180, 80, 255),
            "error": (200, 80, 80, 255),
            "info": (80, 150, 200, 255),

            # Table
            "table_header_bg": (45, 45, 45, 255),
            "table_border_light": (60, 60, 60, 255),
            "table_border_dark": (40, 40, 40, 255),
            "row_hovered": (50, 50, 50, 255),
            "row_alternate": (35, 35, 35, 255),
        }


class LightTheme(Theme):
    """Light theme for the application."""

    @staticmethod
    def get_colors() -> Dict[str, Tuple[int, int, int, int]]:
        """Return light theme colors."""
        return {
            # Window backgrounds
            "window_bg": (240, 240, 240, 255),
            "child_bg": (245, 245, 245, 255),
            "popup_bg": (250, 250, 250, 255),

            # Text
            "text": (30, 30, 30, 255),
            "text_disabled": (140, 140, 140, 255),

            # Buttons
            "button": (180, 180, 180, 255),
            "button_hovered": (160, 160, 160, 255),
            "button_active": (170, 170, 170, 255),

            # Frames
            "frame_bg": (235, 235, 235, 255),

            # Headers
            "header": (200, 200, 200, 255),
            "header_hovered": (190, 190, 190, 255),
            "header_active": (195, 195, 195, 255),

            # Selection
            "selection": (100, 150, 220, 255),
            "selection_hovered": (110, 160, 230, 255),

            # Title bar
            "title_bg": (220, 220, 220, 255),
            "title_bg_active": (210, 210, 210, 255),

            # Scrollbar
            "scrollbar_bg": (230, 230, 230, 255),
            "scrollbar_grab": (180, 180, 180, 255),
            "scrollbar_grab_hovered": (160, 160, 160, 255),
            "scrollbar_grab_active": (170, 170, 170, 255),

            # Status colors
            "success": (60, 160, 60, 255),
            "warning": (180, 140, 40, 255),
            "error": (180, 60, 60, 255),
            "info": (60, 120, 180, 255),

            # Table
            "table_header_bg": (215, 215, 215, 255),
            "table_border_light": (200, 200, 200, 255),
            "table_border_dark": (220, 220, 220, 255),
            "row_hovered": (230, 230, 230, 255),
            "row_alternate": (245, 245, 245, 255),
        }


def apply_theme(theme_name: str = "Dark") -> None:
    """
    Apply theme to Dear PyGui.

    Args:
        theme_name: Name of theme ("Dark" or "Light")
    """
    try:
        import dearpygui.dearpygui as dpg
    except ImportError:
        return

    theme_class = DarkTheme if theme_name == "Dark" else LightTheme
    colors = theme_class.get_colors()

    # Dear PyGui 2.x uses different color constants
    # Apply global theme with error handling for missing constants
    try:
        with dpg.theme() as global_theme:
            with dpg.theme_component(0, id=dpg.mvReservedUUID_2):  # 0 = dpg.mvAll in DPG 2.x
                # Window colors
                if hasattr(dpg, 'mvStyleVar_WindowPadding'):
                    dpg.add_theme_color(dpg.mvThemeCol_WindowBg, colors["window_bg"])
                if hasattr(dpg, 'mvThemeCol_ChildBg'):
                    dpg.add_theme_color(dpg.mvThemeCol_ChildBg, colors["child_bg"])
                if hasattr(dpg, 'mvThemeCol_PopupBg'):
                    dpg.add_theme_color(dpg.mvThemeCol_PopupBg, colors["popup_bg"])

                # Text colors
                if hasattr(dpg, 'mvThemeCol_Text'):
                    dpg.add_theme_color(dpg.mvThemeCol_Text, colors["text"])
                if hasattr(dpg, 'mvThemeCol_TextDisabled'):
                    dpg.add_theme_color(dpg.mvThemeCol_TextDisabled, colors["text_disabled"])

                # Button colors
                if hasattr(dpg, 'mvThemeCol_Button'):
                    dpg.add_theme_color(dpg.mvThemeCol_Button, colors["button"])
                if hasattr(dpg, 'mvThemeCol_ButtonHovered'):
                    dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, colors["button_hovered"])
                if hasattr(dpg, 'mvThemeCol_ButtonActive'):
                    dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, colors["button_active"])

                # Frame colors
                if hasattr(dpg, 'mvThemeCol_FrameBg'):
                    dpg.add_theme_color(dpg.mvThemeCol_FrameBg, colors["frame_bg"])

                # Header colors
                if hasattr(dpg, 'mvThemeCol_Header'):
                    dpg.add_theme_color(dpg.mvThemeCol_Header, colors["header"])
                if hasattr(dpg, 'mvThemeCol_HeaderHovered'):
                    dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered, colors["header_hovered"])
                if hasattr(dpg, 'mvThemeCol_HeaderActive'):
                    dpg.add_theme_color(dpg.mvThemeCol_HeaderActive, colors["header_active"])

                # Selection colors
                if hasattr(dpg, 'mvThemeCol_CheckMark'):
                    dpg.add_theme_color(dpg.mvThemeCol_CheckMark, colors["selection"])

                # Title bar
                if hasattr(dpg, 'mvThemeCol_TitleBg'):
                    dpg.add_theme_color(dpg.mvThemeCol_TitleBg, colors["title_bg"])
                if hasattr(dpg, 'mvThemeCol_TitleBgActive'):
                    dpg.add_theme_color(dpg.mvThemeCol_TitleBgActive, colors["title_bg_active"])

                # Scrollbar
                if hasattr(dpg, 'mvThemeCol_ScrollbarBg'):
                    dpg.add_theme_color(dpg.mvThemeCol_ScrollbarBg, colors["scrollbar_bg"])
                if hasattr(dpg, 'mvThemeCol_ScrollbarGrab'):
                    dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrab, colors["scrollbar_grab"])
                if hasattr(dpg, 'mvThemeCol_ScrollbarGrabHovered'):
                    dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrabHovered, colors["scrollbar_grab_hovered"])
                if hasattr(dpg, 'mvThemeCol_ScrollbarGrabActive'):
                    dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrabActive, colors["scrollbar_grab_active"])

        dpg.bind_theme(global_theme)
    except Exception as e:
        # If theme application fails, continue without custom theme
        pass


def get_status_color(status: str, theme: str = "Dark") -> Tuple[int, int, int, int]:
    """
    Get color for status message.

    Args:
        status: Status type ("success", "warning", "error", "info")
        theme: Theme name

    Returns:
        RGB color tuple
    """
    theme_class = DarkTheme if theme == "Dark" else LightTheme
    colors = theme_class.get_colors()
    return colors.get(status, colors["info"])
