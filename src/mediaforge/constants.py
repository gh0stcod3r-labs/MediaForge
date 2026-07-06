"""Design constants and theming for MediaForge Organizer."""

# ============================================================================
# Colors
# ============================================================================
# Two palettes are defined below: dark (default) and light. get_stylesheet()
# picks between them based on the requested theme name.

# --- Dark theme (default) ---
PRIMARY_TEXT = "#F3F4F6"
SECONDARY_TEXT = "#C7CBD3"
MUTED_TEXT = "#9AA3AF"

BG_DARK = "#1F2937"
BG_DARKER = "#111827"
BG_SURFACE = "#374151"
BG_CARD = "#25324A"

ACCENT_PRIMARY = "#3B82F6"      # Blue
ACCENT_PRIMARY_HOVER = "#2563EB"
ACCENT_PRIMARY_PRESSED = "#1D4ED8"
ACCENT_SUCCESS = "#10B981"      # Green
ACCENT_WARNING = "#F59E0B"      # Amber
ACCENT_ERROR = "#EF4444"        # Red

BORDER_COLOR = "#4B5563"

# --- Light theme ---
LIGHT_PRIMARY_TEXT = "#111827"
LIGHT_SECONDARY_TEXT = "#374151"
LIGHT_MUTED_TEXT = "#6B7280"

LIGHT_BG_DARK = "#F3F4F6"
LIGHT_BG_DARKER = "#E5E7EB"
LIGHT_BG_SURFACE = "#FFFFFF"
LIGHT_BG_CARD = "#FFFFFF"

LIGHT_ACCENT_PRIMARY = "#2563EB"
LIGHT_ACCENT_PRIMARY_HOVER = "#1D4ED8"
LIGHT_ACCENT_PRIMARY_PRESSED = "#1E40AF"
LIGHT_ACCENT_SUCCESS = "#059669"
LIGHT_ACCENT_WARNING = "#D97706"
LIGHT_ACCENT_ERROR = "#DC2626"

LIGHT_BORDER_COLOR = "#D1D5DB"

# ============================================================================
# Typography
# ============================================================================

# Font Family
FONT_FAMILY = "Segoe UI"

# Font Sizes
HEADER_FONT = 22
TITLE_FONT = 18
SUBTITLE_FONT = 16
BODY_FONT = 14
LIST_ITEM_FONT = 16
LIST_PATH_FONT = 12
SMALL_FONT = 12
TINY_FONT = 10
STATUS_FONT = 11

# Font Weights
FONT_BOLD = 700
FONT_SEMIBOLD = 600
FONT_NORMAL = 400

# ============================================================================
# Spacing
# ============================================================================

# Padding and Margins (in pixels)
SPACING_XS = 4
SPACING_SM = 8
SPACING_MD = 12
SPACING_LG = 16
SPACING_XL = 20
SPACING_2XL = 24
SPACING_3XL = 32

# Common Padding for Components
CARD_PADDING = 20
BUTTON_PADDING = 10
DIALOG_PADDING = 24
INPUT_PADDING = 8

# ============================================================================
# Borders & Radius
# ============================================================================

# Border Radius
CARD_RADIUS = 14
BUTTON_RADIUS = 8
INPUT_RADIUS = 6
SMALL_RADIUS = 4

# Border Width
BORDER_WIDTH = 1
BORDER_WIDTH_THICK = 2

# ============================================================================
# Dimensions
# ============================================================================

# Component Heights
BUTTON_HEIGHT = 40
INPUT_HEIGHT = 36
DIALOG_MIN_WIDTH = 500
DIALOG_MIN_HEIGHT = 300

# Table/List
TABLE_ROW_HEIGHT = 48
TABLE_HEADER_HEIGHT = 40
STATUS_BAR_HEIGHT = 32

# ============================================================================
# Effects
# ============================================================================

# Opacity
OPACITY_DISABLED = 0.5
OPACITY_HOVER = 0.8
OPACITY_ACTIVE = 1.0

# Shadows (for QSS)
SHADOW_SMALL = "0px 1px 2px rgba(0, 0, 0, 0.1)"
SHADOW_MEDIUM = "0px 4px 6px rgba(0, 0, 0, 0.1)"
SHADOW_LARGE = "0px 10px 15px rgba(0, 0, 0, 0.1)"


# ============================================================================
# Theme Generator
# ============================================================================

