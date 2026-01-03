"""
Spacing constants for consistent UI layout.

Uses a 4px base unit system for consistent spacing across the application.
"""


class Spacing:
    """
    Spacing constants based on 4px base unit.

    Following modern design systems (Material Design, Ant Design, etc.)
    where spacing is derived from a base unit for consistency.
    """

    # Base spacing units (4px increments)
    XS = 4    # Extra small: 4px
    SM = 8    # Small: 8px
    MD = 16   # Medium: 16px
    LG = 24   # Large: 24px
    XL = 32   # Extra large: 32px
    XXL = 48  # Double extra large: 48px

    # Common layout spacing
    SPACING_TIGHT = SM      # Tight spacing between related items
    SPACING_NORMAL = MD     # Normal spacing between sections
    SPACING_RELAXED = LG    # Relaxed spacing for major sections
    SPACING_LOOSE = XL      # Loose spacing for major breaks

    # Component-specific spacing
    BUTTON_SPACING = SM     # Space between buttons in a group
    INPUT_SPACING = SM      # Space around input fields
    LABEL_SPACING = XS      # Space between label and input
    SECTION_SPACING = LG    # Space between major sections

    # Dialog spacing
    DIALOG_PADDING = LG     # Padding inside dialogs
    DIALOG_SPACING = MD     # Space between dialog elements
    DIALOG_BUTTON_SPACING = SM  # Space between dialog buttons

    # Panel spacing
    PANEL_PADDING = MD      # Padding inside panels
    PANEL_SPACING = SM      # Space between panel elements
    PANEL_SECTION_SPACING = LG  # Space between panel sections

    # Table spacing
    TABLE_ROW_SPACING = XS  # Space between table rows
    TABLE_CELL_SPACING = SM # Space between table cells

    # Toolbar spacing
    TOOLBAR_SPACING = SM    # Space between toolbar items
    TOOLBAR_PADDING = SM    # Padding inside toolbar

    # Menu spacing
    MENU_ITEM_SPACING = SM  # Space between menu items
    MENU_PADDING = SM       # Padding inside menus

    # Form spacing
    FORM_FIELD_SPACING = MD # Space between form fields
    FORM_GROUP_SPACING = LG # Space between form groups

    # Card spacing
    CARD_PADDING = MD       # Padding inside cards
    CARD_SPACING = SM       # Space between cards
    CARD_SECTION_SPACING = MD  # Space between card sections

    # Helper methods
    @staticmethod
    def scale(value: float, factor: float = 1.0) -> int:
        """
        Scale a spacing value by a factor.

        Args:
            value: Base spacing value
            factor: Scale factor (default 1.0)

        Returns:
            Scaled spacing value

        Example:
            Spacing.scale(Spacing.MD, 1.5)  # Returns 24
        """
        return int(value * factor)

    @staticmethod
    def get_spacing(level: str) -> int:
        """
        Get spacing by level name.

        Args:
            level: Spacing level (xs, sm, md, lg, xl, xxl)

        Returns:
            Spacing value in pixels

        Example:
            Spacing.get_spacing("md")  # Returns 16
        """
        spacing_map = {
            "xs": Spacing.XS,
            "sm": Spacing.SM,
            "md": Spacing.MD,
            "lg": Spacing.LG,
            "xl": Spacing.XL,
            "xxl": Spacing.XXL,
        }
        return spacing_map.get(level.lower(), Spacing.MD)
