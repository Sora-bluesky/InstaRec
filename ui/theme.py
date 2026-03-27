"""Design tokens inspired by Apple Human Interface Guidelines.

Principles applied:
- Clarity: Every element serves a purpose. No decoration.
- Deference: UI recedes behind content. Translucent, minimal chrome.
- Depth: Layered surfaces with subtle transparency.
"""


class Colors:
    """Apple HIG-inspired palette with translucent dark surfaces."""

    # Surfaces (frosted glass style)
    SURFACE = "#1E1E1E"
    SURFACE_HOVER = "#2A2A2A"
    SURFACE_PRESSED = "#363636"

    # Accent - recording red (SF Symbols style)
    RED = "#FF3B30"
    RED_HOVER = "#FF6961"

    # Overlay
    OVERLAY_DIM = "#000000"

    # Selection
    SELECTION_BORDER = "#FFFFFF"
    RECORDING_BORDER = "#FF3B30"

    # Text
    TEXT_PRIMARY = "#FFFFFF"
    TEXT_SECONDARY = "#98989D"
    TEXT_TERTIARY = "#636366"

    # Separator
    SEPARATOR = "#38383A"


class Fonts:
    """Typography - clean, system font hierarchy."""

    # Use Segoe UI on Windows (closest to SF Pro)
    FAMILY = "Segoe UI"

    # Size scale (Apple-style: clear hierarchy, generous)
    TITLE = 13
    BODY = 12
    CAPTION = 10
    COUNTDOWN = 72
    TIMER = 13


# Layout constants (generous spacing, Apple-style)
TOOLBAR_HEIGHT = 40
TOOLBAR_PADDING = 6
CORNER_RADIUS = 10
BUTTON_SIZE = 28
ICON_SIZE = 16
HANDLE_SIZE = 8
OVERLAY_ALPHA = 0.4
RECORDING_BORDER_WIDTH = 2
COUNTDOWN_SECONDS = 3