def get_theme_colors(theme: str = "dark") -> dict:
    """Return the semantic color palette for the requested theme name."""
    if theme == "light":
        return {
            "primary_text": LIGHT_PRIMARY_TEXT,
            "secondary_text": LIGHT_SECONDARY_TEXT,
            "muted_text": LIGHT_MUTED_TEXT,
            "bg_dark": LIGHT_BG_DARK,
            "bg_darker": LIGHT_BG_DARKER,
            "bg_surface": LIGHT_BG_SURFACE,
            "bg_card": LIGHT_BG_CARD,
            "accent_primary": LIGHT_ACCENT_PRIMARY,
            "accent_primary_hover": LIGHT_ACCENT_PRIMARY_HOVER,
            "accent_primary_pressed": LIGHT_ACCENT_PRIMARY_PRESSED,
            "accent_success": LIGHT_ACCENT_SUCCESS,
            "accent_warning": LIGHT_ACCENT_WARNING,
            "accent_error": LIGHT_ACCENT_ERROR,
            "border": LIGHT_BORDER_COLOR,
        }
    return {
        "primary_text": PRIMARY_TEXT,
        "secondary_text": SECONDARY_TEXT,
        "muted_text": MUTED_TEXT,
        "bg_dark": BG_DARK,
        "bg_darker": BG_DARKER,
        "bg_surface": BG_SURFACE,
        "bg_card": BG_CARD,
        "accent_primary": ACCENT_PRIMARY,
        "accent_primary_hover": ACCENT_PRIMARY_HOVER,
        "accent_primary_pressed": ACCENT_PRIMARY_PRESSED,
        "accent_success": ACCENT_SUCCESS,
        "accent_warning": ACCENT_WARNING,
        "accent_error": ACCENT_ERROR,
        "border": BORDER_COLOR,
    }


def get_stylesheet(theme: str = "dark") -> str:
    """Generate the QSS stylesheet from design constants.

    Args:
        theme: "dark" (default) or "light".
    """
    c = get_theme_colors(theme)

    return f"""
    * {{
        background-color: {c['bg_dark']};
        color: {c['primary_text']};
        font-family: '{FONT_FAMILY}';
        font-size: {BODY_FONT}pt;
    }}

    QMainWindow {{
        background-color: {c['bg_darker']};
    }}

    QWidget {{
        background-color: {c['bg_dark']};
        color: {c['primary_text']};
    }}

    QToolTip {{
        background-color: {c['bg_card']};
        color: {c['primary_text']};
        border: {BORDER_WIDTH}px solid {c['border']};
        padding: {SPACING_SM}px;
        border-radius: {SMALL_RADIUS}px;
    }}

    /* --- Branding header --- */
    QLabel#appTitle {{
        color: {c['primary_text']};
        font-size: {HEADER_FONT}pt;
        font-weight: bold;
        background-color: transparent;
    }}

    QLabel#appSubtitle {{
        color: {c['muted_text']};
        font-size: {SMALL_FONT}pt;
        background-color: transparent;
    }}

    QLabel {{
        color: {c['primary_text']};
        background-color: transparent;
    }}

    QLabel#header {{
        color: {c['primary_text']};
        font-size: {SUBTITLE_FONT}pt;
        font-weight: 600;
    }}

    QLabel#secondary {{
        color: {c['secondary_text']};
    }}

    QLabel#muted {{
        color: {c['muted_text']};
    }}

    QLabel#status {{
        color: {c['primary_text']};
        font-size: {STATUS_FONT}pt;
    }}

    /* --- Card sections (group boxes) --- */
    QGroupBox {{
        background-color: {c['bg_card']};
        border: {BORDER_WIDTH}px solid {c['border']};
        border-radius: {CARD_RADIUS}px;
        margin-top: {SPACING_LG}px;
        padding: {SPACING_LG}px {SPACING_LG}px {SPACING_MD}px {SPACING_LG}px;
        font-weight: 600;
    }}

    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: {SPACING_MD}px;
        padding: 0 {SPACING_SM}px;
        color: {c['primary_text']};
        font-size: {SUBTITLE_FONT}pt;
        font-weight: 600;
        background-color: transparent;
    }}

    QPushButton {{
        background-color: {c['accent_primary']};
        color: #FFFFFF;
        border: none;
        border-radius: {BUTTON_RADIUS}px;
        padding: {BUTTON_PADDING}px {BUTTON_PADDING + 4}px;
        font-weight: 600;
        min-height: {BUTTON_HEIGHT}px;
        min-width: 100px;
    }}

    QPushButton:hover {{
        background-color: {c['accent_primary_hover']};
    }}

    QPushButton:pressed {{
        background-color: {c['accent_primary_pressed']};
    }}

    QPushButton:disabled {{
        background-color: {c['bg_surface']};
        color: {c['muted_text']};
    }}

    QPushButton#secondaryButton {{
        background-color: transparent;
        color: {c['primary_text']};
        border: {BORDER_WIDTH}px solid {c['border']};
    }}

    QPushButton#secondaryButton:hover {{
        background-color: {c['bg_surface']};
    }}

    QLineEdit {{
        background-color: {c['bg_surface']};
        color: {c['primary_text']};
        border: {BORDER_WIDTH}px solid {c['border']};
        border-radius: {INPUT_RADIUS}px;
        padding: {INPUT_PADDING}px;
        min-height: {INPUT_HEIGHT}px;
        selection-background-color: {c['accent_primary']};
    }}

    QLineEdit:focus {{
        border: {BORDER_WIDTH_THICK}px solid {c['accent_primary']};
    }}

    QComboBox {{
        background-color: {c['bg_surface']};
        color: {c['primary_text']};
        border: {BORDER_WIDTH}px solid {c['border']};
        border-radius: {INPUT_RADIUS}px;
        padding: {INPUT_PADDING}px;
        min-height: {INPUT_HEIGHT}px;
    }}

    QComboBox:focus {{
        border: {BORDER_WIDTH_THICK}px solid {c['accent_primary']};
    }}

    QComboBox::drop-down {{
        border: none;
        width: 24px;
    }}

    QComboBox QAbstractItemView {{
        background-color: {c['bg_surface']};
        color: {c['primary_text']};
        border: {BORDER_WIDTH}px solid {c['border']};
        selection-background-color: {c['accent_primary']};
    }}

    QCheckBox {{
        color: {c['primary_text']};
        background-color: transparent;
        spacing: {SPACING_MD}px;
    }}

    QCheckBox::indicator {{
        width: {BUTTON_HEIGHT - 20}px;
        height: {BUTTON_HEIGHT - 20}px;
        border: {BORDER_WIDTH}px solid {c['border']};
        border-radius: {SMALL_RADIUS}px;
        background-color: {c['bg_surface']};
    }}

    QCheckBox::indicator:checked {{
        background-color: {c['accent_primary']};
        border: {BORDER_WIDTH}px solid {c['accent_primary']};
    }}

    QTableWidget {{
        background-color: {c['bg_surface']};
        color: {c['primary_text']};
        gridline-color: {c['border']};
        border: {BORDER_WIDTH}px solid {c['border']};
        border-radius: {CARD_RADIUS}px;
        alternate-background-color: {c['bg_dark']};
    }}

    QTableWidget::item {{
        padding: {SPACING_MD}px {SPACING_SM}px;
        border: none;
    }}

    QTableWidget::item:selected {{
        background-color: {c['accent_primary']};
        color: #FFFFFF;
    }}

    QTableWidget::item:hover {{
        background-color: {c['bg_darker']};
    }}

    QHeaderView::section {{
        background-color: {c['bg_darker']};
        color: {c['primary_text']};
        padding: {SPACING_MD}px;
        border: none;
        border-right: {BORDER_WIDTH}px solid {c['border']};
        font-weight: 600;
        font-size: {SMALL_FONT}pt;
    }}

    QProgressBar {{
        background-color: {c['bg_darker']};
        border: {BORDER_WIDTH}px solid {c['border']};
        border-radius: {SMALL_RADIUS}px;
        text-align: center;
        color: {c['primary_text']};
        font-size: {SMALL_FONT}pt;
    }}

    QProgressBar::chunk {{
        background-color: {c['accent_success']};
        border-radius: {SMALL_RADIUS}px;
    }}

    QStatusBar {{
        background-color: {c['bg_darker']};
        color: {c['secondary_text']};
        border-top: {BORDER_WIDTH}px solid {c['border']};
    }}

    QScrollBar:vertical {{
        background: transparent;
        width: 12px;
        margin: 2px;
    }}

    QScrollBar::handle:vertical {{
        background: {c['border']};
        border-radius: 5px;
        min-height: 24px;
    }}

    QScrollBar::handle:vertical:hover {{
        background: {c['muted_text']};
    }}

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}

    QMessageBox {{
        background-color: {c['bg_dark']};
    }}

    QMessageBox QLabel {{
        color: {c['primary_text']};
    }}
    """


def get_color(color_name: str, theme: str = "dark") -> str:
    """Get a color by semantic name for the given theme."""
    colors = get_theme_colors(theme)
    return colors.get(color_name.lower(), colors["primary_text"])
